"""Database: schema da migrazioni, integrità, coerenza con i CSV di origine."""
from collections import Counter, defaultdict

from conftest import REPO, api_json, leggi_csv

TABELLE = ["seasons", "races", "circuits", "drivers", "constructors",
           "sessions", "results", "laps", "stints", "pit_stops"]
# figlia -> genitori che deve raggiungere tramite chiavi esterne (anche indirettamente)
RAGGIUNGIBILI = {
    "races": {"seasons", "circuits"},
    "sessions": {"races"},
    "results": {"races", "drivers", "constructors"},
    "laps": {"races", "drivers"},
    "stints": {"races", "drivers"},
    "pit_stops": {"races", "drivers"},
}


def interroga(db, sql, *args):
    with db.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def test_schema_da_migrazioni(db):
    assert list((REPO / "database" / "migrations").glob("*.sql")), "nessuna migrazione in database/migrations/"
    storico = interroga(db, """SELECT table_name FROM information_schema.tables
        WHERE table_name IN ('flyway_schema_history', 'databasechangelog')""")
    assert storico, "manca la tabella di storico delle migrazioni"
    presenti = {r[0] for r in interroga(db, "SELECT table_name FROM information_schema.tables WHERE table_schema='public'")}
    assert set(TABELLE) <= presenti, f"tabelle mancanti: {set(TABELLE) - presenti}"


def test_chiavi_primarie_ed_esterne(db):
    con_pk = {r[0] for r in interroga(db, """SELECT tc.table_name FROM information_schema.table_constraints tc
        WHERE tc.table_schema='public' AND tc.constraint_type='PRIMARY KEY'""")}
    assert set(TABELLE) <= con_pk, f"tabelle senza chiave primaria: {set(TABELLE) - con_pk}"

    archi = defaultdict(set)
    for figlia, genitore, valida in interroga(db, """SELECT c.conrelid::regclass::text, c.confrelid::regclass::text, c.convalidated
            FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE c.contype='f' AND n.nspname='public'"""):
        assert valida, f"chiave esterna {figlia}->{genitore} non convalidata"
        archi[figlia.strip('"')].add(genitore.strip('"'))

    def raggiunge(da):
        visti, coda = set(), [da]
        while coda:
            for g in archi[coda.pop()] - visti:
                visti.add(g); coda.append(g)
        return visti

    for figlia, genitori in RAGGIUNGIBILI.items():
        assert genitori <= raggiunge(figlia), f"{figlia} non è collegata tramite chiavi esterne a {genitori - raggiunge(figlia)}"


def test_chiave_naturale_gare(db, gare_api):
    vincoli_unici = interroga(db, """SELECT count(*) FROM pg_index i
        WHERE i.indrelid = 'races'::regclass AND i.indisunique AND NOT i.indisprimary""")[0][0]
    assert vincoli_unici >= 1, "races deve avere un vincolo di unicità sulla chiave naturale (stagione + round)"
    for anno in {a for a, _ in gare_api}:
        round_ = [g["round"] for g in api_json(f"/api/seasons/{anno}/races")]
        assert len(round_) == len(set(round_)), f"round duplicati nella stagione {anno}"


def test_coerenza_con_csv(gare_api, scarti_per_gara):
    gare_csv = {r["raceId"]: (int(r["year"]), int(r["round"])) for r in leggi_csv("races.csv")}
    risultati_csv = Counter(r["raceId"] for r in leggi_csv("results.csv"))
    giri_per_gara = Counter(r["raceId"] for r in leggi_csv("lap_times.csv"))

    assert set(gare_csv.values()) == set(gare_api), "le gare dell'API non coincidono con races.csv"
    for race_id, chiave in sorted(gare_csv.items(), key=lambda x: x[1]):
        gara = gare_api[chiave]
        risultati = api_json(f"/api/races/{gara['id']}/results")
        attesi = risultati_csv[race_id] - scarti_per_gara[("results.csv", race_id)]
        assert len(risultati) == attesi, f"gara {chiave}: {len(risultati)} risultati, attesi {attesi}"

        giri = sum(len(api_json(f"/api/races/{gara['id']}/laps/{r['driver']['id']}")) for r in risultati)
        attesi = giri_per_gara[race_id] - scarti_per_gara[("lap_times.csv", race_id)]
        assert giri == attesi, f"gara {chiave}: {giri} giri, attesi {attesi}"
