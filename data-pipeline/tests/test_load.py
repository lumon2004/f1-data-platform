"""`load`: controlli che non richiedono un database, e test su un database dedicato.

I test che scrivono su PostgreSQL girano **solo** se la variabile d'ambiente
`F1_PIPELINE_TEST_DSN` indica un database dedicato, già migrato (V1..V4) e
sacrificabile: i test ne svuotano le tabelle. Esempio:

    F1_PIPELINE_TEST_DSN="host=f1-pipe-db dbname=postgres user=postgres password=prova"

Non usano mai le variabili POSTGRES_* dell'ambiente: quelle possono indicare
il database dello stack di verifica, che i test non devono toccare. Il
caricamento sul sistema vero è coperto dai test di accettazione.
"""

from __future__ import annotations

import os

import psycopg
import pytest
from conftest import N, colonna, scrivi_csv
from psycopg.conninfo import conninfo_to_dict

from f1_pipeline import cli, load
from f1_pipeline.tabelle import TABELLE
from f1_pipeline.transform import trasforma

VAR_DSN = "F1_PIPELINE_TEST_DSN"
DSN = os.environ.get(VAR_DSN, "").strip()
# Valori finti, nell'ordine di load.VARIABILI (host, porta, database, utente, parola d'ordine).
AMBIENTE_FINTO = dict(zip(load.VARIABILI, ("db.invalid", "5432", "f1", "f1", "finta")))
FINTA = "parola-segreta-di-prova"


# ---------- Senza database ----------


def test_parametri_dalle_variabili_d_ambiente():
    parametri = load.parametri_connessione(AMBIENTE_FINTO)
    assert (parametri["host"], parametri["port"], parametri["dbname"], parametri["user"]) == (
        "db.invalid", 5432, "f1", "f1",
    )
    predefiniti = load.parametri_connessione(
        {nome: valore for nome, valore in AMBIENTE_FINTO.items() if nome not in ("POSTGRES_HOST", "POSTGRES_PORT")}
    )
    assert (predefiniti["host"], predefiniti["port"]) == ("localhost", 5432)


def test_variabili_mancanti_errore_con_i_soli_nomi(tmp_path, monkeypatch, capsys):
    for nome in load.VARIABILI:
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("POSTGRES_USER", "utente-di-prova")
    assert cli.main(["load", "--input", str(tmp_path)]) == 1
    errore = capsys.readouterr().err
    assert "POSTGRES_DB" in errore and "POSTGRES_PASSWORD" in errore
    assert "utente-di-prova" not in errore


def test_porta_non_numerica():
    with pytest.raises(load.ErroreCaricamento, match="POSTGRES_PORT"):
        load.parametri_connessione({**AMBIENTE_FINTO, "POSTGRES_PORT": "abc"})


def test_input_non_prodotto_da_transform(tmp_path, capsys):
    assert load.esegui(tmp_path / "manca", AMBIENTE_FINTO) == 1
    assert "non esiste" in capsys.readouterr().err
    (tmp_path / "vuota").mkdir()
    assert load.esegui(tmp_path / "vuota", AMBIENTE_FINTO) == 1
    assert "results.parquet" in capsys.readouterr().err


def test_colonne_inattese_rifiutate_prima_di_connettersi(tmp_path, csv_puliti, capsys):
    import pyarrow.parquet as pq

    uscita = tmp_path / "out"
    trasforma(csv_puliti, uscita)
    laps = pq.read_table(uscita / "laps.parquet")
    pq.write_table(laps.rename_columns(["raceId", *laps.column_names[1:]]), uscita / "laps.parquet")
    assert load.esegui(uscita, AMBIENTE_FINTO) == 1
    assert "laps.parquet" in capsys.readouterr().err


def test_database_irraggiungibile_errore_chiaro_senza_password(tmp_path, csv_puliti, capsys):
    uscita = tmp_path / "out"
    trasforma(csv_puliti, uscita)
    ambiente = dict(zip(load.VARIABILI, ("127.0.0.1", "1", "f1", "f1", FINTA)))
    assert load.esegui(uscita, ambiente) == 1
    errore = capsys.readouterr().err
    assert "connessione a PostgreSQL non riuscita" in errore
    assert FINTA not in errore


# ---------- Con un database dedicato ----------

con_database = pytest.mark.skipif(
    not DSN,
    reason=f"{VAR_DSN} non impostata: i test che scrivono su PostgreSQL richiedono un "
    "database dedicato e già migrato (il caricamento resta coperto dai test di accettazione)",
)


@pytest.fixture
def ambiente_db():
    """Variabili POSTGRES_* ricavate dal DSN di prova; tabelle svuotate prima del test."""
    parti = conninfo_to_dict(DSN)
    ambiente = {
        "POSTGRES_HOST": str(parti.get("host", "localhost")),
        "POSTGRES_PORT": str(parti.get("port", "5432")),
        "POSTGRES_DB": str(parti["dbname"]),
        "POSTGRES_USER": str(parti["user"]),
        "POSTGRES_PASSWORD": str(parti.get("password") or "non-usata"),
    }
    stessa = all(
        os.environ.get(nome) == ambiente[nome] for nome in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB")
    )
    if stessa:
        pytest.skip(f"{VAR_DSN} indica lo stesso database delle variabili POSTGRES_*: serve un database dedicato")
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("TRUNCATE " + ", ".join(t.nome for t in TABELLE) + " RESTART IDENTITY")
    return ambiente


def conteggi() -> dict[str, int]:
    with psycopg.connect(DSN) as conn:
        return {t.nome: conn.execute(f"SELECT count(*) FROM {t.nome}").fetchone()[0] for t in TABELLE}


def uno(query: str, *parametri):
    with psycopg.connect(DSN) as conn:
        return conn.execute(query, parametri).fetchone()


@con_database
def test_caricamento_e_idempotenza(tmp_path, csv_puliti, ambiente_db):
    uscita = tmp_path / "out"
    esito = trasforma(csv_puliti, uscita)
    assert load.esegui(uscita, ambiente_db) == 0
    prima = conteggi()
    assert prima == esito.righe
    id_prima = uno("SELECT array_agg(id ORDER BY session_type, source_id) FROM results")[0]
    scritte = load.carica(uscita, ambiente_db)
    assert load.esegui(uscita, ambiente_db) == 0
    assert conteggi() == prima, "ricaricare gli stessi dati non cambia il numero di righe"
    assert all(n == 0 for nome, (_, n) in scritte.items() if nome != "stints"), "nessuna riga riscritta"
    assert uno("SELECT array_agg(id ORDER BY session_type, source_id) FROM results")[0] == id_prima


@con_database
def test_valori_caricati(tmp_path, csv_puliti, ambiente_db):
    uscita = tmp_path / "out"
    trasforma(csv_puliti, uscita)
    load.carica(uscita, ambiente_db)
    assert uno(
        "SELECT position, outcome, points::text, time_ms, fastest_lap_time_ms, grid_position "
        "FROM results WHERE session_type = 'race' AND source_id = 100"
    ) == (1, "classified", "25.00", 301500, 99019, 1)
    assert uno(
        "SELECT position, outcome, grid_position FROM results WHERE session_type = 'race' AND source_id = 102"
    ) == (None, "retired", None)
    assert uno("SELECT session_date::text, start_time_utc::text FROM sessions WHERE race_id = 10 AND session_type = 'race'") == (
        "2023-03-05", "15:00:00",
    )
    assert uno("SELECT count(*) FROM sessions WHERE session_type = 'race'")[0] == 2
    assert uno("SELECT time_of_day::text, duration_ms FROM pit_stops WHERE driver_id = 1") == ("15:05:10", 22500)
    assert uno("SELECT code, permanent_number, date_of_birth::text FROM drivers WHERE id = 3") == (None, None, "1920-05-05")
    assert uno("SELECT latitude::text FROM circuits WHERE id = 1") == ("45.615600",)


@con_database
def test_upsert_aggiorna_senza_duplicare_e_sostituisce_gli_stint(tmp_path, base, ambiente_db):
    scrivi_csv(tmp_path / "csv1", base)
    trasforma(tmp_path / "csv1", tmp_path / "out1")
    load.carica(tmp_path / "out1", ambiente_db)
    prima = conteggi()

    base["results.csv"][0][colonna("results.csv", "points")] = "26"
    base["drivers.csv"][0][colonna("drivers.csv", "code")] = N
    base["pit_stops.csv"] = base["pit_stops.csv"][:1]  # il pilota 2 non si ferma più
    scrivi_csv(tmp_path / "csv2", base)
    trasforma(tmp_path / "csv2", tmp_path / "out2")
    scritte = load.carica(tmp_path / "out2", ambiente_db)

    dopo = conteggi()
    assert scritte["results"][1] == 1 and scritte["drivers"][1] == 1
    assert uno("SELECT points::text FROM results WHERE session_type = 'race' AND source_id = 100") == ("26.00",)
    assert uno("SELECT code FROM drivers WHERE id = 1") == (None,)
    assert dopo["stints"] == prima["stints"] - 1, "stint sostituiti, nessuna riga orfana"
    assert uno("SELECT count(*) FROM stints WHERE driver_id = 2")[0] == 1
    assert {k: v for k, v in dopo.items() if k not in ("stints", "pit_stops")} == {
        k: v for k, v in prima.items() if k not in ("stints", "pit_stops")
    }


@con_database
def test_errore_a_meta_non_lascia_nulla(tmp_path, csv_puliti, ambiente_db):
    """Una sola transazione: se una tabella fallisce, non entra niente."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    uscita = tmp_path / "out"
    trasforma(csv_puliti, uscita)
    giri = pq.read_table(uscita / "laps.parquet")
    indice = giri.column_names.index("time_ms")
    rotta = giri.set_column(indice, "time_ms", pa.array([-1] * giri.num_rows, pa.int32()))
    pq.write_table(rotta, uscita / "laps.parquet")
    with pytest.raises(load.ErroreCaricamento, match="ck_laps_time_ms"):
        load.carica(uscita, ambiente_db)
    assert set(conteggi().values()) == {0}


@con_database
def test_schema_assente_errore_chiaro(tmp_path, csv_puliti, ambiente_db, monkeypatch, capsys):
    uscita = tmp_path / "out"
    trasforma(csv_puliti, uscita)
    # Uno schema di ricerca senza tabelle equivale a un database non migrato.
    monkeypatch.setenv("PGOPTIONS", "-c search_path=pg_catalog")
    assert load.esegui(uscita, ambiente_db) == 1
    errore = capsys.readouterr().err
    assert "migrazioni" in errore and "seasons" in errore
