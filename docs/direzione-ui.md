# Direzione UI

Come si presenta la dashboard di F1 Data Platform e perché. Chi modifica `frontend/` parte da qui: le regole di questa pagina valgono per ogni vista e per ogni grafico.

## Principi

- **Prodotto dati, non sito di tifosi.** Sfondo chiaro, tabelle dense, grafici leggibili. Nessun elemento decorativo: ogni cosa sullo schermo è un dato, un'etichetta o un controllo.
- **Solo testo per piloti e scuderie.** Nomi e sigle come compaiono nella fonte. Nessun logo, fotografia, bandiera, carattere o colore ufficiale di Formula 1, FIA, scuderie o sponsor. I colori delle serie non rimandano alle livree: sono assegnati per ordine di selezione.
- **Il colore non porta mai l'informazione da solo.** Ogni serie di un grafico ha colore, tratteggio e marcatore propri, più un'etichetta o una legenda con il nome.
- **Lo stato dei dati è sempre dichiarato.** Caricamento, lista vuota, dato assente nella fonte ed errore dell'API hanno ciascuno un messaggio esplicito; un grafico non resta mai vuoto senza spiegazione.
- **Funziona senza rete esterna.** Caratteri e libreria dei grafici sono serviti dalla dashboard stessa: nessuna CDN.

## Palette

Tema chiaro unico. I neutri sono la scala *slate* di Tailwind; i rapporti di contrasto sono calcolati secondo WCAG 2.1 rispetto al bianco.

| Ruolo | Colore | Contrasto sul bianco |
|---|---|---|
| Sfondo della pagina | `#f8fafc` | — |
| Superfici (schede, tabelle, grafici) | `#ffffff` | — |
| Bordi e griglie | `#e2e8f0` | — |
| Testo principale | `#0f172a` | 17,8 : 1 |
| Testo secondario, assi dei grafici | `#475569` | 7,6 : 1 |
| Accento (collegamenti, fuoco, elemento attivo) | `#0369a1` | 5,9 : 1 |
| Errore | `#b91c1c` su `#fef2f2` | 6,5 : 1 |
| Serie di contesto nei grafici (piloti non selezionati) | `#94a3b8` | linee sottili, sempre con etichetta |

Il testo rispetta almeno il livello AA (4,5 : 1); linee e marcatori dei grafici almeno 3 : 1.

### Scala categorica delle serie

Sei posizioni, assegnate nell'ordine in cui i piloti vengono selezionati. I colori derivano dalle palette di Okabe-Ito e di Paul Tol, pensate per restare distinguibili con le forme più comuni di daltonismo, scuriti dove serviva per arrivare a 3 : 1 sul bianco. Ogni posizione ha anche un tratteggio e un marcatore, così la serie si riconosce in scala di grigi.

| # | Colore | Nome | Tratteggio | Marcatore |
|---|---|---|---|---|
| 1 | `#0072b2` | blu | continuo | cerchio |
| 2 | `#d55e00` | vermiglio | tratti lunghi | quadrato |
| 3 | `#007a5e` | verde | punti | triangolo |
| 4 | `#aa4499` | porpora | tratto-punto | rombo |
| 5 | `#8a6d00` | ocra | tratti corti | croce |
| 6 | `#333333` | antracite | tratto lungo-corto | stella |

- Il limite è di **sei serie colorate per grafico**: oltre, i colori non sarebbero più distinguibili. Gli altri piloti restano visibili come linee grigie di contesto con la sigla a fine linea (grafico delle posizioni).
- Nei confronti a due, **A** usa la posizione 1 (blu, tinta piena) e **B** la posizione 2 (vermiglio, a righe diagonali); i valori numerici sono sempre scritti accanto alle barre.
- La definizione vive in `frontend/src/js/palette.js`; un test del componente verifica il contrasto minimo di ogni colore.

## Tipografia

- **Inter** (variabile, licenza SIL Open Font 1.1), inclusa nella build dal pacchetto `@fontsource-variable/inter` e servita in locale da `fonts/`; ripiego sui caratteri di sistema (`system-ui`, `sans-serif`). Nessun carattere ufficiale o che imiti quelli del campionato.
- Un solo carattere per interfaccia e grafici (i grafici ereditano quello della pagina).
- **Cifre tabellari** (`font-variant-numeric: tabular-nums`) in tabelle, statistiche e assi: le colonne di numeri restano allineate.
- Scala: titolo di vista 24 px semibold; titolo di sezione 16 px semibold; testo e tabelle 14 px; etichette dei filtri, note e assi 12 px. Intestazioni di tabella in maiuscoletto 11–12 px, colore secondario.
- Formati: tempi sul giro `m:ss.mmm` e distacchi `+s.mmm` con il punto, come nei cronologici; medie e punti con la virgola decimale italiana; date brevi (`5 mar 2023`).
- Lingua: interfaccia in italiano; i nomi delle cinque viste restano in inglese come nel brief; i dati (nomi dei Gran Premi, stato di arrivo) restano come nella fonte.

## Libreria dei grafici

**Observable Plot 0.6** (licenza ISC), con D3 7 da cui dipende.

- Perché: produce **SVG**, quindi testo vero (assi, etichette, suggerimenti) nitido negli screenshot e a ogni ingrandimento; la grammatica a "marchi" copre con lo stesso codice linee, punti, barre orizzontali per gli stint e fasce di sfondo; tratteggi e simboli per serie sono opzioni native, il che rende semplice non affidarsi al solo colore.
- Come è inclusa: i file `plot.umd.min.js` e `d3.min.js` vengono copiati da `node_modules` in `dist/vendor/` da `npm run build` (con le rispettive licenze) e caricati dalla pagina come script locali. Nessun bundler, nessuna CDN.
- Le barre dei confronti a due (quote tra A e B) sono HTML e CSS, non SVG: sono poche barre con i valori scritti, e così restano testo selezionabile.
- Il codice che prepara i dati dei grafici (`trasformazioni.js`) non dipende dalla libreria ed è coperto dai test del componente; `grafici.js` si limita a disegnare.

### Regole per i grafici

- Ogni grafico ha un titolo, una frase che dice come leggerlo e gli assi con etichetta e unità.
- **Tempi sul giro.** L'asse verticale è limitato al passo di gara: i giri molto più lenti (primo giro, giri di sosta, neutralizzazioni) non vengono nascosti, ma segnati con un triangolo sul bordo superiore, nella riga del pilota, e contati nella nota sotto il grafico. La soglia è il terzo quartile più tre volte lo scarto interquartile dei tempi mostrati. Un interruttore "Scala completa" li riporta tutti in scala. Le fasce grigie indicano i giri lenti per tutto il gruppo: sono ricavate dai tempi, perché la fonte non registra safety car o bandiere.
- **Posizioni.** Prima posizione in alto; il giro 0 è la griglia di partenza. Tutti i piloti sono disegnati: i selezionati con il proprio stile, gli altri in grigio. La sigla è scritta alla fine di ogni linea.
- **Stint e pit stop.** Una riga per pilota in ordine d'arrivo, segmenti numerati alternati in due grigi, una tacca scura per ogni sosta. Nessun colore di mescola: una nota fissa ricorda che la fonte non contiene le mescole e che gli stint sono ricavati dalle soste. Se la gara non ha soste registrate compare un messaggio, non un grafico vuoto.
- **Confronto tra due piloti in gara.** Tempi sul giro dei due e distacco in pista giro per giro (differenza dei tempi cumulati), con la linea dello zero in evidenza.
- I suggerimenti al passaggio del puntatore aggiungono il dettaglio (giro, tempo, posizione, sosta); nulla di essenziale sta solo lì.
- Ogni grafico dichiara nell'attributo `data-punti` quanti punti ha disegnato: serve ai test end-to-end.

## Layout

- **Struttura fissa**: intestazione con il nome del progetto e la navigazione tra le cinque viste; area della vista; footer con attribuzione della fonte e disclaimer di non affiliazione. Larghezza massima del contenuto 1280 px, centrato.
- **Ogni vista** segue lo stesso ordine: titolo e descrizione di una riga; barra dei filtri; contenuto in schede bianche con bordo sottile (raggio 8 px, nessuna ombra marcata).
- **Filtri**: elementi `<select>` nativi con etichetta visibile, nella barra subito sotto il titolo; un filtro che riguarda una sola sezione sta nell'intestazione di quella sezione. Stagione, gara, piloti e scuderie scelti si conservano passando da una vista all'altra. Quando cambia la stagione, i filtri che ne dipendono si svuotano e si ricaricano.
- **Griglia**: spaziatura a multipli di 4 px; dodici colonne da 1024 px in su, una colonna sotto.

| Vista | Disposizione (schermo largo) |
|---|---|
| Season overview | riga di indicatori; calendario con vincitori (7/12) accanto alla classifica piloti (5/12); classifica costruttori a tutta larghezza |
| Race explorer | elenco delle gare della stagione (4/12) accanto a scheda della gara e risultati della sessione scelta (8/12) |
| Driver comparison | due schede affiancate (A e B); barre di confronto; confronto in una gara con tempi sul giro e distacco |
| Team comparison | due schede affiancate (A e B) con statistiche e piloti; barre di confronto |
| Race analysis | scelta dei piloti; tempi sul giro; posizioni; stint e pit stop, uno sotto l'altro a tutta larghezza |

- **Schermi stretti** (da 360 px): la navigazione va a capo, le schede si impilano, le tabelle larghe scorrono in orizzontale dentro la propria scheda, i grafici si ridisegnano alla larghezza disponibile.
- **Accessibilità**: navigazione e filtri usabili da tastiera con fuoco visibile; `aria-current` sulla vista attiva; l'errore dell'API è un `role="alert"`; le tabelle hanno intestazioni di colonna vere; ogni grafico ha un'etichetta testuale che ne riassume il contenuto.

## Stati e messaggi

| Situazione | Che cosa si vede |
|---|---|
| Dati in arrivo | "Caricamento…" nella sezione interessata; i filtri dipendenti sono disattivati |
| Nessun dato per la scelta fatta | una frase che dice che cosa manca (es. "Nessun dato di qualifica per questa gara") |
| Dato assente nella fonte | nota fissa (mescole) o messaggio dedicato (stint e pit stop non disponibili) |
| L'API non risponde o risponde con un errore | riquadro rosso in cima alla vista con il messaggio e il pulsante "Riprova"; il resto della pagina resta al suo posto |

I messaggi che arrivano dall'API sono inseriti solo come testo, mai come HTML.

## Fuori dal perimetro

- Tema scuro.
- Grafici dell'andamento dei punti gara per gara: richiedono un dato che l'API oggi non espone.
