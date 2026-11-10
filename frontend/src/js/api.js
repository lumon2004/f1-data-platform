// Client dell'API: tutte le chiamate usano percorsi relativi /api/...
// (il server del frontend fa da proxy verso il backend).

export const API_BASE = '/api';

/** Errore di una chiamata all'API: `status` è 0 quando l'API non risponde. */
export class ApiError extends Error {
  constructor(message, { status = 0, path = '', cause } = {}) {
    super(message, { cause });
    this.name = 'ApiError';
    this.status = status;
    this.path = path;
  }
}

/** Costruisce l'URL relativo, scartando i parametri vuoti. */
export function buildUrl(path, params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value));
  }
  const qs = query.toString();
  return `${API_BASE}${path}${qs ? `?${qs}` : ''}`;
}

/**
 * GET JSON. Lancia sempre ApiError (mai errori grezzi di rete), così le viste
 * possono mostrare un messaggio chiaro.
 */
export async function getJson(path, { params, signal, fetchImpl = globalThis.fetch } = {}) {
  const url = buildUrl(path, params);
  let response;
  try {
    response = await fetchImpl(url, { headers: { Accept: 'application/json' }, signal });
  } catch (cause) {
    if (cause?.name === 'AbortError') throw cause;
    throw new ApiError("L'API non risponde.", { path: url, cause });
  }
  if (!response.ok) {
    let message = `Errore ${response.status} dall'API.`;
    try {
      const body = await response.json();
      if (typeof body?.message === 'string' && body.message.trim()) message = body.message;
    } catch {
      // corpo non JSON (es. errore di un proxy intermedio): resta il messaggio generico
    }
    throw new ApiError(message, { status: response.status, path: url });
  }
  try {
    return await response.json();
  } catch (cause) {
    throw new ApiError("Risposta dell'API non valida.", { status: response.status, path: url, cause });
  }
}

/**
 * Messaggio per l'utente a partire da un errore qualsiasi. È testo semplice: chi lo mostra
 * lo inserisce con textContent, mai come HTML.
 */
export function messaggioErrore(errore) {
  if (!(errore instanceof ApiError)) return 'Si è verificato un errore imprevisto nella dashboard.';
  if (errore.status >= 200 && errore.status < 300) return `L'API ha risposto, ma con dati in una forma inattesa. ${errore.message}`;
  if (errore.status === 0) {
    return "L'API non risponde. Controlla che il backend sia avviato e raggiungibile, poi riprova.";
  }
  if (errore.status === 502 || errore.status === 503 || errore.status === 504) {
    return `L'API non è disponibile in questo momento (errore ${errore.status}). ${errore.message}`;
  }
  if (errore.status === 404) return `Dato non trovato. ${errore.message}`;
  if (errore.status === 400) return `Richiesta non valida. ${errore.message}`;
  return `L'API ha risposto con un errore (${errore.status}). ${errore.message}`;
}

/**
 * Titolo e testo del riquadro degli errori. Un guasto dell'API ("Dati non disponibili") è cosa diversa da
 * un'eccezione interna della dashboard: quest'ultima non dipende dai dati e non si risolve riprovando.
 */
export function descriviErrore(errore) {
  const interno = !(errore instanceof ApiError);
  return {
    interno,
    titolo: interno ? 'Errore della dashboard' : 'Dati non disponibili',
    testo: interno
      ? 'Si è verificato un errore imprevisto nel codice della dashboard, non un guasto dell’API. Ricarica la pagina; i dettagli sono nella console del browser.'
      : messaggioErrore(errore),
  };
}

const seg = (value) => encodeURIComponent(String(value));

/**
 * Crea un client dell'API. Con `cache: true` ogni URL viene richiesto una sola volta
 * (i dati non cambiano mentre la dashboard è aperta); le risposte fallite non restano in cache.
 */
export function creaClient({ fetchImpl, cache = false } = {}) {
  const memoria = new Map();

  function get(path, params) {
    const chiave = buildUrl(path, params);
    if (cache && memoria.has(chiave)) return memoria.get(chiave);
    const promessa = getJson(path, { params, fetchImpl: fetchImpl ?? globalThis.fetch });
    if (cache) {
      memoria.set(chiave, promessa);
      promessa.catch(() => memoria.delete(chiave));
    }
    return promessa;
  }

  /** Endpoint che restituiscono una lista: una risposta 200 di altra forma è un errore dell'API, non "nessun dato". */
  async function lista(path, params) {
    const corpo = await get(path, params);
    if (!Array.isArray(corpo)) throw new ApiError("Risposta dell'API non valida: era attesa una lista.", { status: 200, path: buildUrl(path, params) });
    return corpo;
  }

  /** Endpoint che restituiscono un oggetto. */
  async function oggetto(path, params) {
    const corpo = await get(path, params);
    if (corpo === null || typeof corpo !== 'object' || Array.isArray(corpo)) {
      throw new ApiError("Risposta dell'API non valida: era atteso un oggetto.", { status: 200, path: buildUrl(path, params) });
    }
    return corpo;
  }

  return {
    seasons: () => lista('/seasons'),
    races: (year) => lista(`/seasons/${seg(year)}/races`),
    seasonDrivers: (year) => lista(`/seasons/${seg(year)}/drivers`),
    seasonTeams: (year) => lista(`/seasons/${seg(year)}/teams`),
    driverStandings: (year) => lista(`/seasons/${seg(year)}/standings/drivers`),
    teamStandings: (year) => lista(`/seasons/${seg(year)}/standings/teams`),
    race: (raceId) => oggetto(`/races/${seg(raceId)}`),
    /** `session`: 'race' (predefinita) oppure 'sprint'. */
    raceResults: (raceId, session) => lista(`/races/${seg(raceId)}/results`, { session: session === 'race' ? undefined : session }),
    qualifying: (raceId) => lista(`/races/${seg(raceId)}/qualifying`),
    allLaps: (raceId) => lista(`/races/${seg(raceId)}/laps`),
    laps: (raceId, driverId) => lista(`/races/${seg(raceId)}/laps/${seg(driverId)}`),
    pitStops: (raceId) => lista(`/races/${seg(raceId)}/pit-stops`),
    stints: (raceId) => lista(`/races/${seg(raceId)}/stints`),
    driverStatistics: (driverId, season) => oggetto(`/drivers/${seg(driverId)}/statistics`, { season }),
    teamStatistics: (teamId, season) => oggetto(`/teams/${seg(teamId)}/statistics`, { season }),
    svuotaCache: () => memoria.clear(),
  };
}

/** Client usato dalla dashboard. */
export const api = creaClient({ cache: true });
