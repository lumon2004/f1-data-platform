// Scelte dell'utente nell'URL (parte dopo #): un link porta alla stessa schermata e il ricaricamento
// non azzera i filtri. Formato: #race-analysis?stagione=2023&gara=1098&piloti=830,815
// Funzioni pure: leggono e scrivono stringhe, la validazione rispetto ai dati la fanno le viste.

export const VISTE = ['season-overview', 'race-explorer', 'driver-comparison', 'team-comparison', 'race-analysis'];
const SESSIONI = ['race', 'qualifying', 'sprint'];

// Parametri che hanno senso in ciascuna vista: [nome nell'URL, chiave dello stato].
const PARAMETRI = {
  'season-overview': [['stagione', 'stagione']],
  'race-explorer': [['stagione', 'stagione'], ['gara', 'garaId'], ['sessione', 'sessione']],
  'driver-comparison': [['stagione', 'stagione'], ['a', 'pilotaA'], ['b', 'pilotaB'], ['gara', 'garaId']],
  'team-comparison': [['stagione', 'stagione'], ['a', 'scuderiaA'], ['b', 'scuderiaB']],
  'race-analysis': [['stagione', 'stagione'], ['gara', 'garaId'], ['piloti', 'pilotiAnalisi']],
};

function interoPositivo(testo) {
  return /^[1-9]\d{0,8}$/.test(testo ?? '') ? Number(testo) : null;
}

/**
 * Interpreta `location.hash`. Restituisce la vista (null se assente o sconosciuta) e le sole scelte
 * presenti e ben formate, con le chiavi dello stato. Valori non validi vengono ignorati.
 */
export function leggiHash(hash) {
  const [nome, query = ''] = String(hash ?? '').replace(/^#/, '').split('?');
  const vista = VISTE.includes(nome) ? nome : null;
  const scelte = {};
  if (!vista) return { vista, scelte };
  const parametri = new URLSearchParams(query);
  for (const [nomeUrl, chiave] of PARAMETRI[vista]) {
    const grezzo = parametri.get(nomeUrl);
    if (grezzo === null) continue;
    if (chiave === 'sessione') {
      if (SESSIONI.includes(grezzo)) scelte.sessione = grezzo;
    } else if (chiave === 'pilotiAnalisi') {
      const ids = grezzo === '' ? [] : grezzo.split(',').map(interoPositivo);
      if (ids.length <= 6 && ids.every((id) => id !== null)) scelte.pilotiAnalisi = [...new Set(ids)];
    } else {
      const valore = interoPositivo(grezzo);
      if (valore !== null) scelte[chiave] = valore;
    }
  }
  return { vista, scelte };
}

/** Costruisce l'hash per la vista e lo stato dati; i valori predefiniti o assenti non compaiono. */
export function scriviHash(vista, stato) {
  const parametri = [];
  for (const [nomeUrl, chiave] of PARAMETRI[vista] ?? []) {
    const valore = stato[chiave];
    if (valore === null || valore === undefined) continue;
    if (chiave === 'sessione' && valore === 'race') continue;
    parametri.push(`${nomeUrl}=${Array.isArray(valore) ? valore.join(',') : encodeURIComponent(valore)}`);
  }
  return `#${vista}${parametri.length ? `?${parametri.join('&')}` : ''}`;
}
