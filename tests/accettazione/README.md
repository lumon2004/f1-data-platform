# Test di accettazione — contratto

Questi test sono **bloccati**: definiscono il traguardo e non si modificano. Si lanciano solo tramite `./verifica.sh`.
Le soglie numeriche stanno in `config/accettazione.json`.

I test guardano il sistema dall'esterno. Per farlo fissano poche interfacce, elencate qui: tutto il resto (librerie, struttura interna, nomi di colonne) è libero.

## Docker Compose (`docker-compose.yml` nella radice)

- Servizi: `postgres`, `backend`, `frontend` con healthcheck; `pipeline`, servizio una tantum che carica il dataset di esempio e termina con codice 0.
- Porte pubblicate sull'host lette da variabili d'ambiente: `POSTGRES_PORT`, `API_PORT`, `WEB_PORT`.
- Credenziali lette da `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`. `verifica.sh` le imposta da sé: il sistema si avvia senza `.env`.
- Il frontend chiama l'API con percorsi relativi `/api/...` (il server del frontend fa da proxy verso il backend).

## Pipeline (`data-pipeline/`)

- Pacchetto Python installabile con `pip install data-pipeline/` (Python 3.12), con extra opzionale `test` per i propri test; i test del componente stanno in `data-pipeline/tests/`.
- Comando `f1-pipeline` con i sottocomandi:
  - `f1-pipeline transform --input DIR --output DIR`: legge i CSV in formato Kaggle/Ergast da `--input`, scrive il formato intermedio Parquet in `--output` (un file `<tabella>.parquet` per tabella, almeno `results.parquet` e `laps.parquet`) e il report degli scarti `scarti.json`.
  - `f1-pipeline load --input DIR`: carica in PostgreSQL l'output di `transform`, in modo idempotente. Connessione da `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
- `scarti.json`: lista di oggetti `{"file": "results.csv", "riga": 42, "motivo": "..."}`, con `riga` numerata da 1 contando l'intestazione come riga 1. Tra due righe duplicate si tiene la prima.
- `data-pipeline/sample/`: CSV Kaggle/Ergast originali (stessi nomi file e colonne) delle sole stagioni del dataset di esempio.

## API (porta `API_PORT`)

Risposte JSON con campi in camelCase. Gli id sono quelli che l'API stessa espone.

| Endpoint | Risposta (campi minimi) |
|---|---|
| `GET /api/seasons` | lista di `{year}` |
| `GET /api/seasons/{year}/races` | lista di `{id, round, name, date}` |
| `GET /api/races/{raceId}` | `{id, season, round, name, date, circuit: {id, name, country}}` |
| `GET /api/races/{raceId}/results` | lista di `{position, points, status, laps, driver: {id, code, name}, team: {id, name}}` (`position` può essere `null`) |
| `GET /api/races/{raceId}/laps/{driverId}` | lista di `{lap, position, timeMs}`; lista vuota se il pilota non ha giri in quella gara |
| `GET /api/drivers/{driverId}/statistics[?season=YYYY]` | `{races, wins, podiums, points}` |
| `GET /api/teams/{teamId}/statistics[?season=YYYY]` | `{races, wins, podiums, points}` |

- Errori: 404 per risorsa inesistente, 400 per parametri non validi, corpo JSON con almeno `{status, message}`.
- OpenAPI in `GET /v3/api-docs`, con tutti i percorsi qui sopra.

## Dashboard (porta `WEB_PORT`)

Elementi individuati dall'attributo `data-testid`:

- Navigazione: `nav-season-overview`, `nav-race-explorer`, `nav-driver-comparison`, `nav-team-comparison`, `nav-race-analysis`.
- Filtri: elementi `<select>` `filtro-stagione` (valore delle opzioni = anno), `filtro-gara`, `filtro-sessione`, `filtro-pilota-a`, `filtro-pilota-b`, `filtro-scuderia-a`, `filtro-scuderia-b`.
- Race explorer: `lista-gare` con elementi `gara` cliccabili; `risultati-gara` con righe `riga-risultato`.
- Race analysis: `grafico-tempi-giro` e `grafico-posizioni`, ciascuno con l'attributo `data-punti` = numero di punti disegnati.
- Driver comparison: `statistiche-pilota-a`, `statistiche-pilota-b`.
- Errore API: `errore-api` visibile quando l'API non risponde.
- `footer` con attribuzione della fonte dati e disclaimer di non affiliazione.
