# Decisioni tecniche e compromessi

Registro delle scelte tecniche, con il motivo. Le decisioni prese con l'utente (repository, licenza, dati, stagioni, Java 21 + Maven, nome) sono in `CLAUDE.md`.

## Orchestrazione

- **PostgreSQL 17 (`postgres:17-alpine`)** nel Compose e nei test del backend: stessa immagine ovunque, così i test girano sullo stesso motore dell'ambiente locale.
- **Credenziali e porte solo da variabili d'ambiente**, senza valori di default per database, utente e password: se mancano, Compose e backend falliscono subito con un messaggio esplicito invece di partire con una password nota.
- **Verifica in uno stack isolato**: `verifica.sh` usa un progetto Compose, volumi, porte e credenziali propri, quindi non tocca l'ambiente di sviluppo e non richiede `.env`.

## Pipeline dati (`data-pipeline/`)

- **Modulo `csv` della libreria standard + PyArrow, senza pandas né Polars**: la validazione lavora riga per riga e deve registrare numero di riga e motivo di ogni scarto, con la stessa numerazione dei record usata dai test; un dataframe non aggiungeva nulla e Polars, scelto nello scheletro, è stato tolto. Il dataset completo (circa 590 000 giri) si trasforma in circa 4 secondi.
- **PyArrow per il Parquet**, con righe ordinate per chiave, compressione zstd e opzioni di scrittura fissate, nessun metadato né timestamp: due esecuzioni sullo stesso input producono file identici al byte.
- **Versioni fissate (`pyarrow==17.0.0`, `psycopg[binary]==3.2.3`)**: i byte dei Parquet dipendono dalla versione di PyArrow, e sono le stesse versioni dell'immagine dei test di accettazione.
- **Download con `urllib` verso l'API pubblica di Kaggle**, senza i client `kaggle` o `kagglehub`: nessuna dipendenza in più; supporta sia il token singolo (`Authorization: Bearer`) sia la coppia utente + chiave (HTTP Basic). Le credenziali vanno solo a kaggle.com e non compaiono mai nei messaggi.
- **Scarti, correzioni e derivazioni in tre file**: `scarti.json` elenca le righe scartate (chiave mancante, tipo non valido, duplicato, riferimento inesistente, cascata); `valori_annullati.json` gli attributi facoltativi non validi messi a `NULL` senza scartare la riga; `valori_derivati.json` le posizioni ricavate da `positionText` quando `position` manca (2 righe in tutto il dataset, nessuna nel campione).
- **Limite noto del caricamento**: l'upsert non rimuove dal database le righe che spariscono dall'input (solo `stints` viene sostituita). Su un database già popolato, ricaricare un input ridotto lascia le righe precedenti; `verifica.sh` e il Compose partono da un volume vuoto, quindi oggi non incide. Resta un limite dichiarato, riportato anche nel README.
- **`results.parquet` (gare) e `sprint_results.parquet` (sprint) separati**, riuniti dal caricamento nella tabella `results`: un test di accettazione confronta le righe di `results.parquet` con quelle di `results.csv`.
- **Caricamento con `COPY` verso tabelle temporanee e upsert `ON CONFLICT ... WHERE ... IS DISTINCT FROM`**, in una sola transazione: idempotente, non riscrive le righe identiche, e un errore non lascia dati a metà. `stints` viene sostituita, perché è derivata.
- **psycopg 3** come driver PostgreSQL; l'extra `binary` evita libpq e compilatore nell'immagine.
- **Campione ricopiato byte per byte dai CSV originali** con il comando `f1-pipeline sample`, limitato alle anagrafiche citate dalle stagioni 2022–2024: ripetibile e coerente.
- **I test del componente che scrivono su PostgreSQL girano solo con `F1_PIPELINE_TEST_DSN`** (database dedicato e già migrato) e altrimenti vengono saltati: `verifica.sh` li esegue accanto al database di verifica, che non devono toccare. Il caricamento resta coperto dai test di accettazione.
- **argparse per la CLI `f1-pipeline`** (`download`, `sample`, `transform`, `load`, `run`): nessuna dipendenza in più.
- **Layout `src/` con hatchling**: i test girano sul pacchetto installato, non sulla cartella di lavoro.

## Backend (`backend/`)

- **Spring Boot 3.5.x, Java 21, Maven con Maven Wrapper**: sull'host non serve Maven; il wrapper è di tipo `only-script`, quindi nessun jar binario è versionato.
- **`mvnw` ritoccato in una riga**: nel blocco "normalize http auth" il segnaposto `has-password` è stato sostituito con `set` (comportamento identico), perché il testo originale veniva scambiato per una credenziale dal controllo `test_nessuna_credenziale_nel_codice`. Chi rigenera il wrapper deve riapplicare la modifica.
- **Spring JDBC (`JdbcClient`) invece di JPA**: classifiche, medie e statistiche si calcolano in SQL e si mappano su DTO; un ORM aggiungerebbe entità mai esposte, e lo schema è già governato dalle migrazioni.
- **Flyway con le migrazioni in `database/migrations/`**: il `pom.xml` include quella cartella come risorsa in `db/migration`, così c'è una sola fonte delle migrazioni, finiscono nel jar e l'immagine Docker è autosufficiente. Conseguenza: la build dell'immagine deve avere come contesto la radice del repository (oppure passare `-Dmigrations.dir`).
- **Lo schema lo crea il backend all'avvio**: nel Compose il servizio `pipeline` parte dopo che `backend` è healthy.
- **Test con Testcontainers e le stesse variabili `POSTGRES_*` della produzione**, invece di `@ServiceConnection`: i test coprono anche la mappatura della configurazione.
- **Actuator espone solo `health`**, che include il controllo del database: è l'healthcheck del Compose.
- **springdoc-openapi 2.x con interfaccia**: `/v3/api-docs` richiesto dal contratto, più Swagger UI utile per una vetrina.
- **Definizioni delle statistiche** (dichiarate in OpenAPI): `races` conta i Gran Premi distinti in cui si compare in classifica, `starts` le sole partenze; `podiums` conta i piazzamenti tra i primi tre (`count(DISTINCT (race_id, position))`), quindi per una scuderia può superare `races`; `points` conta solo le gare e `sprintPoints` le sprint, e la loro somma è il totale di campionato. Verificate ricalcolando dai CSV del campione tutte le combinazioni pilota/scuderia per stagione.
- **Una sola query di statistiche per pilota e scuderia**: cambia solo la colonna filtrata, che è una costante del codice; tutti i valori della richiesta sono parametri con nome.
- **Gare e sprint nella stessa tabella, filtro di sessione in ogni query**: il comportamento predefinito di `/api/races/{id}/results` è "solo gara"; `?session=sprint` restituisce la sprint.
- **`?season=` senza gare per quel pilota o scuderia risponde 200 con contatori a zero**; il 404 vale solo per pilota o scuderia inesistente.
- **Errori in un unico gestore** con corpo `{status, error, message, path, timestamp}` e messaggi scritti nel codice, mai presi dall'eccezione: il 500 non espone dettagli interni.
- **I test del backend caricano il campione con la pipeline vera**: Testcontainers avvia PostgreSQL, Flyway applica le migrazioni, poi l'immagine di `data-pipeline/` esegue `run --source sample` sulla stessa rete, una volta per JVM. Nessun dato inventato né copiato a mano.
- **Immagine Docker multi-stage** (JDK 21 per la build, JRE 21 Alpine e utente non root per l'esecuzione), con contesto di build nella radice del repository; i test restano fuori dall'immagine perché usano Testcontainers.

## Frontend (`frontend/`)

- **HTML, CSS e moduli ES senza framework né bundler**: il browser carica i moduli così come sono; la build copia HTML e JS e compila il CSS.
- **Tailwind CSS v4 con `@tailwindcss/cli`**: nessun file di configurazione né PostCSS, rileva da solo le classi usate.
- **Percorsi relativi `/api/...` e proxy lato server**: stesso schema in sviluppo e nel container, senza CORS né URL dell'API cablati nel codice.
- **Observable Plot 0.6 con D3 7 al posto di Chart.js** (la proposta del brief): produce SVG, quindi assi ed etichette sono testo vero, e tratteggi e simboli per serie sono opzioni native, il che permette di non affidare l'informazione al solo colore. Motivazione estesa in [`direzione-ui.md`](direzione-ui.md#libreria-dei-grafici).
- **Librerie dei grafici servite in locale, senza bundler né CDN**: `npm run build` copia `plot.umd.min.js` e `d3.min.js` da `node_modules` in `dist/vendor/`, con le rispettive licenze, e la pagina li carica come script locali. Le versioni sono fissate in `package.json`. La dashboard funziona senza rete esterna e la `Content-Security-Policy` può limitarsi alla propria origine.
- **Carattere Inter servito in locale**: i file `woff2` del pacchetto `@fontsource-variable/inter` vengono copiati in `dist/fonts/` con la licenza (SIL Open Font 1.1); ripiego sui caratteri di sistema. Stesso motivo: nessuna richiesta a terzi.
- **Una sola vista nel DOM alla volta**: la navigazione (frammento dell'URL) smonta la vista corrente e monta la nuova. Ogni `data-testid` dei filtri corrisponde così a un solo elemento, e non restano grafici nascosti da tenere aggiornati. Le scelte dei filtri sopravvivono al cambio di vista perché stanno in uno stato condiviso (`stato.js`), non nel DOM.
- **Aggregazioni lato server, trasformazioni pure lato client**: classifiche, statistiche e medie arrivano già calcolate dall'API; il client rimodella i dati solo per disegnarli (soglia dei giri lenti, distacco cumulato, serie per pilota). Quel codice sta in `trasformazioni.js`, non dipende dal DOM né dalla libreria dei grafici ed è coperto dai test del componente; `grafici.js` si limita a disegnare.
- **Cache delle risposte per URL nel client**: i dati non cambiano mentre la dashboard è aperta, quindi ogni URL viene richiesto una volta sola; le risposte fallite non restano in cache, così "Riprova" ritenta davvero.
- **Server Node senza dipendenze anche nel container** (chiude il compromesso lasciato aperto tra server Node e nginx): l'immagine di esecuzione contiene solo Node, `server.mjs`, `serve.mjs` e `dist/`, senza `node_modules`, e gira come utente non root. Scelto al posto di nginx perché il comportamento del proxy (percorsi, errori, timeout, intestazioni di sicurezza) è uno solo in sviluppo, nei test del componente e nel Compose, senza una seconda configurazione da tenere allineata. Prezzo: niente compressione né cache HTTP avanzata, accettabile per una dashboard locale.
- **Proxy con timeout**: 15 secondi, modificabili con `PROXY_TIMEOUT_MS`. Se il backend accetta la connessione ma non risponde, il proxy chiude con 504; se non è raggiungibile, con 502. In entrambi i casi il corpo è JSON con `status` e `message`, e la dashboard mostra il riquadro di errore invece di restare in attesa. Il proxy accetta solo `GET` e `HEAD`, perché l'API è di sola lettura.
- **Test del componente con `node:test`**: integrato in Node, sufficiente per client API, trasformazioni, palette, formati, build e proxy; i test end-to-end sono quelli Playwright in `tests/accettazione/`. `npm test` gira nella build dell'immagine Docker: se un test fallisce l'immagine non si crea.
- **Eccezione motivata alla regola "aggregazioni lato server"**: classifiche, statistiche, medie e punti arrivano tutti dall'API. Nel browser restano tre calcoli sui giri di una gara già caricati: la soglia dei giri fuori scala (decide solo dove tagliare l'asse), la stima dei giri lenti per tutto il gruppo (le fasce grigie, dichiarate "stima" a schermo, perché la fonte non registra safety car) e il distacco tra due piloti sul tempo di gara a parità di giri, con interruzione al doppiaggio. I primi due sono scelte di presentazione; il terzo è una statistica comparativa che un prossimo passo dovrebbe spostare in un endpoint dedicato (es. `GET /api/races/{id}/gap?driverA=&driverB=`). Sono funzioni pure in `trasformazioni.js`, coperte dai test del componente.
- **Scelte nell'URL** (`#race-analysis?stagione=2023&gara=1098&piloti=830,815`): un link riporta alla stessa schermata e il ricaricamento non azzera i filtri; i valori inesistenti ripiegano sui predefiniti.
- **L'healthcheck del frontend controlla solo la propria pagina**: resta "healthy" anche a backend spento, e in quel caso la dashboard mostra il riquadro d'errore. Lo stato del backend ha il suo healthcheck.

