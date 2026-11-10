// Driver comparison: due piloti della stessa stagione affiancati, con statistiche, barre di confronto
// e confronto diretto in una gara (tempi sul giro e distacco in pista).

import { api } from '../api.js';
import { areaGrafico, barraFiltri, barreConfronto, campoSelect, caricamento, filtroStagione, grigliaStatistiche, intestazioneVista, legendaSerie, lettera, messaggio, riempiSelect, scheda, svuotaSelect, tabella } from '../componenti.js';
import { el, riempi } from '../dom.js';
import * as formato from '../format.js';
import { disegnaDistacco, disegnaTempi, montaGrafico, smontaGrafico } from '../grafici.js';
import { creaTurni, impostaGara, scegliValido, stato } from '../stato.js';
import { confronto, distaccoCumulato, serieTempi } from '../trasformazioni.js';

const METRICHE = [
  { chiave: 'punti', etichetta: 'Punti (gare + sprint)', valore: (s) => (s ? s.points + s.sprintPoints : null) },
  { chiave: 'wins', etichetta: 'Vittorie' },
  { chiave: 'podiums', etichetta: 'Podi' },
  { chiave: 'poles', etichetta: 'Pole position' },
  { chiave: 'fastestLaps', etichetta: 'Giri veloci' },
];

/** Voci della scheda di un pilota o di una scuderia a partire dalle statistiche dell'API. */
export function vociStatistiche(s) {
  return [
    ['Gare', formato.intero(s.races)],
    ['Partenze', formato.intero(s.starts)],
    ['Vittorie', formato.intero(s.wins)],
    ['Podi', formato.intero(s.podiums)],
    ['Pole', formato.intero(s.poles)],
    ['Giri veloci', formato.intero(s.fastestLaps)],
    ['Ritiri', formato.intero(s.retirements)],
    ['Punti in gara', formato.punti(s.points)],
    ['Punti sprint', formato.punti(s.sprintPoints)],
    ['Miglior arrivo', formato.posizione(s.bestFinish)],
    ['Media arrivo', formato.media(s.averageFinish)],
    ['Media griglia', formato.media(s.averageGrid)],
  ];
}

export function monta(radice, ctx) {
  const turniStagione = creaTurni();
  const turniStatistiche = creaTurni();
  const turniGara = creaTurni();
  let piloti = [];
  let classifica = [];
  let gare = [];

  const filtri = {
    a: campoSelect({ etichetta: 'Pilota A', testid: 'filtro-pilota-a' }),
    b: campoSelect({ etichetta: 'Pilota B', testid: 'filtro-pilota-b' }),
  };
  const schede = {
    a: el('section', { class: 'scheda min-w-0', testid: 'statistiche-pilota-a', 'aria-label': 'Statistiche del pilota A' }),
    b: el('section', { class: 'scheda min-w-0', testid: 'statistiche-pilota-b', 'aria-label': 'Statistiche del pilota B' }),
  };
  for (const lato of ['a', 'b']) {
    svuotaSelect(filtri[lato].select);
    filtri[lato].select.addEventListener('change', () => {
      if (!filtri[lato].select.value) return;
      stato[lato === 'a' ? 'pilotaA' : 'pilotaB'] = Number(filtri[lato].select.value);
      ctx.pulisciErrore();
      aggiornaStatistiche();
      aggiornaGara();
    });
  }

  const barre = scheda({
    titolo: 'Confronto nella stagione',
    nota: 'Ogni barra è divisa in proporzione ai valori dei due piloti; i numeri sono ai lati.',
  });

  const gara = campoSelect({ etichetta: 'Gran Premio', testid: 'filtro-gara', classe: 'min-w-0 sm:min-w-72' });
  svuotaSelect(gara.select);
  gara.select.addEventListener('change', () => {
    if (!gara.select.value) return;
    impostaGara(Number(gara.select.value));
    ctx.pulisciErrore();
    aggiornaGara();
  });
  const inGara = scheda({
    titolo: 'Confronto in una gara',
    nota: 'Risultato, tempi sul giro e distacco in pista dei due piloti nel Gran Premio scelto.',
    azioni: gara.campo,
  });
  const esiti = el('div', {});
  const legenda = el('div', {});
  const graficoTempi = areaGrafico('grafico-confronto-tempi');
  const noteTempi = el('p', { class: 'px-4 pt-1 pb-3 text-xs text-slate-600' });
  const titoloDistacco = el('h3', { class: 'border-t border-slate-200 px-4 pt-3 text-sm font-semibold' }, 'Distacco in pista');
  const notaDistacco = el('p', { class: 'px-4 text-xs text-slate-600' }, 'Differenza tra i tempi cumulati alla fine di ogni giro. I salti corrispondono di solito alle soste ai box.');
  const graficoDistacco = areaGrafico('grafico-confronto-distacco');
  inGara.corpo.append(esiti, legenda, graficoTempi.involucro, noteTempi, titoloDistacco, notaDistacco, graficoDistacco.involucro);

  radice.append(
    intestazioneVista('Driver comparison', 'Due piloti della stessa stagione a confronto: statistiche calcolate dall’API e andamento in una gara.'),
    barraFiltri(filtroStagione(ctx, caricaStagione), filtri.a.campo, filtri.b.campo),
    el('div', { class: 'grid grid-cols-1 gap-5 lg:grid-cols-2' }, schede.a, schede.b),
    barre.sezione,
    inGara.sezione,
  );
  caricaStagione();

  const pilota = (id) => piloti.find((p) => p.id === id);

  function attesa(testo) {
    for (const lato of ['a', 'b']) riempi(schede[lato], messaggio(testo));
    riempi(barre.corpo, messaggio(testo));
  }

  function attesaGara(testo) {
    riempi(esiti);
    riempi(legenda);
    riempi(noteTempi);
    smontaGrafico(graficoTempi.area, testo);
    smontaGrafico(graficoDistacco.area, testo);
  }

  async function caricaStagione() {
    const anno = stato.stagione;
    const turno = turniStagione.nuovo();
    turniStatistiche.nuovo();
    turniGara.nuovo();
    for (const s of [filtri.a.select, filtri.b.select, gara.select]) svuotaSelect(s);
    attesa('Caricamento…');
    attesaGara('Caricamento…');
    try {
      const risposta = await Promise.all([api.seasonDrivers(anno), api.driverStandings(anno), api.races(anno)]);
      if (!turniStagione.valido(turno) || !ctx.attiva()) return;
      [piloti, classifica, gare] = risposta;
    } catch (errore) {
      if (!turniStagione.valido(turno) || !ctx.attiva()) return;
      for (const s of [filtri.a.select, filtri.b.select, gara.select]) svuotaSelect(s, 'Non disponibile');
      attesa('Dati non disponibili.');
      attesaGara('Dati non disponibili.');
      return ctx.errore(errore);
    }
    if (!piloti.length) {
      for (const s of [filtri.a.select, filtri.b.select, gara.select]) svuotaSelect(s, 'Nessun dato');
      attesa('Nessun pilota con risultati in questa stagione.');
      return attesaGara('Nessun dato da mostrare.');
    }
    // All'apertura: i primi due della classifica. Le scelte già fatte restano, se valide per la stagione.
    const ids = piloti.map((p) => p.id);
    const primi = classifica.map((r) => r.driver.id);
    stato.pilotaA = scegliValido(stato.pilotaA, ids, primi);
    stato.pilotaB = scegliValido(stato.pilotaB, ids, primi.filter((id) => id !== stato.pilotaA));
    const opzioni = piloti.map((p) => ({ valore: p.id, etichetta: `${p.familyName} ${p.givenName} · ${p.team.name}` }));
    riempiSelect(filtri.a.select, opzioni, stato.pilotaA);
    riempiSelect(filtri.b.select, opzioni, stato.pilotaB);
    if (gare.length) {
      impostaGara(scegliValido(stato.garaId, gare.map((g) => g.id)));
      riempiSelect(gara.select, gare.map((g) => ({ valore: g.id, etichetta: `${g.round} · ${g.name}` })), stato.garaId);
    } else svuotaSelect(gara.select, 'Nessuna gara');
    aggiornaStatistiche();
    aggiornaGara();
  }

  async function aggiornaStatistiche() {
    const anno = stato.stagione;
    const turno = turniStatistiche.nuovo();
    attesa('Caricamento…');
    try {
      const [a, b] = await Promise.all([api.driverStatistics(stato.pilotaA, anno), api.driverStatistics(stato.pilotaB, anno)]);
      if (!turniStatistiche.valido(turno) || !ctx.attiva()) return;
      mostraScheda('a', a);
      mostraScheda('b', b);
      riempi(
        barre.corpo,
        barreConfronto(confronto(a, b, METRICHE), { nomeA: a.driver.name, nomeB: b.driver.name, formati: { punti: formato.punti } }),
        stato.pilotaA === stato.pilotaB ? el('p', { class: 'px-4 pb-4 text-xs text-slate-600' }, 'Hai scelto lo stesso pilota per A e B.') : null,
      );
    } catch (errore) {
      if (!turniStatistiche.valido(turno) || !ctx.attiva()) return;
      attesa('Statistiche non disponibili.');
      ctx.errore(errore);
    }
  }

  function mostraScheda(lato, s) {
    const anagrafica = pilota(s.driver.id);
    const riga = classifica.find((r) => r.driver.id === s.driver.id);
    const scuderie = anagrafica?.teams?.map((t) => t.name).join(', ');
    riempi(
      schede[lato],
      el(
        'div',
        { class: 'scheda-testa items-start' },
        el(
          'div',
          { class: 'flex min-w-0 items-start gap-3' },
          lettera(lato),
          el(
            'div',
            { class: 'min-w-0' },
            el('h2', { class: 'scheda-titolo' }, s.driver.name),
            el('p', { class: 'secondario' }, [formato.sigla(s.driver), s.driver.nationality, scuderie].filter(Boolean).join(' · ')),
          ),
        ),
        riga
          ? el('p', { class: 'text-right text-sm tabular-nums' }, el('span', { class: 'block font-semibold' }, `${formato.posizione(riga.position)} in classifica`), el('span', { class: 'secondario block' }, `${formato.punti(riga.points)} punti`))
          : null,
      ),
      el('div', { class: 'px-4 py-4' }, grigliaStatistiche(vociStatistiche(s))),
    );
  }

  async function aggiornaGara() {
    const garaId = stato.garaId;
    const idA = stato.pilotaA;
    const idB = stato.pilotaB;
    const turno = turniGara.nuovo();
    if (!garaId || !idA || !idB) return attesaGara('Nessuna gara da confrontare.');
    attesaGara('Caricamento…');
    try {
      const [giriA, giriB, risultati, soste] = await Promise.all([
        api.laps(garaId, idA),
        idA === idB ? Promise.resolve([]) : api.laps(garaId, idB),
        api.raceResults(garaId, 'race'),
        api.pitStops(garaId),
      ]);
      if (!turniGara.valido(turno) || !ctx.attiva()) return;
      mostraGara({ idA, idB, giriA, giriB: idA === idB ? giriA : giriB, risultati, soste });
    } catch (errore) {
      if (!turniGara.valido(turno) || !ctx.attiva()) return;
      attesaGara('Dati della gara non disponibili.');
      ctx.errore(errore);
    }
  }

  function mostraGara({ idA, idB, giriA, giriB, risultati, soste }) {
    const lati = [
      { lato: 'a', id: idA, giri: giriA },
      { lato: 'b', id: idB, giri: giriB },
    ].map((x) => ({ ...x, pilota: pilota(x.id), risultato: risultati.find((r) => r.driver.id === x.id) }));

    riempi(
      esiti,
      tabella({
        didascalia: 'Risultato dei due piloti nella gara scelta',
        righe: lati,
        colonne: [
          { titolo: '', cella: (x) => lettera(x.lato) },
          { titolo: 'Pilota', classe: 'font-medium', cella: (x) => x.pilota?.name ?? formato.VUOTO },
          { titolo: 'Scuderia', cella: (x) => x.risultato?.team.name ?? formato.VUOTO },
          { titolo: 'Griglia', num: true, cella: (x) => x.risultato?.grid ?? formato.VUOTO },
          { titolo: 'Arrivo', num: true, classe: 'font-semibold', cella: (x) => (x.risultato ? formato.posizioneOEsito(x.risultato) : 'Assente') },
          { titolo: 'Tempo / distacco', num: true, classe: 'whitespace-nowrap', cella: (x) => (x.risultato ? formato.tempoODistacco(x.risultato) : formato.VUOTO) },
          { titolo: 'Giri', num: true, cella: (x) => (x.risultato ? formato.intero(x.risultato.laps) : formato.VUOTO) },
          { titolo: 'Punti', num: true, cella: (x) => (x.risultato ? formato.punti(x.risultato.points) : formato.VUOTO) },
          { titolo: 'Giro veloce', num: true, cella: (x) => formato.tempo(x.risultato?.fastestLap?.timeMs) },
        ],
      }),
    );

    const distinti = idA === idB ? lati.slice(0, 1) : lati;
    const pilotiGiri = distinti.map((x) => ({ driver: x.pilota ?? { id: x.id, name: `Pilota ${x.id}` }, team: x.risultato?.team ?? x.pilota?.team, laps: x.giri }));
    const serie = serieTempi(pilotiGiri, { selezionati: distinti.map((x) => x.id), scalaCompleta: stato.scalaCompleta, soste });
    const senzaGiri = lati.filter((x) => x.giri.length === 0).map((x) => x.pilota?.name ?? `Pilota ${x.lato.toUpperCase()}`);
    riempi(noteTempi);
    if (serie.puntiDisegnati === 0) {
      riempi(legenda);
      smontaGrafico(graficoTempi.area, 'Nessuno dei due piloti ha giri cronometrati in questa gara.');
    } else {
      riempi(legenda, legendaSerie(serie.serie));
      montaGrafico(graficoTempi.area, (larghezza) => disegnaTempi(serie, { larghezza, altezza: 320 }));
      const note = [];
      if (serie.fuoriScala > 0) note.push(`${serie.fuoriScala} ${serie.fuoriScala === 1 ? 'giro è' : 'giri sono'} oltre la scala (più di ${formato.tempo(serie.soglia)}) e sono segnati con un triangolo sopra il grafico.`);
      if (senzaGiri.length && idA !== idB) note.push(`${[...new Set(senzaGiri)].join(' e ')}: nessun giro cronometrato in questa gara.`);
      noteTempi.textContent = note.join(' ');
    }

    const distacco = idA === idB ? [] : distaccoCumulato(giriA, giriB);
    if (!distacco.length) {
      const motivo = idA === idB ? 'Scegli due piloti diversi per vedere il distacco.' : 'Distacco non calcolabile: almeno uno dei due piloti non ha giri cronometrati in questa gara.';
      return smontaGrafico(graficoDistacco.area, motivo);
    }
    const [a, b] = lati;
    montaGrafico(graficoDistacco.area, (larghezza) =>
      disegnaDistacco(distacco, { larghezza, siglaA: a.pilota ? formato.sigla(a.pilota) : 'A', siglaB: b.pilota ? formato.sigla(b.pilota) : 'B' }),
    );
  }
}
