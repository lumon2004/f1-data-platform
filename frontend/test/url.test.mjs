import assert from 'node:assert/strict';
import { test } from 'node:test';
import { VISTE, leggiHash, scriviHash } from '../src/js/url.js';

test('leggiHash: vista e scelte ben formate', () => {
  assert.deepEqual(leggiHash('#race-analysis?stagione=2023&gara=1098&piloti=830,815,4'), {
    vista: 'race-analysis',
    scelte: { stagione: 2023, garaId: 1098, pilotiAnalisi: [830, 815, 4] },
  });
  assert.deepEqual(leggiHash('#driver-comparison?stagione=2023&a=848&b=4&gara=1104').scelte, { stagione: 2023, pilotaA: 848, pilotaB: 4, garaId: 1104 });
  assert.deepEqual(leggiHash('#team-comparison?a=9&b=131').scelte, { scuderiaA: 9, scuderiaB: 131 }, 'a e b sono scuderie in Team comparison');
  assert.deepEqual(leggiHash('#race-explorer?gara=1101&sessione=sprint').scelte, { garaId: 1101, sessione: 'sprint' });
  assert.deepEqual(leggiHash('#race-analysis?piloti=').scelte, { pilotiAnalisi: [] }, 'nessun pilota in evidenza è una scelta');
});

test('leggiHash: senza parametri, senza hash o con vista sconosciuta', () => {
  assert.deepEqual(leggiHash('#race-explorer'), { vista: 'race-explorer', scelte: {} });
  assert.deepEqual(leggiHash(''), { vista: null, scelte: {} });
  assert.deepEqual(leggiHash(undefined), { vista: null, scelte: {} });
  assert.deepEqual(leggiHash('#altro?stagione=2023'), { vista: null, scelte: {} });
});

test('leggiHash: i valori non validi vengono ignorati, non interpretati', () => {
  const { scelte } = leggiHash('#race-analysis?stagione=20x3&gara=-1&piloti=830,abc');
  assert.deepEqual(scelte, {});
  assert.deepEqual(leggiHash('#race-explorer?sessione=fp1&gara=0').scelte, {});
  assert.deepEqual(leggiHash('#race-explorer?gara=1e3').scelte, {});
  assert.deepEqual(leggiHash('#race-explorer?gara=<script>').scelte, {});
  assert.deepEqual(leggiHash('#race-analysis?piloti=1,2,3,4,5,6,7').scelte, {}, 'più piloti del massimo');
  assert.deepEqual(leggiHash('#race-analysis?piloti=830,830,4').scelte, { pilotiAnalisi: [830, 4] }, 'i doppioni si tolgono');
  // i parametri di un'altra vista non si applicano
  assert.deepEqual(leggiHash('#season-overview?stagione=2022&gara=1098&a=1').scelte, { stagione: 2022 });
});

test('scriviHash: solo le scelte che hanno senso nella vista, senza i valori predefiniti', () => {
  const stato = { stagione: 2023, garaId: 1098, sessione: 'race', pilotaA: 848, pilotaB: 4, scuderiaA: 9, scuderiaB: null, pilotiAnalisi: null };
  assert.equal(scriviHash('season-overview', stato), '#season-overview?stagione=2023');
  assert.equal(scriviHash('race-explorer', stato), '#race-explorer?stagione=2023&gara=1098');
  assert.equal(scriviHash('race-explorer', { ...stato, sessione: 'qualifying' }), '#race-explorer?stagione=2023&gara=1098&sessione=qualifying');
  assert.equal(scriviHash('driver-comparison', stato), '#driver-comparison?stagione=2023&a=848&b=4&gara=1098');
  assert.equal(scriviHash('team-comparison', stato), '#team-comparison?stagione=2023&a=9');
  assert.equal(scriviHash('race-analysis', { ...stato, pilotiAnalisi: [830, 4] }), '#race-analysis?stagione=2023&gara=1098&piloti=830,4');
  assert.equal(scriviHash('race-analysis', { ...stato, pilotiAnalisi: [] }), '#race-analysis?stagione=2023&gara=1098&piloti=');
  assert.equal(scriviHash('season-overview', { stagione: null }), '#season-overview');
});

test('scrittura e lettura sono coerenti per ogni vista', () => {
  const stato = { stagione: 2022, garaId: 1074, sessione: 'sprint', pilotaA: 1, pilotaB: 830, scuderiaA: 131, scuderiaB: 6, pilotiAnalisi: [1, 830] };
  for (const vista of VISTE) {
    const letto = leggiHash(scriviHash(vista, stato));
    assert.equal(letto.vista, vista);
    for (const [chiave, valore] of Object.entries(letto.scelte)) assert.deepEqual(valore, stato[chiave], `${vista}: ${chiave}`);
    assert.equal(letto.scelte.stagione, 2022);
  }
});
