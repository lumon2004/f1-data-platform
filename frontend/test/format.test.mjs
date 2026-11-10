import assert from 'node:assert/strict';
import { test } from 'node:test';
import * as f from '../src/js/format.js';

test('tempo: m:ss.mmm, con le ore quando servono', () => {
  assert.equal(f.tempo(96236), '1:36.236');
  assert.equal(f.tempo(59999), '0:59.999');
  assert.equal(f.tempo(60000), '1:00.000');
  assert.equal(f.tempo(5636736), '1:33:56.736');
  assert.equal(f.tempo(0), '0:00.000');
});

test('tempo: valori mancanti o non validi diventano un trattino', () => {
  for (const v of [null, undefined, NaN, -1, '96236']) assert.equal(f.tempo(v), f.VUOTO);
});

test('distacco: segno sempre scritto, minuti oltre i 60 secondi', () => {
  assert.equal(f.distacco(11987), '+11.987');
  assert.equal(f.distacco(987), '+0.987');
  assert.equal(f.distacco(72647), '+1:12.647');
  assert.equal(f.distacco(0), '+0.000');
  assert.equal(f.distacco(-1500), '−1.500');
  assert.equal(f.distacco(null), f.VUOTO);
});

test('durataSosta: secondi con un decimale', () => {
  assert.equal(f.durataSosta(25885), '25.9 s');
  assert.equal(f.durataSosta(2400), '2.4 s');
  assert.equal(f.durataSosta(1205000), '20:05.000'); // sosta in regime di bandiera rossa
  assert.equal(f.durataSosta(null), f.VUOTO);
});

test('tempoAsse: etichette degli assi in secondi', () => {
  assert.equal(f.tempoAsse(96.5), '1:36.5');
  assert.equal(f.tempoAsse(100), '1:40.0');
  assert.equal(f.tempoAsse(59.96), '1:00.0');
});

test('punti, interi e medie in formato italiano', () => {
  assert.equal(f.punti(575), '575');
  assert.equal(f.punti(12.5), '12,5');
  assert.equal(f.punti(0), '0');
  assert.equal(f.punti(null), f.VUOTO);
  assert.equal(f.intero(22), '22');
  assert.equal(f.media(1.27), '1,27');
  assert.equal(f.media(3), '3,00');
  assert.equal(f.media(null), f.VUOTO);
});

test('date brevi, senza dipendere dal fuso orario', () => {
  assert.equal(f.data('2023-03-05'), '5 mar 2023');
  assert.equal(f.dataCorta('2023-11-26'), '26 nov');
  assert.equal(f.data(null), f.VUOTO);
  assert.equal(f.data('non una data'), f.VUOTO);
});

test('posizione o sigla dell’esito per i non classificati', () => {
  assert.equal(f.posizioneOEsito({ position: 3, outcome: 'classified' }), '3');
  assert.equal(f.posizioneOEsito({ position: null, outcome: 'retired' }), 'Rit.');
  assert.equal(f.posizioneOEsito({ position: null, outcome: 'disqualified' }), 'Sq.');
  assert.equal(f.posizioneOEsito({ position: null, outcome: 'qualcosa di nuovo' }), 'N.C.');
  assert.equal(f.esito('retired'), 'Ritirato');
  assert.equal(f.posizione(1), '1º');
  assert.equal(f.posizione(null), f.VUOTO);
});

test('tempoODistacco: tempo per il vincitore, distacco per gli altri, stato per chi non ha tempo', () => {
  assert.equal(f.tempoODistacco({ timeMs: 5636736, gapMs: 0, status: 'Finished' }), '1:33:56.736');
  assert.equal(f.tempoODistacco({ timeMs: 5648723, gapMs: 11987, status: 'Finished' }), '+11.987');
  assert.equal(f.tempoODistacco({ timeMs: null, gapMs: null, status: '+1 Lap' }), '+1 Lap');
  assert.equal(f.tempoODistacco({ timeMs: null, gapMs: null, status: '' }), f.VUOTO);
});

test('sigla: codice del pilota o ripiego sul cognome', () => {
  assert.equal(f.sigla({ code: 'VER', familyName: 'Verstappen' }), 'VER');
  assert.equal(f.sigla({ code: null, familyName: 'de Portago' }), 'DEP');
  assert.equal(f.sigla({ code: null, familyName: "O'Brien" }), 'OBR');
  assert.equal(f.sigla({}), '?');
});

test('nomi delle sessioni', () => {
  assert.equal(f.sessione('race'), 'Gara');
  assert.equal(f.sessione('qualifying'), 'Qualifica');
  assert.equal(f.sessione('fp2'), 'Prove libere 2');
  assert.equal(f.sessione('altro'), 'altro');
});
