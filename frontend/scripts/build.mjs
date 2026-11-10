// Build: copia HTML e moduli ES in dist/ e compila Tailwind CSS in dist/styles.css.
import { execFileSync } from 'node:child_process';
import { cpSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'src');
const dist = join(root, 'dist');

rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });
cpSync(join(src, 'index.html'), join(dist, 'index.html'));
cpSync(join(src, 'js'), join(dist, 'js'), { recursive: true });

const tailwind = join(root, 'node_modules', '.bin', 'tailwindcss');
execFileSync(tailwind, ['-i', join(src, 'styles.css'), '-o', join(dist, 'styles.css'), '--minify'], {
  cwd: root,
  stdio: 'inherit',
});

console.log(`Build completata in ${dist}`);
