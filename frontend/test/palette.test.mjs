import assert from 'node:assert/strict';
import { test } from 'node:test';
import { CONTESTO, MAX_SERIE, SERIE, SFONDO, TESTO_SECONDARIO, contrasto, stileSerie } from '../src/js/palette.js';

test('contrasto WCAG: valori noti', () => {
  assert.equal(Math.round(contrasto('#000000', '#ffffff')), 21);
  assert.equal(contrasto('#ffffff', '#ffffff'), 1);
  assert.equal(contrasto('#0072b2', '#ffffff'), contrasto('#ffffff', '#0072b2'));
  assert.throws(() => contrasto('rosso', '#fff'));
});

test('ogni colore di serie ha contrasto di almeno 3:1 sullo sfondo dei grafici', () => {
  for (const s of SERIE) {
    assert.ok(contrasto(s.colore, SFONDO) >= 3, `${s.nome} ${s.colore}: ${contrasto(s.colore, SFONDO).toFixed(2)}`);
  }
  assert.ok(contrasto(TESTO_SECONDARIO, SFONDO) >= 4.5);
});

test('le serie non si distinguono per il solo colore: colore, tratteggio e marcatore sono tutti diversi', () => {
  assert.equal(MAX_SERIE, SERIE.length);
  for (const chiave of ['colore', 'tratteggio', 'simbolo', 'nome']) {
    assert.equal(new Set(SERIE.map((s) => s[chiave])).size, SERIE.length, `${chiave} ripetuto`);
  }
  assert.ok(!SERIE.some((s) => s.colore === CONTESTO));
});

test('stileSerie ricomincia da capo oltre l’ultima posizione', () => {
  assert.equal(stileSerie(0), SERIE[0]);
  assert.equal(stileSerie(SERIE.length), SERIE[0]);
  assert.equal(stileSerie(SERIE.length + 1), SERIE[1]);
});
