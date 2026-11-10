import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  alternaSelezione,
  confronto,
  distaccoCumulato,
  giriLenti,
  giroMassimo,
  numeroStintVisibile,
  quantile,
  selezionePredefinita,
  seriePosizioni,
  serieTempi,
  sigleUniche,
  sogliaFuoriScala,
  stintPerGrafico,
} from '../src/js/trasformazioni.js';

const pilota = (id, code, name = code) => ({ id, code, name, familyName: name });
const giri = (tempi, posizione = 1) => tempi.map((timeMs, i) => ({ lap: i + 1, position: posizione, timeMs }));

/** Gara di 20 giri sui 90 s: il primo giro è lento, `lenti` elenca altri giri lenti (numero -> tempo). */
function gara20(base, lenti = {}) {
  return Array.from({ length: 20 }, (_, i) => lenti[i + 1] ?? (i === 0 ? base + 6000 : base + (i % 4) * 100));
}

const VER = pilota(830, 'VER', 'Max Verstappen');
const PER = pilota(815, 'PER', 'Sergio Pérez');
const ALO = pilota(4, 'ALO', 'Fernando Alonso');

test('quantile interpola tra i valori ordinati', () => {
  assert.equal(quantile([1, 2, 3, 4, 5], 0.5), 3);
  assert.equal(quantile([1, 2, 3, 4], 0.5), 2.5);
  assert.equal(quantile([10], 0.75), 10);
  assert.equal(quantile([], 0.5), null);
});

test('sogliaFuoriScala: terzo quartile più tre scarti interquartili, con margine minimo', () => {
  const tempi = [90000, 90100, 90200, 90300, 90000, 90100, 90200, 90300, 120000];
  const soglia = sogliaFuoriScala(tempi);
  assert.ok(soglia > 90300 && soglia < 120000, String(soglia));
  // tempi tutti uguali: lo scarto è zero, vale il margine del 2%
  assert.equal(sogliaFuoriScala(Array(10).fill(90000)), 91800);
  // troppo pochi tempi per stimare un passo
  assert.equal(sogliaFuoriScala([90000, 91000, 150000]), null);
});

test('serieTempi: i giri lenti restano nella serie, segnati come fuori scala', () => {
  const dati = [
    { driver: VER, team: { name: 'Red Bull' }, laps: giri(gara20(90000, { 10: 112000 })) },
    { driver: PER, team: { name: 'Red Bull' }, laps: giri(gara20(90500), 2) },
    { driver: ALO, team: { name: 'Aston Martin' }, laps: giri(gara20(91000), 3) },
  ];
  const r = serieTempi(dati, { selezionati: [815, 830], soste: [{ driver: VER, stop: 1, lap: 9 }] });
  assert.deepEqual(r.serie.map((s) => [s.sigla, s.indice]), [['PER', 0], ['VER', 1]], "l'ordine è quello della selezione");
  assert.equal(r.puntiDisegnati, 40, 'nessun giro viene scartato');
  const ver = r.serie[1];
  assert.equal(ver.punti.length, 20);
  assert.deepEqual(ver.punti.filter((p) => p.fuoriScala).map((p) => p.giro), [1, 10]);
  assert.equal(r.fuoriScala, 3, 'primo giro di entrambi e giro 10 di VER');
  assert.ok(r.massimo < r.soglia && r.minimo === 90000);
  assert.equal(ver.punti[8].sosta, 'ingresso');
  assert.equal(ver.punti[9].sosta, 'uscita');
  assert.equal(ver.punti[10].sosta, null);
  assert.equal(r.giroMassimo, 20);
});

test('serieTempi con scala completa: nessun giro fuori scala', () => {
  const dati = [{ driver: VER, team: { name: 'Red Bull' }, laps: giri(gara20(90000, { 10: 112000 })) }];
  const r = serieTempi(dati, { selezionati: [830], scalaCompleta: true });
  assert.equal(r.fuoriScala, 0);
  assert.equal(r.soglia, null);
  assert.equal(r.massimo, 112000);
  assert.equal(r.puntiDisegnati, 20);
});

test('serieTempi: selezione vuota, pilota senza giri o id sconosciuto', () => {
  const dati = [
    { driver: VER, team: { name: 'Red Bull' }, laps: [] },
    { driver: PER, team: { name: 'Red Bull' }, laps: giri([90000, 90100]) },
  ];
  assert.equal(serieTempi(dati, { selezionati: [] }).puntiDisegnati, 0);
  const r = serieTempi(dati, { selezionati: [830, 999, 815] });
  assert.equal(r.serie.length, 2);
  assert.equal(r.puntiDisegnati, 2);
  assert.equal(r.soglia, null, 'con pochi giri non si stima una soglia');
  assert.equal(serieTempi(dati, { selezionati: [830] }).minimo, null);
});

test('seriePosizioni: il giro 0 è la casella di partenza, quando è nota', () => {
  const dati = [
    { driver: VER, team: { name: 'Red Bull' }, laps: [{ lap: 1, position: 1, timeMs: 1 }, { lap: 2, position: 1, timeMs: 1 }] },
    { driver: PER, team: { name: 'Red Bull' }, laps: [{ lap: 1, position: 3, timeMs: 1 }, { lap: 2, position: null, timeMs: 1 }] },
    { driver: ALO, team: { name: 'Aston Martin' }, laps: [] },
  ];
  const risultati = [
    { driver: VER, grid: 2 },
    { driver: PER, grid: null }, // partenza dalla pit lane
    { driver: ALO, grid: 5 }, // in classifica ma senza giri: nessuna linea
  ];
  const r = seriePosizioni(dati, risultati);
  assert.deepEqual(r.serie.map((s) => s.sigla), ['VER', 'PER']);
  assert.deepEqual(r.serie.map((s) => s.classificato), [true, true], 'senza position nei risultati non si presume un ritiro');
  const conRitiro = seriePosizioni(dati, [{ driver: VER, grid: 2, position: 1 }, { driver: PER, grid: null, position: null }]);
  assert.deepEqual(conRitiro.serie.map((s) => s.classificato), [true, false]);
  assert.deepEqual(r.serie[0].punti, [{ giro: 0, posizione: 2 }, { giro: 1, posizione: 1 }, { giro: 2, posizione: 1 }]);
  assert.deepEqual(r.serie[1].punti, [{ giro: 1, posizione: 3 }]);
  assert.equal(r.puntiDisegnati, 4);
  assert.equal(r.posizioneMassima, 3);
  assert.equal(r.giroMassimo, 2);
});

test('seriePosizioni senza giri: nessun punto', () => {
  assert.deepEqual(seriePosizioni([], []), { serie: [], puntiDisegnati: 0, posizioneMassima: 0, giroMassimo: 0 });
});

test('distaccoCumulato: positivo quando A è davanti, si ferma al primo giro mancante', () => {
  const a = giri([90000, 91000, 90000, 90000]);
  const b = giri([91000, 90500, 95000]);
  assert.deepEqual(distaccoCumulato(a, b), {
    punti: [
      { giro: 1, ms: 1000 },
      { giro: 2, ms: 500 },
      { giro: 3, ms: 5500 },
    ],
    doppiaggio: null,
  });
  assert.deepEqual(distaccoCumulato(b, a).punti.map((p) => p.ms), [-1000, -500, -5500]);
  assert.deepEqual(distaccoCumulato(a, []), { punti: [], doppiaggio: null });
  // un buco nei giri di uno dei due interrompe il confronto: i tempi cumulati non sarebbero più confrontabili
  assert.equal(distaccoCumulato(a, [{ lap: 1, timeMs: 90000 }, { lap: 3, timeMs: 90000 }]).punti.length, 1);
});

test('distaccoCumulato: la serie si ferma quando uno dei due viene doppiato', () => {
  // A gira in 60 s, B in 80 s: B perde 20 s al giro. A completa il giro 5 (300 s) prima che B completi il 4 (320 s).
  const veloce = giri(Array(10).fill(60000));
  const lento = giri(Array(10).fill(80000));
  const r = distaccoCumulato(veloce, lento);
  assert.deepEqual(r.doppiaggio, { giro: 5, doppiato: 'b' });
  assert.deepEqual(r.punti.map((p) => [p.giro, p.ms]), [[1, 20000], [2, 40000], [3, 60000], [4, 80000]]);
  assert.ok(r.punti.every((p) => p.ms < 80000 + 1), 'nessun punto supera un giro di distacco');
  // a parti invertite il doppiato è A e i distacchi cambiano segno
  const inverso = distaccoCumulato(lento, veloce);
  assert.deepEqual(inverso.doppiaggio, { giro: 5, doppiato: 'a' });
  assert.deepEqual(inverso.punti.map((p) => p.ms), [-20000, -40000, -60000, -80000]);
});

test('distaccoCumulato: un distacco grande ma inferiore a un giro non è un doppiaggio', () => {
  // B perde 50 s in una sosta al giro 2 e poi gira come A: resta nello stesso giro fino alla fine.
  const a = giri(Array(8).fill(90000));
  const b = giri([90000, 140000, 90000, 90000, 90000, 90000, 90000, 90000]);
  const r = distaccoCumulato(a, b);
  assert.equal(r.doppiaggio, null);
  assert.equal(r.punti.length, 8);
  assert.equal(r.punti.at(-1).ms, 50000);
});

test('numeroStintVisibile: il numero si scrive solo se il segmento è abbastanza largo', () => {
  assert.equal(numeroStintVisibile(1, 15), true, 'un giro a schermo largo');
  assert.equal(numeroStintVisibile(1, 4), false, 'un giro su telefono');
  assert.equal(numeroStintVisibile(3, 4), true);
  assert.equal(numeroStintVisibile(2, 4.5), true);
  assert.equal(numeroStintVisibile(0, 20), false);
  assert.equal(numeroStintVisibile(5, NaN), false);
});

test('giriLenti: intervalli di giri lenti per tutto il gruppo, escluso il primo', () => {
  const lenti = { 8: 130000, 9: 131000, 10: 129000, 15: 128000 };
  const dati = [VER, PER, ALO].map((d, i) => ({ driver: d, laps: giri(gara20(90000 + i * 300, lenti)) }));
  assert.deepEqual(giriLenti(dati), [{ da: 8, a: 10 }, { da: 15, a: 15 }]);
  // il giro lento di un solo pilota (una sosta) non è un giro lento del gruppo
  const unaSosta = [
    { driver: VER, laps: giri(gara20(90000, { 12: 112000 })) },
    { driver: PER, laps: giri(gara20(90300)) },
    { driver: ALO, laps: giri(gara20(90600)) },
  ];
  assert.deepEqual(giriLenti(unaSosta), []);
  assert.deepEqual(giriLenti([]), []);
});

test('stintPerGrafico: un giro occupa (L−1, L], le soste chiudono gli stint', () => {
  const stints = [
    { driver: VER, stint: 1, startLap: 1, endLap: 14, laps: 14, compound: null },
    { driver: VER, stint: 2, startLap: 15, endLap: 57, laps: 43, compound: null },
    { driver: PER, stint: 1, startLap: 1, endLap: 57, laps: 57, compound: null },
  ];
  const soste = [
    { driver: VER, stop: 1, lap: 14, durationMs: 24500 },
    { driver: ALO, stop: 1, lap: 1, durationMs: null }, // soste senza stint: il pilota ha comunque una riga
  ];
  const r = stintPerGrafico(stints, soste);
  assert.deepEqual(r.righe, ['VER', 'PER', 'ALO']);
  assert.deepEqual(r.segmenti.map((s) => [s.riga, s.stint, s.da, s.a, s.giri]), [
    ['VER', 1, 0, 14, 14],
    ['VER', 2, 14, 57, 43],
    ['PER', 1, 0, 57, 57],
  ]);
  assert.equal(r.segmenti[0].soste.length, 1);
  assert.equal(r.segmenti[1].soste.length, 0);
  assert.deepEqual(r.tacche, [
    { riga: 'VER', nome: 'Max Verstappen', giro: 14, sosta: 1, durataMs: 24500 },
    { riga: 'ALO', nome: 'Fernando Alonso', giro: 1, sosta: 1, durataMs: null },
  ]);
  assert.equal(r.giroMassimo, 57);
  assert.deepEqual(stintPerGrafico([], []), { righe: [], segmenti: [], tacche: [], giroMassimo: 0 });
});

test('sigleUniche distingue i piloti con la stessa sigla', () => {
  const sigle = sigleUniche([pilota(1, 'MSC'), pilota(2, 'MSC'), pilota(3, 'VET')]);
  assert.deepEqual([...sigle.values()], ['MSC 1', 'MSC 2', 'VET']);
});

test('confronto: valori e quote per la larghezza delle barre', () => {
  const a = { wins: 19, podiums: 21, poles: 0, points: 530, sprintPoints: 45, averageFinish: null };
  const b = { wins: 2, podiums: 9, poles: 0, points: 260, sprintPoints: 25, averageFinish: 4.5 };
  const righe = confronto(a, b, [
    { chiave: 'wins', etichetta: 'Vittorie' },
    { chiave: 'poles', etichetta: 'Pole' },
    { chiave: 'punti', etichetta: 'Punti', valore: (s) => s.points + s.sprintPoints },
    { chiave: 'averageFinish', etichetta: 'Media' },
  ]);
  assert.equal(righe[0].a, 19);
  assert.equal(righe[0].b, 2);
  assert.ok(Math.abs(righe[0].quotaA - (19 / 21) * 100) < 1e-9);
  assert.ok(Math.abs(righe[0].quotaA + righe[0].quotaB - 100) < 1e-9);
  assert.deepEqual([righe[1].a, righe[1].b, righe[1].quotaA, righe[1].quotaB], [0, 0, null, null], 'zero a zero: nessuna barra');
  assert.deepEqual([righe[2].a, righe[2].b], [575, 285]);
  assert.deepEqual([righe[3].a, righe[3].b, righe[3].quotaA], [null, 4.5, null], 'valore mancante: nessuna barra');
});

test('confronto con valori presi da oggetti diversi: i punti vengono dalla classifica, non da una somma', () => {
  const metriche = [
    { chiave: 'punti', etichetta: 'Punti', valore: (x) => x?.classifica?.points ?? null },
    { chiave: 'wins', etichetta: 'Vittorie', valore: (x) => x?.statistiche.wins },
  ];
  const a = { statistiche: { wins: 19, points: 530, sprintPoints: 45 }, classifica: { points: 575 } };
  const senzaClassifica = { statistiche: { wins: 2, points: 260, sprintPoints: 25 }, classifica: undefined };
  const righe = confronto(a, senzaClassifica, metriche);
  assert.deepEqual([righe[0].a, righe[0].b, righe[0].quotaA], [575, null, null], 'senza riga di classifica il valore manca: non si ricostruisce');
  assert.deepEqual([righe[1].a, righe[1].b], [19, 2]);
});

test('selezione dei piloti: predefinita, aggiunta, rimozione e limite', () => {
  const dati = [
    { driver: VER, laps: giri([1, 2]) },
    { driver: PER, laps: [] },
    { driver: ALO, laps: giri([1]) },
  ];
  assert.deepEqual(selezionePredefinita(dati, 3), [830, 4], 'chi non ha giri non viene selezionato');
  assert.deepEqual(selezionePredefinita(dati, 1), [830]);
  assert.equal(giroMassimo(dati), 2);
  assert.deepEqual(alternaSelezione([1, 2], 3, 6), [1, 2, 3]);
  assert.deepEqual(alternaSelezione([1, 2], 1, 6), [2]);
  assert.deepEqual(alternaSelezione([1, 2], 3, 2), [1, 2], 'oltre il limite la selezione non cambia');
});
