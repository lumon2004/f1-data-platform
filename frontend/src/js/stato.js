// Stato condiviso tra le viste: le scelte dei filtri si conservano passando da una vista all'altra.
// Ogni modifica viene notificata a chi si è registrato con alCambio() (main.js la riporta nell'URL).

const valori = {
  /** Stagioni disponibili (risposta di /api/seasons), dalla più recente. */
  stagioni: [],
  stagione: null,
  garaId: null,
  /** Sessione del Race explorer: 'race', 'qualifying' oppure 'sprint'. */
  sessione: 'race',
  pilotaA: null,
  pilotaB: null,
  scuderiaA: null,
  scuderiaB: null,
  /** Piloti in evidenza nei grafici di Race analysis; null = selezione predefinita per la gara. */
  pilotiAnalisi: null,
  /** "Scala completa" dei tempi sul giro: ogni vista ha il proprio interruttore. */
  scalaCompletaAnalisi: false,
  scalaCompletaConfronto: false,
};

const ascoltatori = new Set();
let notificaInCoda = false;

function notifica() {
  if (notificaInCoda) return;
  notificaInCoda = true;
  // Più modifiche nello stesso passaggio producono una sola notifica.
  queueMicrotask(() => {
    notificaInCoda = false;
    for (const fn of ascoltatori) fn();
  });
}

export const stato = new Proxy(valori, {
  set(oggetto, chiave, valore) {
    if (!Object.hasOwn(oggetto, chiave)) throw new TypeError(`Chiave di stato sconosciuta: ${String(chiave)}`);
    const cambiato = oggetto[chiave] !== valore;
    oggetto[chiave] = valore;
    if (cambiato) notifica();
    return true;
  },
});

/** Registra una funzione chiamata (una volta per passaggio) dopo ogni modifica dello stato. */
export function alCambio(fn) {
  ascoltatori.add(fn);
  return () => ascoltatori.delete(fn);
}

/** Cambia stagione: le scelte che dipendono dalla gara si azzerano. */
export function impostaStagione(anno) {
  if (stato.stagione === anno) return;
  stato.stagione = anno;
  stato.garaId = null;
  stato.sessione = 'race';
  stato.pilotiAnalisi = null;
}

export function impostaGara(garaId) {
  if (stato.garaId === garaId) return;
  stato.garaId = garaId;
  stato.pilotiAnalisi = null;
}

/**
 * Contatore dei caricamenti: protegge dalle risposte in ritardo. Chi avvia un caricamento prende un turno
 * con nuovo(); quando la risposta arriva, la usa solo se valido(turno) è ancora vero, cioè se nel frattempo
 * non è partito un caricamento più recente.
 */
export function creaTurni() {
  let corrente = 0;
  return {
    nuovo: () => (corrente += 1),
    valido: (turno) => turno === corrente,
  };
}

/** Tiene `valore` se è tra quelli ammessi, altrimenti il primo dei predefiniti ammessi. */
export function scegliValido(valore, ammessi, predefiniti = []) {
  if (ammessi.includes(valore)) return valore;
  return predefiniti.find((v) => ammessi.includes(v)) ?? ammessi[0] ?? null;
}
