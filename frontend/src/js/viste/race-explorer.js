// Race explorer: stagione → elenco delle gare → risultati della gara scelta (gara, qualifica, sprint).

import { api } from '../api.js';
import { barraFiltri, campoSelect, caricamento, dueRighe, filtroStagione, intestazioneVista, messaggio, riempiSelect, scheda, svuotaSelect, tabella } from '../componenti.js';
import { el, riempi } from '../dom.js';
import * as formato from '../format.js';
import { creaTurni, impostaGara, scegliValido, stato } from '../stato.js';

export function monta(radice, ctx) {
  const turniStagione = creaTurni();
  const turniGara = creaTurni();
  let gare = [];

  const sessione = campoSelect({ etichetta: 'Sessione', testid: 'filtro-sessione' });
  svuotaSelect(sessione.select);
  sessione.select.addEventListener('change', () => {
    stato.sessione = sessione.select.value;
    ctx.pulisciErrore();
    caricaRisultati();
  });

  const elenco = el('ol', { class: 'max-h-80 overflow-y-auto py-1 lg:max-h-none', testid: 'lista-gare' });
  const schedaElenco = scheda({ titolo: 'Gran Premi', nota: 'In ordine di round.', classe: 'lg:col-span-4 lg:self-start' });
  schedaElenco.corpo.append(elenco);

  const dettaglio = el('div', { class: 'scheda px-4 py-3' });
  const risultati = scheda({ titolo: 'Risultati' });
  const collegamento = el('a', { href: '#race-analysis', class: 'text-sm font-medium text-accento hover:underline' }, 'Apri in Race analysis');

  radice.append(
    intestazioneVista('Race explorer', 'Scegli una stagione e un Gran Premio per leggerne la classifica di gara, qualifica o sprint.'),
    barraFiltri(filtroStagione(ctx, caricaStagione), sessione.campo),
    el(
      'div',
      { class: 'grid grid-cols-1 gap-5 lg:grid-cols-12' },
      schedaElenco.sezione,
      el('div', { class: 'min-w-0 space-y-5 lg:col-span-8' }, dettaglio, risultati.sezione),
    ),
  );
  caricaStagione();

  async function caricaStagione() {
    const anno = stato.stagione;
    const turno = turniStagione.nuovo();
    turniGara.nuovo();
    gare = [];
    riempi(elenco, el('li', { class: 'messaggio' }, 'Caricamento…'));
    svuotaSelect(sessione.select);
    riempi(dettaglio, el('p', { class: 'text-sm text-slate-600' }, 'Caricamento…'));
    riempi(risultati.corpo, caricamento());
    try {
      const risposta = await api.races(anno);
      if (!turniStagione.valido(turno) || !ctx.attiva()) return;
      gare = risposta;
    } catch (errore) {
      if (!turniStagione.valido(turno) || !ctx.attiva()) return;
      riempi(elenco, el('li', { class: 'messaggio' }, 'Elenco delle gare non disponibile.'));
      riempi(dettaglio, el('p', { class: 'text-sm text-slate-600' }, 'Nessuna gara selezionata.'));
      riempi(risultati.corpo, messaggio('Dati non disponibili.'));
      return ctx.errore(errore);
    }
    if (!gare.length) {
      riempi(elenco, el('li', { class: 'messaggio' }, 'Nessun Gran Premio caricato per questa stagione.'));
      riempi(dettaglio, el('p', { class: 'text-sm text-slate-600' }, 'Nessuna gara selezionata.'));
      riempi(risultati.corpo, messaggio('Nessun risultato da mostrare.'));
      return;
    }
    riempi(
      elenco,
      gare.map((g) =>
        el(
          'li',
          {},
          el(
            'button',
            {
              type: 'button',
              testid: 'gara',
              'data-gara': g.id,
              class:
                'flex w-full items-baseline gap-3 border-l-2 border-transparent px-4 py-2 text-left text-sm hover:bg-slate-50 aria-[current=true]:border-accento aria-[current=true]:bg-slate-100 aria-[current=true]:font-semibold',
              on: { click: () => selezionaGara(g.id) },
            },
            el('span', { class: 'w-5 shrink-0 text-right text-xs text-slate-600 tabular-nums' }, g.round),
            el('span', { class: 'min-w-0 flex-1' }, g.name, g.hasSprint ? el('span', { class: 'etichetta-tag font-normal' }, 'Sprint') : null),
            el('span', { class: 'shrink-0 text-xs font-normal text-slate-600 tabular-nums' }, formato.dataCorta(g.date)),
          ),
        ),
      ),
    );
    selezionaGara(scegliValido(stato.garaId, gare.map((g) => g.id)));
  }

  function selezionaGara(garaId) {
    impostaGara(garaId);
    const gara = gare.find((g) => g.id === garaId);
    for (const bottone of elenco.querySelectorAll('button')) {
      if (bottone.getAttribute('data-gara') === String(garaId)) bottone.setAttribute('aria-current', 'true');
      else bottone.removeAttribute('aria-current');
    }
    if (stato.sessione === 'sprint' && !gara?.hasSprint) stato.sessione = 'race';
    riempiSelect(
      sessione.select,
      [
        { valore: 'race', etichetta: 'Gara' },
        { valore: 'qualifying', etichetta: 'Qualifica' },
        gara?.hasSprint ? { valore: 'sprint', etichetta: 'Sprint' } : null,
      ].filter(Boolean),
      stato.sessione,
    );
    ctx.pulisciErrore();
    caricaRisultati();
  }

  async function caricaRisultati() {
    const garaId = stato.garaId;
    const tipo = stato.sessione;
    const turno = turniGara.nuovo();
    riempi(risultati.corpo, caricamento());
    try {
      const [gara, righe] = await Promise.all([
        api.race(garaId),
        tipo === 'qualifying' ? api.qualifying(garaId) : api.raceResults(garaId, tipo),
      ]);
      if (!turniGara.valido(turno) || !ctx.attiva()) return;
      mostraDettaglio(gara);
      risultati.sezione.querySelector('h2').textContent = `Risultati · ${formato.sessione(tipo)}`;
      if (!righe.length) {
        const vuoto = tipo === 'qualifying' ? 'Nessun dato di qualifica per questa gara.' : 'Nessun risultato caricato per questa sessione.';
        return riempi(risultati.corpo, el('div', { testid: 'risultati-gara' }, messaggio(vuoto)));
      }
      riempi(risultati.corpo, tipo === 'qualifying' ? tabellaQualifica(righe) : tabellaClassifica(righe));
    } catch (errore) {
      if (!turniGara.valido(turno) || !ctx.attiva()) return;
      riempi(risultati.corpo, messaggio('Risultati non disponibili.'));
      ctx.errore(errore);
    }
  }

  function mostraDettaglio(gara) {
    const luogo = [gara.circuit.locality, gara.circuit.country].filter(Boolean).join(', ');
    riempi(
      dettaglio,
      el(
        'div',
        { class: 'flex flex-wrap items-start justify-between gap-x-6 gap-y-2' },
        el(
          'div',
          {},
          el('h2', { class: 'text-lg font-semibold' }, gara.name),
          el('p', { class: 'text-sm text-slate-600' }, `Round ${gara.round} · ${formato.data(gara.date)} · ${gara.circuit.name}${luogo ? ` (${luogo})` : ''}`),
        ),
        collegamento,
      ),
      el(
        'ul',
        { class: 'mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-600', 'aria-label': 'Sessioni del weekend' },
        gara.sessions.map((s) => el('li', {}, el('span', { class: 'font-medium text-slate-900' }, formato.sessione(s.type)), ` ${s.date ? formato.dataCorta(s.date) : 'data non riportata'}`)),
      ),
    );
  }

  function pilota(r) {
    return dueRighe(r.driver.name, [formato.sigla(r.driver), r.carNumber ? `n. ${r.carNumber}` : null].filter(Boolean).join(' · '));
  }

  function tabellaClassifica(righe) {
    return tabella({
      testid: 'risultati-gara',
      testidRiga: 'riga-risultato',
      didascalia: 'Classifica della sessione in ordine di arrivo',
      minimo: 'min-w-[46rem]',
      righe,
      colonne: [
        { titolo: 'Pos.', num: true, classe: 'font-semibold', cella: (r) => el('span', { title: formato.esito(r.outcome) }, formato.posizioneOEsito(r)) },
        { titolo: 'Pilota', cella: pilota },
        { titolo: 'Scuderia', cella: (r) => r.team.name },
        { titolo: 'Griglia', num: true, cella: (r) => (r.grid ?? formato.VUOTO) },
        { titolo: 'Giri', num: true, cella: (r) => formato.intero(r.laps) },
        { titolo: 'Tempo / distacco', num: true, classe: 'whitespace-nowrap', cella: (r) => formato.tempoODistacco(r) },
        { titolo: 'Punti', num: true, classe: 'font-semibold', cella: (r) => formato.punti(r.points) },
        {
          titolo: 'Giro veloce',
          num: true,
          classe: 'whitespace-nowrap',
          cella: (r) =>
            r.fastestLap?.timeMs
              ? [formato.tempo(r.fastestLap.timeMs), r.fastestLap.rank === 1 ? el('span', { class: 'etichetta-tag' }, 'più veloce') : null]
              : formato.VUOTO,
        },
      ],
    });
  }

  function tabellaQualifica(righe) {
    return tabella({
      testid: 'risultati-gara',
      testidRiga: 'riga-risultato',
      didascalia: 'Classifica della qualifica',
      minimo: 'min-w-[34rem]',
      righe,
      colonne: [
        { titolo: 'Pos.', num: true, classe: 'font-semibold', cella: (r) => r.position },
        { titolo: 'Pilota', cella: pilota },
        { titolo: 'Scuderia', cella: (r) => r.team.name },
        { titolo: 'Q1', num: true, cella: (r) => formato.tempo(r.q1Ms) },
        { titolo: 'Q2', num: true, cella: (r) => formato.tempo(r.q2Ms) },
        { titolo: 'Q3', num: true, cella: (r) => formato.tempo(r.q3Ms) },
      ],
    });
  }
}
