import assert from 'node:assert/strict';
import { test } from 'node:test';
import { alCambio, creaTurni, impostaGara, impostaStagione, scegliValido, stato } from '../src/js/stato.js';

const attesa = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

test('creaTurni: vale solo il turno più recente', () => {
  const turni = creaTurni();
  const primo = turni.nuovo();
  assert.equal(turni.valido(primo), true);
  const secondo = turni.nuovo();
  assert.equal(turni.valido(primo), false, 'un turno superato non è più valido');
  assert.equal(turni.valido(secondo), true);
  // contatori indipendenti: una vista non invalida i caricamenti di un'altra
  const altri = creaTurni();
  altri.nuovo();
  altri.nuovo();
  altri.nuovo();
  assert.equal(turni.valido(secondo), true);
});

test('creaTurni: una risposta arrivata in ritardo non sovrascrive quella della richiesta più recente', async () => {
  const turni = creaTurni();
  let mostrato = null;
  // Stesso schema delle viste: prendo un turno, aspetto la risposta, la uso solo se il turno è ancora valido.
  async function carica(valore, ritardoMs) {
    const turno = turni.nuovo();
    await attesa(ritardoMs);
    if (!turni.valido(turno)) return 'ignorata';
    mostrato = valore;
    return 'mostrata';
  }
  // La prima richiesta (stagione 2024) è lenta; l'utente passa subito al 2023, che risponde prima.
  const esiti = await Promise.all([carica(2024, 40), carica(2023, 5)]);
  assert.deepEqual(esiti, ['ignorata', 'mostrata']);
  assert.equal(mostrato, 2023);
});

test('creaTurni: anche con le risposte in ordine, conta solo l\u2019ultima richiesta', async () => {
  const turni = creaTurni();
  const mostrati = [];
  async function carica(valore, ritardoMs) {
    const turno = turni.nuovo();
    await attesa(ritardoMs);
    if (turni.valido(turno)) mostrati.push(valore);
  }
  await Promise.all([carica('a', 5), carica('b', 10), carica('c', 15)]);
  assert.deepEqual(mostrati, ['c']);
});

test('scegliValido: tiene la scelta se esiste, altrimenti il primo predefinito ammesso', () => {
  assert.equal(scegliValido(830, [4, 830, 815]), 830);
  assert.equal(scegliValido(999, [4, 830, 815], [830, 815]), 830, 'scelta di un\u2019altra stagione: si torna al primo in classifica');
  assert.equal(scegliValido(null, [4, 830, 815], [777, 815]), 815, 'i predefiniti non ammessi si saltano');
  assert.equal(scegliValido(null, [4, 830], []), 4, 'senza predefiniti: il primo ammesso');
  assert.equal(scegliValido(830, []), null, 'nessun valore ammesso');
});

test('cambio di stagione e di gara: le scelte che ne dipendono si azzerano', () => {
  stato.stagione = 2024;
  stato.garaId = 1121;
  stato.sessione = 'sprint';
  stato.pilotiAnalisi = [830, 815];
  stato.pilotaA = 830;

  impostaStagione(2024);
  assert.equal(stato.garaId, 1121, 'stessa stagione: non cambia nulla');

  impostaStagione(2023);
  assert.deepEqual([stato.stagione, stato.garaId, stato.sessione, stato.pilotiAnalisi], [2023, null, 'race', null]);
  assert.equal(stato.pilotaA, 830, 'il pilota resta: lo convalida la vista sulla nuova stagione');

  stato.pilotiAnalisi = [4];
  impostaGara(1098);
  assert.deepEqual([stato.garaId, stato.pilotiAnalisi], [1098, null]);
  stato.pilotiAnalisi = [4];
  impostaGara(1098);
  assert.deepEqual(stato.pilotiAnalisi, [4], 'stessa gara: la selezione dei piloti resta');
});

test('lo stato notifica le modifiche una volta per passaggio e rifiuta chiavi sconosciute', async () => {
  let notifiche = 0;
  const annulla = alCambio(() => (notifiche += 1));
  await attesa(0); // smaltisce le notifiche dei test precedenti
  notifiche = 0;
  stato.pilotaA = 1;
  stato.pilotaB = 2;
  stato.pilotaB = 2; // valore identico: nessuna modifica
  assert.equal(notifiche, 0, 'la notifica non è sincrona');
  await attesa(0);
  assert.equal(notifiche, 1);
  stato.pilotaB = 2;
  await attesa(0);
  assert.equal(notifiche, 1, 'riscrivere lo stesso valore non notifica');
  annulla();
  stato.pilotaB = 3;
  await attesa(0);
  assert.equal(notifiche, 1);
  assert.throws(() => {
    stato.scalaCompleta = true; // chiave rimossa: un refuso non crea stato nascosto
  }, TypeError);
});
