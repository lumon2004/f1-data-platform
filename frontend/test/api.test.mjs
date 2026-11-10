import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, buildUrl, creaClient, descriviErrore, getJson, messaggioErrore } from '../src/js/api.js';

const risposta = (status, body) => new Response(body === undefined ? null : JSON.stringify(body), { status });

/** Finto fetch che registra gli URL richiesti. */
function registra(rispondi = (url) => risposta(200, /\/(races\/[^/]+|statistics(\?.*)?)$/.test(url) && !/\/seasons\//.test(url) ? {} : [])) {
  const chiamate = [];
  const fetchImpl = async (url) => {
    chiamate.push(url);
    return rispondi(url);
  };
  return { chiamate, fetchImpl };
}

test('buildUrl usa percorsi relativi /api e scarta i parametri vuoti', () => {
  assert.equal(buildUrl('/seasons'), '/api/seasons');
  assert.equal(buildUrl('/drivers/1/statistics', { season: 2023 }), '/api/drivers/1/statistics?season=2023');
  assert.equal(buildUrl('/drivers/1/statistics', { season: undefined }), '/api/drivers/1/statistics');
  assert.equal(buildUrl('/drivers/1/statistics', { season: '' }), '/api/drivers/1/statistics');
});

test('getJson restituisce il corpo JSON', async () => {
  const { chiamate, fetchImpl } = registra(() => risposta(200, [{ year: 2024 }]));
  assert.deepEqual(await getJson('/seasons', { fetchImpl }), [{ year: 2024 }]);
  assert.deepEqual(chiamate, ['/api/seasons']);
});

test('gli endpoint puntano ai percorsi attesi', async () => {
  const { chiamate, fetchImpl } = registra();
  const api = creaClient({ fetchImpl });
  await api.seasons();
  await api.races(2023);
  await api.seasonDrivers(2023);
  await api.seasonTeams(2023);
  await api.driverStandings(2023);
  await api.teamStandings(2023);
  await api.race(7);
  await api.raceResults(7);
  await api.raceResults(7, 'race');
  await api.raceResults(7, 'sprint');
  await api.qualifying(7);
  await api.allLaps(7);
  await api.laps(7, 44);
  await api.pitStops(7);
  await api.stints(7);
  await api.driverStatistics(44, 2023);
  await api.teamStatistics(9, undefined);
  assert.deepEqual(chiamate, [
    '/api/seasons',
    '/api/seasons/2023/races',
    '/api/seasons/2023/drivers',
    '/api/seasons/2023/teams',
    '/api/seasons/2023/standings/drivers',
    '/api/seasons/2023/standings/teams',
    '/api/races/7',
    '/api/races/7/results',
    '/api/races/7/results',
    '/api/races/7/results?session=sprint',
    '/api/races/7/qualifying',
    '/api/races/7/laps',
    '/api/races/7/laps/44',
    '/api/races/7/pit-stops',
    '/api/races/7/stints',
    '/api/drivers/44/statistics?season=2023',
    '/api/teams/9/statistics',
  ]);
});

test('i segmenti di percorso vengono codificati', async () => {
  const { chiamate, fetchImpl } = registra();
  await creaClient({ fetchImpl }).race('7/../../x?y');
  assert.deepEqual(chiamate, ['/api/races/7%2F..%2F..%2Fx%3Fy']);
});

test('con la cache ogni URL viene richiesto una sola volta', async () => {
  const { chiamate, fetchImpl } = registra(() => risposta(200, [1]));
  const api = creaClient({ fetchImpl, cache: true });
  const [a, b] = await Promise.all([api.races(2023), api.races(2023)]);
  await api.races(2023);
  await api.races(2024);
  assert.deepEqual(a, b);
  assert.deepEqual(chiamate, ['/api/seasons/2023/races', '/api/seasons/2024/races']);
});

test('la cache non conserva le risposte fallite', async () => {
  let tentativi = 0;
  const fetchImpl = async () => {
    tentativi += 1;
    return tentativi === 1 ? risposta(503, { status: 503, message: 'Database non raggiungibile' }) : risposta(200, [{ year: 2024 }]);
  };
  const api = creaClient({ fetchImpl, cache: true });
  await assert.rejects(api.seasons(), ApiError);
  assert.deepEqual(await api.seasons(), [{ year: 2024 }]);
  assert.equal(tentativi, 2);
});

test("errore HTTP: ApiError con status e messaggio dell'API", async () => {
  const fetchImpl = async () => risposta(404, { status: 404, message: 'Gara 999 inesistente' });
  await assert.rejects(getJson('/races/999', { fetchImpl }), (err) => {
    assert.ok(err instanceof ApiError);
    assert.equal(err.status, 404);
    assert.equal(err.message, 'Gara 999 inesistente');
    assert.equal(err.path, '/api/races/999');
    return true;
  });
});

test('errore HTTP senza corpo JSON: messaggio generico con il codice', async () => {
  const fetchImpl = async () => new Response('<html>Bad Gateway</html>', { status: 502 });
  await assert.rejects(getJson('/seasons', { fetchImpl }), (err) => {
    assert.equal(err.status, 502);
    assert.equal(err.message, "Errore 502 dall'API.");
    return true;
  });
});

test('API irraggiungibile: ApiError con status 0', async () => {
  const fetchImpl = async () => {
    throw new TypeError('fetch failed');
  };
  await assert.rejects(getJson('/seasons', { fetchImpl }), (err) => {
    assert.ok(err instanceof ApiError);
    assert.equal(err.status, 0);
    return true;
  });
});

test('risposta 200 con corpo non JSON: ApiError', async () => {
  const fetchImpl = async () => new Response('non json', { status: 200 });
  await assert.rejects(getJson('/seasons', { fetchImpl }), (err) => {
    assert.ok(err instanceof ApiError);
    assert.match(err.message, /non valida/);
    return true;
  });
});

test("messaggioErrore distingue API assente, non disponibile, dato non trovato", () => {
  assert.match(messaggioErrore(new ApiError("L'API non risponde.")), /non risponde.*riprova/i);
  assert.match(messaggioErrore(new ApiError('Database non raggiungibile', { status: 503 })), /non è disponibile.*503.*Database non raggiungibile/);
  assert.match(messaggioErrore(new ApiError('Gara 999 inesistente', { status: 404 })), /non trovato.*Gara 999 inesistente/i);
  assert.match(messaggioErrore(new ApiError('Anno non valido', { status: 400 })), /non valida.*Anno non valido/);
  assert.match(messaggioErrore(new ApiError('Errore interno', { status: 500 })), /errore \(500\)/);
  // un errore che non viene dall'API non espone dettagli interni
  assert.equal(messaggioErrore(new TypeError('x is undefined')), 'Si è verificato un errore imprevisto nella dashboard.');
});

test("descriviErrore: un guasto dell'API e un errore interno della dashboard hanno titoli diversi", () => {
  const api = descriviErrore(new ApiError('Database non raggiungibile', { status: 503 }));
  assert.equal(api.interno, false);
  assert.equal(api.titolo, 'Dati non disponibili');
  assert.match(api.testo, /503.*Database non raggiungibile/);

  const interno = descriviErrore(new TypeError("Cannot read properties of undefined (reading 'laps')"));
  assert.equal(interno.interno, true);
  assert.equal(interno.titolo, 'Errore della dashboard');
  assert.notEqual(interno.titolo, api.titolo);
  assert.doesNotMatch(interno.testo, /undefined|laps/, "il testo non espone i dettagli dell'eccezione");
  assert.match(interno.testo, /non un guasto dell’API/);
});

test('una risposta 200 di forma inattesa è un errore, non una lista vuota', async () => {
  const api = creaClient({ fetchImpl: async () => risposta(200, { non: 'una lista' }) });
  await assert.rejects(api.races(2023), (err) => {
    assert.ok(err instanceof ApiError);
    assert.equal(err.status, 200);
    assert.match(err.message, /attesa una lista/);
    assert.match(messaggioErrore(err), /forma inattesa/);
    return true;
  });
  const liste = creaClient({ fetchImpl: async () => risposta(200, []) });
  await assert.rejects(liste.race(7), /atteso un oggetto/);
  await assert.rejects(liste.driverStatistics(1, 2023), /atteso un oggetto/);
  assert.deepEqual(await liste.stints(7), [], 'una lista vuota resta una risposta valida');
  const nullo = creaClient({ fetchImpl: async () => risposta(200, null) });
  await assert.rejects(nullo.race(7), ApiError);
});
