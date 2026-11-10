"""Test del sottocomando `download`, senza rete esterna.

Kaggle è sostituito da un server HTTP locale che si comporta come l'API vera:
l'endpoint risponde con un reindirizzamento verso lo "storage", che serve lo
zip. Le credenziali sono valori finti scritti qui.
"""

from __future__ import annotations

import base64
import io
import json
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from f1_pipeline import cli
from f1_pipeline import download as dl

TOKEN_FINTO = "KGAT_segretissimo0123456789"
UTENTE_FINTO = "pilota-di-prova"
CHIAVE_FINTA = "chiave-segreta-abcdef"
SEGRETI = (
    TOKEN_FINTO,
    CHIAVE_FINTA,
    base64.b64encode(f"{UTENTE_FINTO}:{CHIAVE_FINTA}".encode()).decode(),
)

CSV_FINTI = {
    "races.csv": "raceId,year,round\n1,2024,1\n",
    "results.csv": "resultId,raceId,driverId\n10,1,7\n",
}


def crea_zip(file: dict[str, str]) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome, testo in file.items():
            zf.writestr(nome, testo)
    return memoria.getvalue()


class KaggleFinto:
    """Server locale: registra le richieste e risponde secondo il percorso."""

    def __init__(self) -> None:
        self.zip = crea_zip(CSV_FINTI)
        self.richieste: list[tuple[str, str | None]] = []  # (percorso, Authorization)
        self.guasti_residui = 0
        finto = self

        class Gestore(BaseHTTPRequestHandler):
            def log_message(self, *args):  # silenzio nei test
                pass

            def _rispondi(self, codice, corpo=b"", tipo="application/json", extra=()):
                self.send_response(codice)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(corpo)))
                for nome, valore in extra:
                    self.send_header(nome, valore)
                self.end_headers()
                self.wfile.write(corpo)

            def do_GET(self):
                percorso = self.path.split("?")[0]
                finto.richieste.append((percorso, self.headers.get("Authorization")))
                if percorso == "/api/download":
                    self._rispondi(
                        302, extra=[("Location", "/storage/archive.zip?firma=XYZ")]
                    )
                elif percorso == "/storage/archive.zip":
                    self._rispondi(200, finto.zip, "application/zip")
                elif percorso.startswith("/errore/"):
                    codice = int(percorso.rsplit("/", 1)[1])
                    corpo = json.dumps(
                        {"code": codice, "message": "messaggio del server"}
                    ).encode()
                    self._rispondi(codice, corpo)
                elif percorso == "/pagina-html":
                    self._rispondi(200, b"<html>Accedi</html>", "text/html")
                elif percorso == "/instabile":
                    if finto.guasti_residui > 0:
                        finto.guasti_residui -= 1
                        self._rispondi(503, b"{}")
                    else:
                        self._rispondi(200, finto.zip, "application/zip")
                else:
                    self._rispondi(404, b"{}")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Gestore)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def chiudi(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def kaggle(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.setenv("no_proxy", "*")
    finto = KaggleFinto()
    yield finto
    finto.chiudi()


@pytest.fixture
def ambiente_pulito(monkeypatch):
    for nome in (dl.VAR_SINGOLO, dl.VAR_UTENTE, dl.VAR_CHIAVE):
        monkeypatch.delenv(nome, raising=False)


def assert_nessun_segreto(*testi: str) -> None:
    for testo in testi:
        for segreto in SEGRETI:
            assert segreto not in testo


# --- credenziali -----------------------------------------------------------


def test_senza_credenziali_fallisce_con_messaggio_chiaro(
    tmp_path, capsys, ambiente_pulito
):
    cartella = tmp_path / "raw"
    assert cli.main(["download", "--output", str(cartella)]) != 0
    catturato = capsys.readouterr()
    assert catturato.out == ""
    for atteso in (
        "KAGGLE_API_TOKEN",
        "KAGGLE_USERNAME",
        "KAGGLE_KEY",
        "data-pipeline/raw/",
        "kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020",
    ):
        assert atteso in catturato.err
    assert csv_in(cartella) == []


def test_variabili_vuote_valgono_come_assenti(tmp_path, capsys):
    # Docker Compose passa stringhe vuote per le variabili non impostate.
    ambiente = {dl.VAR_SINGOLO: "", dl.VAR_UTENTE: "  ", dl.VAR_CHIAVE: ""}
    assert dl.leggi_credenziali(ambiente) is None
    assert dl.esegui(tmp_path / "raw", ambiente=ambiente) != 0
    assert "Credenziali Kaggle non trovate" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("ambiente", "mancante"),
    [
        ({dl.VAR_UTENTE: UTENTE_FINTO}, dl.VAR_CHIAVE),
        ({dl.VAR_CHIAVE: CHIAVE_FINTA}, dl.VAR_UTENTE),
    ],
)
def test_coppia_legacy_a_meta(tmp_path, capsys, ambiente, mancante):
    assert dl.esegui(tmp_path / "raw", ambiente=ambiente) != 0
    errore = capsys.readouterr().err
    assert "incomplete" in errore
    assert mancante in errore
    assert_nessun_segreto(errore)


def test_token_singolo_diventa_bearer():
    credenziali = dl.leggi_credenziali({dl.VAR_SINGOLO: f"  {TOKEN_FINTO}\n"})
    assert credenziali.intestazione() == f"Bearer {TOKEN_FINTO}"


def test_coppia_legacy_diventa_basic():
    credenziali = dl.leggi_credenziali(
        {dl.VAR_UTENTE: UTENTE_FINTO, dl.VAR_CHIAVE: f'"{CHIAVE_FINTA}"'}
    )
    tipo, valore = credenziali.intestazione().split(" ")
    assert tipo == "Basic"
    assert base64.b64decode(valore).decode() == f"{UTENTE_FINTO}:{CHIAVE_FINTA}"


def test_il_token_singolo_ha_la_precedenza():
    credenziali = dl.leggi_credenziali(
        {
            dl.VAR_SINGOLO: TOKEN_FINTO,
            dl.VAR_UTENTE: UTENTE_FINTO,
            dl.VAR_CHIAVE: CHIAVE_FINTA,
        }
    )
    assert credenziali.intestazione().startswith("Bearer ")


def test_credenziali_non_stampabili():
    credenziali = dl.leggi_credenziali({dl.VAR_SINGOLO: TOKEN_FINTO})
    assert_nessun_segreto(repr(credenziali), str(credenziali), f"{credenziali}")


def test_token_con_spazi_interni_rifiutato_senza_mostrarlo(tmp_path, capsys):
    ambiente = {dl.VAR_SINGOLO: "KGAT_meta segreta-con-spazio"}
    assert dl.esegui(tmp_path / "raw", ambiente=ambiente) != 0
    errore = capsys.readouterr().err
    assert dl.VAR_SINGOLO in errore
    assert "segreta-con-spazio" not in errore


# --- cartella già popolata -------------------------------------------------


def csv_in(cartella):
    return [p.name for p in dl.csv_presenti(cartella)]


def test_cartella_gia_popolata_non_riscarica(tmp_path, capsys, kaggle):
    (tmp_path / "races.csv").write_text("contenuto locale\n")
    codice = dl.esegui(
        tmp_path, ambiente={dl.VAR_SINGOLO: TOKEN_FINTO}, url=kaggle.base + "/api/download"
    )
    assert codice == 0
    assert kaggle.richieste == []
    assert (tmp_path / "races.csv").read_text() == "contenuto locale\n"
    assert "--force" in capsys.readouterr().out


def test_cartella_gia_popolata_non_richiede_credenziali(
    tmp_path, capsys, ambiente_pulito
):
    (tmp_path / "races.csv").write_text("contenuto locale\n")
    assert cli.main(["download", "--output", str(tmp_path)]) == 0
    assert capsys.readouterr().err == ""


def test_force_riscarica_e_sovrascrive(tmp_path, capsys, kaggle):
    (tmp_path / "races.csv").write_text("contenuto locale\n")
    codice = dl.esegui(
        tmp_path,
        force=True,
        ambiente={dl.VAR_SINGOLO: TOKEN_FINTO},
        url=kaggle.base + "/api/download",
    )
    assert codice == 0
    assert (tmp_path / "races.csv").read_text() == CSV_FINTI["races.csv"]


def test_force_arriva_dalla_riga_di_comando(tmp_path, monkeypatch):
    visti = {}

    def finto(cartella, *, force=False, **_altro):
        visti["force"] = force
        return 0

    monkeypatch.setattr(dl, "esegui", finto)
    assert cli.main(["download", "--output", str(tmp_path), "--force"]) == 0
    assert visti == {"force": True}


# --- download ed estrazione ------------------------------------------------


@pytest.mark.parametrize(
    ("ambiente", "intestazione_attesa"),
    [
        ({dl.VAR_SINGOLO: TOKEN_FINTO}, f"Bearer {TOKEN_FINTO}"),
        (
            {dl.VAR_UTENTE: UTENTE_FINTO, dl.VAR_CHIAVE: CHIAVE_FINTA},
            "Basic "
            + base64.b64encode(f"{UTENTE_FINTO}:{CHIAVE_FINTA}".encode()).decode(),
        ),
    ],
    ids=["token-singolo", "coppia-legacy"],
)
def test_download_completo(tmp_path, capsys, kaggle, ambiente, intestazione_attesa):
    cartella = tmp_path / "nuova" / "raw"  # non esiste ancora
    codice = dl.esegui(cartella, ambiente=ambiente, url=kaggle.base + "/api/download")
    catturato = capsys.readouterr()
    assert codice == 0, catturato.err

    # I CSV direttamente nella cartella, e nient'altro (zip e temporanei rimossi).
    assert sorted(p.name for p in cartella.iterdir()) == sorted(CSV_FINTI)
    for nome, testo in CSV_FINTI.items():
        assert (cartella / nome).read_text() == testo

    # Le credenziali vanno all'API e NON seguono il reindirizzamento allo storage.
    assert kaggle.richieste == [
        ("/api/download", intestazione_attesa),
        ("/storage/archive.zip", None),
    ]
    assert_nessun_segreto(catturato.out, catturato.err)
    assert "firma" not in catturato.out + catturato.err


def test_estrazione_appiattisce_e_ignora_il_resto(tmp_path):
    archivio = tmp_path / "a.zip"
    archivio.write_bytes(
        crea_zip(
            {
                "cartella/races.csv": "a\n1\n",
                "LEGGIMI.txt": "non serve",
                "__MACOSX/cartella/._races.csv": "spazzatura",
                "../../fuori.csv": "b\n2\n",
            }
        )
    )
    cartella = tmp_path / "raw"
    assert dl.estrai_csv(archivio, cartella) == ["fuori.csv", "races.csv"]
    assert sorted(p.name for p in cartella.iterdir()) == ["fuori.csv", "races.csv"]
    assert not (tmp_path / "fuori.csv").exists()
    assert not (tmp_path.parent / "fuori.csv").exists()


def test_zip_senza_csv(tmp_path):
    archivio = tmp_path / "a.zip"
    archivio.write_bytes(crea_zip({"LEGGIMI.txt": "niente dati"}))
    with pytest.raises(dl.ErroreDownload, match="non contiene file .csv"):
        dl.estrai_csv(archivio, tmp_path / "raw")


def test_risposta_che_non_e_uno_zip(tmp_path, capsys, kaggle):
    cartella = tmp_path / "raw"
    codice = dl.esegui(
        cartella, ambiente={dl.VAR_SINGOLO: TOKEN_FINTO}, url=kaggle.base + "/pagina-html"
    )
    assert codice != 0
    assert "non è un archivio zip valido" in capsys.readouterr().err
    assert list(cartella.iterdir()) == []


# --- errori HTTP e di rete -------------------------------------------------


@pytest.mark.parametrize(
    ("codice_http", "atteso"),
    [
        (401, "rifiutato le credenziali"),
        (403, "negato l'accesso"),
        (404, "Dataset non trovato"),
        (429, "Troppe richieste"),
    ],
)
def test_errori_http_tradotti(tmp_path, capsys, kaggle, codice_http, atteso):
    cartella = tmp_path / "raw"
    codice = dl.esegui(
        cartella,
        ambiente={dl.VAR_SINGOLO: TOKEN_FINTO},
        url=f"{kaggle.base}/errore/{codice_http}",
    )
    catturato = capsys.readouterr()
    assert codice != 0
    assert catturato.out == ""
    assert atteso in catturato.err
    assert f"HTTP {codice_http}" in catturato.err
    assert "messaggio del server" in catturato.err
    assert "data-pipeline/raw/" in catturato.err  # alternativa manuale
    assert "Traceback" not in catturato.err
    assert_nessun_segreto(catturato.err)
    assert len(kaggle.richieste) == 1  # nessun nuovo tentativo sugli errori 4xx
    assert list(cartella.iterdir()) == []


def test_errore_temporaneo_si_riprova(tmp_path, capsys, kaggle):
    kaggle.guasti_residui = 2
    codice = dl.esegui(
        tmp_path / "raw",
        ambiente={dl.VAR_SINGOLO: TOKEN_FINTO},
        url=kaggle.base + "/instabile",
        attesa=0,
    )
    assert codice == 0, capsys.readouterr().err
    assert len(kaggle.richieste) == 3


def test_errore_5xx_persistente(tmp_path, capsys, kaggle):
    codice = dl.esegui(
        tmp_path / "raw",
        ambiente={dl.VAR_SINGOLO: TOKEN_FINTO},
        url=kaggle.base + "/errore/503",
        tentativi=2,
        attesa=0,
    )
    assert codice != 0
    assert "HTTP 503" in capsys.readouterr().err
    assert len(kaggle.richieste) == 2


def test_server_irraggiungibile(tmp_path, capsys, kaggle):
    url = kaggle.base + "/api/download"
    kaggle.chiudi()  # la porta ora rifiuta le connessioni
    codice = dl.esegui(
        tmp_path / "raw",
        ambiente={dl.VAR_UTENTE: UTENTE_FINTO, dl.VAR_CHIAVE: CHIAVE_FINTA},
        url=url,
        tentativi=2,
        attesa=0,
    )
    catturato = capsys.readouterr()
    assert codice != 0
    assert "Impossibile scaricare da 127.0.0.1" in catturato.err
    assert "Traceback" not in catturato.err
    assert_nessun_segreto(catturato.err)
