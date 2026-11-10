// Test di fumo sulla build: `npm test` esegue prima `npm run build` (pretest).
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const dist = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const html = () => readFileSync(join(dist, 'index.html'), 'utf8');

test('la build produce pagina, moduli e CSS compilato', () => {
  for (const nome of ['index.html', 'styles.css', 'js/main.js', 'js/api.js']) {
    assert.ok(existsSync(join(dist, nome)), `manca dist/${nome}`);
  }
  const css = readFileSync(join(dist, 'styles.css'), 'utf8');
  assert.ok(!css.includes('@import "tailwindcss"'), 'CSS non compilato');
  assert.match(css, /\.min-h-screen/, 'classi di utilità non generate');
  // classi applicate solo da main.js: devono essere rilevate anche lì
  assert.match(css, /\.bg-slate-900/, 'classi usate nei moduli JS non generate');
});

test('la pagina contiene i data-testid del contratto', () => {
  const pagina = html();
  for (const id of [
    'nav-season-overview',
    'nav-race-explorer',
    'nav-driver-comparison',
    'nav-team-comparison',
    'nav-race-analysis',
    'footer',
  ]) {
    assert.ok(pagina.includes(`data-testid="${id}"`), `manca data-testid="${id}"`);
  }
});

test('il footer cita la fonte dati e il disclaimer di non affiliazione', () => {
  const footer = html().match(/<footer[\s\S]*<\/footer>/)?.[0] ?? '';
  for (const testo of ['Kaggle', 'Formula 1 World Championship', 'Rohan Rao', 'Ergast', 'non è affiliato', 'FIA']) {
    assert.ok(footer.includes(testo), `nel footer manca "${testo}"`);
  }
});

test('nessuna immagine nella pagina (solo dati testuali)', () => {
  assert.doesNotMatch(html(), /<img\b|<svg\b|<picture\b/i);
});
