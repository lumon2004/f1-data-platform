"""`transform`: validazione, normalizzazione, cascata, sessioni, stint, riproducibilità."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from conftest import INTESTAZIONI, N, colonna, scrivi_csv

from f1_pipeline import cli
from f1_pipeline.tabelle import FILE_PARQUET, TABELLE
from f1_pipeline.transform import categoria, deriva_stint, trasforma


def esegui(tmp_path: Path, dati) -> tuple[Path, object]:
    ingresso, uscita = tmp_path / "csv", tmp_path / "out"
    scrivi_csv(ingresso, dati)
    return uscita, trasforma(ingresso, uscita)


def tabella(uscita: Path, nome: str) -> list[dict]:
    """Righe di una tabella; `results` unisce gare e sprint, come fa il caricamento."""
    righe = pq.read_table(uscita / f"{nome}.parquet").to_pylist()
    if nome == "results":
        righe += pq.read_table(uscita / "sprint_results.parquet").to_pylist()
    return righe


def scarti_di(esito, file: str) -> dict[int, str]:
    return {s["riga"]: s["motivo"] for s in esito.scarti if s["file"] == file}


def imposta(dati, file: str, indice: int, **valori) -> None:
    for nome, valore in valori.items():
        dati[file][indice][colonna(file, nome)] = valore


def impronta(cartella: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(cartella.iterdir())}


# ---------- Dataset pulito ----------


def test_dataset_pulito_nessuno_scarto(tmp_path, base):
    uscita, esito = esegui(tmp_path, base)
    assert esito.scarti == [] and esito.annullati == []
    assert esito.righe == {
        "seasons": 2, "circuits": 3, "drivers": 4, "constructors": 3, "statuses": 3,
        "races": 2, "sessions": 7, "results": 7, "qualifying_results": 4,
        "laps": 7, "pit_stops": 3, "stints": 5,
    }
    assert {p.name for p in uscita.iterdir()} == {f"{t.nome}.parquet" for t in TABELLE} | {
        "sprint_results.parquet", "scarti.json", "valori_annullati.json", "valori_derivati.json"
    }
    assert esito.derivati == [] and json.loads((uscita / "valori_derivati.json").read_text()) == []
    assert json.loads((uscita / "scarti.json").read_text()) == []


def test_un_parquet_per_tabella_con_le_colonne_dello_schema(tmp_path, base):
    uscita, _ = esegui(tmp_path, base)
    for t in TABELLE:
        for file in t.file:
            letta = pq.read_table(uscita / file)
            assert tuple(letta.column_names) == t.nomi
            assert letta.schema.metadata is None, "nessun metadato d'ambiente nei Parquet"
    assert "id" not in pq.read_table(uscita / "results.parquet").column_names


def test_results_parquet_contiene_le_sole_gare(tmp_path, base):
    """Come results.csv: le sprint stanno in sprint_results.parquet, stesse colonne."""
    uscita, esito = esegui(tmp_path, base)
    gare = pq.read_table(uscita / "results.parquet").to_pylist()
    sprint = pq.read_table(uscita / "sprint_results.parquet").to_pylist()
    assert len(gare) == len(base["results.csv"]) and {r["session_type"] for r in gare} == {"race"}
    assert len(sprint) == len(base["sprint_results.csv"]) and {r["session_type"] for r in sprint} == {"sprint"}
    assert esito.righe["results"] == len(gare) + len(sprint)


# ---------- Validazione: ogni tipo di scarto ----------


@pytest.mark.parametrize(
    ("modifica", "tipo"),
    [
        ({"raceId": ""}, "chiave mancante"),
        ({"resultId": N}, "chiave mancante"),
        ({"driverId": N}, "chiave mancante"),
        ({"raceId": "abc"}, "tipo non valido"),
        ({"resultId": "1.5"}, "tipo non valido"),
        ({"points": "tanti"}, "tipo non valido"),
        ({"laps": "x"}, "tipo non valido"),
        ({"points": N}, "campo obbligatorio mancante"),
        ({"positionOrder": N}, "campo obbligatorio mancante"),
        ({"positionText": N}, "campo obbligatorio mancante"),
        ({"positionOrder": "0"}, "valore non valido"),
        ({"points": "-1"}, "valore non valido"),
        ({"laps": "-3"}, "valore non valido"),
        ({"positionText": "X"}, "valore non valido"),
        ({"positionText": "0"}, "valore non valido"),  # numerico ma non positivo
        ({"positionText": "0", "position": N}, "valore non valido"),
        ({"positionText": "99999999999", "position": N}, "tipo non valido"),
        ({"positionText": "R"}, "valore non valido"),  # ritirato ma con position
        ({"raceId": "999"}, "riferimento inesistente"),
        ({"driverId": "999"}, "riferimento inesistente"),
        ({"constructorId": "999"}, "riferimento inesistente"),
        ({"statusId": "999"}, "riferimento inesistente"),
    ],
)
def test_risultato_scartato_e_registrato(tmp_path, base, modifica, tipo):
    imposta(base, "results.csv", 1, **modifica)  # seconda riga di dati = riga 3 del file
    uscita, esito = esegui(tmp_path, base)
    scarti = scarti_di(esito, "results.csv")
    assert list(scarti) == [3]
    assert categoria(scarti[3]) == tipo
    assert 101 not in {r["source_id"] for r in tabella(uscita, "results") if r["session_type"] == "race"}
    assert json.loads((uscita / "scarti.json").read_text()) == esito.scarti
    assert set(esito.scarti[0]) == {"file", "riga", "motivo"}


# ---------- Esito e posizione ----------


def _risultato(uscita, origine):
    return next(r for r in tabella(uscita, "results") if (r["session_type"], r["source_id"]) == ("race", origine))


def test_posizione_derivata_da_position_text(tmp_path, base):
    """positionText intero positivo senza position: classificato, posizione ricavata."""
    imposta(base, "results.csv", 1, position=N)  # riga 3: positionText "2"
    uscita, esito = esegui(tmp_path, base)
    assert esito.scarti == [] and esito.annullati == []
    assert esito.derivati == [
        {"file": "results.csv", "riga": 3, "colonna": "position", "valore": 2, "origine": "positionText"}
    ]
    assert json.loads((uscita / "valori_derivati.json").read_text()) == esito.derivati
    risultato = _risultato(uscita, 101)
    assert (risultato["position"], risultato["outcome"]) == (2, "classified")
    assert esito.righe["laps"] == 7, "nessuna cascata: i giri del pilota restano"


@pytest.mark.parametrize("sbagliata", ["abc", "0", "-3", "2.0"])
def test_position_non_valida_annullata_e_poi_derivata(tmp_path, base, sbagliata):
    imposta(base, "results.csv", 1, position=sbagliata)
    uscita, esito = esegui(tmp_path, base)
    assert esito.scarti == []
    assert [(a["riga"], a["colonna"], a["valore"]) for a in esito.annullati] == [(3, "position", sbagliata)]
    assert [(d["riga"], d["valore"]) for d in esito.derivati] == [(3, 2)]
    assert _risultato(uscita, 101)["position"] == 2


def test_con_entrambe_valorizzate_vale_position(tmp_path, base):
    imposta(base, "results.csv", 1, positionText="7")  # position resta 2
    uscita, esito = esegui(tmp_path, base)
    assert esito.scarti == [] and esito.derivati == []
    risultato = _risultato(uscita, 101)
    assert (risultato["position"], risultato["outcome"]) == (2, "classified")


def test_posizione_derivata_anche_nelle_sprint(tmp_path, base):
    imposta(base, "sprint_results.csv", 0, position=N)
    _, esito = esegui(tmp_path, base)
    assert esito.scarti == []
    assert [(d["file"], d["riga"], d["valore"]) for d in esito.derivati] == [("sprint_results.csv", 2, 1)]


def test_derivazione_di_una_riga_scartata_non_si_registra(tmp_path, base):
    imposta(base, "results.csv", 1, position=N, driverId="999")
    _, esito = esegui(tmp_path, base)
    assert categoria(scarti_di(esito, "results.csv")[3]) == "riferimento inesistente"
    assert esito.derivati == []


def test_riepilogo_conta_le_posizioni_derivate(tmp_path, base, capsys):
    imposta(base, "results.csv", 1, position=N)
    scrivi_csv(tmp_path / "csv", base)
    assert cli.main(["transform", "--input", str(tmp_path / "csv"), "--output", str(tmp_path / "out")]) == 0
    assert "Posizioni derivate da positionText: 1" in capsys.readouterr().out


def test_duplicato_si_tiene_la_prima_riga(tmp_path, base):
    copia = list(base["results.csv"][0])
    copia[colonna("results.csv", "points")] = "99"
    base["results.csv"].append(copia)
    uscita, esito = esegui(tmp_path, base)
    scarti = scarti_di(esito, "results.csv")
    assert list(scarti) == [7] and categoria(scarti[7]) == "duplicato"
    assert "riga 2" in scarti[7]
    tenuta = [r for r in tabella(uscita, "results") if (r["session_type"], r["source_id"]) == ("race", 100)]
    assert len(tenuta) == 1 and tenuta[0]["points"] == Decimal("25.00")


@pytest.mark.parametrize(
    ("file", "tabella_out"),
    [("qualifying.csv", "qualifying_results"), ("lap_times.csv", "laps"), ("pit_stops.csv", "pit_stops")],
)
def test_duplicati_su_chiave_naturale(tmp_path, base, file, tabella_out):
    righe_prima = len(base[file])
    copia = list(base[file][0])
    if file == "qualifying.csv":
        copia[colonna(file, "qualifyId")] = "999"  # altro id, stessa (gara, pilota)
    base[file].append(copia)
    uscita, esito = esegui(tmp_path, base)
    scarti = scarti_di(esito, file)
    assert list(scarti) == [righe_prima + 2] and categoria(scarti[righe_prima + 2]) == "duplicato"
    assert len(tabella(uscita, tabella_out)) == righe_prima


def test_stesso_resultid_in_gara_e_sprint_non_e_un_duplicato(tmp_path, base):
    imposta(base, "sprint_results.csv", 0, resultId="100")
    _, esito = esegui(tmp_path, base)
    assert esito.scarti == []


def test_duplicati_sulle_chiavi_naturali_delle_anagrafiche(tmp_path, base):
    base["drivers.csv"].append(["5", "verstappen", N, N, "Altro", "Pilota", N, N, N])
    base["status.csv"].append(["4", "Finished"])
    base["circuits.csv"].append(list(base["circuits.csv"][0]))
    base["races.csv"].append(["12", "2023", "1", "2", "Stesso round", "2023-04-01", N, N] + [N] * 10)
    uscita, esito = esegui(tmp_path, base)
    assert {(s["file"], categoria(s["motivo"])) for s in esito.scarti} == {
        ("drivers.csv", "duplicato"), ("status.csv", "duplicato"),
        ("circuits.csv", "duplicato"), ("races.csv", "duplicato"),
    }
    assert [r["id"] for r in tabella(uscita, "races")] == [10, 11]


def test_riga_malformata(tmp_path, base):
    ingresso = tmp_path / "csv"
    scrivi_csv(ingresso, base)
    with open(ingresso / "results.csv", "a", encoding="utf-8") as f:
        f.write("900,10,1\n")
    esito = trasforma(ingresso, tmp_path / "out")
    assert categoria(scarti_di(esito, "results.csv")[7]) == "riga malformata"


def test_numerazione_delle_righe_intestazione_uguale_a_uno(tmp_path, base):
    imposta(base, "results.csv", 0, raceId="")
    imposta(base, "results.csv", 4, raceId="abc")
    _, esito = esegui(tmp_path, base)
    assert sorted(scarti_di(esito, "results.csv")) == [2, 6]


def test_caso_del_test_di_accettazione(tmp_path, base):
    """Tre righe sporche in coda: chiave mancante, tipo non valido, duplicato."""
    valida = base["results.csv"][0]
    mancante = list(valida); mancante[0] = "900"; mancante[1] = ""
    errata = list(valida); errata[0] = "901"; errata[1] = "abc"
    base["results.csv"] += [mancante, errata, list(valida)]
    uscita, esito = esegui(tmp_path, base)
    scarti = scarti_di(esito, "results.csv")
    assert [categoria(scarti[n]) for n in (7, 8, 9)] == ["chiave mancante", "tipo non valido", "duplicato"]
    assert pq.read_table(uscita / "results.parquet").num_rows == 5


def test_gara_senza_data_scartata_con_tutto_cio_che_la_cita(tmp_path, base):
    imposta(base, "races.csv", 1, date=N)
    uscita, esito = esegui(tmp_path, base)
    assert categoria(scarti_di(esito, "races.csv")[3]) == "campo obbligatorio mancante"
    per_risultati = scarti_di(esito, "results.csv")
    assert sorted(per_risultati) == [5, 6]
    assert all("scartate di races.csv" in m for m in per_risultati.values())
    assert categoria(scarti_di(esito, "qualifying.csv")[5]) == "riferimento inesistente"
    assert {r["race_id"] for r in tabella(uscita, "sessions")} == {10}


def test_pilota_scartato_porta_con_se_risultati_giri_e_soste(tmp_path, base):
    imposta(base, "drivers.csv", 1, surname=N)  # pilota 2: campo obbligatorio mancante
    uscita, esito = esegui(tmp_path, base)
    tipi = {(s["file"], categoria(s["motivo"])) for s in esito.scarti}
    assert tipi == {
        ("drivers.csv", "campo obbligatorio mancante"),
        ("results.csv", "riferimento inesistente"),
        ("sprint_results.csv", "riferimento inesistente"),
        ("qualifying.csv", "riferimento inesistente"),
        ("lap_times.csv", "riferimento inesistente"),
        ("pit_stops.csv", "riferimento inesistente"),
    }
    for nome in ("results", "qualifying_results", "laps", "pit_stops", "stints"):
        assert 2 not in {r["driver_id"] for r in tabella(uscita, nome)}


# ---------- Attributi facoltativi: NULL e registrazione, la riga resta ----------


def test_attributo_facoltativo_non_valido_diventa_null(tmp_path, base):
    imposta(base, "drivers.csv", 0, code="Ve", number="100", dob="ieri")
    imposta(base, "circuits.csv", 0, lat="91", alt="alto")
    imposta(base, "results.csv", 0, fastestLapTime="veloce", fastestLap="0", grid="-1", milliseconds="0")
    imposta(base, "qualifying.csv", 0, q3="abc")
    imposta(base, "lap_times.csv", 0, position="0")
    imposta(base, "pit_stops.csv", 0, time="25:00:00", milliseconds="-5")
    imposta(base, "races.csv", 1, time="mezzogiorno", fp1_time="10:00:00")
    uscita, esito = esegui(tmp_path, base)
    assert esito.scarti == [], "un attributo facoltativo non valido non scarta la riga"
    assert {(a["file"], a["riga"], a["colonna"]) for a in esito.annullati} == {
        ("drivers.csv", 2, "code"), ("drivers.csv", 2, "number"), ("drivers.csv", 2, "dob"),
        ("circuits.csv", 2, "lat"), ("circuits.csv", 2, "alt"),
        ("results.csv", 2, "fastestLapTime"), ("results.csv", 2, "fastestLap"),
        ("results.csv", 2, "grid"), ("results.csv", 2, "milliseconds"),
        ("qualifying.csv", 2, "q3"), ("lap_times.csv", 2, "position"),
        ("pit_stops.csv", 2, "time"), ("pit_stops.csv", 2, "milliseconds"),
        ("races.csv", 3, "time"), ("races.csv", 3, "fp1_time"),
    }
    assert all(a["motivo"] and a["valore"] for a in esito.annullati)
    assert json.loads((uscita / "valori_annullati.json").read_text()) == esito.annullati
    pilota = tabella(uscita, "drivers")[0]
    assert (pilota["code"], pilota["permanent_number"], pilota["date_of_birth"]) == (None, None, None)
    assert pilota["family_name"] == "Verstappen"
    risultato = next(r for r in tabella(uscita, "results") if r["source_id"] == 100 and r["session_type"] == "race")
    assert risultato["fastest_lap_time_ms"] is None and risultato["time_ms"] is None
    assert risultato["points"] == Decimal("25.00")
    assert tabella(uscita, "pit_stops")[0]["time_of_day"] is None


def test_attributi_annullati_di_una_riga_scartata_non_si_registrano(tmp_path, base):
    imposta(base, "results.csv", 0, fastestLapTime="veloce", raceId="")
    _, esito = esegui(tmp_path, base)
    assert len(esito.scarti) >= 1 and esito.annullati == []


# ---------- Normalizzazione ----------


def test_marcatori_null_e_valori_magici(tmp_path, base):
    uscita, _ = esegui(tmp_path, base)
    risultati = {(r["session_type"], r["source_id"]): r for r in tabella(uscita, "results")}
    ritirato = risultati[("race", 102)]
    assert ritirato["position"] is None and ritirato["outcome"] == "retired"
    assert ritirato["grid_position"] is None, "griglia 0 -> NULL"
    assert ritirato["fastest_lap_rank"] is None, "rank 0 -> NULL"
    assert ritirato["time_ms"] is None and ritirato["fastest_lap_speed_kph"] is None
    vincitore = risultati[("race", 100)]
    assert vincitore["outcome"] == "classified" and vincitore["position"] == 1
    assert vincitore["time_ms"] == 301500
    assert vincitore["fastest_lap_time_ms"] == 99019
    assert vincitore["fastest_lap_speed_kph"] == Decimal("210.123")
    assert risultati[("race", 103)]["points"] == Decimal("12.50")
    sprint = risultati[("sprint", 1)]
    assert sprint["fastest_lap_rank"] is None and sprint["fastest_lap_speed_kph"] is None
    assert sprint["fastest_lap_time_ms"] == 94000

    piloti = {p["id"]: p for p in tabella(uscita, "drivers")}
    assert piloti[3]["code"] is None and piloti[3]["permanent_number"] is None
    assert piloti[1]["date_of_birth"] == dt.date(1997, 9, 30)
    assert tabella(uscita, "circuits")[1]["altitude_m"] is None
    assert tabella(uscita, "circuits")[0]["latitude"] == Decimal("45.615600")


def test_tempi_e_durate_in_millisecondi(tmp_path, base):
    uscita, _ = esegui(tmp_path, base)
    qualifiche = {(q["race_id"], q["driver_id"]): q for q in tabella(uscita, "qualifying_results")}
    assert (qualifiche[(10, 1)]["q1_ms"], qualifiche[(10, 1)]["q3_ms"]) == (90100, 88999)
    assert qualifiche[(10, 2)]["q3_ms"] is None, "stringa vuota -> NULL"
    assert qualifiche[(10, 3)]["q2_ms"] is None
    assert [g["time_ms"] for g in tabella(uscita, "laps")][:3] == [101000, 99019, 101481]
    soste = tabella(uscita, "pit_stops")
    assert soste[0]["duration_ms"] == 22500 and soste[0]["time_of_day"] == dt.time(15, 5, 10)
    assert soste[2]["duration_ms"] == 1043456


def test_durata_dal_testo_se_mancano_i_millisecondi(tmp_path, base):
    imposta(base, "lap_times.csv", 0, milliseconds=N)
    imposta(base, "pit_stops.csv", 2, milliseconds=N)
    uscita, esito = esegui(tmp_path, base)
    assert esito.scarti == []
    assert tabella(uscita, "laps")[0]["time_ms"] == 101000
    assert tabella(uscita, "pit_stops")[2]["duration_ms"] == 1043456


def test_giro_senza_tempo_scartato(tmp_path, base):
    imposta(base, "lap_times.csv", 0, milliseconds=N, time=N)
    _, esito = esegui(tmp_path, base)
    assert categoria(scarti_di(esito, "lap_times.csv")[2]) == "campo obbligatorio mancante"


def test_nessun_marcatore_ne_tempo_testuale_nei_parquet(tmp_path, base):
    uscita, _ = esegui(tmp_path, base)
    tempo = re.compile(r"^\d+:\d{2}\.\d{3}$")
    for parquet in uscita.glob("*.parquet"):
        letta = pq.read_table(parquet)
        for nome in letta.column_names:
            if str(letta.column(nome).type) == "string":
                valori = [v for v in letta.column(nome).to_pylist() if v is not None]
                assert r"\N" not in valori and "" not in valori
                assert not any(tempo.match(v) for v in valori)
            elif nome.endswith("_ms"):
                assert str(letta.column(nome).type) == "int32"


def test_sprint_results_senza_rank_e_colonne_in_altro_ordine(tmp_path, base):
    """I CSV si leggono per nome di colonna, non per posizione."""
    ingresso = tmp_path / "csv"
    scrivi_csv(ingresso, base)
    originale = (ingresso / "results.csv").read_text().splitlines()
    rovesciato = [",".join(reversed(riga.split(","))) for riga in originale]
    (ingresso / "results.csv").write_text("\n".join(rovesciato) + "\n")
    uscita = tmp_path / "out"
    esito = trasforma(ingresso, uscita)
    assert esito.scarti == []
    assert esito.righe["results"] == 7


# ---------- Cascata ----------


def test_giri_e_soste_di_un_pilota_senza_risultato_valido(tmp_path, base):
    imposta(base, "results.csv", 1, positionText="X")  # pilota 2, gara 10: risultato scartato
    uscita, esito = esegui(tmp_path, base)
    giri = scarti_di(esito, "lap_times.csv")
    soste = scarti_di(esito, "pit_stops.csv")
    assert sorted(giri) == [5, 6, 7] and sorted(soste) == [3, 4]
    assert {categoria(m) for m in (*giri.values(), *soste.values())} == {"senza risultato valido"}
    # Conteggio alla maniera del test di coerenza: giri dei piloti con risultato.
    con_risultato = {(r["race_id"], r["driver_id"]) for r in tabella(uscita, "results") if r["session_type"] == "race"}
    caricati = tabella(uscita, "laps")
    assert all((g["race_id"], g["driver_id"]) in con_risultato for g in caricati)
    assert len(caricati) == len(base["lap_times.csv"]) - len(giri)
    assert 2 not in {s["driver_id"] for s in tabella(uscita, "stints")}


def test_il_risultato_sprint_non_basta_per_tenere_i_giri(tmp_path, base):
    imposta(base, "results.csv", 0, laps="x")  # pilota 1 resta solo nella sprint della gara 10
    _, esito = esegui(tmp_path, base)
    assert sorted(scarti_di(esito, "lap_times.csv")) == [2, 3, 4]


# ---------- Sessioni ----------


def test_sessione_race_sempre_presente(tmp_path, base):
    base["races.csv"].append(["12", "2024", "2", "1", "Gara senza dati", "2024-04-01", N, N] + [N] * 10)
    uscita, esito = esegui(tmp_path, base)
    assert esito.scarti == []
    sessioni = {(s["race_id"], s["session_type"]): s for s in tabella(uscita, "sessions")}
    gare = [g["id"] for g in tabella(uscita, "races")]
    assert gare == [10, 11, 12]
    for gara in gare:
        assert sessioni[(gara, "race")]["session_date"] is not None
    assert [t for (g, t) in sessioni if g == 12] == ["race"]
    assert sessioni[(10, "race")] == {
        "race_id": 10, "session_type": "race",
        "session_date": dt.date(2023, 3, 5), "start_time_utc": dt.time(15, 0),
    }
    assert sessioni[(11, "race")]["start_time_utc"] is None


def test_sessioni_secondarie(tmp_path, base):
    uscita, _ = esegui(tmp_path, base)
    sessioni = {(s["race_id"], s["session_type"]): s for s in tabella(uscita, "sessions")}
    assert {t for (g, t) in sessioni if g == 10} == {"race", "fp1", "fp2", "qualifying", "sprint"}
    # Gara 11: qualifica senza data, creata perché esistono righe di qualifica.
    assert {t for (g, t) in sessioni if g == 11} == {"race", "qualifying"}
    assert sessioni[(11, "qualifying")]["session_date"] is None
    assert sessioni[(11, "qualifying")]["start_time_utc"] is None
    # Ogni riga figlia ha la sua sessione (chiave esterna composta).
    for nome in ("results", "qualifying_results", "laps", "pit_stops", "stints"):
        assert {(r["race_id"], r["session_type"]) for r in tabella(uscita, nome)} <= set(sessioni)


def test_races_csv_senza_colonne_delle_sessioni(tmp_path, base):
    """Versioni vecchie del dataset: races.csv ha solo date e time della gara."""
    ingresso = tmp_path / "csv"
    scrivi_csv(ingresso, base)
    righe = [",".join(r.split(",")[:8]) for r in (ingresso / "races.csv").read_text().splitlines()]
    (ingresso / "races.csv").write_text("\n".join(righe) + "\n")
    uscita = tmp_path / "out"
    assert trasforma(ingresso, uscita).scarti == []
    assert {(s["race_id"], s["session_type"]) for s in tabella(uscita, "sessions")} == {
        (10, "race"), (10, "qualifying"), (10, "sprint"), (11, "race"), (11, "qualifying"),
    }


# ---------- Stint ----------


def test_stint_dal_dataset(tmp_path, base):
    uscita, _ = esegui(tmp_path, base)
    stint = [(s["race_id"], s["session_type"], s["driver_id"], s["stint_number"], s["start_lap"], s["end_lap"], s["compound"])
             for s in tabella(uscita, "stints")]
    assert stint == [
        (10, "race", 1, 1, 1, 2, None),
        (10, "race", 1, 2, 3, 3, None),
        (10, "race", 2, 1, 1, 1, None),  # sosta al giro 1
        (10, "race", 2, 2, 2, 3, None),  # sosta all'ultimo giro: nessuno stint vuoto
        (10, "race", 3, 1, 1, 1, None),  # nessuna sosta: uno stint solo
    ]


def test_deriva_stint_casi_limite():
    giri = {
        (1, "race", 1): 50,   # due soste nello stesso giro
        (1, "race", 2): 10,   # sosta registrata oltre l'ultimo giro completato
        (1, "race", 3): 0,    # nessun giro completato: nessuno stint
        (1, "race", 4): 30,   # nessuna sosta
        (2, "race", 1): 60,   # gara senza soste registrate: nessuno stint
        (1, "sprint", 1): 20, # sessione senza soste
    }
    soste = [(1, "race", 1, 20), (1, "race", 1, 20), (1, "race", 1, 35), (1, "race", 2, 12), (1, "race", 3, 1)]
    assert sorted(deriva_stint(giri, soste)) == [
        (1, "race", 1, 1, 1, 20, None),
        (1, "race", 1, 2, 21, 35, None),
        (1, "race", 1, 3, 36, 50, None),
        (1, "race", 2, 1, 1, 10, None),
        (1, "race", 4, 1, 1, 30, None),
    ]


def test_stint_rispettano_i_vincoli_dello_schema(tmp_path, base):
    uscita, _ = esegui(tmp_path, base)
    stint = tabella(uscita, "stints")
    assert all(s["start_lap"] >= 1 and s["end_lap"] >= s["start_lap"] for s in stint)
    inizi = [(s["race_id"], s["session_type"], s["driver_id"], s["start_lap"]) for s in stint]
    assert len(inizi) == len(set(inizi))


# ---------- Riproducibilità ----------


def test_riproducibilita_al_byte(tmp_path, base):
    imposta(base, "results.csv", 1, raceId="abc")       # scarti non vuoti
    imposta(base, "drivers.csv", 0, code="troppo lungo")  # annullati non vuoti
    imposta(base, "results.csv", 3, position=N)           # derivati non vuoti
    ingresso = tmp_path / "csv"
    scrivi_csv(ingresso, base)
    trasforma(ingresso, tmp_path / "a")
    trasforma(ingresso, tmp_path / "b")
    trasforma(ingresso, tmp_path / "a")  # riscrivere sopra un output esistente non cambia nulla
    prima, seconda = impronta(tmp_path / "a"), impronta(tmp_path / "b")
    assert len(prima) == len(FILE_PARQUET) + 3
    assert prima == seconda


def test_ordine_delle_righe_indipendente_dall_ordine_dei_csv(tmp_path, base):
    scrivi_csv(tmp_path / "csv1", base)
    trasforma(tmp_path / "csv1", tmp_path / "a")
    for file in ("lap_times.csv", "pit_stops.csv", "qualifying.csv", "drivers.csv", "races.csv"):
        base[file].reverse()
    scrivi_csv(tmp_path / "csv2", base)
    trasforma(tmp_path / "csv2", tmp_path / "b")
    assert impronta(tmp_path / "a") == impronta(tmp_path / "b")


# ---------- Input inutilizzabile ----------


def test_file_obbligatorio_mancante(tmp_path, csv_puliti, capsys):
    (csv_puliti / "results.csv").unlink()
    assert cli.main(["transform", "--input", str(csv_puliti), "--output", str(tmp_path / "out")]) == 1
    assert "results.csv" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_colonna_mancante(tmp_path, csv_puliti, capsys):
    testo = (csv_puliti / "lap_times.csv").read_text().replace("milliseconds", "millis", 1)
    (csv_puliti / "lap_times.csv").write_text(testo)
    assert cli.main(["transform", "--input", str(csv_puliti), "--output", str(tmp_path / "out")]) == 1
    errore = capsys.readouterr().err
    assert "lap_times.csv" in errore and "milliseconds" in errore


def test_cartella_di_input_inesistente(tmp_path, capsys):
    assert cli.main(["transform", "--input", str(tmp_path / "manca"), "--output", str(tmp_path / "out")]) == 1
    assert "non esiste" in capsys.readouterr().err


def test_file_facoltativi_assenti_valgono_come_vuoti(tmp_path, csv_puliti, capsys):
    for file in ("sprint_results.csv", "qualifying.csv", "lap_times.csv", "pit_stops.csv"):
        (csv_puliti / file).unlink()
    esito = trasforma(csv_puliti, tmp_path / "out")
    assert esito.scarti == []
    assert (esito.righe["results"], esito.righe["laps"], esito.righe["stints"]) == (5, 0, 0)
    assert esito.righe["sessions"] == 6  # resta la qualifica della gara 10, che ha una data
    assert tuple(pq.read_table(tmp_path / "out" / "laps.parquet").column_names) == (
        "race_id", "session_type", "driver_id", "lap_number", "position", "time_ms",
    )
    assert "Avviso" in capsys.readouterr().err


def test_cli_transform_stampa_il_riepilogo(tmp_path, csv_puliti, capsys):
    assert cli.main(["transform", "--input", str(csv_puliti), "--output", str(tmp_path / "out")]) == 0
    uscita = capsys.readouterr().out
    assert "results" in uscita and "Righe scartate: 0" in uscita
    assert set(INTESTAZIONI) >= {"results.csv"}
