// Mattoni dell'interfaccia condivisi dalle viste: intestazioni, filtri, schede, tabelle, barre di confronto.

import { el, riempi } from './dom.js';
import * as formato from './format.js';
import { campioneSerie } from './grafici.js';
import { impostaStagione, stato } from './stato.js';

let progressivo = 0;
const nuovoId = (prefisso) => `${prefisso}-${(progressivo += 1)}`;

export function intestazioneVista(titolo, descrizione) {
  return el('header', {}, el('h1', { class: 'text-2xl font-semibold tracking-tight' }, titolo), el('p', { class: 'mt-1 max-w-3xl text-sm text-slate-600' }, descrizione));
}

export function barraFiltri(...campi) {
  return el('form', { class: 'scheda flex flex-wrap items-end gap-x-5 gap-y-3 px-4 py-3', 'aria-label': 'Filtri', on: { submit: (e) => e.preventDefault() } }, campi);
}

/** Campo con etichetta visibile e `<select>` nativo. */
export function campoSelect({ etichetta, testid, classe = '' }) {
  const id = nuovoId('filtro');
  const select = el('select', { id, testid, class: 'campo-select' });
  const campo = el('div', { class: `flex flex-col gap-1 ${classe}` }, el('label', { for: id, class: 'etichetta' }, etichetta), select);
  return { campo, select };
}

/** Sostituisce le opzioni: `[{ valore, etichetta, disattivata }]`. */
export function riempiSelect(select, opzioni, valore) {
  select.replaceChildren(
    ...opzioni.map((o) => el('option', { value: String(o.valore), disabled: o.disattivata === true }, o.etichetta)),
  );
  select.disabled = opzioni.length === 0;
  if (valore !== null && valore !== undefined) select.value = String(valore);
}

/** Svuota un select mentre i suoi dati vengono ricaricati (opzione segnaposto con valore vuoto). */
export function svuotaSelect(select, segnaposto = 'Caricamento…') {
  select.replaceChildren(el('option', { value: '' }, segnaposto));
  select.disabled = true;
}

/** Filtro della stagione, uguale in tutte le viste. */
export function filtroStagione(ctx, alCambio) {
  const { campo, select } = campoSelect({ etichetta: 'Stagione', testid: 'filtro-stagione' });
  riempiSelect(select, stato.stagioni.map((s) => ({ valore: s.year, etichetta: String(s.year) })), stato.stagione);
  select.addEventListener('change', () => {
    impostaStagione(Number(select.value));
    ctx.pulisciErrore();
    alCambio();
  });
  return campo;
}

/** Scheda con intestazione; restituisce anche il corpo, da riempire quando arrivano i dati. */
export function scheda({ titolo, nota, azioni, testid, classe = '' }) {
  const corpo = el('div', {});
  const id = nuovoId('scheda');
  const sezione = el(
    'section',
    { class: `scheda min-w-0 ${classe}`, 'aria-labelledby': id, testid },
    el('div', { class: 'scheda-testa' }, el('div', { class: 'min-w-0' }, el('h2', { id, class: 'scheda-titolo' }, titolo), nota ? el('p', { class: 'scheda-nota' }, nota) : null), azioni ?? null),
    corpo,
  );
  return { sezione, corpo };
}

export function messaggio(testo, attributi = {}) {
  return el('p', { class: 'messaggio', ...attributi }, testo);
}

export const caricamento = () => messaggio('Caricamento…');

/**
 * Tabella con intestazioni vere. `colonne`: `[{ titolo, num, classe, cella(riga, indice) }]`;
 * `cella` restituisce testo o nodi.
 */
export function tabella({ colonne, righe, testid, testidRiga, didascalia }) {
  return el(
    'div',
    { class: 'overflow-x-auto', testid },
    el(
      'table',
      { class: 'tabella' },
      didascalia ? el('caption', { class: 'sr-only' }, didascalia) : null,
      el('thead', {}, el('tr', {}, colonne.map((c) => el('th', { scope: 'col', class: c.num ? 'num' : undefined }, c.titolo)))),
      el(
        'tbody',
        {},
        righe.map((riga, i) =>
          el('tr', { testid: testidRiga }, colonne.map((c) => el('td', { class: [c.num ? 'num' : '', c.classe ?? ''].join(' ').trim() || undefined }, c.cella(riga, i)))),
        ),
      ),
    ),
  );
}

/** Due righe in una cella: valore principale e dettaglio secondario. */
export function dueRighe(principale, secondario) {
  return [el('span', { class: 'block font-medium' }, principale), secondario ? el('span', { class: 'secondario block' }, secondario) : null];
}

/** Indicatore sintetico: etichetta, valore, dettaglio. */
export function indicatore(etichetta, valore, dettaglio) {
  return el(
    'div',
    { class: 'scheda px-4 py-3' },
    el('p', { class: 'etichetta' }, etichetta),
    el('p', { class: 'mt-1 text-lg leading-tight font-semibold tabular-nums' }, valore),
    dettaglio ? el('p', { class: 'secondario mt-0.5' }, dettaglio) : null,
  );
}

/** Elenco di statistiche (etichetta sopra, valore sotto) in griglia. */
export function grigliaStatistiche(voci) {
  return el(
    'dl',
    { class: 'grid grid-cols-3 gap-x-4 gap-y-3 sm:grid-cols-4' },
    voci.map(([etichetta, valore]) => el('div', {}, el('dt', { class: 'etichetta' }, etichetta), el('dd', { class: 'text-base font-semibold tabular-nums' }, valore))),
  );
}

/** Contrassegno "A" o "B" dei confronti, nello stile della rispettiva serie. */
export function lettera(lato) {
  return el('span', { class: `lettera ${lato === 'a' ? 'barra-a' : 'bg-serie-b'}`, 'aria-hidden': 'true' }, lato.toUpperCase());
}

/**
 * Barre di confronto tra A e B: per ogni metrica i due valori scritti e una barra divisa in proporzione.
 * `righe` viene da confronto(); `formati` associa a una chiave la funzione di formato (predefinito: intero).
 */
export function barreConfronto(righe, { nomeA, nomeB, formati = {} }) {
  const legenda = el(
    'div',
    { class: 'mb-4 flex flex-wrap items-center justify-between gap-3 text-sm font-medium' },
    el('span', { class: 'flex items-center gap-2' }, el('span', { class: 'barra-a inline-block h-3 w-6 rounded-sm', 'aria-hidden': 'true' }), nomeA),
    el('span', { class: 'flex items-center gap-2' }, nomeB, el('span', { class: 'barra-b inline-block h-3 w-6 rounded-sm', 'aria-hidden': 'true' })),
  );
  const lista = el(
    'ul',
    { class: 'space-y-3' },
    righe.map((r) => {
      const fmt = formati[r.chiave] ?? formato.intero;
      const senzaQuote = r.quotaA === null;
      return el(
        'li',
        { class: 'grid grid-cols-[4.5rem_1fr_4.5rem] items-center gap-x-3 tabular-nums' },
        el('span', { class: 'col-span-3 text-center text-xs font-medium text-slate-600' }, r.etichetta),
        el('span', { class: 'text-right text-sm font-semibold' }, fmt(r.a)),
        el(
          'span',
          { class: 'flex h-4 overflow-hidden rounded-sm bg-slate-100', role: 'img', 'aria-label': `${r.etichetta}: ${nomeA} ${fmt(r.a)}, ${nomeB} ${fmt(r.b)}` },
          senzaQuote ? null : el('span', { class: 'barra-a h-full', style: `width:${r.quotaA.toFixed(2)}%` }),
          senzaQuote ? null : el('span', { class: 'h-full w-0.5 shrink-0 bg-white' }),
          senzaQuote ? null : el('span', { class: 'barra-b h-full flex-1' }),
        ),
        el('span', { class: 'text-sm font-semibold' }, fmt(r.b)),
      );
    }),
  );
  return el('div', { class: 'px-4 py-4' }, legenda, lista);
}

/** Legenda delle serie di un grafico: campione (colore, tratteggio, marcatore) e nome del pilota. */
export function legendaSerie(serie) {
  return el(
    'ul',
    { class: 'flex flex-wrap gap-x-5 gap-y-1 px-4 pt-3 text-xs text-slate-700', 'aria-label': 'Legenda' },
    serie.map((s, i) => el('li', { class: 'flex items-center gap-2' }, campioneSerie(s.indice ?? i), el('span', {}, el('span', { class: 'font-semibold' }, s.sigla), ` ${s.nome}`, s.scuderia ? ` (${s.scuderia})` : ''))),
  );
}

/**
 * Contenitore di un grafico. `area` è l'elemento con il data-testid (e, dopo il disegno, data-punti):
 * non ha margini interni, così la sua larghezza è quella del grafico. `involucro` va messo nella scheda.
 */
export function areaGrafico(testid) {
  const area = el('div', { class: 'grafico', testid }, el('p', { class: 'messaggio' }, 'Caricamento…'));
  return { area, involucro: el('div', { class: 'px-2 pt-2 pb-1' }, area) };
}

export { riempi };
