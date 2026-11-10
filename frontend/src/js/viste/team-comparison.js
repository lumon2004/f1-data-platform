// Team comparison: due scuderie della stessa stagione affiancate, con statistiche, piloti e barre di confronto.

import { api } from '../api.js';
import { barraFiltri, barreConfronto, campoSelect, filtroStagione, grigliaStatistiche, intestazioneVista, lettera, messaggio, riempiSelect, scheda, svuotaSelect } from '../componenti.js';
import { el, riempi } from '../dom.js';
import * as formato from '../format.js';
import { creaTurni, scegliValido, stato } from '../stato.js';
import { confronto } from '../trasformazioni.js';
import { METRICHE, notaStatistiche, vociStatistiche } from './driver-comparison.js';

// I punti di campionato sono il campo `points` della classifica dell'API (gare + sprint): nessuna somma nel browser.
const METRICHE_SCUDERIA = METRICHE.map((m) => (m.chiave === 'podiums' ? { ...m, etichetta: 'Piazzamenti a podio' } : m));

export function monta(radice, ctx) {
  const turniStagione = creaTurni();
  const turniStatistiche = creaTurni();
  let scuderie = [];
  let classifica = [];
  let piloti = [];

  const filtri = {
    a: campoSelect({ etichetta: 'Scuderia A', testid: 'filtro-scuderia-a' }),
    b: campoSelect({ etichetta: 'Scuderia B', testid: 'filtro-scuderia-b' }),
  };
  const schede = {
    a: el('section', { class: 'scheda min-w-0', testid: 'statistiche-scuderia-a', 'aria-label': 'Statistiche della scuderia A' }),
    b: el('section', { class: 'scheda min-w-0', testid: 'statistiche-scuderia-b', 'aria-label': 'Statistiche della scuderia B' }),
  };
  for (const lato of ['a', 'b']) {
    svuotaSelect(filtri[lato].select);
    filtri[lato].select.addEventListener('change', () => {
      if (!filtri[lato].select.value) return;
      stato[lato === 'a' ? 'scuderiaA' : 'scuderiaB'] = Number(filtri[lato].select.value);
      ctx.pulisciErrore();
      aggiorna();
    });
  }
  const barre = scheda({
    titolo: 'Confronto nella stagione',
    nota: 'Ogni barra è divisa in proporzione ai valori delle due scuderie; i numeri sono ai lati. I podi contano i piazzamenti: due vetture tra i primi tre valgono due.',
  });

  radice.append(
    intestazioneVista('Team comparison', 'Due scuderie della stessa stagione a confronto, su tutte le loro vetture.'),
    barraFiltri(filtroStagione(ctx, caricaStagione), filtri.a.campo, filtri.b.campo),
    el('div', { class: 'grid grid-cols-1 gap-5 lg:grid-cols-2' }, schede.a, schede.b),
    barre.sezione,
  );
  caricaStagione();

  function attesa(testo) {
    for (const lato of ['a', 'b']) riempi(schede[lato], messaggio(testo));
    riempi(barre.corpo, messaggio(testo));
  }

  async function caricaStagione() {
    const anno = stato.stagione;
    const turno = turniStagione.nuovo();
    turniStatistiche.nuovo();
    for (const s of [filtri.a.select, filtri.b.select]) svuotaSelect(s);
    attesa('Caricamento…');
    try {
      const risposta = await Promise.all([api.seasonTeams(anno), api.teamStandings(anno), api.seasonDrivers(anno)]);
      if (!turniStagione.valido(turno) || !ctx.attiva()) return;
      [scuderie, classifica, piloti] = risposta;
    } catch (errore) {
      if (!turniStagione.valido(turno) || !ctx.attiva()) return;
      for (const s of [filtri.a.select, filtri.b.select]) svuotaSelect(s, 'Non disponibile');
      attesa('Dati non disponibili.');
      return ctx.errore(errore);
    }
    if (!scuderie.length) {
      for (const s of [filtri.a.select, filtri.b.select]) svuotaSelect(s, 'Nessun dato');
      return attesa('Nessuna scuderia con risultati in questa stagione.');
    }
    // All'apertura: le prime due della classifica. Le scelte già fatte restano, se valide per la stagione.
    const ids = scuderie.map((t) => t.id);
    const prime = classifica.map((r) => r.team.id);
    stato.scuderiaA = scegliValido(stato.scuderiaA, ids, prime);
    stato.scuderiaB = scegliValido(stato.scuderiaB, ids, prime.filter((id) => id !== stato.scuderiaA));
    const opzioni = scuderie.map((t) => ({ valore: t.id, etichetta: t.name }));
    riempiSelect(filtri.a.select, opzioni, stato.scuderiaA);
    riempiSelect(filtri.b.select, opzioni, stato.scuderiaB);
    aggiorna();
  }

  async function aggiorna() {
    const anno = stato.stagione;
    const turno = turniStatistiche.nuovo();
    attesa('Caricamento…');
    try {
      const [a, b] = await Promise.all([api.teamStatistics(stato.scuderiaA, anno), api.teamStatistics(stato.scuderiaB, anno)]);
      if (!turniStatistiche.valido(turno) || !ctx.attiva()) return;
      mostraScheda('a', a);
      mostraScheda('b', b);
      riempi(
        barre.corpo,
        barreConfronto(
          confronto(
            { statistiche: a, classifica: classifica.find((r) => r.team.id === a.team.id) },
            { statistiche: b, classifica: classifica.find((r) => r.team.id === b.team.id) },
            METRICHE_SCUDERIA,
          ),
          { nomeA: a.team.name, nomeB: b.team.name, formati: { punti: formato.punti } },
        ),
        stato.scuderiaA === stato.scuderiaB ? el('p', { class: 'px-4 pb-4 text-xs text-slate-600' }, 'Hai scelto la stessa scuderia per A e B.') : null,
      );
    } catch (errore) {
      if (!turniStatistiche.valido(turno) || !ctx.attiva()) return;
      attesa('Statistiche non disponibili.');
      ctx.errore(errore);
    }
  }

  function mostraScheda(lato, s) {
    const riga = classifica.find((r) => r.team.id === s.team.id);
    const suoi = piloti.filter((p) => p.teams.some((t) => t.id === s.team.id));
    riempi(
      schede[lato],
      el(
        'div',
        { class: 'scheda-testa items-start' },
        el(
          'div',
          { class: 'flex min-w-0 items-start gap-3' },
          lettera(lato),
          el('div', { class: 'min-w-0' }, el('h2', { class: 'scheda-titolo' }, s.team.name), el('p', { class: 'secondario' }, s.team.nationality ?? 'Nazionalità non riportata')),
        ),
        riga
          ? el('p', { class: 'text-right text-sm tabular-nums' }, el('span', { class: 'block font-semibold' }, `${formato.posizione(riga.position)} in classifica`), el('span', { class: 'secondario block' }, `${formato.punti(riga.points)} punti`))
          : null,
      ),
      el(
        'div',
        { class: 'space-y-4 px-4 py-4' },
        grigliaStatistiche(vociStatistiche(s, 'scuderia')),
        el(
          'div',
          {},
          el('p', { class: 'etichetta' }, 'Piloti nella stagione'),
          el('p', { class: 'text-sm' }, suoi.length ? suoi.map((p) => p.name).join(', ') : formato.VUOTO),
        ),
        el('p', { class: 'text-xs text-slate-600' }, notaStatistiche('scuderia')),
      ),
    );
  }
}
