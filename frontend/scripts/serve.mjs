// Avvio del server della dashboard: `npm run serve` (dopo `npm run build`). È lo stesso server usato nel container.
// Variabili d'ambiente: API_TARGET (default http://localhost:8080), PORT (default 3000), HOST (default 127.0.0.1),
// PROXY_TIMEOUT_MS (default 15000).
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { TIMEOUT_PROXY_MS, createServer } from './server.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const apiTarget = process.env.API_TARGET || 'http://localhost:8080';
const port = Number(process.env.PORT || 3000);
const host = process.env.HOST || '127.0.0.1';
const timeoutProxyMs = Number(process.env.PROXY_TIMEOUT_MS) > 0 ? Number(process.env.PROXY_TIMEOUT_MS) : TIMEOUT_PROXY_MS;

if (!existsSync(join(root, 'index.html'))) {
  console.error('dist/ non trovata: esegui prima `npm run build`.');
  process.exit(1);
}

const server = createServer({ root, apiTarget, timeoutProxyMs });
server.listen(port, host, () => {
  console.log(`Dashboard su http://${host}:${port} (proxy /api -> ${apiTarget})`);
});

// Arresto ordinato: `docker stop` invia SIGTERM.
for (const segnale of ['SIGTERM', 'SIGINT']) {
  process.on(segnale, () => {
    server.close(() => process.exit(0));
    server.closeAllConnections?.();
  });
}
