import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, api, buildUrl, getJson } from '../src/js/api.js';

const risposta = (status, body) => new Response(body === undefined ? null : JSON.stringify(body), { status });

test('buildUrl usa percorsi relativi /api e scarta i parametri vuoti', () => {
  assert.equal(buildUrl('/seasons'), '/api/seasons');
  assert.equal(buildUrl('/drivers/1/statistics', { season: 2023 }), '/api/drivers/1/statistics?season=2023');
  assert.equal(buildUrl('/drivers/1/statistics', { season: undefined }), '/api/drivers/1/statistics');
});

test('getJson restituisce il corpo JSON', async () => {
  const chiamate = [];
  const fetchImpl = async (url) => {
    chiamate.push(url);
    return risposta(200, [{ year: 2024 }]);
  };
  assert.deepEqual(await api.seasons({ fetchImpl }), [{ year: 2024 }]);
  assert.deepEqual(chiamate, ['/api/seasons']);
});

test('gli endpoint del contratto puntano ai percorsi attesi', async () => {
  const chiamate = [];
  const fetchImpl = async (url) => {
    chiamate.push(url);
    return risposta(200, {});
  };
  await api.races(2023, { fetchImpl });
  await api.race(7, { fetchImpl });
  await api.raceResults(7, { fetchImpl });
  await api.laps(7, 44, { fetchImpl });
  await api.driverStatistics(44, 2023, { fetchImpl });
  await api.teamStatistics(9, undefined, { fetchImpl });
  assert.deepEqual(chiamate, [
    '/api/seasons/2023/races',
    '/api/races/7',
    '/api/races/7/results',
    '/api/races/7/laps/44',
    '/api/drivers/44/statistics?season=2023',
    '/api/teams/9/statistics',
  ]);
});

test("errore HTTP: ApiError con status e messaggio dell'API", async () => {
  const fetchImpl = async () => risposta(404, { status: 404, message: 'Gara non trovata' });
  await assert.rejects(getJson('/races/999', { fetchImpl }), (err) => {
    assert.ok(err instanceof ApiError);
    assert.equal(err.status, 404);
    assert.equal(err.message, 'Gara non trovata');
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
