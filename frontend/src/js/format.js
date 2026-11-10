// Formattazione di tempi, distacchi, numeri e date. Funzioni pure, senza DOM.

export const VUOTO = '—';

const numero = (v) => typeof v === 'number' && Number.isFinite(v);
const due = (n) => String(n).padStart(2, '0');
const tre = (n) => String(n).padStart(3, '0');

/** Millisecondi → `m:ss.mmm` (oppure `h:mm:ss.mmm` da un'ora in su). */
export function tempo(ms) {
  if (!numero(ms) || ms < 0) return VUOTO;
  const totale = Math.round(ms);
  const millesimi = totale % 1000;
  const secondi = Math.floor(totale / 1000) % 60;
  const minuti = Math.floor(totale / 60000) % 60;
  const ore = Math.floor(totale / 3600000);
  if (ore > 0) return `${ore}:${due(minuti)}:${due(secondi)}.${tre(millesimi)}`;
  return `${minuti}:${due(secondi)}.${tre(millesimi)}`;
}

/** Distacco in millisecondi → `+s.mmm` oppure `+m:ss.mmm`. Il segno è sempre scritto. */
export function distacco(ms) {
  if (!numero(ms)) return VUOTO;
  const totale = Math.round(Math.abs(ms));
  const segno = ms < 0 ? '−' : '+';
  const millesimi = totale % 1000;
  const secondi = Math.floor(totale / 1000);
  if (secondi < 60) return `${segno}${secondi}.${tre(millesimi)}`;
  return `${segno}${Math.floor(secondi / 60)}:${due(secondi % 60)}.${tre(millesimi)}`;
}

/** Durata breve in secondi con un decimale, per le soste: `24.3 s`. */
export function durataSosta(ms) {
  if (!numero(ms) || ms < 0) return VUOTO;
  if (ms >= 60000) return tempo(ms);
  return `${(ms / 1000).toFixed(1)} s`;
}

/** Etichetta d'asse per un tempo sul giro espresso in secondi: `1:36.5`. */
export function tempoAsse(secondi) {
  if (!numero(secondi) || secondi < 0) return '';
  const decimi = Math.round(secondi * 10);
  const s = Math.floor(decimi / 10);
  return `${Math.floor(s / 60)}:${due(s % 60)}.${decimi % 10}`;
}

const interi = new Intl.NumberFormat('it-IT', { maximumFractionDigits: 0 });
const unDecimale = new Intl.NumberFormat('it-IT', { minimumFractionDigits: 0, maximumFractionDigits: 1 });
const dueDecimali = new Intl.NumberFormat('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Punti: interi senza decimali, mezzi punti con la virgola (`12,5`). */
export function punti(v) {
  return numero(v) ? unDecimale.format(v) : VUOTO;
}

export function intero(v) {
  return numero(v) ? interi.format(v) : VUOTO;
}

/** Media a due decimali (`1,27`). */
export function media(v) {
  return numero(v) ? dueDecimali.format(v) : VUOTO;
}

const dataBreve = new Intl.DateTimeFormat('it-IT', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
const dataSenzaAnno = new Intl.DateTimeFormat('it-IT', { day: 'numeric', month: 'short', timeZone: 'UTC' });

function comeData(iso) {
  if (typeof iso !== 'string' || !/^\d{4}-\d{2}-\d{2}/.test(iso)) return null;
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Data ISO → `5 mar 2023`. */
export function data(iso) {
  const d = comeData(iso);
  return d ? dataBreve.format(d) : VUOTO;
}

/** Data ISO → `5 mar`. */
export function dataCorta(iso) {
  const d = comeData(iso);
  return d ? dataSenzaAnno.format(d) : VUOTO;
}

/** Posizione con il simbolo ordinale: `3º`. */
export function posizione(v) {
  return numero(v) ? `${v}º` : VUOTO;
}

const SESSIONI = { fp1: 'Prove libere 1', fp2: 'Prove libere 2', fp3: 'Prove libere 3', qualifying: 'Qualifica', sprint: 'Sprint', race: 'Gara' };

export function sessione(tipo) {
  return SESSIONI[tipo] ?? String(tipo ?? VUOTO);
}

const ESITI = {
  retired: 'Rit.',
  disqualified: 'Sq.',
  excluded: 'Escl.',
  withdrawn: 'N.P.',
  failed_to_qualify: 'N.Q.',
  not_classified: 'N.C.',
};

const ESITI_ESTESI = {
  classified: 'Classificato',
  retired: 'Ritirato',
  disqualified: 'Squalificato',
  excluded: 'Escluso',
  withdrawn: 'Non partito',
  failed_to_qualify: 'Non qualificato',
  not_classified: 'Non classificato',
};

/** Colonna della posizione: il numero, oppure la sigla dell'esito per chi non è classificato. */
export function posizioneOEsito(risultato) {
  if (numero(risultato?.position)) return String(risultato.position);
  return ESITI[risultato?.outcome] ?? 'N.C.';
}

export function esito(codice) {
  return ESITI_ESTESI[codice] ?? String(codice ?? VUOTO);
}

/**
 * Colonna "Tempo / distacco" di una classifica: tempo totale per il vincitore, distacco per chi
 * arriva a pieni giri, altrimenti lo stato di arrivo così com'è nella fonte (es. "+1 Lap").
 */
export function tempoODistacco(risultato) {
  if (numero(risultato?.gapMs) && risultato.gapMs > 0) return distacco(risultato.gapMs);
  if (numero(risultato?.timeMs)) return tempo(risultato.timeMs);
  return risultato?.status ? String(risultato.status) : VUOTO;
}

/** Sigla di tre lettere del pilota; per i piloti storici senza sigla, le prime tre del cognome. */
export function sigla(pilota) {
  if (pilota?.code) return String(pilota.code);
  const cognome = String(pilota?.familyName ?? pilota?.name ?? '').replace(/[^\p{L}]/gu, '');
  return cognome ? cognome.slice(0, 3).toUpperCase() : '?';
}
