"""Dati di prova condivisi: un piccolo dataset in formato Kaggle/Ergast.

Due stagioni, due gare, tre piloti. Abbastanza per coprire sprint, qualifiche
senza data, soste e stint, e per sporcarlo a piacere nei singoli test.
"""

from __future__ import annotations

import copy
import csv
from pathlib import Path

import pytest

N = r"\N"

INTESTAZIONI = {
    "seasons.csv": ["year", "url"],
    "circuits.csv": ["circuitId", "circuitRef", "name", "location", "country", "lat", "lng", "alt", "url"],
    "drivers.csv": ["driverId", "driverRef", "number", "code", "forename", "surname", "dob", "nationality", "url"],
    "constructors.csv": ["constructorId", "constructorRef", "name", "nationality", "url"],
    "status.csv": ["statusId", "status"],
    "races.csv": [
        "raceId", "year", "round", "circuitId", "name", "date", "time", "url",
        "fp1_date", "fp1_time", "fp2_date", "fp2_time", "fp3_date", "fp3_time",
        "quali_date", "quali_time", "sprint_date", "sprint_time",
    ],
    "results.csv": [
        "resultId", "raceId", "driverId", "constructorId", "number", "grid", "position",
        "positionText", "positionOrder", "points", "laps", "time", "milliseconds",
        "fastestLap", "rank", "fastestLapTime", "fastestLapSpeed", "statusId",
    ],
    "sprint_results.csv": [
        "resultId", "raceId", "driverId", "constructorId", "number", "grid", "position",
        "positionText", "positionOrder", "points", "laps", "time", "milliseconds",
        "fastestLap", "fastestLapTime", "statusId",
    ],
    "qualifying.csv": ["qualifyId", "raceId", "driverId", "constructorId", "number", "position", "q1", "q2", "q3"],
    "lap_times.csv": ["raceId", "driverId", "lap", "position", "time", "milliseconds"],
    "pit_stops.csv": ["raceId", "driverId", "stop", "lap", "time", "duration", "milliseconds"],
}

_BASE = {
    "seasons.csv": [
        ["2023", "http://example.org/2023"],
        ["2024", "http://example.org/2024"],
    ],
    "circuits.csv": [
        ["1", "monza", "Autodromo di Monza", "Monza", "Italy", "45.6156", "9.28111", "162", "http://example.org/monza"],
        ["2", "spa", "Spa-Francorchamps", "Spa", "Belgium", "50.4372", "5.97139", N, "http://example.org/spa"],
        ["3", "mai_usato", "Circuito mai usato", "Altrove", "Nowhere", "0", "0", "5", N],
    ],
    "drivers.csv": [
        ["1", "verstappen", "1", "VER", "Max", "Verstappen", "1997-09-30", "Dutch", "http://example.org/ver"],
        ["2", "hamilton", "44", "HAM", "Lewis", "Hamilton", "1985-01-07", "British", "http://example.org/ham"],
        ["3", "storico", N, N, "Pilota", "Storico", "1920-05-05", "Italian", N],
        ["4", "mai_usato", N, N, "Mai", "Usato", N, N, N],
    ],
    "constructors.csv": [
        ["1", "red_bull", "Red Bull", "Austrian", "http://example.org/rb"],
        ["2", "mercedes", "Mercedes", "German", "http://example.org/merc"],
        ["3", "mai_usata", "Mai Usata", N, N],
    ],
    "status.csv": [["1", "Finished"], ["2", "Accident"], ["3", "Mai usato"]],
    "races.csv": [
        ["10", "2023", "1", "1", "Gran Premio Uno", "2023-03-05", "15:00:00", "http://example.org/gp1",
         "2023-03-03", "11:30:00", "2023-03-03", "15:00:00", N, N,
         "2023-03-04", "15:00:00", "2023-03-04", "11:00:00"],
        ["11", "2024", "1", "2", "Gran Premio Due", "2024-03-10", N, N,
         N, N, N, N, N, N, N, N, N, N],
    ],
    "results.csv": [
        ["100", "10", "1", "1", "1", "1", "1", "1", "1", "25", "3", "5:01.500", "301500", "2", "1", "1:39.019", "210.123", "1"],
        ["101", "10", "2", "2", "44", "2", "2", "2", "2", "18", "3", "+2.500", "304000", "3", "2", "1:40.250", "208.500", "1"],
        ["102", "10", "3", "2", "63", "0", N, "R", "3", "0", "1", N, N, N, "0", N, N, "2"],
        ["103", "11", "1", "1", "1", "1", "1", "1", "1", "12.5", "2", "3:20.000", "200000", N, N, N, N, "1"],
        ["104", "11", "2", "2", "44", "2", N, "R", "2", "0", "0", N, N, N, N, N, N, "2"],
    ],
    "sprint_results.csv": [
        ["1", "10", "1", "1", "1", "2", "1", "1", "1", "8", "2", "3:10.000", "190000", "2", "1:34.000", "1"],
        ["2", "10", "2", "2", "44", "1", "2", "2", "2", "7", "2", "+1.000", "191000", "1", "1:34.500", "1"],
    ],
    "qualifying.csv": [
        ["1", "10", "1", "1", "1", "1", "1:30.100", "1:29.500", "1:28.999"],
        ["2", "10", "2", "2", "44", "2", "1:30.200", "1:29.700", ""],
        ["3", "10", "3", "2", "63", "3", "1:31.000", N, N],
        ["4", "11", "1", "1", "1", "1", "1:45.000", N, N],
    ],
    "lap_times.csv": [
        ["10", "1", "1", "1", "1:41.000", "101000"],
        ["10", "1", "2", "1", "1:39.019", "99019"],
        ["10", "1", "3", "1", "1:41.481", "101481"],
        ["10", "2", "1", "2", "1:42.000", "102000"],
        ["10", "2", "2", "2", "1:41.750", "101750"],
        ["10", "2", "3", "2", "1:40.250", "100250"],
        ["10", "3", "1", "3", "1:50.000", "110000"],
    ],
    "pit_stops.csv": [
        ["10", "1", "1", "2", "15:05:10", "22.500", "22500"],
        ["10", "2", "1", "1", "15:03:00", "24.000", "24000"],
        ["10", "2", "2", "3", "15:07:00", "17:23.456", "1043456"],
    ],
}


def scrivi_csv(cartella: Path, dati: dict[str, list[list[str]]]) -> None:
    """Scrive i CSV nello stile della fonte (testo tra virgolette, \\N nudo)."""
    cartella.mkdir(parents=True, exist_ok=True)
    for file, righe in dati.items():
        with open(cartella / file, "w", newline="", encoding="utf-8") as f:
            f.write(",".join(INTESTAZIONI[file]) + "\n")
            for riga in righe:
                f.write(",".join(_campo(v) for v in riga) + "\n")


def _campo(valore: str) -> str:
    if valore == N or valore.lstrip("-").replace(".", "", 1).isdigit():
        return valore
    return '"' + valore.replace('"', '""') + '"'


def leggi_righe(percorso: Path) -> list[dict[str, str]]:
    with open(percorso, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def colonna(file: str, nome: str) -> int:
    return INTESTAZIONI[file].index(nome)


@pytest.fixture
def base() -> dict[str, list[list[str]]]:
    """Copia modificabile del dataset di prova."""
    return copy.deepcopy(_BASE)


@pytest.fixture
def csv_puliti(tmp_path, base) -> Path:
    cartella = tmp_path / "csv"
    scrivi_csv(cartella, base)
    return cartella


@pytest.fixture(autouse=True)
def _senza_credenziali_kaggle(monkeypatch):
    """Nessun test deve poter raggiungere Kaggle con credenziali vere."""
    for nome in ("KAGGLE_API_TOKEN", "KAGGLE_USERNAME", "KAGGLE_KEY"):
        monkeypatch.delenv(nome, raising=False)
