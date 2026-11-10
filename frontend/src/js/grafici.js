// Disegno dei grafici con Observable Plot (caricato dalla pagina come script locale: globalThis.Plot).
// I dati arrivano già pronti da trasformazioni.js; qui si decide solo come disegnarli.
// Regole di stile in docs/direzione-ui.md.

import { el, svg } from './dom.js';
import * as formato from './format.js';
import { CONTESTO, stileSerie } from './palette.js';

const GRIGLIA = '#e2e8f0';
const TESTO = '#0f172a';
const FASCIA = '#e2e8f0';
const STILE = { fontFamily: 'inherit', fontSize: '12px', overflow: 'visible', background: 'transparent' };

const osservatori = new WeakMap();

/**
 * Disegna un grafico in `contenitore` e lo ridisegna quando cambia la larghezza disponibile.
 * `disegna(larghezza)` restituisce `{ nodo, punti }`; `punti` finisce nell'attributo data-punti.
 */
export function montaGrafico(contenitore, disegna) {
  smontaGrafico(contenitore);
  let larghezza = 0;
  let richiesta = 0;
  const ridisegna = () => {
    const disponibile = Math.floor(contenitore.clientWidth);
    if (disponibile <= 0 || disponibile === larghezza) return;
    larghezza = disponibile;
    if (!globalThis.Plot) {
      contenitore.replaceChildren(el('p', { class: 'messaggio' }, 'La libreria dei grafici non è stata caricata.'));
      contenitore.removeAttribute('data-punti');
      return;
    }
    const { nodo, punti } = disegna(larghezza);
    contenitore.replaceChildren(nodo);
    contenitore.setAttribute('data-punti', String(punti));
  };
  ridisegna();
  if (typeof ResizeObserver === 'function') {
    const osservatore = new ResizeObserver(() => {
      cancelAnimationFrame(richiesta);
      richiesta = requestAnimationFrame(ridisegna);
    });
    osservatore.observe(contenitore);
    osservatori.set(contenitore, () => {
      osservatore.disconnect();
      cancelAnimationFrame(richiesta);
    });
  }
}

/** Toglie il grafico e mostra al suo posto un messaggio (caricamento, nessun dato). */
export function smontaGrafico(contenitore, messaggio) {
  osservatori.get(contenitore)?.();
  osservatori.delete(contenitore);
  contenitore.removeAttribute('data-punti');
  if (messaggio !== undefined) contenitore.replaceChildren(el('p', { class: 'messaggio' }, messaggio));
}

const tickInteri = (v) => (Number.isInteger(v) ? String(v) : '');

function etichettaGiro(giro) {
  return giro === 0 ? 'Griglia di partenza' : `Giro ${giro}`;
}

/**
 * Tempi sul giro. `dati` viene da serieTempi(); `fasce` da giriLenti().
 * I giri fuori scala sono triangoli sopra il riquadro, una riga per pilota.
 */
export function disegnaTempi(dati, { larghezza, fasce = [], altezza = 380 }) {
  const Plot = globalThis.Plot;
  const n = dati.serie.length;
  // Sopra il riquadro: una riga di triangoli per pilota, più lo spazio per l'etichetta dell'asse.
  const spazioFuoriScala = dati.fuoriScala > 0 ? n * 10 + 16 : 0;
  const minimo = (dati.minimo ?? 0) / 1000;
  const massimo = (dati.massimo ?? 1) / 1000;
  const margine = Math.max((massimo - minimo) * 0.05, 0.25);
  const dominioY = [minimo - margine, massimo + margine];
  const ultimoGiro = Math.max(dati.giroMassimo, 2);

  const marchi = [];
  if (fasce.length) {
    marchi.push(
      Plot.rect(fasce, {
        x1: (d) => Math.max(d.da - 0.5, 0.5),
        x2: (d) => Math.min(d.a + 0.5, ultimoGiro + 0.5),
        fill: FASCIA,
        fillOpacity: 0.75,
      }),
    );
  }
  marchi.push(Plot.frame({ stroke: GRIGLIA }));
  const suggerimenti = [];
  for (const s of dati.serie) {
    const stile = stileSerie(s.indice);
    const punti = s.punti.map((p) => ({ ...p, serie: s, y: p.fuoriScala ? NaN : p.ms / 1000 }));
    const inScala = punti.filter((p) => !p.fuoriScala);
    const fuori = punti.filter((p) => p.fuoriScala);
    marchi.push(
      Plot.line(punti, {
        x: 'giro',
        y: 'y',
        stroke: stile.colore,
        strokeWidth: 1.75,
        strokeDasharray: stile.tratteggio ?? undefined,
      }),
      Plot.dot(inScala, { x: 'giro', y: 'y', fill: stile.colore, symbol: stile.simbolo, r: 2.5 }),
    );
    if (fuori.length) {
      marchi.push(
        Plot.dot(fuori, {
          x: 'giro',
          frameAnchor: 'top',
          dy: -(7 + (n - 1 - s.indice) * 10),
          fill: stile.colore,
          symbol: 'triangle',
          r: 3.5,
        }),
      );
    }
    for (const p of punti) suggerimenti.push({ ...p, yTip: p.fuoriScala ? dominioY[1] : p.y });
  }
  marchi.push(
    Plot.tip(
      suggerimenti,
      Plot.pointer({
        x: 'giro',
        y: 'yTip',
        title: (d) =>
          [
            `${d.serie.sigla} · ${d.serie.nome}`,
            `Giro ${d.giro}: ${formato.tempo(d.ms)}${d.fuoriScala ? ' (fuori scala)' : ''}`,
            d.posizione ? `Posizione: ${d.posizione}º` : null,
            d.sosta === 'ingresso' ? 'Giro di ingresso ai box' : d.sosta === 'uscita' ? 'Giro di uscita dai box' : null,
          ]
            .filter(Boolean)
            .join('\n'),
      }),
    ),
  );

  const nodo = Plot.plot({
    width: larghezza,
    height: altezza + spazioFuoriScala,
    marginTop: 14 + spazioFuoriScala,
    marginLeft: 58,
    marginRight: 16,
    marginBottom: 40,
    style: STILE,
    x: {
      label: 'Giro',
      domain: [0.5, ultimoGiro + 0.5],
      ticks: Math.min(ultimoGiro, larghezza < 520 ? 6 : 14),
      tickFormat: tickInteri,
    },
    y: { label: 'Tempo sul giro (min:s)', domain: dominioY, tickFormat: formato.tempoAsse, grid: true, ticks: 7 },
    marks: marchi,
  });
  nodo.setAttribute('role', 'img');
  nodo.setAttribute(
    'aria-label',
    `Tempi sul giro di ${dati.serie.map((s) => s.nome).join(', ')}: ${dati.puntiDisegnati} giri disegnati.`,
  );
  return { nodo, punti: dati.puntiDisegnati };
}

/**
 * Posizioni giro per giro. `dati` viene da seriePosizioni(); `selezionati` è la lista ordinata degli id
 * dei piloti in evidenza (gli altri sono linee grigie di contesto, comunque etichettate).
 */
export function disegnaPosizioni(dati, selezionati, { larghezza }) {
  const Plot = globalThis.Plot;
  const massima = Math.max(dati.posizioneMassima, 2);
  const altezza = Math.max(280, massima * 20 + 84);
  const indice = new Map(selezionati.map((id, i) => [id, i]));
  const contesto = dati.serie.filter((s) => !indice.has(s.id));
  const evidenza = dati.serie.filter((s) => indice.has(s.id)).sort((a, b) => indice.get(a.id) - indice.get(b.id));

  const marchi = [Plot.frame({ stroke: GRIGLIA })];
  for (const s of contesto) {
    marchi.push(Plot.line(s.punti, { x: 'giro', y: 'posizione', stroke: CONTESTO, strokeWidth: 1, strokeOpacity: 0.8 }));
  }
  marchi.push(
    Plot.text(
      contesto.map((s) => ({ ...s.punti.at(-1), sigla: s.sigla })),
      { x: 'giro', y: 'posizione', text: 'sigla', dx: 6, textAnchor: 'start', fill: '#64748b', stroke: 'white', strokeWidth: 3, fontSize: 11 },
    ),
  );
  for (const s of evidenza) {
    const stile = stileSerie(indice.get(s.id));
    marchi.push(
      Plot.line(s.punti, {
        x: 'giro',
        y: 'posizione',
        stroke: stile.colore,
        strokeWidth: 2.5,
        strokeDasharray: stile.tratteggio ?? undefined,
      }),
      Plot.dot([s.punti[0], s.punti.at(-1)], { x: 'giro', y: 'posizione', fill: stile.colore, symbol: stile.simbolo, r: 4 }),
      Plot.text([{ ...s.punti.at(-1), sigla: s.sigla }], {
        x: 'giro',
        y: 'posizione',
        text: 'sigla',
        dx: 8,
        textAnchor: 'start',
        fill: stile.colore,
        stroke: 'white',
        strokeWidth: 3,
        fontWeight: 700,
        fontSize: 12,
      }),
    );
  }
  marchi.push(
    Plot.tip(
      dati.serie.flatMap((s) => s.punti.map((p) => ({ ...p, serie: s }))),
      Plot.pointer({
        x: 'giro',
        y: 'posizione',
        title: (d) => `${d.serie.sigla} · ${d.serie.nome}\n${etichettaGiro(d.giro)}: ${d.posizione}º`,
      }),
    ),
  );

  const nodo = Plot.plot({
    width: larghezza,
    height: altezza,
    marginTop: 30,
    marginLeft: 44,
    marginRight: 44,
    marginBottom: 40,
    style: STILE,
    x: {
      label: 'Giro (0 = griglia di partenza)',
      domain: [0, Math.max(dati.giroMassimo, 1)],
      ticks: Math.min(dati.giroMassimo, larghezza < 520 ? 6 : 14),
      tickFormat: tickInteri,
    },
    y: {
      label: 'Posizione',
      domain: [1, massima],
      reverse: true,
      ticks: Array.from({ length: massima }, (_, i) => i + 1),
      tickFormat: (v) => String(v),
      grid: true,
    },
    marks: marchi,
  });
  nodo.setAttribute('role', 'img');
  nodo.setAttribute(
    'aria-label',
    `Posizioni giro per giro di ${dati.serie.length} piloti; in evidenza ${evidenza.map((s) => s.nome).join(', ') || 'nessuno'}.`,
  );
  return { nodo, punti: dati.puntiDisegnati };
}

/** Stint e soste: una riga per pilota. `dati` viene da stintPerGrafico(). */
export function disegnaStint(dati, { larghezza }) {
  const Plot = globalThis.Plot;
  const altezza = dati.righe.length * 22 + 56;
  const centro = (d) => (d.da + d.a) / 2;
  const nodo = Plot.plot({
    width: larghezza,
    height: altezza,
    marginTop: 10,
    marginLeft: 48,
    marginRight: 16,
    marginBottom: 40,
    style: STILE,
    x: {
      label: 'Giro',
      domain: [0, Math.max(dati.giroMassimo, 1)],
      ticks: Math.min(dati.giroMassimo, larghezza < 520 ? 6 : 14),
      tickFormat: tickInteri,
      grid: true,
    },
    y: { label: null, domain: dati.righe, tickSize: 0 },
    marks: [
      Plot.barX(dati.segmenti, {
        x1: 'da',
        x2: 'a',
        y: 'riga',
        fill: (d) => (d.stint % 2 === 1 ? '#cbd5e1' : '#f1f5f9'),
        stroke: '#64748b',
        strokeWidth: 0.75,
        insetTop: 3,
        insetBottom: 3,
      }),
      Plot.text(
        dati.segmenti.filter((d) => d.giri >= 3),
        { x: centro, y: 'riga', text: (d) => String(d.stint), fill: TESTO, fontSize: 10, fontWeight: 600 },
      ),
      Plot.tickX(dati.tacche, { x: 'giro', y: 'riga', stroke: TESTO, strokeWidth: 3 }),
      Plot.tip(
        dati.segmenti,
        Plot.pointer({
          x: centro,
          y: 'riga',
          title: (d) =>
            [
              `${d.riga} · ${d.nome}`,
              `Stint ${d.stint}: giri ${d.primoGiro}–${d.ultimoGiro} (${d.giri} ${d.giri === 1 ? 'giro' : 'giri'})`,
              ...d.soste.map((s) => `Sosta ${s.stop} al giro ${s.lap}: ${formato.durataSosta(s.durationMs)}`),
            ].join('\n'),
        }),
      ),
    ],
  });
  nodo.setAttribute('role', 'img');
  nodo.setAttribute(
    'aria-label',
    `Stint e soste di ${dati.righe.length} piloti: ${dati.segmenti.length} stint, ${dati.tacche.length} soste.`,
  );
  return { nodo, punti: dati.segmenti.length + dati.tacche.length };
}

/** Distacco in pista tra A e B (positivo = A davanti). `punti` viene da distaccoCumulato(). */
export function disegnaDistacco(punti, { larghezza, siglaA, siglaB, altezza = 300 }) {
  const Plot = globalThis.Plot;
  const ultimoGiro = Math.max(punti.at(-1)?.giro ?? 1, 2);
  const valori = punti.map((p) => p.ms / 1000);
  const estremo = Math.max(1, ...valori.map(Math.abs)) * 1.1;
  const nodo = Plot.plot({
    width: larghezza,
    height: altezza,
    marginTop: 16,
    marginLeft: 58,
    marginRight: 16,
    marginBottom: 40,
    style: STILE,
    x: {
      label: 'Giro',
      domain: [0.5, ultimoGiro + 0.5],
      ticks: Math.min(ultimoGiro, larghezza < 520 ? 6 : 14),
      tickFormat: tickInteri,
    },
    y: {
      label: 'Distacco (s)',
      domain: [Math.min(0, ...valori) < 0 ? -estremo : -estremo * 0.15, Math.max(0, ...valori) > 0 ? estremo : estremo * 0.15],
      grid: true,
      tickFormat: (v) => (v > 0 ? `+${v}` : v < 0 ? `−${Math.abs(v)}` : '0'),
    },
    marks: [
      Plot.frame({ stroke: GRIGLIA }),
      Plot.areaY(punti, { x: 'giro', y: (d) => d.ms / 1000, fill: '#94a3b8', fillOpacity: 0.25 }),
      Plot.ruleY([0], { stroke: TESTO, strokeWidth: 1 }),
      Plot.line(punti, { x: 'giro', y: (d) => d.ms / 1000, stroke: '#334155', strokeWidth: 2 }),
      Plot.text([`Sopra lo zero: davanti ${siglaA}`], { frameAnchor: 'top-left', dx: 8, dy: 8, fill: '#475569', textAnchor: 'start' }),
      Plot.text([`Sotto lo zero: davanti ${siglaB}`], { frameAnchor: 'bottom-left', dx: 8, dy: -8, fill: '#475569', textAnchor: 'start' }),
      Plot.tip(
        punti,
        Plot.pointer({
          x: 'giro',
          y: (d) => d.ms / 1000,
          title: (d) =>
            `Fine del giro ${d.giro}\n${d.ms === 0 ? 'Appaiati' : `${d.ms > 0 ? siglaA : siglaB} davanti di ${formato.distacco(Math.abs(d.ms)).slice(1)} s`}`,
        }),
      ),
    ],
  });
  nodo.setAttribute('role', 'img');
  nodo.setAttribute('aria-label', `Distacco in pista tra ${siglaA} e ${siglaB} alla fine di ogni giro: ${punti.length} giri.`);
  return { nodo, punti: punti.length };
}

const SIMBOLI_D3 = {
  circle: 'symbolCircle',
  square: 'symbolSquare',
  triangle: 'symbolTriangle',
  diamond: 'symbolDiamond',
  cross: 'symbolCross',
  star: 'symbolStar',
};

/** Campione di una serie per le legende: linea con il suo tratteggio e marcatore al centro. */
export function campioneSerie(indice) {
  const stile = stileSerie(indice);
  const d3 = globalThis.d3;
  const figura = svg('svg', { width: 38, height: 12, viewBox: '0 0 38 12', 'aria-hidden': 'true', class: 'shrink-0' });
  figura.append(
    svg('line', {
      x1: 1,
      x2: 37,
      y1: 6,
      y2: 6,
      stroke: stile.colore,
      'stroke-width': 2,
      'stroke-dasharray': stile.tratteggio ?? undefined,
    }),
  );
  const percorso = d3?.symbol ? d3.symbol(d3[SIMBOLI_D3[stile.simbolo]] ?? d3.symbolCircle, 44)() : null;
  if (percorso) figura.append(svg('path', { d: percorso, transform: 'translate(19,6)', fill: stile.colore, stroke: 'white', 'stroke-width': 0.75 }));
  return figura;
}
