// Scala categorica delle serie dei grafici (vedi docs/direzione-ui.md).
// Ogni posizione ha colore, tratteggio e marcatore: l'informazione non passa mai dal solo colore.

export const SFONDO = '#ffffff';
export const CONTESTO = '#7c8aa0'; // serie non selezionate: linee sottili ma comunque ad almeno 3:1 sul bianco
export const ETICHETTA_CONTESTO = '#475569'; // sigle delle serie non selezionate
export const TESTO_SECONDARIO = '#475569';

export const SERIE = [
  { colore: '#0072b2', nome: 'blu', tratteggio: null, simbolo: 'circle' },
  { colore: '#d55e00', nome: 'vermiglio', tratteggio: '7 3', simbolo: 'square' },
  { colore: '#007a5e', nome: 'verde', tratteggio: '2 3', simbolo: 'triangle' },
  { colore: '#aa4499', nome: 'porpora', tratteggio: '8 3 2 3', simbolo: 'diamond' },
  { colore: '#8a6d00', nome: 'ocra', tratteggio: '4 2', simbolo: 'cross' },
  { colore: '#333333', nome: 'antracite', tratteggio: '10 3 4 3', simbolo: 'star' },
];

export const MAX_SERIE = SERIE.length;

/** Stile della serie in posizione `indice` (0 = prima selezionata). */
export function stileSerie(indice) {
  return SERIE[((indice % SERIE.length) + SERIE.length) % SERIE.length];
}

function luminanza(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m) throw new Error(`Colore non valido: ${hex}`);
  const canali = [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16) / 255);
  const [r, g, b] = canali.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Rapporto di contrasto WCAG 2.1 tra due colori esadecimali (da 1 a 21). */
export function contrasto(a, b) {
  const [chiaro, scuro] = [luminanza(a), luminanza(b)].sort((x, y) => y - x);
  return (chiaro + 0.05) / (scuro + 0.05);
}
