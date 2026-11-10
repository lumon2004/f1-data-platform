"""API REST: endpoint, schema JSON, errori, statistiche note, OpenAPI, tempi di risposta."""
import re
import statistics
import time

import pytest

from conftest import CFG, api_get, api_json

INESISTENTE = 999999999
NUMERO = (int, float)

# Statistiche note, calcolate a mano dai risultati ufficiali della stagione 2023 (solo Gran Premi, sprint esclusi).
VER_2023 = {"races": 22, "wins": 19, "podiums": 21}
RED_BULL_2023_VITTORIE = 21


def ha_campi(oggetto, campi, dove):
    mancanti = [c for c in campi if c not in oggetto]
    assert not mancanti, f"{dove}: campi mancanti {mancanti} in {str(oggetto)[:200]}"


def test_seasons():
    stagioni = api_json("/api/seasons")
    assert isinstance(stagioni, list)
    for s in stagioni:
        ha_campi(s, ["year"], "/api/seasons")
    assert set(CFG["dataset_esempio"]["stagioni"]) <= {s["year"] for s in stagioni}


def test_races_di_una_stagione(gare_api):
    for g in gare_api.values():
        ha_campi(g, ["id", "round", "name", "date"], "/api/seasons/{year}/races")


def test_race(gara_di_riferimento):
    gara = gara_di_riferimento["gara"]
    dettaglio = api_json(f"/api/races/{gara['id']}")
    ha_campi(dettaglio, ["id", "season", "round", "name", "date", "circuit"], "/api/races/{id}")
    ha_campi(dettaglio["circuit"], ["id", "name", "country"], "/api/races/{id}.circuit")


def test_results(gara_di_riferimento):
    risultati = gara_di_riferimento["risultati"]
    assert risultati, "nessun risultato per la gara di riferimento"
    for r in risultati:
        ha_campi(r, ["position", "points", "status", "laps", "driver", "team"], "/api/races/{id}/results")
        ha_campi(r["driver"], ["id", "code", "name"], "results.driver")
        ha_campi(r["team"], ["id", "name"], "results.team")
        assert r["position"] is None or isinstance(r["position"], int)
        assert isinstance(r["points"], NUMERO)


def test_laps(gara_di_riferimento):
    gara, pilota = gara_di_riferimento["gara"], gara_di_riferimento["pilota"]
    giri = api_json(f"/api/races/{gara['id']}/laps/{pilota['id']}")
    assert giri, "il vincitore deve avere giri registrati"
    for g in giri:
        ha_campi(g, ["lap", "position", "timeMs"], "/api/races/{id}/laps/{driverId}")
        assert isinstance(g["timeMs"], int) and g["timeMs"] > 0
    assert [g["lap"] for g in giri] == sorted(g["lap"] for g in giri), "giri non ordinati"


@pytest.mark.parametrize("tipo", ["drivers", "teams"])
def test_statistiche_schema(gara_di_riferimento, tipo):
    entita = gara_di_riferimento["pilota" if tipo == "drivers" else "scuderia"]
    for query in ("", f"?season={CFG['dataset_esempio']['stagioni'][1]}"):
        stat = api_json(f"/api/{tipo}/{entita['id']}/statistics{query}")
        ha_campi(stat, ["races", "wins", "podiums", "points"], f"/api/{tipo}/{{id}}/statistics{query}")
        assert all(isinstance(stat[c], NUMERO) for c in ("races", "wins", "podiums", "points"))


def _verstappen_2023(gare_api):
    for (anno, _), gara in sorted(gare_api.items()):
        if anno == 2023:
            for r in api_json(f"/api/races/{gara['id']}/results"):
                if r["driver"]["code"] == "VER":
                    return r["driver"], r["team"]
    pytest.fail("Verstappen non trovato nei risultati 2023")


def test_statistiche_note_pilota(gare_api):
    pilota, _ = _verstappen_2023(gare_api)
    stat = api_json(f"/api/drivers/{pilota['id']}/statistics?season=2023")
    assert {k: stat[k] for k in VER_2023} == VER_2023


def test_statistiche_note_scuderia(gare_api):
    _, scuderia = _verstappen_2023(gare_api)
    stat = api_json(f"/api/teams/{scuderia['id']}/statistics?season=2023")
    assert stat["wins"] == RED_BULL_2023_VITTORIE


def _errore(percorso, atteso):
    r = api_get(percorso)
    assert r.status_code == atteso, f"GET {percorso} -> {r.status_code}, atteso {atteso}"
    corpo = r.json()
    ha_campi(corpo, ["status", "message"], f"errore {percorso}")
    assert corpo["status"] == atteso


def test_risorse_inesistenti_404(gara_di_riferimento):
    gara = gara_di_riferimento["gara"]
    for p in ["/api/seasons/1800/races", f"/api/races/{INESISTENTE}", f"/api/races/{INESISTENTE}/results",
              f"/api/races/{gara['id']}/laps/{INESISTENTE}", f"/api/drivers/{INESISTENTE}/statistics",
              f"/api/teams/{INESISTENTE}/statistics"]:
        _errore(p, 404)


def test_parametri_non_validi_400(gara_di_riferimento):
    pilota = gara_di_riferimento["pilota"]
    for p in ["/api/seasons/abc/races", "/api/races/abc", "/api/races/abc/results",
              f"/api/drivers/{pilota['id']}/statistics?season=abc"]:
        _errore(p, 400)


def test_openapi():
    doc = api_json("/v3/api-docs")
    percorsi = {re.sub(r"\{[^}]+\}", "{}", p) for p in doc.get("paths", {})}
    attesi = {"/api/seasons", "/api/seasons/{}/races", "/api/races/{}", "/api/races/{}/results",
              "/api/races/{}/laps/{}", "/api/drivers/{}/statistics", "/api/teams/{}/statistics"}
    assert attesi <= percorsi, f"percorsi mancanti nella documentazione OpenAPI: {attesi - percorsi}"


def test_tempi_di_risposta(gara_di_riferimento):
    gara, pilota, scuderia = (gara_di_riferimento[k] for k in ("gara", "pilota", "scuderia"))
    anno = CFG["dataset_esempio"]["stagioni"][1]
    soglia, n = CFG["api"]["max_response_ms"], CFG["api"]["ripetizioni_misura"]
    lenti = {}
    for p in ["/api/seasons", f"/api/seasons/{anno}/races", f"/api/races/{gara['id']}",
              f"/api/races/{gara['id']}/results", f"/api/races/{gara['id']}/laps/{pilota['id']}",
              f"/api/drivers/{pilota['id']}/statistics", f"/api/teams/{scuderia['id']}/statistics"]:
        api_get(p)  # riscaldamento
        tempi = []
        for _ in range(n):
            t0 = time.perf_counter()
            assert api_get(p).status_code == 200
            tempi.append((time.perf_counter() - t0) * 1000)
        if statistics.median(tempi) > soglia:
            lenti[p] = round(statistics.median(tempi))
    assert not lenti, f"endpoint oltre {soglia} ms (mediana): {lenti}"
