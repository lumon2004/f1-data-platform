"""Configurazione condivisa dei test di accettazione (contratto in README.md)."""
import csv
import json
import os
import subprocess
from collections import Counter
from pathlib import Path

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

REPO = Path(__file__).resolve().parents[2]
SAMPLE = REPO / "data-pipeline" / "sample"
VERIFICA = REPO / ".verifica"
CFG = json.loads((REPO / "config" / "accettazione.json").read_text())

API_URL = os.environ.get("API_URL", f"http://localhost:{CFG['porte_verifica']['api']}").rstrip("/")
WEB_URL = os.environ.get("WEB_URL", f"http://localhost:{CFG['porte_verifica']['web']}").rstrip("/")


# ---------- CSV del dataset di esempio ----------

def leggi_csv(nome, cartella=SAMPLE):
    """Righe di un CSV Ergast come dict; ogni riga porta il suo numero (intestazione = riga 1)."""
    with open(cartella / nome, newline="", encoding="utf-8") as f:
        righe = list(csv.DictReader(f))
    for i, r in enumerate(righe, start=2):
        r["__riga"] = i
    return righe


# ---------- API ----------

# Una sola sessione HTTP per tutti i test: riusa la connessione (invece di aprirne una nuova
# per ognuna delle circa 1 400 richieste del test di coerenza) e ritenta gli errori di rete,
# che non dicono nulla sul comportamento dell'API. Gli stati HTTP non vengono mai ritentati.
SESSIONE = requests.Session()
SESSIONE.mount("http://", HTTPAdapter(max_retries=Retry(total=3, connect=3, read=3, status=0, backoff_factor=0.2)))


def api_get(percorso, **kwargs):
    return SESSIONE.get(API_URL + percorso, timeout=(5, 30), **kwargs)


def api_json(percorso):
    r = api_get(percorso)
    assert r.status_code == 200, f"GET {percorso} -> {r.status_code}: {r.text[:300]}"
    return r.json()


@pytest.fixture(scope="session")
def gare_api():
    """{(anno, round): gara} per tutte le stagioni del dataset di esempio, lette dall'API."""
    gare = {}
    for anno in CFG["dataset_esempio"]["stagioni"]:
        for g in api_json(f"/api/seasons/{anno}/races"):
            gare[(anno, int(g["round"]))] = g
    return gare


@pytest.fixture(scope="session")
def gara_di_riferimento(gare_api):
    """Una gara del dataset di esempio con risultati e giri: la prima della stagione centrale."""
    anno = CFG["dataset_esempio"]["stagioni"][len(CFG["dataset_esempio"]["stagioni"]) // 2]
    primo_round = min(r for (a, r) in gare_api if a == anno)
    gara = gare_api[(anno, primo_round)]
    risultati = api_json(f"/api/races/{gara['id']}/results")
    vincitore = next(r for r in risultati if r["position"] == 1)
    return {"gara": gara, "risultati": risultati, "pilota": vincitore["driver"], "scuderia": vincitore["team"]}


# ---------- Pipeline ----------

def f1_pipeline(*args, env=None):
    r = subprocess.run(["f1-pipeline", *map(str, args)], capture_output=True, text=True,
                       env={**os.environ, **(env or {})}, timeout=1800)
    assert r.returncode == 0, f"f1-pipeline {' '.join(map(str, args))} fallito:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
    return r


@pytest.fixture(scope="session")
def trasformato(tmp_path_factory):
    """Output di `f1-pipeline transform` sul dataset di esempio."""
    out = tmp_path_factory.mktemp("trasformato")
    f1_pipeline("transform", "--input", SAMPLE, "--output", out)
    return out


def leggi_scarti(cartella):
    percorso = Path(cartella) / "scarti.json"
    assert percorso.exists(), "manca scarti.json nell'output di transform"
    return json.loads(percorso.read_text())


@pytest.fixture(scope="session")
def scarti_per_gara(trasformato):
    """Counter {(file, raceId CSV): righe scartate} per results.csv e lap_times.csv del campione."""
    conteggio = Counter()
    per_file = {}
    for s in leggi_scarti(trasformato):
        if s["file"] in ("results.csv", "lap_times.csv"):
            if s["file"] not in per_file:
                per_file[s["file"]] = {r["__riga"]: r for r in leggi_csv(s["file"])}
            riga = per_file[s["file"]].get(int(s["riga"]))
            if riga is not None:
                conteggio[(s["file"], riga["raceId"])] += 1
    return conteggio


# ---------- Database ----------

@pytest.fixture(scope="session")
def db():
    import psycopg
    conn = psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", CFG["porte_verifica"]["postgres"])),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        autocommit=True,
    )
    yield conn
    conn.close()


def conta_righe(conn, tabelle):
    with conn.cursor() as cur:
        conteggi = {}
        for t in tabelle:
            cur.execute(f'SELECT count(*) FROM "{t}"')
            conteggi[t] = cur.fetchone()[0]
    return conteggi
