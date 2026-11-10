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
};

function inoltra(req, res, target) {
  const upstream = http.request(
    {
      protocol: target.protocol,
      hostname: target.hostname,
      port: target.port || 80,
      method: req.method,
      path: req.url,
      headers: { ...req.headers, host: target.host },
    },
    (risposta) => {
      res.writeHead(risposta.statusCode ?? 502, risposta.headers);
      risposta.pipe(res);
    },
  );
  upstream.on('error', () => {
    if (res.headersSent) return res.destroy();
    res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ status: 502, message: 'Backend non raggiungibile.' }));
  });
  req.pipe(upstream);
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
 * @param {{ root: string, apiTarget: string }} opzioni cartella da servire e URL del backend (solo http)
 */
export function createServer({ root, apiTarget }) {
  const target = new URL(apiTarget);
  if (target.protocol !== 'http:') throw new Error(`API_TARGET deve essere un URL http: ${apiTarget}`);
  const base = resolve(root);

  return http.createServer((req, res) => {
    const { pathname } = new URL(req.url, 'http://localhost');
    if (pathname === '/api' || pathname.startsWith('/api/')) return inoltra(req, res, target);

    if (req.method !== 'GET' && req.method !== 'HEAD') {
      res.writeHead(405, { Allow: 'GET, HEAD' });
      return res.end();
    }
    const percorso = file(base, pathname);
    if (!percorso) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      return res.end('Non trovato');
    }
    res.writeHead(200, {
      'Content-Type': MIME[extname(percorso)] ?? 'application/octet-stream',
      'Cache-Control': 'no-cache',
    });
    if (req.method === 'HEAD') return res.end();
    createReadStream(percorso).pipe(res);
  });
}
