// Avvio della dashboard: navigazione tra le viste, caricamento delle stagioni, riquadro degli errori dell'API.
// Nel DOM c'è sempre una sola vista: così ogni data-testid dei filtri corrisponde a un solo elemento.

import { api, descriviErrore } from './api.js';
import { intestazioneVista } from './componenti.js';
import { el } from './dom.js';
import { alCambio, impostaStagione, stato } from './stato.js';
import { leggiHash, scriviHash } from './url.js';
import { monta as seasonOverview } from './viste/season-overview.js';
import { monta as raceExplorer } from './viste/race-explorer.js';
import { monta as driverComparison } from './viste/driver-comparison.js';
import { monta as teamComparison } from './viste/team-comparison.js';
import { monta as raceAnalysis } from './viste/race-analysis.js';

const VISTE = {
  'season-overview': { titolo: 'Season overview', monta: seasonOverview },
  'race-explorer': { titolo: 'Race explorer', monta: raceExplorer },
  'driver-comparison': { titolo: 'Driver comparison', monta: driverComparison },
  'team-comparison': { titolo: 'Team comparison', monta: teamComparison },
  'race-analysis': { titolo: 'Race analysis', monta: raceAnalysis },
};
const VISTA_PREDEFINITA = 'season-overview';

const radice = document.getElementById('vista');
const riquadroErrore = document.getElementById('errore-api');
const titoloErrore = document.getElementById('errore-api-titolo');
const testoErrore = document.getElementById('errore-api-testo');

let generazione = 0;
let caricamentoStagioni = null;

function vistaCorrente() {
  return leggiHash(window.location.hash).vista ?? VISTA_PREDEFINITA;
}

/**
 * Porta nello stato le scelte scritte nell'URL (link condiviso, ricaricamento, tasto "indietro").
 * Qui si controlla solo la stagione; gara, piloti e scuderie li convalida la vista rispetto ai dati
 * della stagione, ripiegando sui predefiniti se non esistono.
 */
function applicaUrl() {
  const { scelte } = leggiHash(window.location.hash);
  if (stato.stagioni.some((s) => s.year === scelte.stagione)) impostaStagione(scelte.stagione);
  for (const [chiave, valore] of Object.entries(scelte)) {
    if (chiave !== 'stagione') stato[chiave] = valore;
  }
}

/** Riporta nell'URL le scelte correnti, senza creare voci nella cronologia né far ripartire la vista. */
function aggiornaUrl() {
  if (!stato.stagioni.length) return;
  const atteso = scriviHash(vistaCorrente(), stato);
  if (window.location.hash !== atteso) window.history.replaceState(null, '', atteso);
}

function mostraErrore(errore) {
  const { interno, titolo, testo } = descriviErrore(errore);
  // Un errore che non viene dall'API è un difetto della dashboard: resta visibile anche in console.
  if (interno) console.error(errore);
  titoloErrore.textContent = titolo;
  testoErrore.textContent = testo;
  riquadroErrore.hidden = false;
}

function nascondiErrore() {
  riquadroErrore.hidden = true;
  testoErrore.textContent = '';
}

function segnaNavigazione(id) {
  for (const link of document.querySelectorAll('[data-view]')) {
    const attivo = link.dataset.view === id;
    link.classList.toggle('bg-slate-900', attivo);
    link.classList.toggle('text-white', attivo);
    link.classList.toggle('hover:bg-slate-100', !attivo);
    if (attivo) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
}

/** Carica le stagioni una sola volta; se fallisce, la prossima navigazione o "Riprova" ritenta. */
function caricaStagioni() {
  caricamentoStagioni ??= api
    .seasons()
    .then((stagioni) => {
      stato.stagioni = stagioni;
      stato.stagione = stagioni[0]?.year ?? null;
      // Subito, nello stesso passaggio: altrimenti la stagione predefinita verrebbe riscritta nell'URL
      // prima di aver letto quella richiesta dal link.
      applicaUrl();
      return { ok: true };
    })
    .catch((errore) => {
      caricamentoStagioni = null;
      return { ok: false, errore };
    });
  return caricamentoStagioni;
}

async function mostraVista() {
  const id = vistaCorrente();
  const vista = VISTE[id];
  generazione += 1;
  const mia = generazione;
  segnaNavigazione(id);
  document.title = `${vista.titolo} · F1 Data Platform`;
  nascondiErrore();

  if (!stato.stagioni.length) {
    radice.replaceChildren(intestazioneVista(vista.titolo, 'Caricamento delle stagioni…'));
    const esito = await caricaStagioni();
    if (mia !== generazione) return;
    if (!esito.ok) {
      radice.replaceChildren(intestazioneVista(vista.titolo, 'Nessun dato da mostrare finché l’API non risponde.'));
      return mostraErrore(esito.errore);
    }
    if (!stato.stagioni.length) {
      radice.replaceChildren(
        intestazioneVista(vista.titolo, 'L’API risponde, ma non ci sono stagioni caricate.'),
        el('p', { class: 'scheda messaggio' }, 'Carica i dati con la pipeline (docker compose up esegue il caricamento del dataset di esempio), poi ricarica la pagina.'),
      );
      return;
    }
  }

  applicaUrl();
  radice.replaceChildren();
  const ctx = {
    attiva: () => mia === generazione,
    errore: (errore) => {
      if (mia === generazione) mostraErrore(errore);
    },
    pulisciErrore: nascondiErrore,
  };
  try {
    vista.monta(radice, ctx);
  } catch (errore) {
    mostraErrore(errore);
  }
  aggiornaUrl();
}

alCambio(aggiornaUrl);

// Rete di sicurezza: un'eccezione sfuggita a una vista (anche dentro una promessa) non deve lasciare
// la pagina a metà senza spiegazioni. Compare il riquadro, con il titolo degli errori interni.
window.addEventListener('unhandledrejection', (evento) => {
  evento.preventDefault();
  mostraErrore(evento.reason instanceof Error ? evento.reason : new Error(String(evento.reason)));
});
window.addEventListener('error', (evento) => {
  if (evento.error instanceof Error) mostraErrore(evento.error);
});

document.getElementById('errore-api-riprova').addEventListener('click', () => mostraVista());
window.addEventListener('hashchange', () => mostraVista());
mostraVista();
