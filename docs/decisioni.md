# Decisioni tecniche e compromessi

Registro delle scelte tecniche, con il motivo. Le decisioni prese con l'utente (repository, licenza, dati, stagioni, Java 21 + Maven, nome) sono in `CLAUDE.md`.

## Orchestrazione

- **PostgreSQL 17 (`postgres:17-alpine`)** nel Compose e nei test del backend: stessa immagine ovunque, così i test girano sullo stesso motore dell'ambiente locale.
- **Credenziali e porte solo da variabili d'ambiente**, senza valori di default per database, utente e password: se mancano, Compose e backend falliscono subito con un messaggio esplicito invece di partire con una password nota.
- **Verifica in uno stack isolato**: `verifica.sh` usa un progetto Compose, volumi, porte e credenziali propri, quindi non tocca l'ambiente di sviluppo e non richiede `.env`.

## Pipeline dati (`data-pipeline/`)

- **Polars invece di pandas**: tipi rigorosi e `null` nativo (niente `NaN` né conversioni implicite a float), tipo `Duration` per tempi e durate, lettura CSV e scrittura Parquet veloci.
- **PyArrow per il Parquet**: permette di controllare compressione e metadati, necessario per avere checksum identici tra due esecuzioni.
- **psycopg 3** come driver PostgreSQL: supporta `COPY` per il caricamento in blocco e l'upsert `ON CONFLICT` per l'idempotenza; l'extra `binary` evita libpq e compilatore nell'immagine.
- **argparse per la CLI `f1-pipeline`**: tre sottocomandi (`transform`, `load`, `download`) non giustificano una dipendenza in più.
- **Layout `src/` con hatchling**: i test girano sul pacchetto installato, non sulla cartella di lavoro.
- **Compromesso aperto**: oggi le dipendenze hanno solo limiti inferiori. Alla tappa 3 va deciso se fissare le versioni, perché i checksum dei Parquet possono cambiare tra versioni di Polars e PyArrow.

## Backend (`backend/`)

- **Spring Boot 3.5.x, Java 21, Maven con Maven Wrapper**: sull'host non serve Maven; il wrapper è di tipo `only-script`, quindi nessun jar binario è versionato.
- **`mvnw` ritoccato in una riga**: nel blocco "normalize http auth" il segnaposto `has-password` è stato sostituito con `set` (comportamento identico), perché il testo originale veniva scambiato per una credenziale dal controllo `test_nessuna_credenziale_nel_codice`. Chi rigenera il wrapper deve riapplicare la modifica.
- **Spring JDBC (`JdbcClient`) invece di JPA**: classifiche, medie e statistiche si calcolano in SQL e si mappano su DTO; un ORM aggiungerebbe entità mai esposte, e lo schema è già governato dalle migrazioni.
- **Flyway con le migrazioni in `database/migrations/`**: il `pom.xml` include quella cartella come risorsa in `db/migration`, così c'è una sola fonte delle migrazioni, finiscono nel jar e l'immagine Docker è autosufficiente. Conseguenza: la build dell'immagine deve avere come contesto la radice del repository (oppure passare `-Dmigrations.dir`).
- **Lo schema lo crea il backend all'avvio**: nel Compose il servizio `pipeline` parte dopo che `backend` è healthy.
- **Test con Testcontainers e le stesse variabili `POSTGRES_*` della produzione**, invece di `@ServiceConnection`: i test coprono anche la mappatura della configurazione.
- **Actuator espone solo `health`**, che include il controllo del database: è l'healthcheck del Compose.
- **springdoc-openapi 2.x con interfaccia**: `/v3/api-docs` richiesto dal contratto, più Swagger UI utile per una vetrina.

## Frontend (`frontend/`)

- **HTML, CSS e moduli ES senza framework né bundler**: il browser carica i moduli così come sono; la build copia HTML e JS e compila il CSS.
- **Tailwind CSS v4 con `@tailwindcss/cli`**: nessun file di configurazione né PostCSS, rileva da solo le classi usate.
- **Percorsi relativi `/api/...` e proxy lato server**: stesso schema in sviluppo (server Node senza dipendenze) e nel container, senza CORS né URL dell'API cablati nel codice.
- **Test del componente con `node:test`**: integrato in Node, sufficiente per client API, build e proxy; i test end-to-end sono quelli Playwright in `tests/accettazione/`.
- **Compromesso aperto**: alla tappa 7 va scelto se servire il frontend nel container con lo stesso server Node o con nginx.
