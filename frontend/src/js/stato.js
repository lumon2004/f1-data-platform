// Stato condiviso tra le viste: le scelte dei filtri si conservano passando da una vista all'altra.

export const stato = {
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
  scalaCompleta: false,
};

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

/** Contatore dei caricamenti: una risposta arrivata dopo una nuova richiesta va ignorata. */
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
