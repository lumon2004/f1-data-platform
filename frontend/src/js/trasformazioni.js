// Dai dati dell'API alle strutture disegnate dai grafici. Funzioni pure: nessun DOM e nessuna dipendenza
// dalla libreria dei grafici.
//
// Classifiche, punti, medie e conteggi arrivano già calcolati dall'API e qui non si toccano.
// Questo file però non si limita a riordinare: contiene tre calcoli fatti nel browser, sui giri già scaricati.
//   - sogliaFuoriScala: quartili dei tempi mostrati, per decidere dove tagliare l'asse (presentazione);
//   - giriLenti: mediana dei tempi di tutti i piloti giro per giro, per le fasce grigie (stima di presentazione,
//     dichiarata come tale a schermo);
//   - distaccoCumulato: differenza dei tempi cumulati di due piloti. È una statistica comparativa vera e propria:
//     sta qui perché l'API non la espone (eccezione motivata in docs/decisioni.md).

import { sigla } from './format.js';

const numero = (v) => typeof v === 'number' && Number.isFinite(v);

/** Quantile con interpolazione lineare su un array già ordinato in modo crescente. */
export function quantile(ordinati, q) {
  if (!ordinati.length) return null;
  const pos = (ordinati.length - 1) * q;
  const base = Math.floor(pos);
  const resto = pos - base;
  const successivo = ordinati[Math.min(base + 1, ordinati.length - 1)];
  return ordinati[base] + (successivo - ordinati[base]) * resto;
}

export function mediana(valori) {
  return quantile([...valori].sort((a, b) => a - b), 0.5);
}

/**
 * Soglia oltre la quale un tempo sul giro è "fuori scala" rispetto al passo di gara:
 * terzo quartile più tre volte lo scarto interquartile (con un margine minimo del 2%).
 * Restituisce null se i tempi sono troppo pochi per stimarla.
 */
export function sogliaFuoriScala(tempiMs) {
  const ordinati = tempiMs.filter(numero).sort((a, b) => a - b);
  if (ordinati.length < 8) return null;
  const q1 = quantile(ordinati, 0.25);
  const q3 = quantile(ordinati, 0.75);
  return Math.max(q3 + 3 * (q3 - q1), q3 * 1.02);
}

/** Sigle uniche per una lista di piloti: in caso di omonimia si aggiunge l'id. */
export function sigleUniche(piloti) {
  const conteggio = new Map();
  for (const p of piloti) conteggio.set(sigla(p), (conteggio.get(sigla(p)) ?? 0) + 1);
  return new Map(piloti.map((p) => [p.id, conteggio.get(sigla(p)) > 1 ? `${sigla(p)} ${p.id}` : sigla(p)]));
}

/** Piloti mostrati all'apertura: i primi `quanti` dell'ordine d'arrivo che hanno giri cronometrati. */
export function selezionePredefinita(pilotiGiri, quanti = 3) {
  return pilotiGiri.filter((p) => p.laps.length > 0).slice(0, quanti).map((p) => p.driver.id);
}

/** Aggiunge o toglie un pilota dalla selezione, senza superare `massimo`. Restituisce una nuova lista. */
export function alternaSelezione(selezione, id, massimo) {
  if (selezione.includes(id)) return selezione.filter((x) => x !== id);
  if (selezione.length >= massimo) return selezione;
  return [...selezione, id];
}

/** Ultimo giro cronometrato tra tutti i piloti. */
export function giroMassimo(pilotiGiri) {
  let max = 0;
  for (const p of pilotiGiri) for (const g of p.laps) if (g.lap > max) max = g.lap;
  return max;
}

/**
 * Giri lenti per tutto il gruppo (dal secondo in poi): quelli in cui la mediana dei tempi di tutti i
 * piloti supera di `fattore` il passo tipico della gara. La fonte non registra safety car né bandiere:
 * è una stima ricavata dai tempi, da presentare come tale. Restituisce intervalli `{ da, a }`.
 */
export function giriLenti(pilotiGiri, { fattore = 1.15, minimoPiloti = 3 } = {}) {
  const perGiro = new Map();
  for (const p of pilotiGiri) {
    for (const g of p.laps) {
      if (g.lap < 2 || !numero(g.timeMs)) continue;
      if (!perGiro.has(g.lap)) perGiro.set(g.lap, []);
      perGiro.get(g.lap).push(g.timeMs);
    }
  }
  const mediane = [...perGiro.entries()]
    .filter(([, tempi]) => tempi.length >= minimoPiloti)
    .map(([giro, tempi]) => ({ giro, valore: mediana(tempi) }))
    .sort((a, b) => a.giro - b.giro);
  if (mediane.length < 5) return [];
  const riferimento = mediana(mediane.map((m) => m.valore));
  const intervalli = [];
  for (const m of mediane) {
    if (m.valore <= riferimento * fattore) continue;
    const ultimo = intervalli.at(-1);
    if (ultimo && ultimo.a === m.giro - 1) ultimo.a = m.giro;
    else intervalli.push({ da: m.giro, a: m.giro });
  }
  return intervalli;
}

/**
 * Serie dei tempi sul giro per i piloti selezionati.
 * I giri oltre la soglia non vengono scartati: restano nella serie con `fuoriScala: true`
 * (il grafico li segna sul bordo); con `scalaCompleta` nessun giro è fuori scala.
 * `soste` (pit stop della gara) serve solo ad annotare i giri di ingresso e di uscita dai box.
 */
export function serieTempi(pilotiGiri, { selezionati, scalaCompleta = false, soste = [] }) {
  const giriSosta = new Map(); // id pilota -> Map(giro -> 'ingresso' | 'uscita')
  for (const s of soste) {
    const id = s.driver?.id;
    if (!giriSosta.has(id)) giriSosta.set(id, new Map());
    giriSosta.get(id).set(s.lap, 'ingresso');
    if (!giriSosta.get(id).has(s.lap + 1)) giriSosta.get(id).set(s.lap + 1, 'uscita');
  }
  const scelti = selezionati
    .map((id) => pilotiGiri.find((p) => p.driver.id === id))
    .filter(Boolean);
  const tutti = scelti.flatMap((p) => p.laps.map((g) => g.timeMs)).filter(numero);
  const soglia = scalaCompleta ? null : sogliaFuoriScala(tutti);

  let fuoriScala = 0;
  let minimo = Infinity;
  let massimo = -Infinity;
  const serie = scelti.map((p, indice) => {
    const punti = p.laps
      .filter((g) => numero(g.timeMs))
      .map((g) => {
        const fuori = soglia !== null && g.timeMs > soglia;
        if (fuori) fuoriScala += 1;
        else {
          if (g.timeMs < minimo) minimo = g.timeMs;
          if (g.timeMs > massimo) massimo = g.timeMs;
        }
        return {
          giro: g.lap,
          ms: g.timeMs,
          posizione: g.position ?? null,
          fuoriScala: fuori,
          sosta: giriSosta.get(p.driver.id)?.get(g.lap) ?? null,
        };
      });
    return { id: p.driver.id, sigla: sigla(p.driver), nome: p.driver.name, scuderia: p.team?.name ?? '', indice, punti };
  });
  const puntiDisegnati = serie.reduce((n, s) => n + s.punti.length, 0);
  return {
    serie,
    soglia,
    minimo: Number.isFinite(minimo) ? minimo : null,
    massimo: Number.isFinite(massimo) ? massimo : null,
    fuoriScala,
    puntiDisegnati,
    giroMassimo: serie.reduce((m, s) => Math.max(m, s.punti.at(-1)?.giro ?? 0), 0),
  };
}

/**
 * Serie delle posizioni giro per giro di tutti i piloti. Il giro 0 è la casella di partenza
 * (dai risultati), quando è nota: chi parte dalla pit lane comincia dal primo giro.
 */
export function seriePosizioni(pilotiGiri, risultati = []) {
  const griglia = new Map(risultati.map((r) => [r.driver.id, r.grid]));
  // Non classificato = position null nei risultati; senza risultati si assume classificato.
  const nonClassificati = new Set(risultati.filter((r) => r.position === null).map((r) => r.driver.id));
  let punti = 0;
  let posizioneMassima = 0;
  let ultimoGiro = 0;
  const serie = pilotiGiri.map((p) => {
    const lista = [];
    const partenza = griglia.get(p.driver.id);
    if (numero(partenza) && partenza > 0 && p.laps.length > 0) lista.push({ giro: 0, posizione: partenza });
    for (const g of p.laps) if (numero(g.position)) lista.push({ giro: g.lap, posizione: g.position });
    for (const x of lista) {
      if (x.posizione > posizioneMassima) posizioneMassima = x.posizione;
      if (x.giro > ultimoGiro) ultimoGiro = x.giro;
    }
    punti += lista.length;
    return {
      id: p.driver.id,
      sigla: sigla(p.driver),
      nome: p.driver.name,
      scuderia: p.team?.name ?? '',
      classificato: !nonClassificati.has(p.driver.id),
      punti: lista,
    };
  }).filter((s) => s.punti.length > 0);
  return { serie, puntiDisegnati: punti, posizioneMassima, giroMassimo: ultimoGiro };
}

/**
 * Distacco sul tempo di gara tra due piloti, a parità di giri completati: alla fine di ogni giro, differenza
 * dei tempi cumulati dal via (B − A), quindi positiva quando A è davanti. Finché i due sono nello stesso giro
 * coincide con il distacco in pista.
 *
 * La serie si ferma:
 *   - al primo giro che manca a uno dei due (ritiro, o un buco nei dati: oltre, i cumulati non sono confrontabili);
 *   - quando uno dei due viene doppiato, cioè quando chi è davanti completa il giro g prima che l'altro abbia
 *     completato il giro g − 1. Da lì la differenza a parità di giri non descrive più la distanza in pista.
 *     In quel caso `doppiaggio` vale `{ giro: g, doppiato: 'a' | 'b' }` e l'ultimo punto è quello del giro g − 1.
 */
export function distaccoCumulato(giriA, giriB) {
  const perGiro = (giri) => new Map(giri.filter((g) => numero(g.timeMs)).map((g) => [g.lap, g.timeMs]));
  const a = perGiro(giriA);
  const b = perGiro(giriB);
  const punti = [];
  let doppiaggio = null;
  let cumA = 0;
  let cumB = 0;
  for (let giro = 1; a.has(giro) && b.has(giro); giro += 1) {
    const precedenteA = cumA;
    const precedenteB = cumB;
    cumA += a.get(giro);
    cumB += b.get(giro);
    if (giro > 1 && cumA < precedenteB) doppiaggio = { giro, doppiato: 'b' };
    else if (giro > 1 && cumB < precedenteA) doppiaggio = { giro, doppiato: 'a' };
    if (doppiaggio) break;
    punti.push({ giro, ms: cumB - cumA });
  }
  return { punti, doppiaggio };
}

/**
 * Il numero di uno stint si scrive dentro il segmento solo se ci sta: servono almeno `minimoPx` pixel.
 * `pxPerGiro` è la larghezza di un giro nel grafico disegnato.
 */
export function numeroStintVisibile(giri, pxPerGiro, minimoPx = 9) {
  return numero(giri) && numero(pxPerGiro) && giri * pxPerGiro >= minimoPx;
}

/**
 * Stint e soste pronti per il grafico a barre orizzontali: una riga per pilota, nell'ordine dell'API
 * (ordine d'arrivo). Un giro L occupa l'intervallo (L−1, L], quindi uno stint va da `startLap − 1` a `endLap`.
 * Ogni stint porta con sé le soste che lo chiudono, per il suggerimento.
 */
export function stintPerGrafico(stints, soste = []) {
  const piloti = [];
  const visti = new Set();
  for (const x of [...stints, ...soste]) {
    if (x.driver && !visti.has(x.driver.id)) {
      visti.add(x.driver.id);
      piloti.push(x.driver);
    }
  }
  const sigle = sigleUniche(piloti);
  const sostePerPilota = new Map();
  for (const s of soste) {
    if (!sostePerPilota.has(s.driver.id)) sostePerPilota.set(s.driver.id, []);
    sostePerPilota.get(s.driver.id).push(s);
  }
  const segmenti = stints.map((s) => ({
    riga: sigle.get(s.driver.id),
    nome: s.driver.name,
    stint: s.stint,
    da: s.startLap - 1,
    a: s.endLap,
    primoGiro: s.startLap,
    ultimoGiro: s.endLap,
    giri: s.laps,
    soste: (sostePerPilota.get(s.driver.id) ?? []).filter((p) => p.lap === s.endLap),
  }));
  const tacche = soste.map((s) => ({
    riga: sigle.get(s.driver.id),
    nome: s.driver.name,
    giro: s.lap,
    sosta: s.stop,
    durataMs: s.durationMs ?? null,
  }));
  return {
    righe: piloti.map((p) => sigle.get(p.id)),
    segmenti,
    tacche,
    giroMassimo: Math.max(0, ...segmenti.map((s) => s.a), ...tacche.map((t) => t.giro)),
  };
}

/**
 * Righe del confronto a due: per ogni metrica i due valori e la quota di ciascuno sul totale (in %),
 * usata solo per la larghezza delle barre. Quote null quando il totale è zero o un valore manca.
 */
export function confronto(a, b, metriche) {
  return metriche.map(({ chiave, etichetta, valore }) => {
    const va = valore ? valore(a) : a?.[chiave];
    const vb = valore ? valore(b) : b?.[chiave];
    const validi = numero(va) && numero(vb) && va >= 0 && vb >= 0 && va + vb > 0;
    const quotaA = validi ? (va / (va + vb)) * 100 : null;
    return {
      chiave,
      etichetta,
      a: numero(va) ? va : null,
      b: numero(vb) ? vb : null,
      quotaA,
      quotaB: validi ? 100 - quotaA : null,
    };
  });
}
