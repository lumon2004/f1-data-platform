// Costruzione del DOM senza innerHTML: tutto il testo (compresi i messaggi dell'API) entra come nodo di testo.

function aggiungi(nodo, figli) {
  for (const figlio of figli.flat(Infinity)) {
    if (figlio === null || figlio === undefined || figlio === false) continue;
    nodo.append(figlio instanceof Node ? figlio : document.createTextNode(String(figlio)));
  }
}

function applica(nodo, attributi) {
  for (const [chiave, valore] of Object.entries(attributi ?? {})) {
    if (valore === undefined || valore === null || valore === false) continue;
    if (chiave === 'class') nodo.setAttribute('class', valore);
    else if (chiave === 'testid') nodo.setAttribute('data-testid', valore);
    else if (chiave === 'on') for (const [evento, fn] of Object.entries(valore)) nodo.addEventListener(evento, fn);
    else if (valore === true) nodo.setAttribute(chiave, '');
    else nodo.setAttribute(chiave, String(valore));
  }
}

/** Crea un elemento HTML: `el('p', { class: '…' }, 'testo', altroNodo)`. */
export function el(tag, attributi, ...figli) {
  const nodo = document.createElement(tag);
  applica(nodo, attributi);
  aggiungi(nodo, figli);
  return nodo;
}

/** Crea un elemento SVG (per i campioni della legenda). */
export function svg(tag, attributi, ...figli) {
  const nodo = document.createElementNS('http://www.w3.org/2000/svg', tag);
  applica(nodo, attributi);
  aggiungi(nodo, figli);
  return nodo;
}

/** Sostituisce il contenuto di un nodo. */
export function riempi(nodo, ...figli) {
  nodo.replaceChildren();
  aggiungi(nodo, figli);
  return nodo;
}
