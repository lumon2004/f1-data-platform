"""Pipeline dati: riproducibilità, idempotenza, validazione, valori mancanti."""
import csv
import hashlib
import re
import shutil

import pyarrow.parquet as pq

from conftest import SAMPLE, conta_righe, f1_pipeline, leggi_csv, leggi_scarti

TABELLE = ["seasons", "races", "circuits", "drivers", "constructors",
           "sessions", "results", "laps", "stints", "pit_stops"]
TEMPO_TESTUALE = re.compile(r"^\d+:\d{2}\.\d{3}$")


def impronta(cartella):
    """{file: sha256} di tutti i file prodotti da transform."""
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(cartella.iterdir()) if p.is_file()}


def test_riproducibilita(trasformato, tmp_path):
    f1_pipeline("transform", "--input", SAMPLE, "--output", tmp_path)
    prima, seconda = impronta(trasformato), impronta(tmp_path)
    assert any(n.endswith(".parquet") for n in prima), "transform non produce file Parquet"
    assert {"results.parquet", "laps.parquet"} <= set(prima)
    assert prima == seconda, "due esecuzioni sullo stesso input producono file diversi"


def test_idempotenza_caricamento(db, trasformato):
    prima = conta_righe(db, TABELLE)
    assert prima["results"] > 0 and prima["laps"] > 0, "il database non contiene il dataset di esempio"
    f1_pipeline("load", "--input", trasformato)
    f1_pipeline("load", "--input", trasformato)
    assert conta_righe(db, TABELLE) == prima, "ricaricare gli stessi dati cambia il numero di righe"


def test_validazione_scarta_e_registra(tmp_path):
    ingresso = tmp_path / "csv"
    shutil.copytree(SAMPLE, ingresso)
    righe = leggi_csv("results.csv", ingresso)
    with open(ingresso / "results.csv", newline="", encoding="utf-8") as f:
        lettore = csv.reader(f)
        intestazione, valida = next(lettore), next(lettore)
    nuovo_id = max(int(r["resultId"]) for r in righe) + 1
    i_id, i_gara = intestazione.index("resultId"), intestazione.index("raceId")

    chiave_mancante = list(valida); chiave_mancante[i_id] = str(nuovo_id); chiave_mancante[i_gara] = ""
    tipo_errato = list(valida); tipo_errato[i_id] = str(nuovo_id + 1); tipo_errato[i_gara] = "abc"
    duplicato = list(valida)
    prima_nuova = len(righe) + 2
    with open(ingresso / "results.csv", "a", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows([chiave_mancante, tipo_errato, duplicato])

    uscita = tmp_path / "out"
    f1_pipeline("transform", "--input", ingresso, "--output", uscita)
    scarti = [s for s in leggi_scarti(uscita) if s["file"] == "results.csv"]
    righe_scartate = {int(s["riga"]) for s in scarti}
    for n, cosa in zip(range(prima_nuova, prima_nuova + 3), ["chiave mancante", "tipo non valido", "duplicato"]):
        assert n in righe_scartate, f"riga {n} ({cosa}) non registrata in scarti.json"
    assert all(str(s.get("motivo", "")).strip() for s in scarti), "ogni scarto deve avere un motivo"

    originali_scartati = len(righe_scartate) - 3
    attese = len(righe) - originali_scartati
    assert pq.read_table(uscita / "results.parquet").num_rows == attese, \
        "le righe non valide non devono finire nel formato intermedio"


def test_valori_mancanti_e_tempi(trasformato):
    for parquet in trasformato.glob("*.parquet"):
        tabella = pq.read_table(parquet)
        for nome in tabella.column_names:
            colonna = tabella.column(nome)
            if str(colonna.type) not in ("string", "large_string"):
                continue
            valori = [v for v in colonna.to_pylist() if v is not None]
            assert "\\N" not in valori, f"{parquet.name}.{nome}: il marcatore \\N deve diventare NULL"
            assert not any(TEMPO_TESTUALE.match(v) for v in valori), \
                f"{parquet.name}.{nome}: i tempi vanno convertiti in tipi numerici o intervalli"
    giri = pq.read_table(trasformato / "laps.parquet")
    assert any(str(giri.column(n).type).startswith(("int", "duration", "double", "decimal"))
               for n in giri.column_names if n.lower() not in ("raceid", "driverid", "lap", "position")), \
        "laps.parquet deve contenere il tempo del giro come numero o intervallo"
