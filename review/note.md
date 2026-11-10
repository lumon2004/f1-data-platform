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
