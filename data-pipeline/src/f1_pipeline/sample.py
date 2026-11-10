"""Sottocomando `sample`: estrae dal dataset completo le sole stagioni richieste.

Il campione resta nel formato originale Kaggle/Ergast: stessi nomi di file,
stessa intestazione, e ogni record è ricopiato byte per byte nell'ordine di
origine. È coerente (ogni gara, pilota, scuderia, circuito e stato citato è
presente) e il più piccolo possibile: delle anagrafiche restano solo le righe
citate, e i file che la pipeline non carica (classifiche di campionato,
`constructor_results.csv`) non vengono copiati.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path

from f1_pipeline.csvio import ErroreInput, leggi_record
from f1_pipeline.normalizza import pulisci

# File legati a una gara tramite raceId.
FILE_DI_GARA = (
    "results.csv",
    "sprint_results.csv",
    "qualifying.csv",
    "lap_times.csv",
    "pit_stops.csv",
)
# Anagrafica -> (colonna chiave, [(file che la cita, colonna)]).
ANAGRAFICHE = {
    "circuits.csv": ("circuitId", [("races.csv", "circuitId")]),
    "drivers.csv": ("driverId", [(f, "driverId") for f in FILE_DI_GARA]),
    "constructors.csv": (
        "constructorId",
        [(f, "constructorId") for f in ("results.csv", "sprint_results.csv", "qualifying.csv")],
    ),
    "status.csv": ("statusId", [(f, "statusId") for f in ("results.csv", "sprint_results.csv")]),
}
FILE_CAMPIONE = ("seasons.csv", "races.csv", *ANAGRAFICHE, *FILE_DI_GARA)


def _filtra(
    origine: Path,
    destinazione: Path,
    colonna: str,
    ammessi: set[str],
    raccogli: Iterable[str] = (),
) -> tuple[int, dict[str, set[str]]]:
    """Copia i record con `colonna` tra gli `ammessi`; raccoglie i valori citati."""
    record = leggi_record(origine)
    try:
        intestazione, testo_intestazione = next(record)
    except StopIteration:
        raise ErroreInput(f"{origine.name}: file vuoto") from None
    nomi = [c.strip() for c in intestazione]
    if colonna not in nomi:
        raise ErroreInput(f"{origine.name}: manca la colonna {colonna}")
    indice = nomi.index(colonna)
    citati: dict[str, set[str]] = {c: set() for c in raccogli if c in nomi}
    indici_citati = {c: nomi.index(c) for c in citati}
    copiati = 0
    with open(destinazione, "w", newline="", encoding="utf-8") as uscita:
        uscita.write(testo_intestazione.lstrip("﻿"))
        for campi, testo in record:
            if len(campi) != len(nomi) or pulisci(campi[indice]) not in ammessi:
                continue
            uscita.write(testo if testo.endswith("\n") else testo + "\n")
            copiati += 1
            for c, i in indici_citati.items():
                valore = pulisci(campi[i])
                if valore is not None:
                    citati[c].add(valore)
    return copiati, citati


def campiona(cartella_input: Path, cartella_output: Path, stagioni: Iterable[int]) -> dict[str, int]:
    """Scrive il campione e restituisce il numero di record per file."""
    cartella_input, cartella_output = Path(cartella_input), Path(cartella_output)
    anni = {str(int(s)) for s in stagioni}
    mancanti = [f for f in FILE_CAMPIONE if not (cartella_input / f).is_file()]
    if mancanti:
        raise ErroreInput(f"file mancanti in {cartella_input}: {', '.join(mancanti)}")
    if cartella_input.resolve() == cartella_output.resolve():
        raise ErroreInput("le cartelle di input e di output coincidono")
    cartella_output.mkdir(parents=True, exist_ok=True)

    def filtra(file: str, colonna: str, ammessi: set[str], raccogli: Iterable[str] = ()):
        return _filtra(cartella_input / file, cartella_output / file, colonna, ammessi, raccogli)

    conteggi: dict[str, int] = {}
    citati: dict[tuple[str, str], set[str]] = {}
    conteggi["seasons.csv"], _ = filtra("seasons.csv", "year", anni)
    conteggi["races.csv"], da_gare = filtra("races.csv", "year", anni, ("raceId", "circuitId"))
    citati[("races.csv", "circuitId")] = da_gare["circuitId"]
    gare = da_gare["raceId"]
    for file in FILE_DI_GARA:
        conteggi[file], trovati = filtra(
            file, "raceId", gare, ("driverId", "constructorId", "statusId")
        )
        for colonna, valori in trovati.items():
            citati[(file, colonna)] = valori
    for file, (chiave, fonti) in ANAGRAFICHE.items():
        ammessi = set().union(*(citati.get(fonte, set()) for fonte in fonti))
        conteggi[file], _ = filtra(file, chiave, ammessi)
    return {f: conteggi[f] for f in FILE_CAMPIONE}


def esegui(cartella_input: Path, cartella_output: Path, stagioni: Iterable[int]) -> int:
    """Logica del sottocomando. Restituisce il codice di uscita."""
    try:
        conteggi = campiona(cartella_input, cartella_output, stagioni)
    except ErroreInput as errore:
        print(f"Errore: {errore}", file=sys.stderr)
        return 1
    if not conteggi["races.csv"]:
        print("Errore: nessuna gara nelle stagioni richieste.", file=sys.stderr)
        return 1
    totale = 0
    for file, n in conteggi.items():
        dimensione = (Path(cartella_output) / file).stat().st_size
        totale += dimensione
        print(f"  {file:22s} {n:>7d} righe {dimensione / 1024:>9.1f} KiB")
    print(f"Campione in {cartella_output}: {totale / 1024 / 1024:.2f} MiB")
    return 0
