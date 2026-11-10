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
 * Tabella con intestazioni vere. `colonne`: `[{ titolo, num, classe, soloLargo, cella(riga, indice) }]`;
 * `cella` restituisce testo o nodi. Le colonne `soloLargo` compaiono da 640 px in su (il loro contenuto
 * su schermo stretto va riportato in un'altra cella). `minimo` è una classe di larghezza minima: sotto
 * quella larghezza la tabella scorre in orizzontale dentro la propria scheda, e un avviso lo dice.
 */
export function tabella({ colonne, righe, testid, testidRiga, didascalia, minimo = '' }) {
  const classi = (c, extra = '') => [c.num ? 'num' : '', c.soloLargo ? 'hidden sm:table-cell' : '', extra].join(' ').trim() || undefined;
  const avviso = el('p', { class: 'border-b border-slate-200 bg-slate-50 px-4 py-1.5 text-xs font-medium text-slate-700', hidden: true }, 'Scorri la tabella in orizzontale per vedere tutte le colonne →');
  const area = el(
    'div',
    { class: 'overflow-x-auto' },
    el(
      'table',
      { class: `tabella ${minimo}`.trim() },
      didascalia ? el('caption', { class: 'sr-only' }, didascalia) : null,
      el('thead', {}, el('tr', {}, colonne.map((c) => el('th', { scope: 'col', class: classi(c) }, c.titolo)))),
      el(
        'tbody',
        {},
        righe.map((riga, i) => el('tr', { testid: testidRiga }, colonne.map((c) => el('td', { class: classi(c, c.classe ?? '') }, c.cella(riga, i))))),
      ),
    ),
  );
  if (typeof ResizeObserver === 'function') {
    // L'avviso compare solo quando la tabella è davvero più larga dello spazio; allora l'area diventa
    // raggiungibile da tastiera, così si può scorrere anche senza puntatore.
    new ResizeObserver(() => {
      const scorre = area.scrollWidth > area.clientWidth + 1;
      if (avviso.hidden !== !scorre) avviso.hidden = !scorre;
      if (scorre) {
        area.setAttribute('tabindex', '0');
        area.setAttribute('role', 'region');
        area.setAttribute('aria-label', `${didascalia ?? 'Tabella'} (scorre in orizzontale)`);
      } else {
        for (const attributo of ['tabindex', 'role', 'aria-label']) area.removeAttribute(attributo);
      }
    }).observe(area);
  }
  return el('div', { class: 'min-w-0', testid }, avviso, area);
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
 * Note sotto un grafico dei tempi sul giro: quanti giri sono fuori scala (e come leggerli) e che cosa sono
 * le fasce grigie. `dati` viene da serieTempi(), `fasce` da giriLenti(). Restituisce i paragrafi.
 */
export function noteTempi(dati, fasce = []) {
  const note = [];
  if (dati.fuoriScala > 0) {
    note.push(
      el(
        'p',
        { testid: 'nota-fuori-scala' },
        `${dati.fuoriScala} ${dati.fuoriScala === 1 ? 'giro è' : 'giri sono'} oltre la scala (più di ${formato.tempo(dati.soglia)}): di solito il primo giro, i giri di ingresso e uscita dai box e le neutralizzazioni. Sono segnati con un triangolo sopra il grafico, nella riga del pilota; per leggerli in scala attiva "Scala completa".`,
      ),
    );
  }
  if (fasce.length) {
    const elenco = fasce.map((f) => (f.da === f.a ? `${f.da}` : `${f.da}–${f.a}`)).join(', ');
    note.push(
      el(
        'p',
        {},
        `Fasce grigie: giri lenti per tutto il gruppo (${fasce.length === 1 && fasce[0].da === fasce[0].a ? 'giro' : 'giri'} ${elenco}). È una stima ricavata dai tempi di tutti i piloti: la fonte non registra safety car, bandiere o pioggia.`,
      ),
    );
  }
  return note;
}

/** Interruttore "Scala completa" di un grafico dei tempi. */
export function interruttoreScala(attivo, alCambio) {
  const casella = el('input', { type: 'checkbox', class: 'h-4 w-4 accent-sky-700' });
  casella.checked = attivo;
  casella.addEventListener('change', () => alCambio(casella.checked));
  return el('label', { class: 'flex items-center gap-2 text-sm' }, casella, 'Scala completa');
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
