import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import http from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { after, before, test } from 'node:test';
import { createServer } from '../scripts/server.mjs';

const ascolta = (server) =>
  new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server.address().port)));

let backend;
let frontend;
let base;

before(async () => {
  const root = mkdtempSync(join(tmpdir(), 'f1-frontend-'));
  writeFileSync(join(root, 'index.html'), '<!doctype html><title>prova</title>');
  backend = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ percorso: req.url }));
  });
  const portaBackend = await ascolta(backend);
  frontend = createServer({ root, apiTarget: `http://127.0.0.1:${portaBackend}` });
  base = `http://127.0.0.1:${await ascolta(frontend)}`;
});

after(() => {
  frontend.close();
  backend.close();
});

test('serve index.html dalla radice', async () => {
  const res = await fetch(`${base}/`);
  assert.equal(res.status, 200);
  assert.match(res.headers.get('content-type'), /text\/html/);
  assert.match(await res.text(), /prova/);
});

test('404 per file inesistenti e percorsi fuori dalla radice', async () => {
  assert.equal((await fetch(`${base}/manca.js`)).status, 404);
  assert.equal((await fetch(`${base}/..%2f..%2fetc%2fpasswd`)).status, 404);
});

test('inoltra /api al backend conservando percorso e query', async () => {
  const res = await fetch(`${base}/api/drivers/1/statistics?season=2023`);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { percorso: '/api/drivers/1/statistics?season=2023' });
});

test('intestazioni di sicurezza sui file statici: nessuna origine esterna ammessa', async () => {
  const res = await fetch(`${base}/`);
  const csp = res.headers.get('content-security-policy');
  assert.match(csp, /default-src 'self'/);
  assert.match(csp, /script-src 'self'(;|$)/);
  assert.doesNotMatch(csp, /https?:/);
  assert.equal(res.headers.get('x-content-type-options'), 'nosniff');
});

test('solo GET e HEAD: gli altri metodi ricevono 405, anche su /api', async () => {
  assert.equal((await fetch(`${base}/api/seasons`, { method: 'POST', body: '{}' })).status, 405);
  assert.equal((await fetch(`${base}/`, { method: 'DELETE' })).status, 405);
  assert.equal((await fetch(`${base}/`, { method: 'HEAD' })).status, 200);
});

test("inoltra anche le risposte d'errore del backend, con il loro corpo", async () => {
  const errore = http.createServer((req, res) => {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 404, message: 'Gara 999 inesistente' }));
  });
  const server = createServer({ root: tmpdir(), apiTarget: `http://127.0.0.1:${await ascolta(errore)}` });
  try {
    const res = await fetch(`http://127.0.0.1:${await ascolta(server)}/api/races/999`);
    assert.equal(res.status, 404);
    assert.equal((await res.json()).message, 'Gara 999 inesistente');
  } finally {
    server.close();
    errore.close();
  }
});

test('504 JSON se il backend non risponde entro il tempo limite', async () => {
  const lento = http.createServer(() => {
    // accetta la richiesta e non risponde mai
  });
  const server = createServer({ root: tmpdir(), apiTarget: `http://127.0.0.1:${await ascolta(lento)}`, timeoutProxyMs: 150 });
  try {
    const inizio = Date.now();
    const res = await fetch(`http://127.0.0.1:${await ascolta(server)}/api/seasons`);
    assert.equal(res.status, 504);
    assert.equal((await res.json()).status, 504);
    assert.ok(Date.now() - inizio < 5000, 'il proxy deve rispondere allo scadere del tempo limite');
  } finally {
    server.close();
    lento.closeAllConnections();
    lento.close();
  }
});

test('502 JSON se il backend non è raggiungibile', async () => {
  const chiuso = http.createServer();
  const porta = await ascolta(chiuso);
  await new Promise((resolve) => chiuso.close(resolve));
  const server = createServer({ root: tmpdir(), apiTarget: `http://127.0.0.1:${porta}` });
  const url = `http://127.0.0.1:${await ascolta(server)}/api/seasons`;
  try {
    const res = await fetch(url);
    assert.equal(res.status, 502);
    assert.equal((await res.json()).status, 502);
  } finally {
    server.close();
  }
});
