"""`sample`: estrazione del dataset di esempio, e controlli sul campione versionato."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from conftest import INTESTAZIONI, leggi_righe, scrivi_csv

from f1_pipeline import cli
from f1_pipeline.sample import FILE_CAMPIONE, campiona
from f1_pipeline.transform import trasforma

CAMPIONE = Path(__file__).resolve().parents[1] / "sample"
STAGIONI_CAMPIONE = {2022, 2023, 2024}
MB = 1024 * 1024

# (file figlio, colonna, file padre, colonna chiave)
RIFERIMENTI = [
    ("races.csv", "year", "seasons.csv", "year"),
    ("races.csv", "circuitId", "circuits.csv", "circuitId"),
    *[(f, "raceId", "races.csv", "raceId")
      for f in ("results.csv", "sprint_results.csv", "qualifying.csv", "lap_times.csv", "pit_stops.csv")],
    *[(f, "driverId", "drivers.csv", "driverId")
      for f in ("results.csv", "sprint_results.csv", "qualifying.csv", "lap_times.csv", "pit_stops.csv")],
    *[(f, "constructorId", "constructors.csv", "constructorId")
      for f in ("results.csv", "sprint_results.csv", "qualifying.csv")],
    *[(f, "statusId", "status.csv", "statusId") for f in ("results.csv", "sprint_results.csv")],
]


def controlla_coerenza(cartella: Path) -> None:
    for figlio, colonna, padre, chiave in RIFERIMENTI:
        presenti = {r[chiave] for r in leggi_righe(cartella / padre)}
        citati = {r[colonna] for r in leggi_righe(cartella / figlio)}
        assert citati <= presenti, f"{figlio}.{colonna}: riferimenti non risolti {sorted(citati - presenti)[:5]}"


def controlla_minimo(cartella: Path) -> None:
    """Ogni riga delle anagrafiche è citata da qualcuno."""
    for padre, chiave in (("circuits.csv", "circuitId"), ("drivers.csv", "driverId"),
                          ("constructors.csv", "constructorId"), ("status.csv", "statusId")):
        citati = set()
        for figlio, colonna, p, _ in RIFERIMENTI:
            if p == padre:
                citati |= {r[colonna] for r in leggi_righe(cartella / figlio)}
        presenti = {r[chiave] for r in leggi_righe(cartella / padre)}
        assert presenti == citati, f"{padre}: righe non citate {sorted(presenti - citati)[:5]}"


# ---------- Il comando, su un dataset di prova ----------


def test_campiona_una_stagione(tmp_path, csv_puliti):
    uscita = tmp_path / "campione"
    conteggi = campiona(csv_puliti, uscita, [2024])
    assert {p.name for p in uscita.iterdir()} == set(FILE_CAMPIONE)
    assert [r["year"] for r in leggi_righe(uscita / "seasons.csv")] == ["2024"]
    assert [r["raceId"] for r in leggi_righe(uscita / "races.csv")] == ["11"]
    assert {r["raceId"] for r in leggi_righe(uscita / "results.csv")} == {"11"}
    assert conteggi["lap_times.csv"] == 0 and conteggi["results.csv"] == 2
    assert [r["circuitId"] for r in leggi_righe(uscita / "circuits.csv")] == ["2"]
    assert [r["driverId"] for r in leggi_righe(uscita / "drivers.csv")] == ["1", "2"]
    controlla_coerenza(uscita)
    controlla_minimo(uscita)


def test_campione_formato_originale_e_record_identici(tmp_path, csv_puliti):
    uscita = tmp_path / "campione"
    campiona(csv_puliti, uscita, [2023, 2024])
    for file in FILE_CAMPIONE:
        originale = (csv_puliti / file).read_text().splitlines()
        copiato = (uscita / file).read_text().splitlines()
        assert copiato[0] == ",".join(INTESTAZIONI[file]), "stessa intestazione"
        assert set(copiato) <= set(originale), "ogni record è ricopiato tale e quale"
        assert copiato == [r for r in originale if r in set(copiato)], "stesso ordine"
    # Tutte le stagioni: restano fuori solo le anagrafiche mai citate.
    assert len(leggi_righe(uscita / "drivers.csv")) == 3
    assert len(leggi_righe(uscita / "results.csv")) == 5
    controlla_coerenza(uscita)
    controlla_minimo(uscita)


def test_campione_deterministico_e_trasformabile(tmp_path, csv_puliti):
    def impronta(cartella):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(cartella.iterdir())}

    campiona(csv_puliti, tmp_path / "a", [2023])
    campiona(csv_puliti, tmp_path / "b", [2023])
    assert impronta(tmp_path / "a") == impronta(tmp_path / "b")
    esito = trasforma(tmp_path / "a", tmp_path / "out")
    assert esito.scarti == [] and esito.righe["races"] == 1 and esito.righe["laps"] == 7


def test_cli_sample(tmp_path, csv_puliti, capsys):
    uscita = tmp_path / "campione"
    assert cli.main(["sample", "--input", str(csv_puliti), "--output", str(uscita), "--seasons", "2023", "2024"]) == 0
    assert "races.csv" in capsys.readouterr().out
    assert len(leggi_righe(uscita / "races.csv")) == 2


def test_cli_sample_errori(tmp_path, csv_puliti, capsys):
    assert cli.main(["sample", "--input", str(csv_puliti), "--output", str(tmp_path / "x"), "--seasons", "1999"]) == 1
    assert "nessuna gara" in capsys.readouterr().err
    assert cli.main(["sample", "--input", str(csv_puliti), "--output", str(csv_puliti), "--seasons", "2023"]) == 1
    assert "coincidono" in capsys.readouterr().err
    (csv_puliti / "pit_stops.csv").unlink()
    assert cli.main(["sample", "--input", str(csv_puliti), "--output", str(tmp_path / "y"), "--seasons", "2023"]) == 1
    assert "pit_stops.csv" in capsys.readouterr().err


# ---------- Il campione versionato in data-pipeline/sample/ ----------

campione_presente = pytest.mark.skipif(
    not (CAMPIONE / "races.csv").is_file(), reason="data-pipeline/sample/ non contiene il campione"
)


@campione_presente
def test_campione_versionato_stagioni_e_file():
    assert {p.name for p in CAMPIONE.iterdir()} == set(FILE_CAMPIONE)
    assert {int(r["year"]) for r in leggi_righe(CAMPIONE / "races.csv")} == STAGIONI_CAMPIONE
    assert {int(r["year"]) for r in leggi_righe(CAMPIONE / "seasons.csv")} == STAGIONI_CAMPIONE


@campione_presente
def test_campione_versionato_coerente_e_minimo():
    controlla_coerenza(CAMPIONE)
    controlla_minimo(CAMPIONE)


@campione_presente
def test_campione_versionato_dimensioni():
    dimensioni = {p.name: p.stat().st_size for p in CAMPIONE.iterdir()}
    assert max(dimensioni.values()) <= 5 * MB, dimensioni
    assert sum(dimensioni.values()) <= 25 * MB


@campione_presente
def test_campione_versionato_si_trasforma_senza_scarti(tmp_path):
    esito = trasforma(CAMPIONE, tmp_path / "out")
    assert esito.scarti == []
    assert esito.righe["results"] == len(leggi_righe(CAMPIONE / "results.csv")) + len(
        leggi_righe(CAMPIONE / "sprint_results.csv")
    )
    assert esito.righe["laps"] == len(leggi_righe(CAMPIONE / "lap_times.csv"))
    assert esito.righe["races"] == len(leggi_righe(CAMPIONE / "races.csv"))
    assert esito.righe["stints"] > 0


@campione_presente
def test_campione_versionato_riproducibile(tmp_path):
    def impronta(cartella):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(cartella.iterdir())}

    trasforma(CAMPIONE, tmp_path / "a")
    trasforma(CAMPIONE, tmp_path / "b")
    assert impronta(tmp_path / "a") == impronta(tmp_path / "b")
