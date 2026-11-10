// Season overview: indicatori della stagione, calendario con vincitori, classifiche piloti e costruttori.

import { api } from '../api.js';
import { barraFiltri, caricamento, dueRighe, filtroStagione, indicatore, intestazioneVista, messaggio, scheda, tabella } from '../componenti.js';
import { el, riempi } from '../dom.js';
import * as formato from '../format.js';
import { creaTurni, impostaGara, stato } from '../stato.js';

export function monta(radice, ctx) {
  const turni = creaTurni();
  const indicatori = el('div', { class: 'grid grid-cols-2 gap-3 lg:grid-cols-4' });
  const calendario = scheda({
    titolo: 'Calendario e vincitori',
    nota: 'Scegli un Gran Premio per aprirne i risultati nel Race explorer.',
    classe: 'lg:col-span-7',
  });
  const piloti = scheda({
    titolo: 'Classifica piloti',
    nota: 'Punti di gare e sprint, calcolati dai risultati caricati.',
    classe: 'lg:col-span-5',
  });
  const costruttori = scheda({
    titolo: 'Classifica costruttori',
    nota: 'La barra mostra i punti rispetto alla prima scuderia: tinta piena per le gare, righe per le sprint.',
    classe: 'lg:col-span-12',
  });

  radice.append(
    intestazioneVista('Season overview', 'Il quadro di una stagione: calendario, vincitori e classifiche aggiornate all’ultima gara caricata.'),
    barraFiltri(filtroStagione(ctx, carica)),
    indicatori,
    el('div', { class: 'grid grid-cols-1 gap-5 lg:grid-cols-12' }, calendario.sezione, piloti.sezione, costruttori.sezione),
  );
  carica();

  async function carica() {
    const anno = stato.stagione;
    const turno = turni.nuovo();
    riempi(indicatori);
    for (const s of [calendario, piloti, costruttori]) riempi(s.corpo, caricamento());
    try {
      const [gare, classificaPiloti, classificaScuderie] = await Promise.all([
        api.races(anno),
        api.driverStandings(anno),
        api.teamStandings(anno),
      ]);
      if (!turni.valido(turno) || !ctx.attiva()) return;
      mostraIndicatori(anno, gare, classificaPiloti, classificaScuderie);
      mostraCalendario(gare);
      mostraPiloti(classificaPiloti);
      mostraCostruttori(classificaScuderie);
    } catch (errore) {
      if (!turni.valido(turno) || !ctx.attiva()) return;
      for (const s of [calendario, piloti, costruttori]) riempi(s.corpo, messaggio('Dati non disponibili.'));
      ctx.errore(errore);
    }
  }

  function mostraIndicatori(anno, gare, classificaPiloti, classificaScuderie) {
    const stagione = stato.stagioni.find((s) => s.year === anno);
    const primo = classificaPiloti[0];
    const prima = classificaScuderie[0];
    const disputate = gare.filter((g) => g.winner).length;
    riempi(
      indicatori,
      indicatore(
        'Gran Premi',
        formato.intero(stagione?.races ?? gare.length),
        `${formato.intero(disputate)} con risultati · ${formato.intero(stagione?.sprints ?? gare.filter((g) => g.hasSprint).length)} con sprint`,
      ),
      indicatore('Periodo', `${formato.dataCorta(stagione?.firstRaceDate ?? gare[0]?.date)} – ${formato.dataCorta(stagione?.lastRaceDate ?? gare.at(-1)?.date)}`, String(anno)),
      indicatore('Primo in classifica piloti', primo ? primo.driver.name : formato.VUOTO, primo ? `${formato.punti(primo.points)} punti · ${primo.team.name}` : null),
      indicatore('Prima in classifica costruttori', prima ? prima.team.name : formato.VUOTO, prima ? `${formato.punti(prima.points)} punti · ${formato.intero(prima.wins)} vittorie` : null),
    );
  }

  function mostraCalendario(gare) {
    if (!gare.length) return riempi(calendario.corpo, messaggio('Nessun Gran Premio caricato per questa stagione.'));
    riempi(
      calendario.corpo,
      tabella({
        didascalia: 'Calendario della stagione con i vincitori',
        righe: gare,
        colonne: [
          { titolo: 'Round', num: true, cella: (g) => g.round },
          { titolo: 'Data', classe: 'whitespace-nowrap', cella: (g) => formato.dataCorta(g.date) },
          {
            titolo: 'Gran Premio',
            cella: (g) => [
              el(
                'a',
                {
                  href: '#race-explorer',
                  class: 'font-medium text-accento hover:underline',
                  on: { click: () => impostaGara(g.id) },
                },
                g.name,
              ),
              g.hasSprint ? el('span', { class: 'etichetta-tag' }, 'Sprint') : null,
              el('span', { class: 'secondario block' }, [g.circuit.name, g.circuit.country].filter(Boolean).join(' · ')),
            ],
          },
          {
            titolo: 'Vincitore',
            cella: (g) => (g.winner ? dueRighe(g.winner.driver.name, g.winner.team.name) : el('span', { class: 'secondario' }, 'Nessun risultato')),
          },
        ],
      }),
    );
  }

  function mostraPiloti(classifica) {
    if (!classifica.length) return riempi(piloti.corpo, messaggio('Nessun risultato caricato per questa stagione.'));
    riempi(
      piloti.corpo,
      tabella({
        didascalia: 'Classifica piloti',
        righe: classifica,
        colonne: [
          { titolo: 'Pos.', num: true, cella: (r) => r.position },
          { titolo: 'Pilota', cella: (r) => dueRighe(r.driver.name, r.team.name) },
          { titolo: 'Punti', num: true, classe: 'font-semibold', cella: (r) => formato.punti(r.points) },
          { titolo: 'Vitt.', num: true, cella: (r) => formato.intero(r.wins) },
          { titolo: 'Podi', num: true, cella: (r) => formato.intero(r.podiums) },
        ],
      }),
    );
  }

  function mostraCostruttori(classifica) {
    if (!classifica.length) return riempi(costruttori.corpo, messaggio('Nessun risultato caricato per questa stagione.'));
    const massimo = Math.max(...classifica.map((r) => r.points), 1);
    const quota = (v) => `width:${((Math.max(v, 0) / massimo) * 100).toFixed(2)}%`;
    riempi(
      costruttori.corpo,
      tabella({
        didascalia: 'Classifica costruttori',
        righe: classifica,
        colonne: [
          { titolo: 'Pos.', num: true, cella: (r) => r.position },
          { titolo: 'Scuderia', classe: 'font-medium whitespace-nowrap', cella: (r) => r.team.name },
          { titolo: 'Punti', num: true, classe: 'font-semibold', cella: (r) => formato.punti(r.points) },
          {
            titolo: 'Gare + sprint',
            classe: 'w-1/2 align-middle',
            cella: (r) =>
              el(
                'span',
                {
                  class: 'flex h-3 w-full min-w-32 overflow-hidden rounded-sm bg-slate-100',
                  role: 'img',
                  'aria-label': `${formato.punti(r.racePoints)} punti nelle gare, ${formato.punti(r.sprintPoints)} nelle sprint`,
                },
                el('span', { class: 'h-full bg-slate-600', style: quota(r.racePoints) }),
                el('span', { class: 'barra-sprint h-full', style: quota(r.sprintPoints) }),
              ),
          },
          { titolo: 'Gare', num: true, cella: (r) => formato.punti(r.racePoints) },
          { titolo: 'Sprint', num: true, cella: (r) => formato.punti(r.sprintPoints) },
          { titolo: 'Vitt.', num: true, cella: (r) => formato.intero(r.wins) },
          { titolo: 'Podi', num: true, cella: (r) => formato.intero(r.podiums) },
        ],
      }),
    );
  }
}
