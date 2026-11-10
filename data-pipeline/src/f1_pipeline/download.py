"""Sottocomando `download`: scarica il dataset Kaggle e ne estrae i CSV.

Scelta tecnica: chiamata HTTP diretta all'API pubblica di Kaggle con la sola
libreria standard, senza il client `kaggle` né `kagglehub`.

- Un solo endpoint serve entrambe le forme di credenziale:
  `GET https://www.kaggle.com/api/v1/datasets/download/<autore>/<dataset>`
  risponde con un reindirizzamento a un URL firmato dello storage, da cui si
  scarica lo zip.
- `KAGGLE_API_TOKEN` (token singolo) viaggia come `Authorization: Bearer`;
  `KAGGLE_USERNAME` + `KAGGLE_KEY` (forma legacy) come HTTP Basic. È lo stesso
  comportamento dei client ufficiali (`kagglesdk.KaggleHttpClient`,
  `kagglehub.clients`), che danno la precedenza al token singolo.
- Nessuna dipendenza in più: i client ufficiali portano con sé `requests`,
  `protobuf` e altro, da tenere compatibili con le versioni fissate
  dall'immagine dei test di accettazione, e una cache propria da cui i file
  andrebbero poi copiati.

Le credenziali si leggono solo da variabili d'ambiente e non compaiono mai nei
messaggi: l'intestazione di autenticazione va al solo host di Kaggle (non segue
il reindirizzamento) e degli URL si stampa soltanto il nome dell'host, perché
quello di destinazione contiene una firma.
"""

from __future__ import annotations

import base64
import http.client
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

DATASET = "rohanrao/formula-1-world-championship-1950-2020"
URL_API = "https://www.kaggle.com/api/v1/datasets/download/" + DATASET
URL_PAGINA = "https://www.kaggle.com/datasets/" + DATASET

VAR_SINGOLO = "KAGGLE_API_TOKEN"
VAR_UTENTE = "KAGGLE_USERNAME"
VAR_CHIAVE = "KAGGLE_KEY"

# Generico di proposito: nessun dato del progetto o dell'utente verso l'esterno.
USER_AGENT = "dataset-downloader/1.0 (python-urllib)"

TIMEOUT_SECONDI = 60
TENTATIVI = 3
ATTESA_SECONDI = 3.0
_BLOCCO = 1024 * 1024

ALTERNATIVA_MANUALE = (
    "In alternativa scarica lo zip a mano dalla pagina del dataset\n"
    f"  {URL_PAGINA}\n"
    "e scompattalo in data-pipeline/raw/ (i file .csv direttamente nella cartella)."
)


class ErroreDownload(Exception):
    """Errore previsto: il messaggio è già pronto per l'utente."""


@dataclass(frozen=True, repr=False)
class Credenziali:
    """Credenziali Kaggle. `repr` e `str` non mostrano mai il segreto."""

    forma: str  # nome leggibile della forma usata, senza valori
    _intestazione: str

    def intestazione(self) -> str:
        return self._intestazione

    def __repr__(self) -> str:
        return f"Credenziali(forma={self.forma!r}, valore=<nascosto>)"


def _valore(ambiente: Mapping[str, str], nome: str) -> str:
    """Valore ripulito: spazi e a capo ai bordi, virgolette di contorno.

    Le virgolette restano nel valore quando il file delle variabili è passato
    a Docker senza l'interpretazione di Compose (`NOME="valore"`).
    """
    valore = (ambiente.get(nome) or "").strip()
    if len(valore) >= 2 and valore[0] == valore[-1] and valore[0] in "\"'":
        valore = valore[1:-1].strip()
    return valore


def _controlla_caratteri(nome: str, valore: str) -> None:
    if not valore.isascii() or any(
        c.isspace() or not c.isprintable() for c in valore
    ):
        raise ErroreDownload(
            f"Il valore di {nome} contiene spazi, a capo o caratteri non ASCII: "
            "ricopialo dalla pagina delle impostazioni di Kaggle senza altro testo."
        )


def leggi_credenziali(ambiente: Mapping[str, str] | None = None) -> Credenziali | None:
    """Legge le credenziali dall'ambiente; `None` se non ce ne sono.

    Il token singolo ha la precedenza sulla coppia legacy, come nei client
    ufficiali. Una coppia a metà è un errore esplicito.
    """
    if ambiente is None:
        ambiente = os.environ
    token = _valore(ambiente, VAR_SINGOLO)
    utente = _valore(ambiente, VAR_UTENTE)
    chiave = _valore(ambiente, VAR_CHIAVE)

    if token:
        _controlla_caratteri(VAR_SINGOLO, token)
        return Credenziali(VAR_SINGOLO, f"Bearer {token}")
    if utente and chiave:
        _controlla_caratteri(VAR_UTENTE, utente)
        _controlla_caratteri(VAR_CHIAVE, chiave)
        coppia = base64.b64encode(f"{utente}:{chiave}".encode()).decode("ascii")
        return Credenziali(f"{VAR_UTENTE} + {VAR_CHIAVE}", f"Basic {coppia}")
    if utente or chiave:
        presente, mancante = (
            (VAR_UTENTE, VAR_CHIAVE) if utente else (VAR_CHIAVE, VAR_UTENTE)
        )
        raise ErroreDownload(
            f"Credenziali Kaggle incomplete: {presente} è impostata ma "
            f"{mancante} è vuota o assente.\n"
            f"Imposta entrambe, oppure usa il token singolo {VAR_SINGOLO}."
        )
    return None


def messaggio_credenziali_mancanti() -> str:
    return (
        "Credenziali Kaggle non trovate nelle variabili d'ambiente.\n"
        "Imposta UNA delle due forme (vedi .env.example):\n"
        f"  - {VAR_SINGOLO}  (token singolo, da https://www.kaggle.com/settings/api)\n"
        f"  - {VAR_UTENTE} e {VAR_CHIAVE}  (forma legacy)\n" + ALTERNATIVA_MANUALE
    )


def csv_presenti(cartella: Path) -> list[Path]:
    if not cartella.is_dir():
        return []
    return sorted(
        p for p in cartella.iterdir() if p.is_file() and p.suffix.lower() == ".csv"
    )


def _host(url: str) -> str:
    return urlsplit(url).hostname or "host sconosciuto"


def _messaggio_del_server(errore: urllib.error.HTTPError) -> str:
    """Campo `message` della risposta JSON di Kaggle, se c'è."""
    try:
        corpo = errore.read(4096)
        dati = json.loads(corpo.decode("utf-8", "replace"))
        testo = dati.get("message") if isinstance(dati, dict) else None
    except Exception:  # noqa: BLE001 - il corpo è solo un aiuto in più
        return ""
    if not isinstance(testo, str) or not testo.strip():
        return ""
    return f"\nRisposta del server: {testo.strip()[:300]}"


def _traduci_errore_http(
    errore: urllib.error.HTTPError, url_richiesto: str, forma: str | None
) -> ErroreDownload:
    codice = errore.code
    # Dopo il reindirizzamento l'errore arriva dallo storage, non da Kaggle.
    host_richiesto = _host(url_richiesto)
    host_errore = _host(errore.url or url_richiesto)
    usate = f" (forma usata: {forma})" if forma else ""
    dettaglio = _messaggio_del_server(errore)

    if host_errore != host_richiesto:
        dettaglio = ""  # il corpo dello storage può citare l'URL firmato
        testo = (
            "Kaggle ha accettato la richiesta, ma lo scaricamento dello zip da "
            f"{host_errore} è fallito con HTTP {codice}. Di solito è temporaneo: "
            "riprova tra qualche minuto."
        )
    elif codice == 401:
        testo = (
            f"Kaggle ha rifiutato le credenziali (HTTP 401){usate}.\n"
            "Il token o la chiave sono errati, scaduti o revocati: generane di "
            "nuovi su https://www.kaggle.com/settings/api e aggiorna le variabili "
            f"{VAR_SINGOLO} oppure {VAR_UTENTE} + {VAR_CHIAVE}."
        )
    elif codice == 403:
        testo = (
            f"Kaggle ha negato l'accesso al dataset (HTTP 403){usate}.\n"
            "Cause possibili: l'account non ha i permessi (account non "
            "verificato, token senza accesso ai dataset), oppure il dataset "
            f"{DATASET} è stato rinominato o rimosso (Kaggle risponde 403 anche "
            f"in quel caso). Controlla dal browser: {URL_PAGINA}"
        )
    elif codice == 404:
        testo = (
            f"Dataset non trovato (HTTP 404): {DATASET}.\n"
            f"Potrebbe essere stato rinominato o rimosso. Controlla: {URL_PAGINA}"
        )
    elif codice == 429:
        testo = (
            "Troppe richieste a Kaggle (HTTP 429): attendi qualche minuto e riprova."
        )
    elif codice >= 500:
        testo = (
            f"Kaggle non è disponibile in questo momento (HTTP {codice}): "
            "riprova più tardi."
        )
    else:
        testo = f"Richiesta a {host_errore} fallita con HTTP {codice}."
    return ErroreDownload(f"{testo}{dettaglio}\n{ALTERNATIVA_MANUALE}")


def _scarica_una_volta(richiesta: urllib.request.Request, destinazione: Path) -> int:
    with urllib.request.urlopen(richiesta, timeout=TIMEOUT_SECONDI) as risposta:  # noqa: S310
        attesi = risposta.headers.get("Content-Length")
        scritti = 0
        with destinazione.open("wb") as uscita:
            while blocco := risposta.read(_BLOCCO):
                uscita.write(blocco)
                scritti += len(blocco)
    if attesi is not None and attesi.isdigit() and int(attesi) != scritti:
        raise urllib.error.URLError(
            f"scaricamento interrotto ({scritti} byte su {attesi})"
        )
    return scritti


def scarica_zip(
    url: str,
    destinazione: Path,
    credenziali: Credenziali | None,
    *,
    tentativi: int = TENTATIVI,
    attesa: float = ATTESA_SECONDI,
    avviso: Callable[[str], None] = lambda _testo: None,
) -> int:
    """Scarica `url` in `destinazione` seguendo i reindirizzamenti.

    Restituisce i byte scritti. Riprova sugli errori temporanei (rete, 5xx);
    gli altri errori HTTP diventano subito un `ErroreDownload` leggibile.
    """
    forma = credenziali.forma if credenziali else None
    ultimo: Exception | None = None
    for tentativo in range(1, tentativi + 1):
        richiesta = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        if credenziali is not None:
            # "Unredirected": l'intestazione non segue il reindirizzamento verso
            # lo storage, che è un altro host e usa un URL già firmato.
            richiesta.add_unredirected_header(
                "Authorization", credenziali.intestazione()
            )
        try:
            return _scarica_una_volta(richiesta, destinazione)
        except urllib.error.HTTPError as errore:
            if errore.code < 500 or tentativo == tentativi:
                raise _traduci_errore_http(errore, url, forma) from None
            ultimo = errore
        except (
            urllib.error.URLError,
            http.client.HTTPException,
            TimeoutError,
            ConnectionError,
        ) as errore:
            ultimo = errore
            if tentativo == tentativi:
                break
        avviso(f"Tentativo {tentativo} di {tentativi} fallito, riprovo...")
        time.sleep(attesa)

    motivo = getattr(ultimo, "reason", ultimo)
    raise ErroreDownload(
        f"Impossibile scaricare da {_host(url)}: {motivo}.\n"
        "Controlla la connessione di rete (o il proxy) e riprova.\n"
        + ALTERNATIVA_MANUALE
    ) from None


def estrai_csv(archivio: Path, cartella: Path) -> list[str]:
    """Estrae i soli `.csv` dello zip direttamente in `cartella`.

    I percorsi interni si appiattiscono al nome del file (nessun percorso
    dello zip può uscire dalla cartella). Si estrae prima in una cartella
    temporanea e si sposta alla fine, così un archivio guasto non lascia la
    destinazione a metà.
    """
    if not zipfile.is_zipfile(archivio):
        raise ErroreDownload(
            "Il file scaricato non è un archivio zip valido "
            f"({archivio.stat().st_size} byte): la risposta non era il dataset.\n"
            + ALTERNATIVA_MANUALE
        )
    cartella.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archivio) as zf:
            membri: dict[str, zipfile.ZipInfo] = {}
            for info in zf.infolist():
                percorso = PurePosixPath(info.filename.replace("\\", "/"))
                nome = percorso.name
                if info.is_dir() or not nome.lower().endswith(".csv"):
                    continue
                if nome.startswith(".") or "__MACOSX" in percorso.parts:
                    continue
                if nome in membri:
                    raise ErroreDownload(
                        f"L'archivio contiene due file con lo stesso nome: {nome}."
                    )
                membri[nome] = info
            if not membri:
                raise ErroreDownload(
                    "L'archivio scaricato non contiene file .csv.\n"
                    + ALTERNATIVA_MANUALE
                )
            with tempfile.TemporaryDirectory(
                dir=cartella, prefix=".estrazione-"
            ) as tmp:
                for nome, info in sorted(membri.items()):
                    with zf.open(info) as sorgente, (Path(tmp) / nome).open(
                        "wb"
                    ) as uscita:
                        shutil.copyfileobj(sorgente, uscita)
                for nome in sorted(membri):
                    os.replace(Path(tmp) / nome, cartella / nome)
    except (zipfile.BadZipFile, EOFError) as errore:
        raise ErroreDownload(
            f"Archivio zip danneggiato ({errore}): riprova il download.\n"
            + ALTERNATIVA_MANUALE
        ) from None
    return sorted(membri)


def esegui(
    cartella: Path,
    *,
    force: bool = False,
    ambiente: Mapping[str, str] | None = None,
    url: str = URL_API,
    tentativi: int = TENTATIVI,
    attesa: float = ATTESA_SECONDI,
) -> int:
    """Logica del sottocomando. Restituisce il codice di uscita."""

    def avviso(testo: str) -> None:
        print(testo, file=sys.stderr, flush=True)

    try:
        presenti = csv_presenti(cartella)
        if presenti and not force:
            print(
                f"{cartella} contiene già {len(presenti)} file CSV: download "
                "saltato. Usa --force per riscaricare e sovrascrivere."
            )
            return 0

        credenziali = leggi_credenziali(ambiente)
        if credenziali is None:
            avviso("Errore: " + messaggio_credenziali_mancanti())
            return 1

        try:
            cartella.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=cartella, prefix=".download-") as tmp:
                archivio = Path(tmp) / "dataset.zip"
                avviso(
                    f"Scarico {DATASET} da {_host(url)} "
                    f"(credenziali: {credenziali.forma})..."
                )
                scritti = scarica_zip(
                    url,
                    archivio,
                    credenziali,
                    tentativi=tentativi,
                    attesa=attesa,
                    avviso=avviso,
                )
                avviso(f"Scaricati {scritti / 1e6:.1f} MB, estraggo i CSV...")
                nomi = estrai_csv(archivio, cartella)
        except OSError as errore:
            raise ErroreDownload(
                f"Impossibile scrivere in {cartella}: {errore.strerror or errore}."
            ) from None
    except ErroreDownload as errore:
        avviso(f"Errore: {errore}")
        return 1

    print(f"{len(nomi)} file CSV in {cartella}: {', '.join(nomi)}")
    return 0
