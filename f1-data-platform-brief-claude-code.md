# Brief per Claude Code — Agente autonomo: F1 Data Platform

> Documento di partenza. Leggilo per intero prima di fare qualsiasi cosa.
> Il "cosa" e il "come" sono decisi qui. Alcuni dettagli vanno chiariti con l'utente (sezione 3).
> Tu (Claude Code) devi impostare il sistema di agenti descritto e poi lavorare finché il traguardo non è raggiunto.

---

## 1. Visione del progetto

- **F1 Data Platform** è una piattaforma di elaborazione e analisi dati che raccoglie, trasforma, archivia ed espone dati storici delle corse di Formula 1 tramite un sistema strutturato e interrogabile.
- **Non è "un sito sulla F1"**: è una **vetrina di data engineering e backend**. Il valore sta nel mostrare come dati grezzi diventano un prodotto dati affidabile, attraverso una pipeline automatizzata.
- Il risultato finale è un'applicazione web pubblica dove si esplorano gare, piloti, scuderie, tempi sul giro, stint, pit stop e altri dati storici con visualizzazioni interattive.
- L'utente può filtrare per **stagione, Gran Premio, sessione, pilota, scuderia** e vedere: risultati di gara e qualifica, tempi sul giro, giri veloci, mescole, stint, pit stop, confronti pilota/scuderia, evoluzione dei tempi, cambi di posizione durante la gara.
- Non si compete con le piattaforme statistiche professionali.
- L'idea centrale da dimostrare:

> **Ho progettato e realizzato un sistema end-to-end che trasforma dati grezzi in un prodotto analitico accessibile.**

## 2. Obiettivo di questo primo step

Un sistema end-to-end funzionante in locale con:

1. **Pipeline dati riproducibile** (Python): ingestione dei CSV grezzi → validazione e pulizia → formato intermedio → caricamento in PostgreSQL.
2. **Modello dati relazionale** (PostgreSQL) progettato come vero modello, non come copia della struttura dei CSV.
3. **API REST** (Spring Boot) con gli endpoint della sezione 5.
4. **Dashboard web** (HTML, CSS, JavaScript, Tailwind CSS) che consuma l'API e mostra almeno le viste della sezione 5.
5. **Docker Compose**: chi clona il repository avvia tutto con una configurazione minima.
6. **Dataset di esempio** incluso nel repository, così il progetto è riproducibile senza accedere alla fonte esterna.

**"Finito" significa una cosa sola: `./verifica.sh` termina con successo** e la cartella `review/` contiene gli screenshot della dashboard per l'approvazione dell'utente.

Fuori da questo step: deploy pubblico, autenticazione utenti, dati in tempo reale o telemetria live, aggiornamento automatico pianificato dalla fonte esterna, pagina del portfolio.

## 3. Domande aperte — da chiarire PRIMA di scrivere codice

Chiedi all'utente:

1. **Repository**: si usa il repository esistente `xoffice-simone/F1_1990` (oggi vuoto) o se ne crea uno nuovo `f1-data-platform`?
2. **Dati**: c'è un account Kaggle con token API per scaricare il dataset completo, oppure l'utente scarica i CSV a mano? Quali **stagioni** usare per il dataset di esempio (es. 2–3 stagioni recenti)?
3. **Stack backend**: versione di Java e strumento di build (Maven o Gradle)? Proposta di default: Java LTS più recente supportata da Spring Boot 3, con Maven.
4. **Nome e marchio**: "F1" e "Formula 1" sono marchi registrati. Per un progetto portfolio pubblico va bene il nome "F1 Data Platform" con un disclaimer di non affiliazione, o preferisce un nome diverso?
5. **Licenza** del repository (MIT, Apache 2.0, altro)?

Finché le risposte mancano, prepara la struttura del progetto e la bozza dei test usando un piccolo dataset sintetico.

## 4. Vincoli su dati, licenze e marchi (OBBLIGATORI)

- **Fonte dati**: dataset Kaggle [Formula 1 World Championship (1950 - 2024)](https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020) di Rohan Rao, derivato dalla [Ergast Developer API](https://ergast.com/mrd/). Prima di usarlo, **verifica la licenza** del dataset sulla pagina Kaggle e documentala in `docs/fonte-dati.md`.
- **Attribuzione**: README e dashboard citano sempre fonte, autore e origine dei dati (sezione "Data Source & Acknowledgements").
- **Nessun materiale ufficiale**: niente loghi ufficiali di Formula 1, FIA, scuderie o sponsor, niente foto protette. Il nome e i loghi delle scuderie compaiono solo come dati testuali.
- **Disclaimer** nel README e nel footer della dashboard: progetto non ufficiale, non affiliato a Formula 1, FIA o scuderie.
- **Dataset completo fuori dal repository**: si versiona solo il dataset di esempio in `data-pipeline/sample/`. I dati completi vanno in una cartella ignorata da git.
- **Credenziali** (database, token Kaggle): solo variabili d'ambiente o `.env` non versionato. Non le leggi, non le scrivi, non le stampi.

Un test automatico (sezione 6) controlla che nel repository non ci siano file `.env`, credenziali, il dataset completo o file grandi oltre la soglia.

## 5. Requisiti minimi di API e dashboard (il resto lo decidi tu)

### Modello dati

Entità minime: `seasons`, `races`, `circuits`, `drivers`, `constructors`, `sessions`, `results`, `laps`, `stints`, `pit_stops`.
Chiavi primarie ed esterne, vincoli e indici devono permettere query analitiche senza ripetere le stesse informazioni. Lo schema è gestito con migrazioni versionate (proposta: Flyway). Documenta il modello e le scelte in `docs/modello-dati.md`, con un diagramma ER.

> Nota: il dataset Kaggle/Ergast non contiene mescole e stint in modo nativo. Se non ci sono, `stints` resta nello schema ma vuoto o derivato dove possibile, e la dashboard lo segnala. Documenta come li hai trattati.

### Endpoint REST minimi

```text
GET /api/seasons
GET /api/seasons/{year}/races
GET /api/races/{raceId}
GET /api/races/{raceId}/results
GET /api/races/{raceId}/laps/{driverId}
GET /api/drivers/{driverId}/statistics
GET /api/teams/{teamId}/statistics
```

Risposte JSON, errori coerenti (404 per risorsa inesistente, 400 per parametri non validi), documentazione OpenAPI generata. Aggregazioni, classifiche, medie e statistiche comparative si calcolano lato server.

### Dashboard

```text
Dashboard
├── Season overview
├── Race explorer
├── Driver comparison
├── Team comparison
└── Race analysis
```

- Almeno: panoramica stagione, esplorazione gara con risultati, grafico dell'evoluzione dei tempi sul giro, grafico dei cambi di posizione, confronto tra due piloti.
- Filtri per stagione, Gran Premio, sessione, pilota, scuderia.
- Documenta le scelte di stile in `docs/direzione-ui.md`: palette, tipografia, libreria dei grafici, layout.

## 6. Criteri di accettazione (diventano i test in `tests/accettazione/`)

Le soglie numeriche stanno in `config/accettazione.json`.

### Pipeline dati (pytest)

- **Riproducibilità**: eseguita due volte sullo stesso input, produce lo stesso output (stesso numero di righe per tabella, stessi checksum dei file intermedi).
- **Idempotenza**: rieseguire il caricamento non crea duplicati nel database.
- **Validazione**: righe con chiavi mancanti, tipi non validi o duplicati vengono scartate o corrette e registrate in un report, non caricate in silenzio.
- **Valori mancanti**: i marcatori del dataset (es. `\N`) diventano `NULL`; tempi e durate vengono convertiti in tipi numerici o intervalli.

### Database

- Lo schema si crea da zero con le sole migrazioni.
- **Integrità**: nessuna violazione di chiave esterna, nessun duplicato sulle chiavi naturali (es. stagione + round).
- **Coerenza**: per ogni gara del dataset di esempio, il numero di risultati e di giri caricati coincide con quello dei CSV di origine (al netto delle righe scartate nel report).

### API (JUnit + Testcontainers, PostgreSQL reale)

- Ogni endpoint della sezione 5 risponde 200 sul dataset di esempio, con lo schema JSON atteso.
- Risorse inesistenti → 404; parametri non validi → 400.
- Le statistiche di un pilota su una stagione nota del dataset di esempio coincidono con valori attesi calcolati a mano e salvati nei test.
- Tempo di risposta degli endpoint sotto la soglia configurata sul dataset di esempio.

### Dashboard (test end-to-end con Playwright)

- La dashboard si carica senza errori nella console del browser.
- Selezionando una stagione compare l'elenco delle gare; selezionando una gara compaiono i risultati.
- Il grafico dei tempi sul giro e quello delle posizioni mostrano dati per la gara selezionata.
- Il confronto tra due piloti mostra le statistiche di entrambi.
- Se l'API non risponde, la dashboard mostra un messaggio di errore chiaro invece di una pagina vuota.

### Docker e riproducibilità

- `docker compose up` su un clone pulito avvia `postgres`, `backend` e `frontend`; il caricamento del dataset di esempio parte come servizio o passo di inizializzazione esplicito.
- Gli healthcheck di tutti i servizi diventano "healthy" entro il tempo soglia.

### Repository e documentazione

- Nessun file `.env`, credenziale, dataset completo o file oltre la dimensione soglia è versionato.
- Il README contiene le 10 sezioni richieste: cosa fa, perché esiste, architettura, pipeline, modello dati, API, avvio locale, screenshot, esempi di richieste API, decisioni tecniche e compromessi. Più il diagramma di architettura e la sezione "Data Source & Acknowledgements".

### Revisione visiva (prodotta, non bloccante)

- `verifica.sh` salva in `review/` gli screenshot di panoramica stagione, esplorazione gara, analisi gara e confronto piloti.
- Il subagent `reviewer` li esamina rispetto a `docs/direzione-ui.md` e scrive le osservazioni in `review/note.md`.
- L'utente dà l'approvazione finale. Il ciclo automatico si chiude quando i test passano; aspetto e leggibilità li giudica l'utente.

I test di accettazione e `verifica.sh` vanno **approvati dall'utente** e poi sono **bloccati**: non li modifichi mai (lo impone un hook). Se un test sembra sbagliato, lo segnali all'utente e non lo cambi.

## 7. Tappe (da tracciare in `PROGRESS.md`)

1. Impostazione del progetto: struttura, Docker Compose con PostgreSQL, pipeline di build per ogni componente, test vuoti.
2. **Modello dati**: schema, migrazioni, diagramma ER, `docs/modello-dati.md`.
3. **Pipeline dati**: ingestione, validazione, normalizzazione, formato intermedio (proposta: Parquet), caricamento, report degli scarti. Prima sul dataset di esempio.
4. **API Spring Boot**: endpoint, aggregazioni, gestione errori, OpenAPI, test con Testcontainers.
5. **Dashboard**: struttura, filtri, chiamate all'API, gestione errori.
6. **Visualizzazioni**: tempi sul giro, posizioni, stint e pit stop, confronti.
7. **Docker end-to-end**: avvio completo da clone pulito, healthcheck, servizio di caricamento dati.
8. **Documentazione**: README completo, diagramma di architettura, esempi API, screenshot.
9. Tutti i test di accettazione verdi e screenshot in `review/`.

`PROGRESS.md` è la memoria tra le sessioni: ogni sessione lo legge all'inizio e lo aggiorna prima di chiudere, indicando tappa corrente, cosa è fatto e cosa blocca.

## 8. Stack

Fissato dal progetto:

- **Python** per la pipeline (proposta: pandas o Polars + PyArrow, pytest)
- **PostgreSQL** per l'archiviazione
- **Java + Spring Boot** per l'API REST (proposta: Spring Data JPA o JDBC, Flyway, springdoc-openapi, JUnit + Testcontainers)
- **HTML, CSS, JavaScript, Tailwind CSS** per la dashboard (proposta per i grafici: Chart.js; Playwright per i test end-to-end)
- **Docker Compose** per l'orchestrazione

Le voci "proposta" puoi sceglierle tu, motivando la scelta in `docs/decisioni.md`. Se trovi un motivo serio per cambiare una voce fissata, proponilo all'utente prima di farlo.

## 9. Struttura del progetto da creare

```
f1-data-platform/
├── CLAUDE.md                  visione, obiettivo, vincoli, criterio di "fatto" (da questo brief)
├── PROGRESS.md                tappe e stato
├── README.md
├── LICENSE
├── docker-compose.yml
├── verifica.sh                esegue tutti i test di accettazione + screenshot — BLOCCATO
├── run.sh                     ciclo esterno che rilancia le sessioni
├── .env.example               nomi delle variabili, senza valori
├── config/
│   └── accettazione.json      soglie dei test
├── data-pipeline/
│   ├── src/
│   ├── tests/
│   ├── sample/                dataset di esempio versionato
│   ├── raw/                   dati completi — ignorato da git
│   └── processed/             formato intermedio — ignorato da git
├── database/
│   └── migrations/
├── backend/                   progetto Spring Boot
├── frontend/
├── docs/
│   ├── architettura.md        con diagramma
│   ├── modello-dati.md        con diagramma ER
│   ├── fonte-dati.md          licenza e attribuzione
│   ├── direzione-ui.md
│   └── decisioni.md           decisioni tecniche e compromessi
├── tests/
│   └── accettazione/          BLOCCATI
├── review/                    screenshot e note del reviewer
├── logs/
└── .claude/
    ├── agents/
    │   ├── architetto-dati.md
    │   ├── sviluppatore-pipeline.md
    │   ├── sviluppatore-backend.md
    │   ├── sviluppatore-frontend.md
    │   ├── technical-writer.md
    │   └── reviewer.md
    ├── settings.json          permessi + hook
    └── hooks/
        ├── blocca-azioni-rischiose.sh   PreToolUse
        └── verifica-completamento.sh    Stop
```

## 10. Subagent

| Subagent | Compito | Strumenti |
|---|---|---|
| `architetto-dati` | Progetta il modello relazionale, le migrazioni e il diagramma ER; scrive `docs/modello-dati.md` | Read, Write, Edit, Web |
| `sviluppatore-pipeline` | Ingestione, validazione, normalizzazione, caricamento, dataset di esempio, test pytest | Read, Write, Edit, Bash |
| `sviluppatore-backend` | API Spring Boot, aggregazioni, gestione errori, OpenAPI, test con Testcontainers | Read, Write, Edit, Bash |
| `sviluppatore-frontend` | Dashboard, filtri, grafici, gestione errori; scrive `docs/direzione-ui.md` | Read, Write, Edit, Bash |
| `technical-writer` | README, diagramma di architettura, esempi API, `docs/decisioni.md`, attribuzione dei dati | Read, Write, Edit |
| `reviewer` | Verifica i criteri, esamina gli screenshot, controlla licenze e attribuzione, segnala scorciatoie e test aggirati; non corregge | Read, Grep, Glob, Bash |

## 11. Hook

**PreToolUse — `blocca-azioni-rischiose.sh`** (esce con codice **2** per bloccare; il codice 1 NON blocca):
- scritture su `tests/accettazione/`, `verifica.sh` e `config/accettazione.json`
- lettura o scrittura di file `.env` e qualsiasi stampa di credenziali (database, token Kaggle)
- `git add` o commit di `data-pipeline/raw/`, `data-pipeline/processed/` o di file oltre la soglia di dimensione
- `git push` sul ramo principale, pubblicazione o deploy
- `rm -rf`, `docker volume rm`, `DROP DATABASE` e cancellazioni massive

**Stop — `verifica-completamento.sh`**:
- esegue `./verifica.sh`
- se passa → exit 0 (puoi fermarti)
- se fallisce → scrive l'errore su stderr ed esce con 2 (riprendi il lavoro)
- conta i tentativi; dopo un massimo (es. 5) lascia fermare l'agente e scrive un report in `PROGRESS.md`

Esempio di `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash|Write|Edit|Read",
        "hooks": [{ "type": "command", "command": ".claude/hooks/blocca-azioni-rischiose.sh" }] }
    ],
    "Stop": [
      { "hooks": [{ "type": "command", "command": ".claude/hooks/verifica-completamento.sh" }] }
    ]
  }
}
```

Verifica il formato esatto di hook e subagent sulla documentazione ufficiale di Claude Code prima di finalizzarli.

## 12. Ciclo esterno — `run.sh`

L'hook Stop ti tiene al lavoro dentro una sessione; `run.sh` rilancia nuove sessioni finché il traguardo non è raggiunto.

```bash
#!/bin/bash
MAX_SESSIONI=30
mkdir -p logs
for i in $(seq 1 $MAX_SESSIONI); do
  ./verifica.sh && { echo "Obiettivo raggiunto alla sessione $i"; exit 0; }
  claude -p "Leggi CLAUDE.md e PROGRESS.md. Riprendi dalla prima tappa non completata. \
Aggiorna PROGRESS.md prima di chiudere." --output-format json > logs/sessione-$i.json
  git add -A && git commit -m "Sessione $i" -q
done
echo "Limite sessioni raggiunto: vedi PROGRESS.md"
```

## 13. Regole generali

- Dati prima dell'interfaccia: una dashboard bella su dati sbagliati non supera questo step.
- Il database è un modello dati vero, non lo specchio dei CSV.
- La pipeline è riproducibile e mai eseguita a mano "una volta sola".
- Ogni componente ha i suoi test e si avvia da Docker Compose.
- Prima di dichiarare finito, delega la verifica al subagent `reviewer`.
- Ogni sessione termina con un commit e con `PROGRESS.md` aggiornato.
- Se ti serve una decisione dell'utente (dati, licenza, nome, credenziali), fermati e chiedi: non indovinare.

## 14. Presentazione nel portfolio (per i passi successivi)

Non fa parte di questo step, ma orienta README e documentazione:

- Il progetto si presenta come **progetto di data engineering / backend**, non come sito a tema F1.
- Scheda: **F1 Data Platform**: *End-to-end data pipeline and analytics platform for Formula 1 racing data.*
- Tecnologie: `Python · PostgreSQL · Java · Spring Boot · REST · JavaScript · Tailwind CSS · Docker`
- Percorso della pagina: Problema → Architettura → Pipeline dati → Database → API → Dashboard.
- Competenze dimostrate: dataset esterni, modello relazionale, pipeline riproducibili, trasformazione dati in Python, progettazione di API REST, Spring Boot, PostgreSQL, interfaccia web su API, visualizzazione dati, containerizzazione, documentazione di un sistema end-to-end.

## 15. Primo compito per Claude Code

1. Fai all'utente le domande della sezione 3.
2. Crea la struttura della sezione 9, con CLAUDE.md, PROGRESS.md, subagent e hook.
3. Scrivi i test di accettazione, `config/accettazione.json` con le soglie e `verifica.sh` sui criteri della sezione 6, e **sottoponili all'utente per approvazione**.
4. Solo dopo l'approvazione: attiva gli hook e avvia il lavoro dalla tappa 1.
