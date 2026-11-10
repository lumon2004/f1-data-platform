# Fonte dati, licenza e attribuzione

Da dove vengono i dati di F1 Data Platform, con quale licenza sono pubblicati, che cosa il repository ridistribuisce e come va citata la fonte.

Verifiche eseguite il **2026-11-10**. Se il dataset o la sua pagina Kaggle cambiano, questo documento va riverificato.

## Fonte e autore

| | |
|---|---|
| Dataset | *Formula 1 World Championship (1950 - 2024)*, sottotitolo "F1 race data from 1950 to 2024" |
| Pubblicato su | Kaggle: <https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020> |
| Autore e proprietario | Rohan Rao (utente Kaggle "Vopani") |
| Ultimo aggiornamento indicato da Kaggle | 2025-01-29 |
| Origine dichiarata | "The data is compiled from http://ergast.com/mrd/" (Ergast Developer API) |

L'indirizzo della pagina riporta "1950-2020" e il titolo "1950 - 2024": è la stessa pagina, non due dataset diversi.

## Licenza

Licenza dichiarata su Kaggle: **CC0: Public Domain**.

Come è stata verificata: lettura del campo licenza nei metadati del dataset, restituiti dall'API pubblica di Kaggle, il 2026-11-10.

Questa è la licenza che l'autore del dataset dichiara su Kaggle. Non dice nulla sui termini della fonte da cui i dati sono stati compilati: vedi la sezione seguente.

## Catena di provenienza

1. **Ergast Developer API** (<http://ergast.com/mrd/>). Servizio sperimentale che forniva dati storici del motorsport "for non-commercial purposes". È stato dismesso a fine 2024.
2. **Dataset Kaggle** di Rohan Rao. Compila i dati di Ergast in 14 file CSV e li pubblica con licenza CC0.
3. **Questo progetto**. Scarica il dataset da Kaggle, lo trasforma e lo carica in PostgreSQL. Il modello relazionale e le trasformazioni sono descritti in [`modello-dati.md`](modello-dati.md).

### Punto aperto: i termini originali di Ergast

- Ergast destinava i propri dati a usi non commerciali.
- La pagina dei termini (`ergast.com/mrd/terms/`) oggi risponde 404: **il testo esatto dei termini non è stato riletto**.
- Le due informazioni su Ergast (uso non commerciale, dismissione a fine 2024) vengono da fonti indirette: la documentazione di FastF1 (<https://docs.fastf1.dev/ergast.html>) e il progetto Jolpica-F1, successore compatibile di Ergast.
- Non è stato verificato come la licenza CC0 dichiarata su Kaggle si concili con i termini della fonte originale.

Conseguenza pratica:

- F1 Data Platform è una vetrina tecnica **non commerciale**, e i dati sono usati in questo ambito.
- **Prima di un eventuale uso commerciale** (del progetto o dei dati che contiene) la questione va rivalutata. Questo documento non è una valutazione legale e non la sostituisce.

## Che cosa è nel repository e che cosa no

| | Dove | In git |
|---|---|---|
| Estratto delle stagioni 2022–2024 (dataset di esempio) | `data-pipeline/sample/` | sì |
| Dataset completo (CSV scaricati da Kaggle) | `data-pipeline/raw/` | no |
| File intermedi prodotti dalla pipeline | `data-pipeline/processed/` | no |

- Il campione contiene **11 dei 14 CSV** del dataset, quelli che la pipeline carica; sono esclusi `driver_standings`, `constructor_standings` e `constructor_results`. La stagione 2024 è completa nei dati: 24 gare.
- Il dataset completo si scarica con `f1-pipeline download --output data-pipeline/raw`. Il token Kaggle si legge dalle variabili d'ambiente (i nomi sono in `.env.example`); non è mai scritto nel codice né nel repository.
- Il repository ridistribuisce **solo il campione**, e il repository è privato.
- Il software è proprietario, senza licenza. **La nota di copyright del progetto riguarda il codice, non i dati.**

## Testo di attribuzione

Da riusare senza modificarne il contenuto. Nomi da non omettere: Kaggle, Rohan Rao, Ergast.

**README**, sezione "Data Source & Acknowledgements":

```markdown
I dati provengono dal dataset [Formula 1 World Championship (1950 - 2024)](https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020)
di Rohan Rao, pubblicato su Kaggle con licenza CC0: Public Domain e compilato a partire dalla
[Ergast Developer API](http://ergast.com/mrd/). Grazie a entrambi per aver reso disponibili questi dati.
Dettagli su licenza e provenienza: [docs/fonte-dati.md](docs/fonte-dati.md).

F1 Data Platform è un progetto non ufficiale, non affiliato a Formula 1, FIA o scuderie.
I nomi di scuderie e piloti compaiono solo come dati testuali; il progetto non usa loghi né fotografie ufficiali.
```

**Footer della dashboard**:

```text
Dati: dataset Kaggle "Formula 1 World Championship (1950 - 2024)" di Rohan Rao, compilato dalla Ergast Developer API.
Progetto non ufficiale, non affiliato a Formula 1, FIA o scuderie.
```

Nel footer il nome del dataset rimanda alla pagina Kaggle.

## Marchi e non affiliazione

- Progetto non ufficiale, non affiliato a Formula 1, FIA o scuderie.
- Nessun logo ufficiale (Formula 1, FIA, scuderie, sponsor) e nessuna fotografia ufficiale.
- I nomi di scuderie e piloti compaiono solo come dati testuali, così come sono nella fonte.

## Contenuto del dataset e limiti noti

Il dataset contiene 14 CSV.

| Uso nel progetto | File |
|---|---|
| Caricati (11) | `circuits`, `constructors`, `drivers`, `lap_times`, `pit_stops`, `qualifying`, `races`, `results`, `seasons`, `sprint_results`, `status` |
| Non caricati (3) | `constructor_results`, `constructor_standings`, `driver_standings`: si ricavano dai risultati |

Limiti:

- **Niente mescole né stint.** Gli stint della dashboard sono ricavati dai pit stop, senza mescola (regola in [`modello-dati.md`](modello-dati.md#stint-e-mescole)).
- **Dati fino alla stagione 2024.** Ergast è dismesso e l'ultimo aggiornamento del dataset è del 2025-01-29: le stagioni successive non ci sono.
- **Copertura non uniforme nel tempo.** Alcuni dati esistono solo per le stagioni più recenti; il dettaglio è in [`modello-dati.md`](modello-dati.md).
- I dati sono caricati così come pubblicati, salvo le conversioni documentate nel modello dati. Il progetto non ne verifica l'esattezza rispetto ai risultati ufficiali.
