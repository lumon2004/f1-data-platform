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
      if (body?.message) message = body.message;
    } catch {
      // corpo non JSON (es. 502 del proxy): resta il messaggio generico
    }
    throw new ApiError(message, { status: response.status, path: url });
  }
  try {
    return await response.json();
  } catch (cause) {
    throw new ApiError("Risposta dell'API non valida.", { status: response.status, path: url, cause });
  }
}

const seg = (value) => encodeURIComponent(String(value));

// Endpoint minimi del contratto dell'API.
export const api = {
  seasons: (opts) => getJson('/seasons', opts),
  races: (year, opts) => getJson(`/seasons/${seg(year)}/races`, opts),
  race: (raceId, opts) => getJson(`/races/${seg(raceId)}`, opts),
  raceResults: (raceId, opts) => getJson(`/races/${seg(raceId)}/results`, opts),
  laps: (raceId, driverId, opts) => getJson(`/races/${seg(raceId)}/laps/${seg(driverId)}`, opts),
  driverStatistics: (driverId, season, opts) =>
    getJson(`/drivers/${seg(driverId)}/statistics`, { ...opts, params: { season } }),
  teamStatistics: (teamId, season, opts) =>
    getJson(`/teams/${seg(teamId)}/statistics`, { ...opts, params: { season } }),
};
