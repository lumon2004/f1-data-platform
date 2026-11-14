# F1 Data Platform

Vetrina di **data engineering e backend**: un sistema end-to-end che trasforma i CSV grezzi del dataset Kaggle/Ergast in un prodotto analitico (pipeline Python → PostgreSQL → API Spring Boot → dashboard web), avviabile con Docker Compose.

La specifica completa è in `f1-data-platform-brief-claude-code.md`: leggila quando ti serve il dettaglio di requisiti, endpoint, criteri di accettazione o tappe.

## Inizio e fine di ogni sessione

1. Leggi `PROGRESS.md` e riprendi dalla prima tappa non completata.
2. Lavora sulla tappa, delegando secondo la tabella **Delega**.
3. Prima di chiudere: aggiorna `PROGRESS.md` (tappa corrente, fatto, bloccanti) e fai un commit.

## Delega

L'agente principale coordina: assegna il lavoro, integra i risultati, tiene aggiornato `PROGRESS.md`. Il lavoro di dominio va al subagent responsabile della tappa.

| Tappa | Responsabile | Supporto |
|---|---|---|
| 1. Impostazione progetto | agente principale (Docker Compose) | `sviluppatore-pipeline`, `sviluppatore-backend`, `sviluppatore-frontend` (build e test vuoti del proprio componente) |
| 2. Modello dati | `architetto-dati` | — |
| 3. Pipeline dati | `sviluppatore-pipeline` | `architetto-dati` (dubbi sullo schema), `technical-writer` (`docs/fonte-dati.md`) |
| 4. API Spring Boot | `sviluppatore-backend` | `architetto-dati` (indici, query analitiche) |
| 5. Dashboard | `sviluppatore-frontend` | — |
| 6. Visualizzazioni | `sviluppatore-frontend` | `sviluppatore-backend` (endpoint aggiuntivi) |
| 7. Docker end-to-end | agente principale | ogni sviluppatore per il Dockerfile e l'healthcheck del proprio componente |
| 8. Documentazione | `technical-writer` | — |
| 9. Test verdi e screenshot | agente principale | `reviewer` |

Ogni tappa si chiude solo dopo il via libera del `reviewer`; le sue osservazioni tornano al responsabile della tappa. Una modifica allo schema, in qualunque tappa, passa da `architetto-dati`.

## Fatto

Il lavoro è **fatto** quando `./verifica.sh` termina con successo e `review/` contiene gli screenshot della dashboard. Prima di dichiararlo, delega la verifica al subagent `reviewer`.

## Decisioni già prese con l'utente

- Repo privata `lumon2004/f1-data-platform`. Nessuna licenza: software proprietario, niente file `LICENSE`.
- Dati: dataset Kaggle *Formula 1 World Championship* (Rohan Rao). La pipeline scarica con il token Kaggle se configurato, altrimenti legge i CSV già presenti in `data-pipeline/raw/`.
- Dataset di esempio versionato: stagioni **2022–2024**, in `data-pipeline/sample/`.
- Backend: **Java 21 + Maven**, Spring Boot 3.
- Nome: **F1 Data Platform**, con disclaimer di non affiliazione in README e footer della dashboard.

Le scelte tecniche che prendi tu (librerie "proposta" del brief) vanno motivate in `docs/decisioni.md`.

## Vincoli

- **Test di accettazione bloccati**: `tests/accettazione/`, `verifica.sh`, `config/accettazione.json`, `.claude/hooks/` e `.claude/settings.json` sono di sola lettura. Se un test sembra sbagliato, segnalalo all'utente.
- **Credenziali** (database, Kaggle) vivono solo in `.env` o `~/.kaggle/`: il codice le legge da variabili d'ambiente; tu lavori con i soli nomi delle variabili (`.env.example`).
- **Versionato**: solo il dataset di esempio. `data-pipeline/raw/` e `data-pipeline/processed/` restano fuori da git.
- **Materiale grafico**: solo dati testuali per scuderie e piloti; nessun logo ufficiale (F1, FIA, scuderie, sponsor) né foto protette.
- **Attribuzione** della fonte dati in README, dashboard e `docs/fonte-dati.md`.
- Dati prima dell'interfaccia; il database è un modello relazionale vero, non lo specchio dei CSV; la pipeline è riproducibile da comando.
- Quando serve una decisione dell'utente (dati, licenze, nome, credenziali), fermati e chiedi.

Gli hook in `.claude/hooks/` fanno rispettare questi vincoli: un'azione bloccata è un segnale per cambiare strada, non un ostacolo da aggirare.
