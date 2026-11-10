# PROGRESS

Memoria tra le sessioni. Ogni sessione la legge all'inizio e la aggiorna prima di chiudere.

## Stato attuale

- **Tappa corrente**: 4 — API Spring Boot (responsabile: `sviluppatore-backend`)
- **Bloccanti**: nessuno.

## Tappe

0. [x] Impostazione del sistema di agenti: struttura, subagent, hook attivi, test di accettazione approvati dall'utente (2026-11-10) e bloccati
1. [x] Impostazione del progetto: Docker Compose con PostgreSQL, build per ogni componente, test vuoti
2. [x] Modello dati: schema, migrazioni, diagramma ER, `docs/modello-dati.md`
3. [x] Pipeline dati: ingestione, validazione, normalizzazione, formato intermedio, caricamento, report scarti
4. [ ] API Spring Boot: endpoint, aggregazioni, gestione errori, OpenAPI, test Testcontainers
5. [ ] Dashboard: struttura, filtri, chiamate API, gestione errori
6. [ ] Visualizzazioni: tempi sul giro, posizioni, stint e pit stop, confronti
7. [ ] Docker end-to-end: avvio da clone pulito, healthcheck, servizio di caricamento dati
8. [ ] Documentazione: README completo, diagramma architettura, esempi API, screenshot
9. [ ] Tutti i test di accettazione verdi e screenshot in `review/`

## Stato dei componenti

- `docker-compose.yml`: `postgres` (17-alpine, healthcheck) e `pipeline` come strumento a richiesta (profilo `strumenti`). `backend`, `frontend` e il caricamento automatico alla tappa 7.
- `data-pipeline/`: `f1-pipeline` con `download`, `sample`, `transform`, `load`, `run` (modulo `csv` + PyArrow, psycopg 3, versioni fissate). Campione 2022–2024 in `sample/` (11 CSV, 2,5 MB, 0 scarti). Dataset completo in `raw/` (non versionato): 0 scarti, 2 posizioni derivate. Test: nell'immagine `f1-verifica-test`, `pip install ".[test]"`, `pytest` (160 passati, 5 saltati senza `F1_PIPELINE_TEST_DSN`).
- `database/migrations/`: V1–V4, 12 tabelle. Modello e regole di trasformazione in `docs/modello-dati.md`.
- `backend/`: scheletro Spring Boot 3.5, `JdbcClient`, Flyway (migrazioni impacchettate nel jar), springdoc. Test: `./mvnw -B -q verify`.
- `frontend/`: scheletro HTML + moduli ES + Tailwind v4, server Node con proxy `/api`. Test: `npm test`.

## Note per le tappe successive

- **Tappa 4**: gli `id` di gare, piloti, scuderie e circuiti sono quelli Ergast (Verstappen 830; Bahrain 2023 è la gara 1098). `results` contiene gare e sprint: ogni query filtra `session_type = 'race'` (15 gare con sprint nel campione; servono test su una di queste), e `GET /api/races/{id}/results` restituisce esattamente le righe `race`. Usare `count(DISTINCT race_id)` per le gare. Decidere e dichiarare in OpenAPI se `podiums` di una scuderia conta i piazzamenti (raccomandato da `architetto-dati`: 30 per Red Bull 2023) o le gare con podio (21), e se `races` conta iscrizioni o partenze; le query sono in `docs/modello-dati.md`. Colonne `NULL` da gestire: `position`, `grid_position`, `time_ms`, giro veloce, `drivers.code`. Valori attesi dai test bloccati, confermati sui dati: VER 2023 = 22 gare, 19 vittorie, 21 podi; Red Bull 2023 = 21 vittorie.
- **Tappa 6**: per stint e pit stop può servire un endpoint in più; stint senza mescola, assenti per le gare senza soste registrate.
- **Tappa 7**: il servizio `pipeline` deve perdere il profilo, eseguire `run --source sample` dopo `backend` healthy e terminare con 0. Frontend nel container con `HOST=0.0.0.0` e `API_TARGET=http://backend:8080`; healthcheck su `/`; timeout al proxy; `npm test` nella build dell'immagine. Contesto di build del backend = radice del repository. Il `load` non rimuove le righe sparite dall'input (vedi `docs/decisioni.md`): decidere con `architetto-dati` se resta un limite documentato. I 5 test della pipeline su database non girano in `verifica.sh` (file bloccato): trovare dove eseguirli.
- **Tappa 8**: il Compose richiede `POSTGRES_DB/USER/PASSWORD` senza default: il README spiega il passo `.env`. Piccole imprecisioni da correggere in `docs/modello-dati.md` tramite `architetto-dati`: le coppie gara-pilota ripetute sono 85 (91 sono le righe in più); la frase "va confermato rieseguendo `transform`" è superata (confermato: 0 scarti, 2 derivate); nominare `valori_derivati.json`.
- `backend/mvnw`: una riga ritoccata, vedi `docs/decisioni.md`; va riapplicata se si rigenera il wrapper.

## Da segnalare all'utente (file bloccati)

- `tests/accettazione/README.md` dice "un file `<tabella>.parquet` per tabella", ma i Parquet sono 13 per 12 tabelle (`sprint_results.parquet` separato) perché `test_validazione_scarta_e_registra` confronta `results.parquet` con `results.csv`.
- La regex di `test_nessuna_credenziale_nel_codice` ha dato falsi positivi su codice innocuo (`mvnw`, una costante con il nome della variabile del token): aggirati rinominando.
- L'hook blocca alcuni comandi di sola lettura (es. `docker run --rm` insieme a un percorso dei test bloccati).

## Registro sessioni

- 2026-11-10 — Domande sezione 3 chiarite; repo creata; struttura, subagent e hook preparati; test di accettazione approvati; hook attivati.
- 2026-11-10 — Tappa 1 chiusa: Compose con PostgreSQL e scheletri di pipeline, backend e frontend con test verdi. Revisione del `reviewer`: due difetti corretti (riga di `mvnw` scambiata per credenziale; `npm test` non funzionante su Node 22/24).
- 2026-11-10 — Tappa 2 chiusa: 4 migrazioni Flyway (12 tabelle), `docs/modello-dati.md`; applicate su PostgreSQL 17 e riviste dal `reviewer` (via libera).
- 2026-11-10 — Tappa 3 chiusa: dataset scaricato dall'utente con il token Kaggle; pipeline completa, campione 2022–2024, `docs/fonte-dati.md` (licenza CC0 verificata su Kaggle; termini originali di Ergast non più consultabili). Assunzioni dello schema verificate sui dati reali; due posizioni mancanti del 2005 derivate da `positionText`. Revisione del `reviewer`: via libera.
