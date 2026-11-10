"""Sottocomando `transform`: CSV Kaggle/Ergast -> Parquet per tabella + report.

Un file `<tabella>.parquet` per tabella dello schema; `results` è divisa in
`results.parquet` (gare) e `sprint_results.parquet` (sprint).

Regole (docs/modello-dati.md, "Corrispondenza CSV -> tabelle"):

- una riga si **scarta** (e finisce in `scarti.json` con il motivo) per: chiave
  mancante, tipo non valido o valore fuori dai vincoli su una chiave o su un
  campo obbligatorio, duplicato (si tiene la prima riga valida), riferimento a
  un'entità inesistente o scartata; un giro o una sosta si scartano anche
  quando il pilota non ha un risultato valido in quella gara;
- un **attributo facoltativo** non valido o fuori dai vincoli diventa NULL: la
  riga resta, e la correzione finisce in `valori_annullati.json`;
- la **posizione derivata**: `positionText` decide l'esito di un risultato.
  Se è un intero positivo il pilota è `classified`; quando la colonna
  `position` manca o non è valida, la posizione si ricava da `positionText`
  (docs/modello-dati.md, "Esito e posizione"). Non è uno scarto né un
  annullamento: finisce in `valori_derivati.json`. Se entrambe sono
  valorizzate vale `position`. Una lettera nota con `position` valorizzata,
  una lettera sconosciuta o un numero non positivo restano scarti;
- tutto ciò che il database rifiuterebbe si intercetta qui: `load` non deve
  mai fallire su un vincolo.

L'output è deterministico al byte: righe ordinate per chiave, compressione e
opzioni di scrittura fissate, nessun timestamp né metadato d'ambiente.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from f1_pipeline import normalizza as nz
from f1_pipeline.csvio import ErroreInput, leggi_csv
from f1_pipeline.tabelle import FILE_ANNULLATI, FILE_DERIVATI, FILE_SCARTI, PER_NOME, TABELLE

# positionText non numerico -> outcome. Un valore numerico vale "classified".
ESITI = {
    "R": "retired",
    "D": "disqualified",
    "E": "excluded",
    "W": "withdrawn",
    "F": "failed_to_qualify",
    "N": "not_classified",
}

# Sessioni diverse dalla gara: tipo nello schema -> prefisso delle colonne di races.csv.
SESSIONI_SECONDARIE = (
    ("fp1", "fp1"),
    ("fp2", "fp2"),
    ("fp3", "fp3"),
    ("qualifying", "quali"),
    ("sprint", "sprint"),
)

# Colonne che devono comparire nell'intestazione. Quelle che variano tra le
# versioni del dataset (rank e fastestLapSpeed in sprint_results.csv, date
# delle sessioni in races.csv) sono lette se presenti.
COLONNE = {
    "seasons.csv": ("year", "url"),
    "circuits.csv": (
        "circuitId", "circuitRef", "name", "location", "country", "lat", "lng", "alt", "url",
    ),
    "drivers.csv": (
        "driverId", "driverRef", "number", "code", "forename", "surname", "dob",
        "nationality", "url",
    ),
    "constructors.csv": ("constructorId", "constructorRef", "name", "nationality", "url"),
    "status.csv": ("statusId", "status"),
    "races.csv": ("raceId", "year", "round", "circuitId", "name", "date", "time", "url"),
    "results.csv": (
        "resultId", "raceId", "driverId", "constructorId", "number", "grid", "position",
        "positionText", "positionOrder", "points", "laps", "milliseconds", "fastestLap",
        "fastestLapTime", "statusId",
    ),
    "qualifying.csv": (
        "raceId", "driverId", "constructorId", "number", "position", "q1", "q2", "q3",
    ),
    "lap_times.csv": ("raceId", "driverId", "lap", "position", "milliseconds"),
    "pit_stops.csv": ("raceId", "driverId", "stop", "lap", "time", "milliseconds"),
}
COLONNE["sprint_results.csv"] = COLONNE["results.csv"]

# Senza questi file non esiste un dataset; gli altri, se assenti, valgono come vuoti.
FILE_OBBLIGATORI = (
    "seasons.csv", "circuits.csv", "drivers.csv", "constructors.csv", "status.csv",
    "races.csv", "results.csv",
)


class Scarto(Exception):
    """La riga corrente va scartata: il messaggio è il motivo."""


@dataclass
class Rapporto:
    scarti: list[dict[str, Any]] = field(default_factory=list)
    annullati: list[dict[str, Any]] = field(default_factory=list)
    derivati: list[dict[str, Any]] = field(default_factory=list)

    def scarta(self, file: str, riga: int, motivo: str) -> None:
        self.scarti.append({"file": file, "riga": riga, "motivo": motivo})


@dataclass
class Esito:
    righe: dict[str, int]
    scarti: list[dict[str, Any]]
    annullati: list[dict[str, Any]]
    derivati: list[dict[str, Any]] = field(default_factory=list)


class Riga:
    """Un record di un CSV con le conversioni e le regole di scarto."""

    __slots__ = ("file", "numero", "valori", "annullati", "extra")

    def __init__(self, file: str, numero: int, valori: dict[str, str]) -> None:
        self.file = file
        self.numero = numero
        self.valori = valori
        self.annullati: list[dict[str, Any]] = []
        self.extra: Any = None

    def testo(self, colonna: str) -> str | None:
        return nz.pulisci(self.valori.get(colonna))

    def chiave(self, colonna: str, minimo: int | None = None) -> int:
        """Identificativo o riferimento intero: obbligatorio."""
        testo = self.testo(colonna)
        if testo is None:
            raise Scarto(f"chiave mancante: {colonna}")
        try:
            valore = nz.intero(testo)
        except nz.NonValido as errore:
            raise Scarto(f"tipo non valido: {colonna}={testo!r} {errore}") from None
        if minimo is not None and valore < minimo:
            raise Scarto(f"valore non valido: {colonna}={testo!r} (atteso >= {minimo})")
        return valore

    def obbligatorio(
        self,
        colonna: str,
        converti: Callable[[str], Any] | None = None,
        valido: Callable[[Any], bool] | None = None,
        regola: str = "",
    ) -> Any:
        testo = self.testo(colonna)
        if testo is None:
            raise Scarto(f"campo obbligatorio mancante: {colonna}")
        if converti is None:
            return testo
        try:
            valore = converti(testo)
        except nz.NonValido as errore:
            raise Scarto(f"tipo non valido: {colonna}={testo!r} {errore}") from None
        if valido is not None and not valido(valore):
            raise Scarto(f"valore non valido: {colonna}={testo!r} ({regola})")
        return valore

    def facoltativo(
        self,
        colonna: str,
        converti: Callable[[str], Any] | None = None,
        valido: Callable[[Any], bool] | None = None,
        regola: str = "",
    ) -> Any:
        """Attributo facoltativo: se non è valido diventa NULL e si registra."""
        testo = self.testo(colonna)
        if testo is None:
            return None
        if converti is None:
            return testo
        try:
            valore = converti(testo)
        except nz.NonValido as errore:
            self.annulla(colonna, testo, f"tipo non valido: {errore}")
            return None
        if valido is not None and not valido(valore):
            self.annulla(colonna, testo, f"valore non valido: {regola}")
            return None
        return valore

    def annulla(self, colonna: str, testo: str, motivo: str) -> None:
        self.annullati.append(
            {
                "file": self.file,
                "riga": self.numero,
                "colonna": colonna,
                "valore": testo,
                "motivo": motivo,
            }
        )


@dataclass
class Anagrafica:
    """Identificativi validi e scartati di un file, per risolvere i riferimenti."""

    file: str
    validi: set[int] = field(default_factory=set)
    scartati: set[int] = field(default_factory=set)

    def verifica(self, colonna: str, valore: int) -> None:
        if valore in self.validi:
            return
        if valore in self.scartati:
            raise Scarto(
                f"riferimento inesistente: {colonna}={valore} è tra le righe scartate di {self.file}"
            )
        raise Scarto(
            f"riferimento inesistente: {colonna}={valore} non è presente in {self.file}"
        )


def _positivo(n: Any) -> bool:
    return n > 0


def _non_negativo(n: Any) -> bool:
    return n >= 0


def _dec(cifre: int, decimali: int) -> Callable[[str], Any]:
    return lambda testo: nz.decimale(testo, cifre, decimali)


def _apri(cartella: Path, file: str):
    """Righe di un CSV, oppure nessuna se il file facoltativo manca."""
    percorso = cartella / file
    if not percorso.is_file():
        if file in FILE_OBBLIGATORI:
            raise ErroreInput(f"manca {file} in {cartella}")
        print(f"Avviso: {file} assente in {cartella}: trattato come vuoto.", file=sys.stderr)
        return iter(())
    _, righe = leggi_csv(percorso, COLONNE[file])
    return righe


# ---------- Anagrafiche e gare ----------


def _anagrafica(
    cartella: Path,
    rap: Rapporto,
    file: str,
    colonna_id: str,
    costruisci: Callable[[Riga], tuple],
    unici: tuple[tuple[str, Callable[[tuple], Any]], ...] = (),
) -> tuple[list[tuple], Anagrafica, dict[int, Any]]:
    """Carica un file con chiave intera nella prima colonna della riga prodotta.

    `unici` elenca le chiavi naturali (etichetta, funzione sulla riga): una
    seconda riga con la stessa chiave naturale è un duplicato.
    """
    righe: list[tuple] = []
    anagrafica = Anagrafica(file)
    viste: dict[int, int] = {}
    naturali: list[dict[Any, int]] = [{} for _ in unici]
    extra: dict[int, Any] = {}
    for numero, valori in _apri(cartella, file):
        if valori is None:
            rap.scarta(file, numero, "riga malformata: numero di campi diverso dall'intestazione")
            continue
        riga_csv = Riga(file, numero, valori)
        try:
            riga = costruisci(riga_csv)
            identificativo = riga[0]
            if identificativo in viste:
                raise Scarto(
                    f"duplicato: {colonna_id}={identificativo} già presente alla riga {viste[identificativo]}"
                )
            for (etichetta, estrai), visti in zip(unici, naturali):
                chiave = estrai(riga)
                if chiave in visti:
                    raise Scarto(
                        f"duplicato: {etichetta}={chiave!r} già presente alla riga {visti[chiave]}"
                    )
        except Scarto as scarto:
            rap.scarta(file, numero, str(scarto))
            try:
                anagrafica.scartati.add(nz.intero(riga_csv.testo(colonna_id) or ""))
            except nz.NonValido:
                pass
            continue
        viste[identificativo] = numero
        for (_, estrai), visti in zip(unici, naturali):
            visti[estrai(riga)] = numero
        anagrafica.validi.add(identificativo)
        rap.annullati.extend(riga_csv.annullati)
        extra[identificativo] = riga_csv.extra
        righe.append(riga)
    anagrafica.scartati -= anagrafica.validi
    return righe, anagrafica, extra


def _stagione(r: Riga) -> tuple:
    anno = r.chiave("year")
    if not 1950 <= anno <= 2100:
        raise Scarto(f"valore non valido: year={anno} (atteso tra 1950 e 2100)")
    return (anno, r.facoltativo("url"))


def _circuito(r: Riga) -> tuple:
    return (
        r.chiave("circuitId"),
        r.obbligatorio("circuitRef"),
        r.obbligatorio("name"),
        r.facoltativo("location"),
        r.obbligatorio("country"),
        r.facoltativo("lat", _dec(9, 6), lambda v: -90 <= v <= 90, "atteso tra -90 e 90"),
        r.facoltativo("lng", _dec(9, 6), lambda v: -180 <= v <= 180, "atteso tra -180 e 180"),
        r.facoltativo("alt", nz.intero),
        r.facoltativo("url"),
    )


def _pilota(r: Riga) -> tuple:
    return (
        r.chiave("driverId"),
        r.obbligatorio("driverRef"),
        r.obbligatorio("forename"),
        r.obbligatorio("surname"),
        r.facoltativo(
            "code",
            str,
            lambda v: len(v) == 3 and v == v.upper(),
            "attesi tre caratteri maiuscoli",
        ),
        r.facoltativo("number", nz.intero, lambda v: 0 <= v <= 99, "atteso tra 0 e 99"),
        r.facoltativo("dob", nz.data),
        r.facoltativo("nationality"),
        r.facoltativo("url"),
    )


def _scuderia(r: Riga) -> tuple:
    return (
        r.chiave("constructorId"),
        r.obbligatorio("constructorRef"),
        r.obbligatorio("name"),
        r.facoltativo("nationality"),
        r.facoltativo("url"),
    )


def _stato(r: Riga) -> tuple:
    return (r.chiave("statusId"), r.obbligatorio("status"))


def _gara(stagioni: Anagrafica, circuiti: Anagrafica) -> Callable[[Riga], tuple]:
    def costruisci(r: Riga) -> tuple:
        gara = r.chiave("raceId")
        anno = r.chiave("year")
        stagioni.verifica("year", anno)
        turno = r.obbligatorio("round", nz.intero, _positivo, "atteso > 0")
        circuito = r.chiave("circuitId")
        circuiti.verifica("circuitId", circuito)
        nome = r.obbligatorio("name")
        # La sessione di gara porta la data del Gran Premio: obbligatoria.
        sessioni = {"race": (r.obbligatorio("date", nz.data), r.facoltativo("time", nz.ora))}
        for tipo, prefisso in SESSIONI_SECONDARIE:
            giorno = r.facoltativo(f"{prefisso}_date", nz.data)
            orario = r.facoltativo(f"{prefisso}_time", nz.ora)
            if orario is not None and giorno is None:
                r.annulla(
                    f"{prefisso}_time",
                    r.testo(f"{prefisso}_time") or "",
                    "valore non valido: orario senza data",
                )
                orario = None
            if giorno is not None:
                sessioni[tipo] = (giorno, orario)
        r.extra = sessioni
        return (gara, anno, turno, circuito, nome, r.facoltativo("url"))

    return costruisci


# ---------- Classifiche ----------


def _risultati(
    cartella: Path,
    rap: Rapporto,
    file: str,
    tipo: str,
    gare: Anagrafica,
    piloti: Anagrafica,
    scuderie: Anagrafica,
    stati: Anagrafica,
) -> list[tuple]:
    righe: list[tuple] = []
    viste: dict[int, int] = {}
    for numero, valori in _apri(cartella, file):
        if valori is None:
            rap.scarta(file, numero, "riga malformata: numero di campi diverso dall'intestazione")
            continue
        r = Riga(file, numero, valori)
        try:
            origine = r.chiave("resultId")
            gara = r.chiave("raceId")
            pilota = r.chiave("driverId")
            scuderia = r.chiave("constructorId")
            stato = r.chiave("statusId")
            ordine = r.obbligatorio("positionOrder", nz.intero, _positivo, "atteso > 0")
            punti = r.obbligatorio("points", _dec(6, 2), _non_negativo, "atteso >= 0")
            giri = r.obbligatorio("laps", nz.intero, _non_negativo, "atteso >= 0")
            testo_posizione = r.obbligatorio("positionText").upper()
            posizione = r.facoltativo("position", nz.intero, _positivo, "atteso > 0")
            derivata = None
            if testo_posizione.isascii() and testo_posizione.isdigit():
                # positionText numerico: classificato in quella posizione.
                try:
                    da_testo = nz.intero(testo_posizione)
                except nz.NonValido as errore:
                    raise Scarto(
                        f"tipo non valido: positionText={testo_posizione!r} {errore}"
                    ) from None
                if da_testo < 1:
                    raise Scarto(
                        f"valore non valido: positionText={testo_posizione!r} (atteso > 0)"
                    )
                esito = "classified"
                if posizione is None:
                    # position assente (o non valida, già registrata tra gli
                    # annullati): si ricava da positionText.
                    posizione = da_testo
                    derivata = {
                        "file": file,
                        "riga": numero,
                        "colonna": "position",
                        "valore": da_testo,
                        "origine": "positionText",
                    }
            elif testo_posizione in ESITI:
                esito = ESITI[testo_posizione]
                if posizione is not None:
                    raise Scarto(
                        f"valore non valido: positionText={testo_posizione!r} "
                        f"ma position={posizione} valorizzata"
                    )
            else:
                raise Scarto(f"valore non valido: positionText={testo_posizione!r} sconosciuto")
            # 0 nella fonte significa "assente" per griglia e rango del giro veloce.
            griglia = r.facoltativo("grid", nz.intero, _non_negativo, "atteso >= 0") or None
            rango = r.facoltativo("rank", nz.intero, _non_negativo, "atteso >= 0") or None
            riga = (
                gara,
                tipo,
                origine,
                pilota,
                scuderia,
                stato,
                r.facoltativo("number", nz.intero, _non_negativo, "atteso >= 0"),
                griglia,
                posizione,
                ordine,
                esito,
                punti,
                giri,
                r.facoltativo("milliseconds", nz.intero, _positivo, "atteso > 0"),
                r.facoltativo("fastestLap", nz.intero, _positivo, "atteso > 0"),
                rango,
                r.facoltativo("fastestLapTime", nz.tempo_ms, _positivo, "atteso > 0"),
                r.facoltativo("fastestLapSpeed", _dec(7, 3), _positivo, "atteso > 0"),
            )
            gare.verifica("raceId", gara)
            piloti.verifica("driverId", pilota)
            scuderie.verifica("constructorId", scuderia)
            stati.verifica("statusId", stato)
            if origine in viste:
                raise Scarto(
                    f"duplicato: resultId={origine} già presente alla riga {viste[origine]}"
                )
        except Scarto as scarto:
            rap.scarta(file, numero, str(scarto))
            continue
        viste[origine] = numero
        rap.annullati.extend(r.annullati)
        if derivata is not None:
            rap.derivati.append(derivata)
        righe.append(riga)
    return righe


def _qualifiche(
    cartella: Path, rap: Rapporto, gare: Anagrafica, piloti: Anagrafica, scuderie: Anagrafica
) -> list[tuple]:
    file = "qualifying.csv"
    righe: list[tuple] = []
    viste: dict[tuple[int, int], int] = {}
    for numero, valori in _apri(cartella, file):
        if valori is None:
            rap.scarta(file, numero, "riga malformata: numero di campi diverso dall'intestazione")
            continue
        r = Riga(file, numero, valori)
        try:
            gara = r.chiave("raceId")
            pilota = r.chiave("driverId")
            scuderia = r.chiave("constructorId")
            riga = (
                gara,
                "qualifying",
                pilota,
                scuderia,
                r.facoltativo("number", nz.intero, _non_negativo, "atteso >= 0"),
                r.obbligatorio("position", nz.intero, _positivo, "atteso > 0"),
                r.facoltativo("q1", nz.tempo_ms, _positivo, "atteso > 0"),
                r.facoltativo("q2", nz.tempo_ms, _positivo, "atteso > 0"),
                r.facoltativo("q3", nz.tempo_ms, _positivo, "atteso > 0"),
            )
            gare.verifica("raceId", gara)
            piloti.verifica("driverId", pilota)
            scuderie.verifica("constructorId", scuderia)
            if (gara, pilota) in viste:
                raise Scarto(
                    f"duplicato: (raceId, driverId)=({gara}, {pilota}) già presente "
                    f"alla riga {viste[(gara, pilota)]}"
                )
        except Scarto as scarto:
            rap.scarta(file, numero, str(scarto))
            continue
        viste[(gara, pilota)] = numero
        rap.annullati.extend(r.annullati)
        righe.append(riga)
    return righe


# ---------- Giri e soste ----------


def _durata(r: Riga, colonna_ms: str, colonna_testo: str, obbligatoria: bool) -> int | None:
    """Millisecondi dalla colonna numerica; se è vuota, dal tempo testuale."""
    if r.testo(colonna_ms) is None and r.testo(colonna_testo) is not None:
        colonna, converti = colonna_testo, nz.tempo_ms
    else:
        colonna, converti = colonna_ms, nz.intero
    leggi = r.obbligatorio if obbligatoria else r.facoltativo
    return leggi(colonna, converti, _positivo, "atteso > 0")


def _per_pilota(
    cartella: Path,
    rap: Rapporto,
    file: str,
    colonna_numero: str,
    costruisci: Callable[[Riga], tuple],
    gare: Anagrafica,
    piloti: Anagrafica,
    con_risultato: set[tuple[int, int]],
) -> list[tuple]:
    """Giri o soste: chiave (gara, pilota, numero), agganciati alla sessione `race`.

    Scarto a cascata: il pilota deve avere un risultato valido in quella gara.
    """
    righe: list[tuple] = []
    viste: dict[tuple[int, int, int], int] = {}
    for numero, valori in _apri(cartella, file):
        if valori is None:
            rap.scarta(file, numero, "riga malformata: numero di campi diverso dall'intestazione")
            continue
        r = Riga(file, numero, valori)
        try:
            gara = r.chiave("raceId")
            pilota = r.chiave("driverId")
            progressivo = r.chiave(colonna_numero, minimo=1)
            riga = (gara, "race", pilota, progressivo, *costruisci(r))
            gare.verifica("raceId", gara)
            piloti.verifica("driverId", pilota)
            if (gara, pilota) not in con_risultato:
                raise Scarto(
                    f"senza risultato valido: il pilota driverId={pilota} non ha un "
                    f"risultato valido in results.csv per la gara raceId={gara}"
                )
            chiave = (gara, pilota, progressivo)
            if chiave in viste:
                raise Scarto(
                    f"duplicato: (raceId, driverId, {colonna_numero})=({gara}, {pilota}, "
                    f"{progressivo}) già presente alla riga {viste[chiave]}"
                )
        except Scarto as scarto:
            rap.scarta(file, numero, str(scarto))
            continue
        viste[chiave] = numero
        if r.annullati:
            rap.annullati.extend(r.annullati)
        righe.append(riga)
    return righe


def _giro(r: Riga) -> tuple:
    return (
        r.facoltativo("position", nz.intero, _positivo, "atteso > 0"),
        _durata(r, "milliseconds", "time", obbligatoria=True),
    )


def _sosta(r: Riga) -> tuple:
    return (
        r.obbligatorio("lap", nz.intero, _positivo, "atteso > 0"),
        r.facoltativo("time", nz.ora),
        _durata(r, "milliseconds", "duration", obbligatoria=False),
    )


# ---------- Stint ----------


def deriva_stint(
    giri_completati: dict[tuple[int, str, int], int],
    soste: Iterable[tuple[int, str, int, int]],
) -> list[tuple]:
    """Stint derivati dai pit stop (docs/modello-dati.md, "Stint e mescole").

    `giri_completati`: (gara, sessione, pilota) -> giri completati (il massimo,
    se il pilota ha più righe). `soste`: (gara, sessione, pilota, giro).
    Si derivano stint solo per le sessioni con almeno una sosta e solo per i
    piloti con almeno un giro completato; la mescola è sempre NULL.
    """
    giri_sosta: dict[tuple[int, str, int], set[int]] = {}
    sessioni_con_soste: set[tuple[int, str]] = set()
    for gara, sessione, pilota, giro in soste:
        sessioni_con_soste.add((gara, sessione))
        giri_sosta.setdefault((gara, sessione, pilota), set()).add(giro)
    stint: list[tuple] = []
    for chiave, ultimo in giri_completati.items():
        gara, sessione, pilota = chiave
        if (gara, sessione) not in sessioni_con_soste or ultimo < 1:
            continue
        fine = {min(giro, ultimo) for giro in giri_sosta.get(chiave, ())} | {ultimo}
        inizio = 1
        for progressivo, giro in enumerate(sorted(fine), start=1):
            stint.append((gara, sessione, pilota, progressivo, inizio, giro, None))
            inizio = giro + 1
    return stint


# ---------- Scrittura ----------


def _scrivi_parquet(cartella: Path, nome: str, righe: list[tuple]) -> int:
    """Scrive il file (o i file, se la tabella è divisa per sessione) di una tabella."""
    tabella = PER_NOME[nome]
    nomi = tabella.nomi
    indici = [nomi.index(c) for c in tabella.ordine]
    righe = sorted(righe, key=lambda riga: tuple(riga[i] for i in indici))
    if tabella.partizioni:
        sessione = nomi.index("session_type")
        parti = [
            (file, [r for r in righe if r[sessione] == tipo])
            for file, (_, tipo) in zip(tabella.file, tabella.partizioni)
        ]
        assert sum(len(p) for _, p in parti) == len(righe)
    else:
        parti = [(tabella.file[0], righe)]
    for file, parte in parti:
        colonne = list(zip(*parte)) if parte else [()] * len(nomi)
        dati = pa.Table.from_arrays(
            [pa.array(valori, type=tipo) for valori, (_, tipo) in zip(colonne, tabella.colonne)],
            schema=tabella.schema,
        )
        # Opzioni fissate per avere gli stessi byte a parità di input.
        pq.write_table(
            dati,
            cartella / file,
            compression="zstd",
            compression_level=3,
            version="2.6",
            data_page_version="1.0",
            use_dictionary=True,
            write_statistics=True,
            row_group_size=1_000_000,
            store_schema=True,
        )
    return len(righe)


def _scrivi_json(percorso: Path, voci: list[dict[str, Any]]) -> None:
    percorso.write_bytes(
        (json.dumps(voci, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


def categoria(motivo: str) -> str:
    """Tipo di scarto: la parte del motivo prima dei due punti."""
    return motivo.split(":", 1)[0]


# ---------- Orchestrazione ----------


def trasforma(cartella_input: Path, cartella_output: Path) -> Esito:
    """Valida e normalizza i CSV e scrive il formato intermedio."""
    cartella_input = Path(cartella_input)
    cartella_output = Path(cartella_output)
    if not cartella_input.is_dir():
        raise ErroreInput(f"la cartella di input {cartella_input} non esiste")
    rap = Rapporto()

    stagioni_r, stagioni, _ = _anagrafica(cartella_input, rap, "seasons.csv", "year", _stagione)
    circuiti_r, circuiti, _ = _anagrafica(
        cartella_input, rap, "circuits.csv", "circuitId", _circuito,
        unici=(("circuitRef", lambda riga: riga[1]),),
    )
    piloti_r, piloti, _ = _anagrafica(
        cartella_input, rap, "drivers.csv", "driverId", _pilota,
        unici=(("driverRef", lambda riga: riga[1]),),
    )
    scuderie_r, scuderie, _ = _anagrafica(
        cartella_input, rap, "constructors.csv", "constructorId", _scuderia,
        unici=(("constructorRef", lambda riga: riga[1]),),
    )
    stati_r, stati, _ = _anagrafica(
        cartella_input, rap, "status.csv", "statusId", _stato,
        unici=(("status", lambda riga: riga[1]),),
    )
    gare_r, gare, sessioni_gara = _anagrafica(
        cartella_input, rap, "races.csv", "raceId", _gara(stagioni, circuiti),
        unici=(("(year, round)", lambda riga: (riga[1], riga[2])),),
    )

    risultati_r = _risultati(
        cartella_input, rap, "results.csv", "race", gare, piloti, scuderie, stati
    )
    risultati_r += _risultati(
        cartella_input, rap, "sprint_results.csv", "sprint", gare, piloti, scuderie, stati
    )
    qualifiche_r = _qualifiche(cartella_input, rap, gare, piloti, scuderie)

    con_risultato = {(r[0], r[3]) for r in risultati_r if r[1] == "race"}
    giri_r = _per_pilota(
        cartella_input, rap, "lap_times.csv", "lap", _giro, gare, piloti, con_risultato
    )
    soste_r = _per_pilota(
        cartella_input, rap, "pit_stops.csv", "stop", _sosta, gare, piloti, con_risultato
    )

    # Sessioni: la gara sempre; le altre se hanno una data, e qualifica o
    # sprint anche senza data quando esistono le loro classifiche.
    con_dati = {(r[0], r[1]) for r in risultati_r} | {(r[0], r[1]) for r in qualifiche_r}
    sessioni_r: list[tuple] = []
    for gara, sessioni in sessioni_gara.items():
        for tipo, (giorno, orario) in sessioni.items():
            sessioni_r.append((gara, tipo, giorno, orario))
        for tipo in ("qualifying", "sprint"):
            if tipo not in sessioni and (gara, tipo) in con_dati:
                sessioni_r.append((gara, tipo, None, None))

    giri_completati: dict[tuple[int, str, int], int] = {}
    for r in risultati_r:
        chiave = (r[0], r[1], r[3])
        giri_completati[chiave] = max(giri_completati.get(chiave, 0), r[12])
    stint_r = deriva_stint(giri_completati, ((s[0], s[1], s[2], s[4]) for s in soste_r))

    righe = {
        "seasons": stagioni_r,
        "circuits": circuiti_r,
        "drivers": piloti_r,
        "constructors": scuderie_r,
        "statuses": stati_r,
        "races": gare_r,
        "sessions": sessioni_r,
        "results": risultati_r,
        "qualifying_results": qualifiche_r,
        "laps": giri_r,
        "pit_stops": soste_r,
        "stints": stint_r,
    }
    cartella_output.mkdir(parents=True, exist_ok=True)
    conteggi = {t.nome: _scrivi_parquet(cartella_output, t.nome, righe[t.nome]) for t in TABELLE}
    rap.scarti.sort(key=lambda s: (s["file"], s["riga"]))
    rap.annullati.sort(key=lambda a: (a["file"], a["riga"], a["colonna"]))
    _scrivi_json(cartella_output / FILE_SCARTI, rap.scarti)
    rap.derivati.sort(key=lambda d: (d["file"], d["riga"], d["colonna"]))
    _scrivi_json(cartella_output / FILE_ANNULLATI, rap.annullati)
    _scrivi_json(cartella_output / FILE_DERIVATI, rap.derivati)
    return Esito(conteggi, rap.scarti, rap.annullati, rap.derivati)


def riepilogo(esito: Esito) -> str:
    righe = ["Righe per tabella (results = gare + sprint):"]
    righe += [f"  {nome:20s} {n:>8d}" for nome, n in esito.righe.items()]
    righe.append(f"Righe scartate: {len(esito.scarti)} (dettaglio in {FILE_SCARTI})")
    per_tipo = Counter((s["file"], categoria(s["motivo"])) for s in esito.scarti)
    righe += [f"  {file:20s} {tipo:28s} {n:>6d}" for (file, tipo), n in sorted(per_tipo.items())]
    righe.append(
        f"Attributi facoltativi messi a NULL: {len(esito.annullati)} (dettaglio in {FILE_ANNULLATI})"
    )
    per_colonna = Counter((a["file"], a["colonna"]) for a in esito.annullati)
    righe += [f"  {file:20s} {colonna:28s} {n:>6d}" for (file, colonna), n in sorted(per_colonna.items())]
    righe.append(
        f"Posizioni derivate da positionText: {len(esito.derivati)} (dettaglio in {FILE_DERIVATI})"
    )
    per_file = Counter(d["file"] for d in esito.derivati)
    righe += [f"  {file:20s} {'position':28s} {n:>6d}" for file, n in sorted(per_file.items())]
    return "\n".join(righe)


def esegui(cartella_input: Path, cartella_output: Path) -> int:
    """Logica del sottocomando. Restituisce il codice di uscita."""
    try:
        esito = trasforma(cartella_input, cartella_output)
    except ErroreInput as errore:
        print(f"Errore: {errore}", file=sys.stderr)
        return 1
    print(riepilogo(esito))
    return 0
