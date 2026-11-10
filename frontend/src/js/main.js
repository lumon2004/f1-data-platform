// Scheletro della dashboard: navigazione tra viste segnaposto.
// Le viste vere (tappa 5) e i grafici (tappa 6) useranno il client in ./api.js.

const VISTE = {
  'season-overview': 'Season overview',
  'race-explorer': 'Race explorer',
  'driver-comparison': 'Driver comparison',
  'team-comparison': 'Team comparison',
  'race-analysis': 'Race analysis',
};
const VISTA_PREDEFINITA = 'season-overview';

function vistaCorrente() {
  const id = window.location.hash.replace(/^#/, '');
  return Object.hasOwn(VISTE, id) ? id : VISTA_PREDEFINITA;
}

function mostraVista() {
  const id = vistaCorrente();
  const contenitore = document.getElementById('vista');
  contenitore.dataset.vista = id;

  const titolo = document.createElement('h1');
  titolo.className = 'text-2xl font-semibold';
  titolo.textContent = VISTE[id];
  const testo = document.createElement('p');
  testo.className = 'mt-2 text-slate-600';
  testo.textContent = 'Vista in preparazione.';
  contenitore.replaceChildren(titolo, testo);

  for (const link of document.querySelectorAll('[data-view]')) {
    const attivo = link.dataset.view === id;
    link.classList.toggle('bg-slate-900', attivo);
    link.classList.toggle('text-white', attivo);
    link.classList.toggle('hover:bg-slate-100', !attivo);
    if (attivo) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
}

window.addEventListener('hashchange', mostraVista);
mostraVista();
