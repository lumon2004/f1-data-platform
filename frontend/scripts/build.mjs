// Build: copia HTML e moduli ES in dist/, compila Tailwind CSS in dist/styles.css e copia da node_modules
// la libreria dei grafici e i caratteri (con le licenze), così la dashboard non dipende da nessuna CDN.
import { execFileSync } from 'node:child_process';
import { cpSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'src');
const dist = join(root, 'dist');
const moduli = join(root, 'node_modules');

// [origine in node_modules, destinazione in dist]
const TERZE_PARTI = [
  ['d3/dist/d3.min.js', 'vendor/d3.min.js'],
  ['d3/LICENSE', 'vendor/d3.LICENSE.txt'],
  ['@observablehq/plot/dist/plot.umd.min.js', 'vendor/plot.umd.min.js'],
  ['@observablehq/plot/LICENSE', 'vendor/plot.LICENSE.txt'],
  ['@fontsource-variable/inter/files/inter-latin-wght-normal.woff2', 'fonts/inter-latin-wght-normal.woff2'],
  ['@fontsource-variable/inter/files/inter-latin-ext-wght-normal.woff2', 'fonts/inter-latin-ext-wght-normal.woff2'],
  ['@fontsource-variable/inter/LICENSE', 'fonts/inter.LICENSE.txt'],
];

rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });
cpSync(join(src, 'index.html'), join(dist, 'index.html'));
cpSync(join(src, 'js'), join(dist, 'js'), { recursive: true });
for (const [origine, destinazione] of TERZE_PARTI) {
  mkdirSync(dirname(join(dist, destinazione)), { recursive: true });
  cpSync(join(moduli, origine), join(dist, destinazione));
}

const tailwind = join(root, 'node_modules', '.bin', 'tailwindcss');
execFileSync(tailwind, ['-i', join(src, 'styles.css'), '-o', join(dist, 'styles.css'), '--minify'], {
  cwd: root,
  stdio: 'inherit',
});

console.log(`Build completata in ${dist}`);
