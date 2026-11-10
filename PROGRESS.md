# PROGRESS

Memoria tra le sessioni. Ogni sessione la legge all'inizio e la aggiorna prima di chiudere.

## Stato attuale

- **Tappa corrente**: 2 — Modello dati (responsabile: `architetto-dati`)
- **Bloccanti**: nessuno.

## Tappe

0. [x] Impostazione del sistema di agenti: struttura, subagent, hook attivi, test di accettazione approvati dall'utente (2026-11-10) e bloccati
1. [x] Impostazione del progetto: Docker Compose con PostgreSQL, build per ogni componente, test vuoti
2. [ ] Modello dati: schema, migrazioni, diagramma ER, `docs/modello-dati.md`
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
- **Tappa 3**: sostituire `test_sottocomandi_non_ancora_implementati` con test veri. L'immagine dei test di accettazione fissa `pyarrow==17.0.0` e `psycopg[binary]==3.2.3`: le versioni della pipeline devono restare compatibili. Scrivere `docs/fonte-dati.md`.
- **Tappa 7**: frontend nel container con `HOST=0.0.0.0` e `API_TARGET=http://backend:8080`; healthcheck su `/`; aggiungere un timeout al proxy; eseguire `npm test` nella build dell'immagine (non è lanciato da `verifica.sh`). Contesto di build del backend = radice del repository.
- **Tappa 8**: il Compose richiede `POSTGRES_DB/USER/PASSWORD` senza default: il README deve spiegare il passo `.env` (da confermare con l'utente se preferisce default di sviluppo).
- `backend/mvnw`: una riga ritoccata, vedi `docs/decisioni.md`; va riapplicata se si rigenera il wrapper.

## Registro sessioni

- 2026-11-10 — Domande sezione 3 chiarite; repo creata; struttura, subagent e hook preparati; test di accettazione approvati; hook attivati.
- 2026-11-10 — Tappa 1 chiusa: Compose con PostgreSQL e scheletri di pipeline, backend e frontend con test verdi. Revisione del `reviewer`: due difetti corretti (riga di `mvnw` scambiata per credenziale; `npm test` non funzionante su Node 22/24).
