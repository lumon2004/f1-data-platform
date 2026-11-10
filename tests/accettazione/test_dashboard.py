"""Dashboard: test end-to-end con Playwright e screenshot per la revisione visiva."""
import re

import pytest
from playwright.sync_api import expect, sync_playwright

from conftest import CFG, REPO, WEB_URL

TIMEOUT = CFG["dashboard"]["timeout_elemento_ms"]
REVIEW = REPO / "review"
VISTE = ["season-overview", "race-explorer", "driver-comparison", "team-comparison", "race-analysis"]
STAGIONE = str(CFG["dataset_esempio"]["stagioni"][1])


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def pagina(browser):
    contesto = browser.new_context(viewport={"width": 1440, "height": 900})
    p = contesto.new_page()
    p.set_default_timeout(TIMEOUT)
    p.goto(WEB_URL)
    yield p
    contesto.close()


def tid(pagina, nome):
    return pagina.get_by_test_id(nome)


def vai(pagina, vista):
    tid(pagina, f"nav-{vista}").click()


def scegli(pagina, filtro, valore=None, indice=0):
    """Seleziona nel <select> `filtro` il valore dato, oppure l'indice-esimo valore non vuoto."""
    select = tid(pagina, filtro)
    expect(select.locator("option[value]:not([value=''])").first).to_be_attached()
    if valore is None:
        valori = [v for v in select.locator("option").evaluate_all("os => os.map(o => o.value)") if v]
        valore = valori[min(indice, len(valori) - 1)]
    select.select_option(valore)


def screenshot(pagina, nome):
    REVIEW.mkdir(exist_ok=True)
    pagina.wait_for_load_state("networkidle")
    pagina.screenshot(path=str(REVIEW / f"{nome}.png"), full_page=True)


def punti(locator):
    expect(locator).to_have_attribute("data-punti", re.compile(r"^[1-9]\d*$"))
    return int(locator.get_attribute("data-punti"))


def test_navigazione_senza_errori_console(browser):
    contesto = browser.new_context()
    p = contesto.new_page()
    p.set_default_timeout(TIMEOUT)
    errori = []
    p.on("console", lambda m: m.type == "error" and errori.append(m.text))
    p.on("pageerror", lambda e: errori.append(str(e)))
    p.goto(WEB_URL)
    for vista in VISTE:
        vai(p, vista)
        p.wait_for_load_state("networkidle")
    contesto.close()
    assert not errori, f"errori nella console del browser: {errori}"


def test_filtri_presenti(pagina):
    trovati = set()
    for vista in VISTE:
        vai(pagina, vista)
        pagina.wait_for_load_state("networkidle")
        for f in ("filtro-stagione", "filtro-gara", "filtro-sessione", "filtro-pilota", "filtro-scuderia"):
            if pagina.locator(f"[data-testid^='{f}']").count():
                trovati.add(f)
    attesi = {"filtro-stagione", "filtro-gara", "filtro-sessione", "filtro-pilota", "filtro-scuderia"}
    assert trovati == attesi, f"filtri mancanti: {attesi - trovati}"


def test_season_overview(pagina):
    vai(pagina, "season-overview")
    scegli(pagina, "filtro-stagione", STAGIONE)
    screenshot(pagina, "season-overview")


def test_race_explorer_stagione_gare_risultati(pagina):
    vai(pagina, "race-explorer")
    scegli(pagina, "filtro-stagione", STAGIONE)
    gare = tid(pagina, "lista-gare").get_by_test_id("gara")
    expect(gare.first).to_be_visible()
    gare.first.click()
    righe = tid(pagina, "risultati-gara").get_by_test_id("riga-risultato")
    expect(righe.first).to_be_visible()
    assert righe.count() > 1
    screenshot(pagina, "race-explorer")


def test_race_analysis_grafici(pagina):
    vai(pagina, "race-analysis")
    scegli(pagina, "filtro-stagione", STAGIONE)
    scegli(pagina, "filtro-gara")
    assert punti(tid(pagina, "grafico-tempi-giro")) > 0
    assert punti(tid(pagina, "grafico-posizioni")) > 0
    screenshot(pagina, "race-analysis")


def test_driver_comparison(pagina):
    vai(pagina, "driver-comparison")
    scegli(pagina, "filtro-stagione", STAGIONE)
    scegli(pagina, "filtro-pilota-a", indice=0)
    scegli(pagina, "filtro-pilota-b", indice=1)
    for lato in ("a", "b"):
        expect(tid(pagina, f"statistiche-pilota-{lato}")).to_contain_text(re.compile(r"\d"))
    screenshot(pagina, "driver-comparison")


def test_footer_attribuzione_e_disclaimer(pagina):
    testo = tid(pagina, "footer").inner_text()
    assert "Ergast" in testo and "Kaggle" in testo, "il footer deve citare la fonte dei dati"
    assert re.search(r"affiliat", testo, re.I), "il footer deve contenere il disclaimer di non affiliazione"


def test_errore_api(browser):
    contesto = browser.new_context()
    p = contesto.new_page()
    p.route(re.compile(r".*/api/.*"), lambda route: route.abort())
    p.goto(WEB_URL)
    expect(p.get_by_test_id("errore-api")).to_be_visible(timeout=TIMEOUT)
    contesto.close()
