# PROGRESS

Memoria tra le sessioni. Ogni sessione la legge all'inizio e la aggiorna prima di chiudere.

## Stato attuale

- **Tappa corrente**: 3 — Pipeline dati (responsabile: `sviluppatore-pipeline`)
- **Bloccanti**: nessuno. Per scaricare il dataset serve il token Kaggle configurato dall'utente (altrimenti CSV a mano in `data-pipeline/raw/`).

## Tappe

0. [x] Impostazione del sistema di agenti: struttura, subagent, hook attivi, test di accettazione approvati dall'utente (2026-11-10) e bloccati
1. [x] Impostazione del progetto: Docker Compose con PostgreSQL, build per ogni componente, test vuoti
2. [x] Modello dati: schema, migrazioni, diagramma ER, `docs/modello-dati.md`
3. [ ] Pipeline dati: ingestione, validazione, normalizzazione, formato intermedio, caricamento, report scarti
4. [ ] API Spring Boot: endpoint, aggregazioni, gestione errori, OpenAPI, test Testcontainers
5. [ ] Dashboard: struttura, filtri, chiamate API, gestione errori
6. [ ] Visualizzazioni: tempi sul giro, posizioni, stint e pit stop, confronti
7. [ ] Docker end-to-end: avvio da clone pulito, healthcheck, servizio di caricamento dati
8. [ ] Documentazione: README completo, diagramma architettura, esempi API, screenshot
9. [ ] Tutti i test di accettazione verdi e screenshot in `review/`

## Stato dei componenti dopo la tappa 1

- `docker-compose.yml`: solo `postgres` (17-alpine, healthcheck). `backend`, `frontend`, `pipeline` alla tappa 7.
- `data-pipeline/`: pacchetto `f1-pipeline` (Polars, PyArrow, psycopg 3); sottocomandi `transform`, `load`, `download` segnaposto. Test: container `python:3.12-slim`, `pip install ".[test]"`, `pytest`.
- `backend/`: Spring Boot 3.5, `JdbcClient`, Flyway su `database/migrations/` (impacchettate nel jar), springdoc. Test: `./mvnw -B -q verify`.
- `frontend/`: HTML + moduli ES + Tailwind v4, server Node con proxy `/api`. Test: `npm test`.

## Note del reviewer per le tappe successive

- **Tappa 2**: i test di accettazione contano le righe delle tabelle `seasons, races, circuits, drivers, constructors, sessions, results, laps, stints, pit_stops`: i nomi sono fissati. `architetto-dati` conferma anche che lo schema lo applica il backend all'avvio (la pipeline carica su un database già migrato). Il test backend su Flyway oggi passa con zero migrazioni: va esteso a una tabella vera.
- **Tappa 3 (dal reviewer della tappa 2)**: un attributo facoltativo fuori dai `CHECK` (sigla e numero del pilota, giro veloce, coordinate) va messo a `NULL` e registrato, non deve far scartare l'intera riga; si scarta solo per chiavi, chiavi esterne e campi obbligatori. Leggere i CSV per nome di colonna (`sprint_results.csv` varia tra versioni). Duplicati in `qualifying.csv` tra gli scarti. Ogni giro o sosta di un pilota senza risultato valido va scartato e registrato sotto il proprio file. La sessione `race` va creata sempre: serve un test. Prima di scrivere il `load`, contare sul campione le violazioni delle assunzioni elencate in fondo a `docs/modello-dati.md`; se un vincolo non regge, nuova migrazione `V5` tramite `architetto-dati`.
- **Tappa 4 (dal reviewer della tappa 2)**: ogni query su `results` filtra `session_type = 'race'` (test su una gara con sprint). Manca la query delle statistiche di scuderia: decidere e documentare se `podiums` conta i piazzamenti o le gare con almeno un podio, e se `races` conta iscrizioni o partenze.
- **Tappa 3**: sostituire `test_sottocomandi_non_ancora_implementati` con test veri. L'immagine dei test di accettazione fissa `pyarrow==17.0.0` e `psycopg[binary]==3.2.3`: le versioni della pipeline devono restare compatibili. Scrivere `docs/fonte-dati.md`.
- **Tappa 7**: frontend nel container con `HOST=0.0.0.0` e `API_TARGET=http://backend:8080`; healthcheck su `/`; aggiungere un timeout al proxy; eseguire `npm test` nella build dell'immagine (non è lanciato da `verifica.sh`). Contesto di build del backend = radice del repository.
- **Tappa 8**: il Compose richiede `POSTGRES_DB/USER/PASSWORD` senza default: il README deve spiegare il passo `.env` (da confermare con l'utente se preferisce default di sviluppo).
- `backend/mvnw`: una riga ritoccata, vedi `docs/decisioni.md`; va riapplicata se si rigenera il wrapper.

## Registro sessioni

- 2026-11-10 — Domande sezione 3 chiarite; repo creata; struttura, subagent e hook preparati; test di accettazione approvati; hook attivati.
- 2026-11-10 — Tappa 1 chiusa: Compose con PostgreSQL e scheletri di pipeline, backend e frontend con test verdi. Revisione del `reviewer`: due difetti corretti (riga di `mvnw` scambiata per credenziale; `npm test` non funzionante su Node 22/24).
- 2026-11-10 — Tappa 2 chiusa: 4 migrazioni Flyway (12 tabelle), `docs/modello-dati.md`; applicate su PostgreSQL 17 e riviste dal `reviewer` (via libera).
