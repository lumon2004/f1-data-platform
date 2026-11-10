// Server statico senza dipendenze: serve dist/ e inoltra /api/* al backend.
import { createReadStream, statSync } from 'node:fs';
import http from 'node:http';
import { extname, join, normalize, resolve, sep } from 'node:path';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.woff2': 'font/woff2',
};

// La pagina carica script, stili e caratteri solo dalla propria origine (nessuna CDN) e parla solo con /api.
// 'unsafe-inline' vale per i soli stili: la libreria dei grafici scrive attributi style negli SVG.
const SICUREZZA = {
  'Content-Security-Policy':
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
};

export const TIMEOUT_PROXY_MS = 15000;

function erroreJson(res, status, message) {
  if (res.headersSent) return res.destroy();
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  res.end(JSON.stringify({ status, message }));
}

function inoltra(req, res, target, timeoutMs) {
  let scaduto = false;
  const upstream = http.request(
    {
      protocol: target.protocol,
      hostname: target.hostname,
      port: target.port || 80,
      method: req.method,
      path: req.url,
      headers: { ...req.headers, host: target.host },
      timeout: timeoutMs,
    },
    (risposta) => {
      res.writeHead(risposta.statusCode ?? 502, risposta.headers);
      risposta.pipe(res);
    },
  );
  // Il backend ha accettato la connessione ma non risponde entro il tempo limite.
  upstream.on('timeout', () => {
    scaduto = true;
    upstream.destroy();
  });
  upstream.on('error', () => {
    if (scaduto) erroreJson(res, 504, 'Il backend non ha risposto in tempo.');
    else erroreJson(res, 502, 'Backend non raggiungibile.');
  });
  // Il browser ha chiuso la richiesta: inutile tenere aperta quella verso il backend.
  res.on('close', () => {
    if (!res.writableEnded) upstream.destroy();
  });
  upstream.end();
}

function file(root, urlPath) {
  let relativo;
  try {
    relativo = normalize(decodeURIComponent(urlPath));
  } catch {
    return null;
  }
  const percorso = join(root, relativo);
  if (percorso !== root && !percorso.startsWith(root + sep)) return null; // fuori dalla radice
  try {
    const info = statSync(percorso);
    if (info.isFile()) return percorso;
    if (info.isDirectory()) {
      const indice = join(percorso, 'index.html');
      if (statSync(indice).isFile()) return indice;
    }
  } catch {
    // non trovato
  }
  return null;
}

/**
 * @param {{ root: string, apiTarget: string, timeoutProxyMs?: number }} opzioni cartella da servire,
 *   URL del backend (solo http) e tempo massimo di attesa della sua risposta
 */
export function createServer({ root, apiTarget, timeoutProxyMs = TIMEOUT_PROXY_MS }) {
  const target = new URL(apiTarget);
  if (target.protocol !== 'http:') throw new Error(`API_TARGET deve essere un URL http: ${apiTarget}`);
  const base = resolve(root);

  return http.createServer((req, res) => {
    // L'API è di sola lettura e la dashboard è statica: si accettano solo GET e HEAD.
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      res.writeHead(405, { Allow: 'GET, HEAD' });
      return res.end();
    }
    let pathname;
    try {
      ({ pathname } = new URL(req.url, 'http://localhost'));
    } catch {
      res.writeHead(400, { 'Content-Type': 'text/plain; charset=utf-8' });
      return res.end('Richiesta non valida');
    }
    if (pathname === '/api' || pathname.startsWith('/api/')) return inoltra(req, res, target, timeoutProxyMs);

    const percorso = file(base, pathname);
    if (!percorso) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8', ...SICUREZZA });
      return res.end('Non trovato');
    }
    res.writeHead(200, {
      'Content-Type': MIME[extname(percorso)] ?? 'application/octet-stream',
      'Cache-Control': 'no-cache',
      ...SICUREZZA,
    });
    if (req.method === 'HEAD') return res.end();
    createReadStream(percorso).pipe(res);
  });
}
