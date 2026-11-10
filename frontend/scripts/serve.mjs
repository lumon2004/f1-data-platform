// Avvio del server di sviluppo: `npm run serve` (dopo `npm run build`).
// Variabili d'ambiente: API_TARGET (default http://localhost:8080), PORT (default 3000), HOST (default 127.0.0.1).
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from './server.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const apiTarget = process.env.API_TARGET || 'http://localhost:8080';
const port = Number(process.env.PORT || 3000);
const host = process.env.HOST || '127.0.0.1';

if (!existsSync(join(root, 'index.html'))) {
  console.error('dist/ non trovata: esegui prima `npm run build`.');
  process.exit(1);
}

createServer({ root, apiTarget }).listen(port, host, () => {
  console.log(`Dashboard su http://${host}:${port} (proxy /api -> ${apiTarget})`);
});
