# PROGRESS

Memoria tra le sessioni. Ogni sessione la legge all'inizio e la aggiorna prima di chiudere.

## Stato attuale

- **Tappa corrente**: 0 — Impostazione del sistema di agenti (prima della tappa 1)
- **Bloccanti**: test di accettazione, `config/accettazione.json` e `verifica.sh` da scrivere e far approvare all'utente; poi attivazione degli hook.

## Tappa 0 — Impostazione del sistema di agenti

- [x] Domande aperte della sezione 3 chiarite con l'utente (vedi `CLAUDE.md`)
- [x] Repository Git + repo privata GitHub
- [x] Struttura cartelle, `CLAUDE.md`, `PROGRESS.md`, `.env.example`, `run.sh`
- [x] Subagent in `.claude/agents/`
- [x] Hook scritti in `.claude/hooks/` (non ancora attivi)
- [x] Test di accettazione, `config/accettazione.json`, `verifica.sh` (contratto in `tests/accettazione/README.md`)
- [x] Approvazione dell'utente sui test (2026-11-10)
- [ ] `.claude/settings.json` con permessi e hook: lo crea l'utente (la scrittura da parte di Claude è bloccata), dopo l'approvazione dei test

## Tappe

1. [ ] Impostazione del progetto: Docker Compose con PostgreSQL, build per ogni componente, test vuoti
2. [ ] Modello dati: schema, migrazioni, diagramma ER, `docs/modello-dati.md`
3. [ ] Pipeline dati: ingestione, validazione, normalizzazione, formato intermedio, caricamento, report scarti
4. [ ] API Spring Boot: endpoint, aggregazioni, gestione errori, OpenAPI, test Testcontainers
5. [ ] Dashboard: struttura, filtri, chiamate API, gestione errori
6. [ ] Visualizzazioni: tempi sul giro, posizioni, stint e pit stop, confronti
7. [ ] Docker end-to-end: avvio da clone pulito, healthcheck, servizio di caricamento dati
8. [ ] Documentazione: README completo, diagramma architettura, esempi API, screenshot
9. [ ] Tutti i test di accettazione verdi e screenshot in `review/`

## Registro sessioni

- 2026-11-10 — Domande sezione 3 chiarite; repo creata; struttura, subagent e hook preparati.
