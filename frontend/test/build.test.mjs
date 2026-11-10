// Test sulla build: `npm test` esegue prima `npm run build` (pretest).
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

const dist = join(dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const html = () => readFileSync(join(dist, 'index.html'), 'utf8');

function fileIn(cartella) {
  return readdirSync(cartella).flatMap((nome) => {
    const percorso = join(cartella, nome);
    return statSync(percorso).isDirectory() ? fileIn(percorso) : [percorso];
  });
}

test('la build produce pagina, moduli, CSS compilato, libreria dei grafici e caratteri', () => {
  for (const nome of [
    'index.html',
    'styles.css',
    'js/main.js',
    'js/api.js',
    'js/grafici.js',
    'js/viste/season-overview.js',
    'js/viste/race-explorer.js',
    'js/viste/driver-comparison.js',
    'js/viste/team-comparison.js',
    'js/viste/race-analysis.js',
    'vendor/d3.min.js',
    'vendor/plot.umd.min.js',
    'vendor/d3.LICENSE.txt',
    'vendor/plot.LICENSE.txt',
    'fonts/inter-latin-wght-normal.woff2',
    'fonts/inter.LICENSE.txt',
  ]) {
    assert.ok(existsSync(join(dist, nome)), `manca dist/${nome}`);
  }
  const css = readFileSync(join(dist, 'styles.css'), 'utf8');
  assert.ok(!css.includes('@import "tailwindcss"'), 'CSS non compilato');
  assert.match(css, /\.min-h-screen/, 'classi di utilità non generate');
  // classi applicate solo dai moduli JS: devono essere rilevate anche lì
  assert.match(css, /\.bg-slate-900/, 'classi usate nei moduli JS non generate');
  assert.match(css, /\.barra-b/, 'classi dei componenti non generate');
});

test('la pagina contiene i data-testid fissi del contratto, ciascuno una sola volta', () => {
  const pagina = html();
  for (const id of [
    'nav-season-overview',
    'nav-race-explorer',
    'nav-driver-comparison',
    'nav-team-comparison',
    'nav-race-analysis',
    'errore-api',
    'footer',
  ]) {
    assert.equal(pagina.split(`data-testid="${id}"`).length - 1, 1, `data-testid="${id}" deve comparire una volta`);
  }
});

test('i data-testid dei filtri e dei grafici sono nei moduli delle viste', () => {
  const sorgenti = fileIn(join(dist, 'js')).map((f) => readFileSync(f, 'utf8')).join('\n');
  for (const id of [
    'filtro-stagione',
    'filtro-gara',
    'filtro-sessione',
    'filtro-pilota-a',
    'filtro-pilota-b',
    'filtro-scuderia-a',
    'filtro-scuderia-b',
    'lista-gare',
    'gara',
    'risultati-gara',
    'riga-risultato',
    'grafico-tempi-giro',
    'grafico-posizioni',
    'statistiche-pilota-a',
    'statistiche-pilota-b',
  ]) {
    assert.ok(sorgenti.includes(`'${id}'`), `manca il data-testid ${id}`);
  }
});

test('il footer cita la fonte dati e il disclaimer di non affiliazione', () => {
  const footer = html().match(/<footer[\s\S]*<\/footer>/)?.[0] ?? '';
  for (const testo of ['Kaggle', 'Formula 1 World Championship (1950 - 2024)', 'Rohan Rao', 'Ergast', 'non affiliato', 'FIA', 'non ufficiale']) {
    assert.ok(footer.includes(testo), `nel footer manca "${testo}"`);
  }
});

test('nessuna immagine nella pagina (solo dati testuali)', () => {
  assert.doesNotMatch(html(), /<img\b|<svg\b|<picture\b/i);
  const immagini = fileIn(dist).filter((f) => /\.(png|jpe?g|gif|webp|avif|svg|ico)$/i.test(f));
  assert.deepEqual(immagini, [], 'la build non deve contenere file di immagine');
});

test('nessuna risorsa esterna: script, stili e caratteri sono serviti dalla dashboard', () => {
  const pagina = html();
  for (const [, url] of pagina.matchAll(/<(?:script|link)\b[^>]*?(?:src|href)="([^"]+)"/g)) {
    assert.ok(!/^(https?:)?\/\//.test(url), `risorsa esterna nella pagina: ${url}`);
  }
  const css = readFileSync(join(dist, 'styles.css'), 'utf8');
  assert.doesNotMatch(css, /url\(\s*["']?(https?:)?\/\//, 'URL esterno nel CSS');
  assert.doesNotMatch(css, /@import\s+url/, 'import esterno nel CSS');
  for (const f of fileIn(join(dist, 'js'))) {
    const sorgente = readFileSync(f, 'utf8');
    assert.doesNotMatch(sorgente, /from\s+['"]https?:/, `import esterno in ${f}`);
    // i dati dell'API entrano nel DOM solo come testo
    assert.doesNotMatch(sorgente, /\.innerHTML|insertAdjacentHTML|document\.write/, `HTML dinamico in ${f}`);
  }
});

test('i moduli importati esistono tutti nella build', () => {
  for (const f of fileIn(join(dist, 'js'))) {
    for (const [, relativo] of readFileSync(f, 'utf8').matchAll(/from\s+'(\.[^']+)'/g)) {
      assert.ok(existsSync(join(dirname(f), relativo)), `${f} importa ${relativo}, che non esiste`);
    }
  }
});
