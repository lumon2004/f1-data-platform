# PROGRESS

Memoria tra le sessioni. Ogni sessione la legge all'inizio e la aggiorna prima di chiudere.

## Stato attuale

- **Tappa corrente**: 9 — verifica finale del `reviewer` in corso; poi approvazione visiva dell'utente sugli screenshot in `review/`.
- **Bloccanti**: nessuno. `./verifica.sh` passa (38 test di accettazione su 38, 2026-11-10).

## Tappe

0. [x] Impostazione del sistema di agenti: struttura, subagent, hook attivi, test di accettazione approvati dall'utente (2026-11-10) e bloccati
1. [x] Impostazione del progetto: Docker Compose con PostgreSQL, build per ogni componente, test vuoti
2. [x] Modello dati: schema, migrazioni, diagramma ER, `docs/modello-dati.md`
3. [x] Pipeline dati: ingestione, validazione, normalizzazione, formato intermedio, caricamento, report scarti
4. [x] API Spring Boot: endpoint, aggregazioni, gestione errori, OpenAPI, test Testcontainers
5. [x] Dashboard: struttura, filtri, chiamate API, gestione errori
6. [x] Visualizzazioni: tempi sul giro, posizioni, stint e pit stop, confronti
7. [x] Docker end-to-end: avvio da clone pulito, healthcheck, servizio di caricamento dati
8. [x] Documentazione: README completo, diagramma architettura, esempi API, screenshot
9. [ ] Tutti i test di accettazione verdi e screenshot in `review/`

## Stato dei componenti

- `docker-compose.yml`: `postgres`, `backend`, `frontend` con healthcheck; `pipeline` una tantum carica il campione dopo `backend` healthy. Avvio: file delle variabili d'ambiente con `POSTGRES_DB/USER/PASSWORD`, poi `docker compose up --build` (API su 8080, dashboard su 8081).
- `data-pipeline/`: `f1-pipeline` con `download`, `sample`, `transform`, `load`, `run`. Campione 2022–2024 in `sample/`. Test: 160 + 5 su database dedicato (`F1_PIPELINE_TEST_DSN`).
- `database/migrations/`: V1–V4, 12 tabelle.
- `backend/`: 15 endpoint (7 del contratto + 8 per la dashboard), errori JSON, OpenAPI. Test: `./mvnw -B -q verify` (176).
- `frontend/`: cinque viste, grafici con Observable Plot + D3 serviti in locale, scelte nell'URL. Test: `npm test` (72).
- Documentazione: `README.md`, `docs/architettura.md`, `modello-dati.md`, `fonte-dati.md`, `direzione-ui.md`, `decisioni.md`. Note di revisione in `review/note.md`.
- Stack di sviluppo eventualmente acceso: progetto Compose `f1-dev` (porte 25432/28080/28081), avviato con variabili inline.

## Possibili passi successivi (fuori da questo step)

- Endpoint per il distacco tra due piloti (oggi calcolato nel browser, eccezione documentata in `docs/decisioni.md`) e per l'andamento dei punti gara per gara.
- Il `load` non rimuove le righe sparite dall'input (limite dichiarato).
- I 5 test della pipeline su database non girano in `verifica.sh` (file bloccato).
- Tema scuro; compressione e cache nel server statico; README in inglese per il portfolio.

## Da segnalare all'utente (file bloccati)

- **Risolto il 2026-11-10 con l'approvazione dell'utente**: il test di coerenza con i CSV falliva circa 1 volta su 3 (una connessione appesa nella rete di Docker Desktop tra le circa 1 430 aperte dal test). L'utente ha applicato una patch al file di configurazione condivisa dei test di accettazione: una sola sessione HTTP che riusa la connessione e ritenta solo gli errori di rete, mai gli stati HTTP. Dopo la patch: 6 esecuzioni complete su 6 verdi.

- `tests/accettazione/README.md` dice "un file `<tabella>.parquet` per tabella", ma i Parquet sono 13 per 12 tabelle (`sprint_results.parquet` separato) perché `test_validazione_scarta_e_registra` confronta `results.parquet` con `results.csv`.
- La regex di `test_nessuna_credenziale_nel_codice` ha dato falsi positivi su codice innocuo (`mvnw`, una costante con il nome della variabile del token): aggirati rinominando.
- L'hook blocca alcuni comandi di sola lettura (es. `docker run --rm` insieme a un percorso dei test bloccati).

## Registro sessioni

- 2026-11-10 — Domande sezione 3 chiarite; repo creata; struttura, subagent e hook preparati; test di accettazione approvati; hook attivati.
- 2026-11-10 — Tappa 1 chiusa: Compose con PostgreSQL e scheletri di pipeline, backend e frontend con test verdi. Revisione del `reviewer`: due difetti corretti (riga di `mvnw` scambiata per credenziale; `npm test` non funzionante su Node 22/24).
- 2026-11-10 — Tappa 2 chiusa: 4 migrazioni Flyway (12 tabelle), `docs/modello-dati.md`; applicate su PostgreSQL 17 e riviste dal `reviewer` (via libera).
- 2026-11-10 — Tappa 3 chiusa: dataset scaricato dall'utente con il token Kaggle; pipeline completa, campione 2022–2024, `docs/fonte-dati.md` (licenza CC0 verificata su Kaggle; termini originali di Ergast non più consultabili). Assunzioni dello schema verificate sui dati reali; due posizioni mancanti del 2005 derivate da `positionText`. Revisione del `reviewer`: via libera.
- 2026-11-10 — Tappa 4 chiusa: API REST con i sette endpoint, 91 test, Dockerfile del backend, Compose con backend e caricamento del campione. Revisione del `reviewer`: via libera; 160 statistiche ricalcolate dai CSV senza differenze.
- 2026-11-10 — Tappe 4–8 chiuse: API (15 endpoint), dashboard con grafici, Compose completo, documentazione. Revisioni del `reviewer` con via libera; giro di rifinitura della dashboard. `./verifica.sh` passa: 38 su 38.
- 2026-11-10 — Verifica finale del `reviewer`: prodotto conforme ai criteri, ma verifica instabile (2 fallimenti su 3 per la rete di Docker). Patch ai test approvata e applicata dall'utente; 6 esecuzioni su 6 verdi.
