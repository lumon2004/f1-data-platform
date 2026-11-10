"""Docker, repository e documentazione."""
import csv
import json
import re

from conftest import CFG, REPO, SAMPLE, VERIFICA

MB = 1024 * 1024


def file_versionati():
    """File che un clone pulito conterrebbe (tracciati + non ignorati), elencati da verifica.sh."""
    return [r for r in (VERIFICA / "file-versionati.txt").read_text().splitlines() if r]


# ---------- Docker ----------

def stato_servizi():
    testo = (VERIFICA / "stato-servizi.json").read_text().strip()
    righe = json.loads(testo) if testo.startswith("[") else [json.loads(r) for r in testo.splitlines()]
    return {r["Service"]: r for r in righe}


def test_servizi_healthy():
    servizi = stato_servizi()
    for nome in ("postgres", "backend", "frontend"):
        assert nome in servizi, f"servizio {nome} assente"
        assert servizi[nome].get("Health") == "healthy", f"{nome}: {servizi[nome].get('Health') or servizi[nome].get('State')}"


def test_caricamento_dati_completato():
    pipeline = stato_servizi().get("pipeline")
    assert pipeline, "servizio pipeline assente"
    assert pipeline["State"] == "exited" and int(pipeline["ExitCode"]) == 0, f"pipeline: {pipeline}"


def test_tempo_di_avvio():
    secondi = float((VERIFICA / "tempo-avvio-s").read_text())
    soglia = CFG["docker"]["max_avvio_healthy_s"]
    assert secondi <= soglia, f"servizi healthy in {secondi:.0f} s, soglia {soglia} s"


# ---------- Repository ----------

def test_nessun_file_proibito():
    proibiti = [f for f in file_versionati()
                if re.search(r"(^|/)\.env(\.|$)", f) and not f.endswith(".env.example")
                or re.search(r"(^|/)kaggle\.json$", f)
                or re.match(r"data-pipeline/(raw|processed)/", f)]
    assert not proibiti, f"file che non devono essere versionati: {proibiti}"


def test_dimensione_file():
    soglia = CFG["repository"]["max_file_mb"] * MB
    grandi = [f for f in file_versionati() if (REPO / f).is_file() and (REPO / f).stat().st_size > soglia]
    assert not grandi, f"file oltre {CFG['repository']['max_file_mb']} MB: {grandi}"


def test_nessuna_credenziale_nel_codice():
    esclusi = re.compile(r"^(tests/accettazione/|verifica\.sh$|\.env\.example$|review/)|\.(png|jpg|jpeg|parquet|ico|woff2?)$")
    segreto = re.compile(r"""(PASSWORD|SECRET|TOKEN|API_KEY|KAGGLE_KEY)["']?\s*[:=]\s*["']?(?!\$\{)[A-Za-z0-9_\-+/]{8,}""", re.I)
    trovati = []
    for f in file_versionati():
        p = REPO / f
        if esclusi.search(f) or not p.is_file() or p.stat().st_size > MB:
            continue
        for n, riga in enumerate(p.read_text(errors="ignore").splitlines(), 1):
            if segreto.search(riga):
                trovati.append(f"{f}:{n}")
    assert not trovati, f"possibili credenziali nel codice: {trovati}"
    esempio = (REPO / ".env.example").read_text()
    assert not re.search(r"^(\w*(PASSWORD|TOKEN|KEY)\w*)=\S+", esempio, re.M), ".env.example deve contenere solo nomi"


def test_dataset_di_esempio():
    stagioni = set(CFG["dataset_esempio"]["stagioni"])
    with open(SAMPLE / "races.csv", newline="", encoding="utf-8") as f:
        anni = {int(r["year"]) for r in csv.DictReader(f)}
    assert anni == stagioni, f"il dataset di esempio deve contenere le stagioni {sorted(stagioni)}, trovate {sorted(anni)}"
    for nome in ("circuits", "constructors", "drivers", "races", "results", "lap_times", "pit_stops", "status"):
        assert (SAMPLE / f"{nome}.csv").is_file(), f"manca data-pipeline/sample/{nome}.csv"
    totale = sum(p.stat().st_size for p in SAMPLE.rglob("*") if p.is_file())
    assert totale <= CFG["repository"]["max_sample_mb"] * MB, "dataset di esempio troppo grande"


# ---------- Documentazione ----------

SEZIONI_README = {
    "cosa fa": r"cosa fa|what it does|overview|panoramica",
    "perché esiste": r"perch|why",
    "architettura": r"architettura|architecture",
    "pipeline": r"pipeline",
    "modello dati": r"modello dati|data model",
    "API": r"\bapi\b",
    "avvio locale": r"avvio|getting started|quick ?start|run locally",
    "screenshot": r"screenshot",
    "esempi di richieste API": r"esemp|example",
    "decisioni tecniche e compromessi": r"decision|compromess|trade-?off",
}


def test_readme():
    testo = (REPO / "README.md").read_text()
    titoli = [t.lower() for t in re.findall(r"^#{2,3}\s+(.+)$", testo, re.M)]
    mancanti = [s for s, regex in SEZIONI_README.items() if not any(re.search(regex, t) for t in titoli)]
    assert not mancanti, f"sezioni mancanti nel README: {mancanti}"
    assert any("data source & acknowledgements" in t for t in titoli), "manca la sezione 'Data Source & Acknowledgements'"
    assert "```mermaid" in testo or re.search(r"!\[[^\]]*archit", testo, re.I), "manca il diagramma di architettura"
    assert re.search(r"!\[[^\]]*\]\([^)]*review/", testo), "il README deve mostrare gli screenshot"
    assert re.search(r"curl\s+\S*/api/", testo), "mancano esempi di richieste API"
    for parola in ("Ergast", "Kaggle", "Rohan Rao"):
        assert parola in testo, f"il README deve citare {parola}"
    assert re.search(r"affiliat", testo, re.I), "manca il disclaimer di non affiliazione"
    assert re.search(r"tutti i diritti riservati|all rights reserved", testo, re.I), "manca la nota di copyright"


def test_documenti():
    attesi = {
        "architettura.md": [r"```mermaid"],
        "modello-dati.md": [r"erDiagram", r"stint"],
        "fonte-dati.md": [r"licen[sz]", r"Rohan Rao", r"Ergast"],
        "direzione-ui.md": [r"palette", r"tipografia|typograph", r"grafic|chart", r"layout"],
        "decisioni.md": [r"\w"],
    }
    for nome, regex in attesi.items():
        testo = (REPO / "docs" / nome).read_text()
        assert "_Da scrivere._" not in testo, f"docs/{nome} è ancora una bozza"
        for r in regex:
            assert re.search(r, testo, re.I), f"docs/{nome} deve trattare: {r}"
