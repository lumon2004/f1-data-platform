# Revisione delle tappe 5 e 6 (dashboard e visualizzazioni)

Data: 2026-11-10. Oggetto: working tree non committato (`frontend/`, servizio `frontend` di Compose, `docs/direzione-ui.md`, screenshot in `review/`).

**Verdetto: via libera alle tappe 5 e 6**, subordinato all'esito dello script di verifica, che in questa revisione non ho eseguito io (era in corso, lanciato dall'agente principale). Nessuna osservazione bloccante; le osservazioni della sezione 2 vanno chiuse o decise prima della chiusura del progetto.

## Come ho verificato

- Lettura integrale di `frontend/src/`, `frontend/scripts/`, `frontend/test/`, `frontend/Dockerfile`, servizio `frontend` in `docker-compose.yml`.
- Test del componente rieseguiti in un container Node 22 su una copia: 54 su 54. Node 20 non riprovato.
- Playwright (Chromium) contro lo stack di sviluppo, che serve file identici al working tree (confrontati): tutte le viste, stagioni 2022/2023/2024, Monaco 2023, Qatar 2023 (gara, sprint, qualifica), 6 piloti e 0 piloti selezionati, tutte le 68 gare in Race analysis, 390 px e 360 px, API interrotta, 503, 500, guasti parziali, backend davvero irraggiungibile (container temporaneo del frontend con backend inesistente: 502 dal proxy), "Riprova", cambi rapidi di filtri e viste con latenza casuale sulle risposte.
- Valori a schermo ricalcolati dai CSV di `data-pipeline/sample/`.
- Non verificato: test di accettazione ufficiali (non lanciati da me), suggerimenti al passaggio del puntatore (il mio tentativo non ha colpito il grafico), ordine completo di tabulazione dalla navigazione, lettori di schermo, browser diversi da Chromium.

Screenshot aggiuntivi, fuori dal repository: `/private/tmp/claude-501/-Users-lucamonaco-Developer-f1-data-platform/6be1e166-f170-4e24-a62c-841413ca8303/scratchpad/shots/` (nomi citati sotto come `shots/...`).

## 1. Bloccanti per le tappe

Nessuno.

## 2. Da sistemare o decidere prima della chiusura del progetto

1. **Driver comparison: scala dei tempi governata da uno stato nascosto, valori fuori scala leggibili solo nel suggerimento.** `frontend/src/js/viste/driver-comparison.js:255` usa `stato.scalaCompleta`, ma l'interruttore "Scala completa" esiste solo in Race analysis (`race-analysis.js:41-51`). Attivandolo lì, il grafico di Driver comparison cambia scala senza alcun controllo né nota (verificato). Senza interruttore, in questa vista il tempo dei giri fuori scala si legge solo nel suggerimento: contrasta con `docs/direzione-ui.md:68` e `:72` ("nulla di essenziale sta solo lì"). Rif. `review/driver-comparison.png` (8 triangoli, nessun interruttore).

2. **Calcoli analitici lato client, mentre il brief (sezione 5) vuole aggregazioni e statistiche comparative lato server.** `frontend/src/js/trasformazioni.js:175-188` (distacco cumulato tra due piloti), `:67-90` (giri lenti del gruppo, da mediane), `:28-34` (soglia fuori scala da quartili); somma `points + sprintPoints` in `driver-comparison.js:13` e `team-comparison.js:12`. I numeri sono corretti (vedi sezione 4), e soglia e fasce sono scelte di presentazione; il distacco però è una statistica comparativa. Decidere: esporlo dall'API, oppure motivare l'eccezione in `docs/decisioni.md` (oggi non c'è). Il commento in testa a `trasformazioni.js:3` ("qui non si ricalcolano statistiche") non descrive quello che il file fa.

3. **"Distacco in pista" è fuorviante con i doppiati.** È la differenza dei tempi cumulati a parità di giro: Verstappen–Pérez a Monaco 2023 arriva a circa +220 s (`shots/driver-ver-per-monaco.png`), ma Pérez è a 2 giri e in pista i due sono vicini. Inoltre non tiene conto del distacco in griglia. Titolo e nota (`driver-comparison.js:87-88`) andrebbero corretti in "distacco sul tempo di gara a parità di giri", o il caso dei doppiati segnalato.

4. **Schermo stretto: le tabelle non si comportano come dichiarato.** `docs/direzione-ui.md:90` dice che le tabelle larghe scorrono in orizzontale. A 390 px il calendario di Season overview non scorre: va a capo fino a 4-5 righe per gara e la pagina supera i 5000 px (`shots/m-season-overview.png`). La classifica costruttori invece scorre, ma la barra è tagliata e le colonne Gare, Sprint, Vitt., Podi restano fuori schermo senza alcun indizio (`season-overview.js:143-161`). Nessuno scorrimento orizzontale della pagina a 390 e 360 px; i grafici a 390 px sono leggibili (`shots/m-race-analysis.png`).

5. **Contrasto delle linee di contesto sotto la soglia dichiarata.** `frontend/src/js/grafici.js:180`: `#94a3b8` con opacità 0,8 su bianco è circa 2,6 : 1 (meno con l'opacità), mentre `docs/direzione-ui.md:28` promette almeno 3 : 1 per linee e marcatori. `frontend/test/palette.test.mjs:12` controlla solo le sei serie, non `CONTESTO`. Le sigle a fine linea (`#64748b`) sono a norma. Scurire il grigio oppure dichiarare l'eccezione.

6. **I test del componente non coprono il codice che disegna.** Sono veri (nessun test saltato, svuotato o con valori di comodo; il proxy è provato con server HTTP reali, compresi 502 e 504), ma coprono solo `api.js`, `format.js`, `palette.js`, `trasformazioni.js`, `server.mjs` e la build. Senza alcun test: `grafici.js`, `componenti.js`, `main.js`, `stato.js` (`creaTurni`, `scegliValido`, cioè la protezione dalle risposte arrivate in ritardo) e le cinque viste. `frontend/test/build.test.mjs:62-83` verifica i `data-testid` cercando stringhe nei sorgenti: non prova che gli elementi vengano creati. Tutto questo oggi è coperto solo dai test end-to-end di accettazione. Almeno `stato.js` è puro e si prova senza DOM.

7. **Etichette delle statistiche ambigue.** In Team comparison "Gare 22 / Partenze 22" per una scuderia con due vetture (`shots/team-comparison-2023.png`; `driver-comparison.js:21-36` riusato da `team-comparison.js:134`). "Media griglia" esclude le partenze dalla pit lane (griglia 0): Alonso 2023 6,33 a schermo contro 6,05 su tutte le 22 gare; Red Bull 5,57 contro 5,32. La scelta del backend è difendibile, ma a schermo non è detta; va verificato che sia scritta nella documentazione dell'API.

8. **Le scelte non stanno nell'URL.** Ricaricando la pagina si torna a stagione 2024 e prima gara (verificato: 2022 diventa 2024); non si può condividere il link a una gara. Per un portfolio è un limite visibile; `docs/direzione-ui.md:79` promette solo la conservazione tra viste, quindi non è una difformità.

## 3. Note

- **`errore-api` anche per errori che non vengono dall'API.** `frontend/src/js/main.js:35-39` e `:110-112`: un'eccezione interna di una vista mostra lo stesso riquadro, intitolato "Dati non disponibili" (`index.html:40`), con il testo "errore imprevisto nella dashboard". Il titolo in quel caso è impreciso. In uso normale il riquadro resta nascosto in tutte le viste (verificato) e compare per API interrotta, 502 reale, 503, 500 e guasti parziali; sparisce cambiando vista e dopo "Riprova" riuscito.
- **Triangoli dei giri fuori scala.** Sono triangoli per tutti i piloti (`grafici.js:110-117`), e il triangolo è anche il marcatore della terza serie: il pilota si riconosce da riga e colore. Con 6 piloti una riga di triangoli tocca il bordo del riquadro (`shots/analysis-monaco-6.png`).
- **Stint brevi senza numero.** `grafici.js:289` numera solo gli stint di almeno 3 giri: a Monaco 2023 le righe di ZHO, PER e HUL (sosta al giro 1) cominciano da "2" (`shots/analysis-monaco.png`).
- **Sigle dei ritirati dentro il grafico delle posizioni**, attraversate dalle linee: LEC, PIA, OCO in `review/race-analysis.png`; STR a Monaco.
- **Incoerenza tra viste**: il grafico dei tempi di Driver comparison non ha le fasce grigie dei giri lenti che ha Race analysis (`driver-comparison.js:263` non passa `fasce`).
- **Richieste superate non annullate.** `api.js:30` accetta `signal`, ma `creaClient` (`:85`) non lo passa mai: le risposte in ritardo vengono ignorate, non interrotte. Con cambi rapidi e latenza casuale lo stato finale è risultato sempre coerente con i filtri.
- **Healthcheck del frontend** (`frontend/Dockerfile:27-28`, `docker-compose.yml:87-92`): controlla solo `/`, quindi il servizio è "healthy" anche con il backend irraggiungibile (verificato). È una scelta sensata, ma va detta in `docs/architettura.md`.
- **Nessuna compressione né validatori di cache** nel server statico (`server.mjs:118-122`): circa 576 kB di D3 e Plot a ogni caricamento. Dichiarato in `docs/decisioni.md:56`.
- **Licenze di terze parti.** Plot e D3 (ISC), Inter (OFL 1.1): i file di licenza sono copiati in `dist/` (`scripts/build.mjs:14-22`) e serviti; il CSS porta l'intestazione MIT di Tailwind. Tutte compatibili con un software proprietario. Mancano un elenco nel README e la licenza di D3 in `docs/direzione-ui.md:58` (tappa 8).
- **Console.** Nessun errore, avviso o eccezione navigando tutte le viste e tutte le 68 gare. Con l'API in errore il browser scrive "Failed to load resource": è inevitabile.
- **Disposizione di `review/`.** Ci sono i quattro screenshot richiesti; Team comparison non è tra quelli prodotti dallo script (non richiesto dal brief).

## 4. Controlli superati

- **Dati a schermo uguali ai CSV.** Classifica 2023: Verstappen 575, Pérez 285, Hamilton 234; Red Bull 860, Mercedes 409, Ferrari 406. Bahrain 2023: ordine d'arrivo, griglie, distacchi, giro più veloce di Zhou (1:33.996), 50 soste. Monaco 2023: 37 soste, 78 giri. Albon 2023: 25 + 2 punti, media arrivo 11,11, media griglia 11,95, 4 ritiri. Verstappen 2023: 19 vittorie, 21 podi, 12 pole, 9 giri veloci, media arrivo 1,27. Distacco finale Albon–Alonso in Bahrain: 51,137 s, uguale alla differenza dei distacchi ufficiali.
- **`data-punti` è onesto.** Viene dai dati passati al disegno (`grafici.js:33-35`, `trasformazioni.js:135`, `:165`), non da una costante, e coincide con i segni nel SVG: Monaco 234 = 77 + 1 + 78 + 78 marcatori; posizioni 1533 = 1513 giri + 20 caselle di griglia. Senza piloti selezionati l'attributo viene tolto e compare un messaggio.
- **Nessuna scorciatoia verso i test.** Nessun ramo che riconosca il browser di test, nessun `data-testid` fittizio; l'unico elemento con `data-testid` nascosto è `errore-api` in assenza di errori.
- **Rete e sicurezza.** Nessuna richiesta esterna; CSP limitata alla propria origine; nessun `innerHTML` (un messaggio dell'API con HTML viene mostrato come testo, verificato).
- **Marchi.** Nessun logo, immagine, bandiera, colore di livrea o carattere ufficiale; colori delle serie assegnati per ordine di selezione. Footer conforme al testo di `docs/fonte-dati.md` (Kaggle, titolo del dataset, Rohan Rao, Ergast, non affiliazione).
- **Repository.** `frontend/node_modules/` e `frontend/dist/` ignorati da `frontend/.gitignore`; nessuna immagine o carattere versionato in `frontend/`; nessuna credenziale nel codice; screenshot di `review/` tra 196 e 364 kB, sotto la soglia di 5 MB.
- **Container.** Utente `node`, test nella build, immagine finale senza `node_modules`; proxy con timeout (504) e 502 in JSON; con il backend spento ogni vista mostra il riquadro di errore con "Riprova".
- **Revisione visiva a 1440 px.** Le quattro viste in `review/` e Team comparison sono coerenti tra loro e con `docs/direzione-ui.md`: gerarchia chiara, assi con etichetta e unità, legende con colore, tratteggio e marcatore, note esplicite su mescole, fuori scala e fasce stimate. Monaco (pioggia, giri 53-70) e Qatar (neutralizzazione ai giri 2-4, sprint e qualifica) reggono. Presentabili in un portfolio: Race analysis, Race explorer, Season overview e Driver comparison a schermo largo. Non ancora: Season overview su telefono (punto 4).

---

# Verifica finale (tappa 9)

Data: 2026-11-10. Oggetto: commit `ec29d4f` (albero di lavoro pulito, salvo `PROGRESS.md` modificato e non in commit).

**Verdetto: lo step NON si può ancora dichiarare chiuso.** Il prodotto soddisfa i criteri della sezione 6, ma lo script di verifica, che è l'unico criterio di "fatto", oggi è instabile: 2 esecuzioni fallite su 3. La causa non è nel codice del progetto, ma sta in file bloccati: serve una decisione dell'utente. Restano inoltre due difformità piccole da chiudere (punti 2 e 3).

## Come ho verificato

- Script di verifica lanciato 3 volte, senza altre attività Docker mie durante la seconda e la terza.
- Clone vero (`git clone` in una cartella esterna), stack `f1-clone` su porte 35432/38080/38081 con variabili passate in linea; esempi `curl` del README e sonde sugli endpoint contro quello stack.
- Playwright (Chromium) contro lo stack del clone: 390 e 360 px su tutte le viste, Verstappen–Pérez a Monaco 2023, interruttore della scala, scelte nell'URL, URL non validi, console.
- Lettura di test di accettazione, migrazioni, `load.py`, query delle statistiche, test del backend; storia git completa (178 percorsi mai aggiunti, blob più grandi).
- Campione confrontato riga per riga con il dataset completo locale; conteggi del README confrontati con database e CSV.
- Non verificato: download da Kaggle e caricamento del dataset completo (servono credenziali), tempi dichiarati della pipeline sul dataset completo (4 s e 20 s), 17 102 stint del dataset completo, build delle immagini di backend e pipeline senza cache, browser diversi da Chromium.

## 1. Bloccante per la chiusura

1. **Lo script di verifica fallisce in modo intermittente: 2 volte su 3.** Esecuzioni 1 e 2: codice 1, `1 failed, 37 passed`, sempre `test_database.py::test_coerenza_con_csv`, su gare diverse (1078, poi 1102). Esecuzione 3: codice 0, 38 su 38. Backend (176 test, 0 saltati) e pipeline (160 passati, 5 saltati) verdi in tutte e tre. Screenshot identici al byte in tutte e tre.
   - Errore mostrato: `[Errno 101] Network is unreachable` verso `host.docker.internal:18080`. È fuorviante: quel nome ha due indirizzi, IPv4 e IPv6; l'IPv6 è sempre irraggiungibile e il messaggio riporta l'ultimo tentativo.
   - Errore vero, catturato replicando lo stesso traffico (stesse 1 430 richieste, stessa libreria) contro lo stack di sviluppo: una singola connessione IPv4 resta appesa fino al timeout di 30 s (`TimeoutError`), poi tutto riprende. Visto 1 volta su 5 repliche; le sessioni fallite durano 45-49 s contro 22 s di quella riuscita, cioè una attesa di 30 s.
   - Quindi: non è un difetto di API, database o pipeline (succede anche contro lo stack di sviluppo, acceso da due ore). È il percorso contenitore dei test → gateway dell'host di Docker Desktop, sommato a un test che apre circa 1 430 connessioni nuove senza alcun nuovo tentativo. Causa ultima non accertata (Docker Desktop 29.9.3, macchina virtuale con 4 GB e più stack accesi: ipotesi, non misurata).
   - Il rimedio sta in file bloccati (client HTTP dei test con sessione e nuovi tentativi, oppure contenitore dei test sulla rete di Compose): va segnalato all'utente, non aggirato. Fino ad allora "lo script passa" è vero solo a volte, e il ciclo esterno e l'hook di completamento ne dipendono.

## 2. Da sistemare

2. **`PROGRESS.md` in commit è fermo alla tappa 5** (tappe 5-9 non spuntate, "manca `frontend`"). La versione aggiornata esiste solo nell'albero di lavoro: un clone riceve quella vecchia. Va messa in commit; la tappa 9 va spuntata solo dopo il punto 1.
3. **`README.md:207` dice "54 test del frontend": sono 72** (build del clone senza cache: `tests 72, pass 72, skipped 0`). `docs/architettura.md:160` elenca le aree coperte senza `stato.js` e `url.js`.
4. **I 5 test della pipeline che scrivono su PostgreSQL non girano in nessun passaggio automatico** (`data-pipeline/tests/test_load.py:94`, saltati senza `F1_PIPELINE_TEST_DSN`). Sono proprio quelli su caricamento, idempotenza e annullamento della transazione. Dichiarato in `README.md:203` e `docs/decisioni.md:23`; il caricamento resta coperto dall'esterno dai test di accettazione, ma il ritorno indietro su errore no.
5. **Licenza dei dati: punto aperto da far decidere all'utente prima di qualunque pubblicazione.** `docs/fonte-dati.md:33-43` è onesto: CC0 dichiarata su Kaggle, termini originali di Ergast (uso non commerciale) non riletti. Con repository privato il rischio è contenuto; la visione del brief parla però di applicazione pubblica.
6. **Volumi Docker rimasti**: `f1-clone_postgres-data` (creato da questa verifica), `f1-prova_postgres-data` e quattro volumi anonimi precedenti, di origine non accertata. Le cartelle `data-pipeline/raw` e `data-pipeline/processed` vengono create nel clone dal montaggio dei volumi (ignorate da git).

## 3. Criteri della sezione 6: test e giudizio

| Criterio | Test che lo verifica | Giudizio |
|---|---|---|
| Riproducibilità | `test_riproducibilita` (checksum di tutti i file di due esecuzioni) | Stringente. Stesso ambiente per entrambe le esecuzioni: non prova la riproducibilità tra macchine |
| Idempotenza | `test_idempotenza_caricamento` (conteggi prima e dopo due caricamenti) | Adeguato; confronta i conteggi, non i contenuti |
| Validazione | `test_validazione_scarta_e_registra` (3 righe guaste in `results.csv`) | Adeguato ma su un solo file; il ramo "corrette" non è provato. I test del componente coprono il resto |
| Valori mancanti e tempi | `test_valori_mancanti_e_tempi` | Parziale: cerca solo `\N` e il formato `m:ss.mmm` nelle colonne di testo; passerebbe anche eliminando le colonne. Comportamento reale corretto (tempi in ms nello schema e nell'API) |
| Schema dalle sole migrazioni | `test_schema_da_migrazioni` | Debole: controlla lo storico Flyway e la presenza delle tabelle, non che nulla nasca fuori dalle migrazioni. Verificato a mano: `load.py:116` crea solo tabelle temporanee |
| Integrità | `test_chiavi_primarie_ed_esterne`, `test_chiave_naturale_gare` | Adeguato sulle chiavi esterne; sulla chiave naturale chiede solo "un indice unico qualsiasi" su `races`. Lo schema reale ha `UNIQUE (season_year, round)` |
| Coerenza con i CSV | `test_coerenza_con_csv` (68 gare, risultati e giri via API) | Stringente; è il test instabile del punto 1 |
| Endpoint 200 e schema | `test_seasons` … `test_statistiche_schema`, `test_openapi`; 176 test JUnit con Testcontainers | Stringente. PostgreSQL reale, dati caricati dalla pipeline vera, nessun mock, nessun test saltato |
| 404 e 400 | `test_risorse_inesistenti_404`, `test_parametri_non_validi_400` | Adeguato |
| Statistiche note | `test_statistiche_note_pilota` (22/19/21), `test_statistiche_note_scuderia` (21 vittorie) | Minimo nei test di accettazione (niente punti); robusto in `StatisticsApiTest.java` (15 casi con punti e sprint) |
| Tempo di risposta | `test_tempi_di_risposta` (7 endpoint, mediana di 5) | Adeguato; `ResponseTimeTest.java` copre anche gli 8 endpoint aggiuntivi. Misurati 6-15 ms |
| Console senza errori | `test_navigazione_senza_errori_console` | Adeguato (solo dati predefiniti) |
| Stagione → gare → risultati | `test_race_explorer_stagione_gare_risultati` | Adeguato |
| Grafici con dati | `test_race_analysis_grafici` | Parziale: si fida dell'attributo `data-punti` dichiarato dalla pagina. Verificato dal vivo: 232 punti dichiarati, 258 segni nel SVG |
| Confronto tra due piloti | `test_driver_comparison` | Debole: basta una cifra qualsiasi nei due riquadri. Comportamento reale corretto (valori ricalcolati nella revisione precedente) |
| Errore dell'API | `test_errore_api` | Adeguato per l'avvio; errori a metà sessione provati solo a mano |
| Avvio da clone pulito | `test_servizi_healthy`, `test_caricamento_dati_completato` | Parziale: la "copia pulita" comprende anche i file non tracciati e non ignorati, quindi non equivale a un clone. Clone vero provato a mano: funziona |
| Healthcheck entro soglia | `test_tempo_di_avvio` (soglia 180 s) | Adeguato; misurati 18 s con immagini già costruite. La build non è nel conteggio |
| Nessun file proibito | `test_nessun_file_proibito`, `test_dimensione_file`, `test_nessuna_credenziale_nel_codice`, `test_dataset_di_esempio` | Adeguato sull'albero; la storia non è controllata dai test. Controllata a mano: pulita |
| README e documenti | `test_readme`, `test_documenti` | Formale: cerca titoli e parole, non la correttezza. Contenuto verificato a mano (sezione 5) |
| Screenshot | prodotti dai test della dashboard | 4 su 4, deterministici |

Nessun criterio è soddisfatto solo sulla carta: dove il test è debole, il comportamento reale regge al controllo manuale.

## 4. Clone pulito

- `git clone` del repository locale, poi `docker compose -p f1-clone up -d --build` con le sei variabili in linea: `postgres`, `backend`, `frontend` healthy e `pipeline` terminata con 0 in 20 s (immagini in cache). Caricamento: 0 scarti, 74 489 giri, 1 659 risultati, 3,1 s.
- `http://localhost:38081/` risponde 200 con la dashboard; `http://localhost:38080/api/seasons` restituisce 2024, 2023, 2022 (24, 22, 22 gare).
- Senza le tre variabili del database Compose si ferma con il messaggio "imposta POSTGRES_DB (vedi .env.example)", come dice il README.
- Le istruzioni del README corrispondono. Il passo del file delle variabili non l'ho potuto eseguire alla lettera (hook): le variabili in linea usano lo stesso meccanismo.
- Stack spento senza rimuovere il volume: resta `f1-clone_postgres-data`.

## 5. Documentazione contro realtà

- **Vero**: 15 endpoint (OpenAPI), 12 tabelle, 4 migrazioni, 11 CSV nel campione e 14 nel dataset; conteggi del campione (68, 1 359, 300, 74 489, 2 542, 3 859) uguali a database e CSV; conteggi del dataset completo uguali ai CSV locali; `compound` sempre `null`; 176 test del backend, 165 della pipeline (5 saltati), 38 di accettazione; porte, healthcheck e ordine di avvio; proxy solo GET e HEAD (POST: 405), intestazione CSP; 400 su `session` e `season` non validi; Swagger UI e `/v3/api-docs` rispondono 200.
- **Esempi `curl` del README**: tutti e quattro restituiscono esattamente i valori scritti (stagioni; Verstappen 2023: 22, 22, 19, 21, 530, 45, 12, 9; Red Bull 2023: 860, 790, 70, 21, 30; 404 con lo stesso messaggio).
- **Falso**: "54 test del frontend" (sono 72); `PROGRESS.md` in commit.
- Diagrammi Mermaid (flowchart nel README, flowchart e sequenza in `docs/architettura.md`, ER in `docs/modello-dati.md`): sintassi plausibile; non li ho resi con un interprete. Ancore dei collegamenti interni corrette.
- Le dieci sezioni richieste, il diagramma, "Data Source & Acknowledgements" e il disclaimer ci sono e dicono cose corrette.

## 6. Vincoli della sezione 4

- Licenza documentata in `docs/fonte-dati.md` con data e metodo di verifica; attribuzione in README, footer della dashboard e documento; disclaimer in README e footer.
- Nessun logo, immagine o carattere ufficiale: le uniche immagini versionate sono i 4 screenshot; nella pagina 0 elementi immagine; nessuna richiesta esterna.
- Storia git: nessun file di credenziali, nessun file di `raw/` o `processed/`, nessun Parquet; blob più grande 2,3 MB (`lap_times.csv` del campione). Nessun file `LICENSE`, per decisione dell'utente.
- Il campione non è ritoccato: ogni riga degli 11 CSV esiste identica al byte nel dataset completo.

## 7. Giro di correzioni della dashboard

Gli otto punti "da sistemare" della revisione precedente sono stati affrontati davvero.

| Punto | Esito |
|---|---|
| 1. Scala in Driver comparison | Chiuso. Interruttore proprio; attivarlo non cambia Race analysis (verificato). Albon–Alonso in Bahrain: asse da 1:36-1:44 a 1:35-2:10 e nota degli 8 giri rimossa |
| 2. Calcoli lato client | Chiuso come eccezione. `docs/decisioni.md:59` è onesta: distingue le due scelte di presentazione dal distacco, che chiama statistica comparativa e rinvia a un endpoint futuro; l'intestazione di `trasformazioni.js` ora dice la stessa cosa. Resta debito tecnico |
| 3. Distacco con doppiati | Chiuso. Monaco 2023: serie ferma al giro 30, linea "Giro 31: PER doppiato", nota esplicita. Ricalcolato dai CSV: Verstappen chiude il giro 31 prima che Pérez chiuda il 30; distacco al giro 30 di 79,175 s |
| 4. Schermo stretto | Chiuso. A 390 e 360 px nessuno scorrimento orizzontale della pagina; Season overview da oltre 5 000 a 3 970 px; calendario compattato; avviso di scorrimento sopra le tabelle larghe |
| 5. Contrasto del grigio | Chiuso sulla carta e nel test (`palette.test.mjs`); rapporto non rimisurato da me |
| 6. Test del componente | In parte: aggiunti `stato.test.mjs` e `url.test.mjs` (72 test). `grafici.js`, `componenti.js` e le viste restano coperti solo dai test end-to-end |
| 7. Etichette | Chiuso: "Gran Premi", "GP al via", "Piazz. a podio" e nota sulla media griglia |
| 8. Scelte nell'URL | Chiuso. Il link apre la stessa schermata in un contesto nuovo; la ricarica conserva le scelte; valori inesistenti ripiegano sui predefiniti senza errori |

Residui minori: `#driver-comparison?...&a=830&b=830` accetta lo stesso pilota sui due lati; lo stato dell'interruttore della scala non è nell'URL; a Monaco Verstappen–Pérez l'interruttore non produce alcun effetto visibile (nessun giro fuori scala) e nulla lo dice. Console: nessun errore né avviso in tutto il giro.

Screenshot di questa verifica, fuori dal repository: `/private/tmp/claude-501/-Users-lucamonaco-Developer-f1-data-platform/6be1e166-f170-4e24-a62c-841413ca8303/scratchpad/finale/shots/`.

## 8. Che cosa resta debole (visto da un valutatore tecnico)

- **Nessuna integrazione continua.** La verifica gira solo in locale, richiede Java 21 e Docker sull'host, ed è instabile.
- **La validazione non scarta nulla sui dati reali**: 0 scarti sul campione e sul dataset completo. Il report degli scarti è dimostrato solo da dati sintetici nei test.
- **Caricamento solo additivo**: le righe sparite dall'input restano nel database (dichiarato). Nessun caricamento incrementale, nessuna pianificazione, nessun controllo di qualità sui dati oltre alla validazione per riga.
- **Stint senza mescole**: è un tratto tra due soste, con `compound` sempre nullo (dichiarato ovunque).
- **Una statistica comparativa nel browser** (distacco), contro la regola del brief; eccezione dichiarata.
- **Codice che disegna senza test unitari**; test di accettazione deboli nei punti indicati in tabella.
- **Storia git a blocchi**: 11 commit, uno solo per le tappe 5, 6 e 8; 7 commit non ancora inviati al remoto.
- **Software senza licenza e termini di Ergast non chiariti**: accettabile finché il repository è privato.
- **Screenshot solo a 1 440 px**; Team comparison non è tra quelli prodotti.
