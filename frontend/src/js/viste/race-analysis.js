// Race analysis: tempi sul giro, posizioni, stint e pit stop della gara scelta.

import { api } from '../api.js';
import { areaGrafico, barraFiltri, campoSelect, filtroStagione, intestazioneVista, legendaSerie, messaggio, riempiSelect, scheda, svuotaSelect, tabella } from '../componenti.js';
import { el, riempi } from '../dom.js';
import * as formato from '../format.js';
import { campioneSerie, disegnaPosizioni, disegnaStint, disegnaTempi, montaGrafico, smontaGrafico } from '../grafici.js';
import { MAX_SERIE } from '../palette.js';
import { creaTurni, impostaGara, scegliValido, stato } from '../stato.js';
import { alternaSelezione, giriLenti, selezionePredefinita, seriePosizioni, serieTempi, stintPerGrafico } from '../trasformazioni.js';

const NOTA_MESCOLE =
  'La fonte dei dati non contiene le mescole: gli stint sono ricavati dai pit stop registrati (tratto tra due soste) e sono solo numerati.';

const elencoGiri = (intervalli) => intervalli.map((i) => (i.da === i.a ? `${i.da}` : `${i.da}–${i.a}`)).join(', ');

export function monta(radice, ctx) {
  const turniStagione = creaTurni();
  const turniGara = creaTurni();
  let gare = [];
  /** Dati della gara caricata: { giri, risultati, soste, stint } oppure null. */
  let dati = null;

  const gara = campoSelect({ etichetta: 'Gran Premio', testid: 'filtro-gara', classe: 'min-w-0 sm:min-w-72' });
  svuotaSelect(gara.select);
  gara.select.addEventListener('change', () => {
    if (!gara.select.value) return;
    impostaGara(Number(gara.select.value));
    ctx.pulisciErrore();
    caricaGara();
  });

  const riepilogo = el('div', { class: 'scheda px-4 py-3' });

  const piloti = scheda({
    titolo: 'Piloti in evidenza',
    nota: `Fino a ${MAX_SERIE} piloti, in ordine d'arrivo. La scelta vale per i tre grafici; all'apertura sono selezionati i primi tre.`,
    azioni: el('button', { type: 'button', class: 'rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50', on: { click: () => seleziona(null) } }, 'Ripristina i primi tre'),
  });

  const scala = el('input', { type: 'checkbox', class: 'h-4 w-4 accent-sky-700' });
  scala.checked = stato.scalaCompleta;
  scala.addEventListener('change', () => {
    stato.scalaCompleta = scala.checked;
    disegnaGraficoTempi();
  });
  const tempi = scheda({
    titolo: 'Tempi sul giro',
    nota: 'Più in basso = giro più veloce. La scala segue il passo di gara: i giri molto più lenti restano segnalati sopra il grafico.',
    azioni: el('label', { class: 'flex items-center gap-2 text-sm' }, scala, 'Scala completa'),
  });
  const graficoTempi = areaGrafico('grafico-tempi-giro');
  const legendaTempi = el('div', {});
  const noteTempi = el('div', { class: 'space-y-1 px-4 pt-2 pb-4 text-xs text-slate-600' });
  tempi.corpo.append(legendaTempi, graficoTempi.involucro, noteTempi);

  const posizioni = scheda({
    titolo: 'Posizioni giro per giro',
    nota: 'Prima posizione in alto; il giro 0 è la griglia di partenza. I piloti non in evidenza sono in grigio, con la sigla a fine linea.',
  });
  const graficoPosizioni = areaGrafico('grafico-posizioni');
  const legendaPosizioni = el('div', {});
  posizioni.corpo.append(legendaPosizioni, graficoPosizioni.involucro);

  const stint = scheda({ titolo: 'Stint e pit stop', nota: 'Una riga per pilota in ordine d’arrivo: segmenti numerati per gli stint, tacca scura per ogni sosta ai box.' });
  const graficoStint = areaGrafico('grafico-stint');
  const notaStint = el('p', { class: 'px-4 pt-1 pb-4 text-xs text-slate-600', testid: 'nota-mescole' }, NOTA_MESCOLE);
  const tabellaSoste = el('div', {});
  stint.corpo.append(graficoStint.involucro, notaStint, tabellaSoste);

  radice.append(
    intestazioneVista('Race analysis', 'Come si è svolta una gara: passo sul giro, cambi di posizione e strategia delle soste.'),
    barraFiltri(filtroStagione(ctx, caricaStagione), gara.campo),
    riepilogo,
    piloti.sezione,
    tempi.sezione,
    posizioni.sezione,
    stint.sezione,
  );
  caricaStagione();

  function azzera(testo) {
    dati = null;
    riempi(riepilogo, el('p', { class: 'text-sm text-slate-600' }, testo));
    riempi(piloti.corpo, messaggio(testo));
    riempi(legendaTempi);
    riempi(legendaPosizioni);
    riempi(noteTempi);
    riempi(tabellaSoste);
    for (const g of [graficoTempi, graficoPosizioni, graficoStint]) smontaGrafico(g.area, testo);
  }

  async function caricaStagione() {
    const anno = stato.stagione;
    const turno = turniStagione.nuovo();
    turniGara.nuovo();
    svuotaSelect(gara.select);
    azzera('Caricamento…');
    try {
      const risposta = await api.races(anno);
      if (!turniStagione.valido(turno) || !ctx.attiva()) return;
      gare = risposta;
    } catch (errore) {
      if (!turniStagione.valido(turno) || !ctx.attiva()) return;
      svuotaSelect(gara.select, 'Non disponibile');
      azzera('Dati non disponibili.');
      return ctx.errore(errore);
    }
    if (!gare.length) {
      svuotaSelect(gara.select, 'Nessuna gara');
      return azzera('Nessun Gran Premio caricato per questa stagione.');
    }
    impostaGara(scegliValido(stato.garaId, gare.map((g) => g.id)));
    riempiSelect(gara.select, gare.map((g) => ({ valore: g.id, etichetta: `${g.round} · ${g.name}` })), stato.garaId);
    caricaGara();
  }

  async function caricaGara() {
    const garaId = stato.garaId;
    const turno = turniGara.nuovo();
    azzera('Caricamento…');
    let giri;
    let risultati;
    try {
      [giri, risultati] = await Promise.all([api.allLaps(garaId), api.raceResults(garaId, 'race')]);
    } catch (errore) {
      if (!turniGara.valido(turno) || !ctx.attiva()) return;
      azzera('Dati non disponibili.');
      return ctx.errore(errore);
    }
    // Soste e stint sono un di più: se mancano, i grafici di tempi e posizioni restano.
    let soste = null;
    let tratti = null;
    let erroreSoste = null;
    try {
      [soste, tratti] = await Promise.all([api.pitStops(garaId), api.stints(garaId)]);
    } catch (errore) {
      erroreSoste = errore;
    }
    if (!turniGara.valido(turno) || !ctx.attiva()) return;
    dati = { giri, risultati, soste, stint: tratti };
    if (erroreSoste) ctx.errore(erroreSoste);
    mostraRiepilogo();
    aggiorna();
    mostraStint();
  }

  function selezione() {
    const conGiri = dati.giri.filter((p) => p.laps.length > 0).map((p) => p.driver.id);
    if (stato.pilotiAnalisi === null) return selezionePredefinita(dati.giri, 3);
    return stato.pilotiAnalisi.filter((id) => conGiri.includes(id));
  }

  function seleziona(nuova) {
    if (!dati) return;
    stato.pilotiAnalisi = nuova;
    aggiorna();
  }

  /** Ridisegna tutto ciò che dipende dalla selezione dei piloti. */
  function aggiorna() {
    mostraPiloti();
    disegnaGraficoTempi();
    disegnaGraficoPosizioni();
    mostraSoste();
  }

  function mostraRiepilogo() {
    const g = gare.find((x) => x.id === stato.garaId);
    const vincitore = dati.risultati.find((r) => r.position === 1);
    const conGiri = dati.giri.filter((p) => p.laps.length > 0).length;
    const voci = [
      ['Vincitore', vincitore ? `${vincitore.driver.name} (${vincitore.team.name})` : formato.VUOTO],
      ['Giri', vincitore ? formato.intero(vincitore.laps) : formato.VUOTO],
      ['Piloti con giri cronometrati', formato.intero(conGiri)],
      ['Soste registrate', dati.soste ? formato.intero(dati.soste.length) : formato.VUOTO],
    ];
    riempi(
      riepilogo,
      el('h2', { class: 'text-lg font-semibold' }, g ? g.name : 'Gara'),
      g ? el('p', { class: 'text-sm text-slate-600' }, `Round ${g.round} · ${formato.data(g.date)} · ${g.circuit.name} (${g.circuit.country})`) : null,
      el('dl', { class: 'mt-3 flex flex-wrap gap-x-8 gap-y-2' }, voci.map(([k, v]) => el('div', {}, el('dt', { class: 'etichetta' }, k), el('dd', { class: 'text-sm font-semibold tabular-nums' }, v)))),
    );
  }

  function mostraPiloti() {
    const scelti = selezione();
    if (!dati.giri.length) return riempi(piloti.corpo, messaggio('Nessun pilota in classifica per questa gara.'));
    riempi(
      piloti.corpo,
      el(
        'ul',
        { class: 'flex flex-wrap gap-2 px-4 py-3' },
        dati.giri.map((p) => {
          const indice = scelti.indexOf(p.driver.id);
          const attivo = indice >= 0;
          const senzaGiri = p.laps.length === 0;
          const casella = el('input', { type: 'checkbox', class: 'sr-only', 'aria-label': `${p.driver.name} (${p.team.name})` });
          casella.checked = attivo;
          casella.disabled = senzaGiri || (!attivo && scelti.length >= MAX_SERIE);
          casella.addEventListener('change', () => seleziona(alternaSelezione(scelti, p.driver.id, MAX_SERIE)));
          return el(
            'li',
            {},
            el(
              'label',
              {
                title: senzaGiri ? `${p.driver.name}: nessun giro cronometrato` : `${p.driver.name} (${p.team.name})`,
                class: [
                  'flex cursor-pointer items-center gap-1.5 rounded-md border px-2 py-1 text-sm tabular-nums has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accento',
                  attivo ? 'border-slate-900 bg-slate-900 font-semibold text-white' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50',
                  casella.disabled ? 'cursor-not-allowed opacity-50' : '',
                ].join(' '),
              },
              casella,
              attivo ? el('span', { class: 'rounded-sm bg-white px-0.5' }, campioneSerie(indice)) : null,
              formato.sigla(p.driver),
            ),
          );
        }),
      ),
    );
  }

  function disegnaGraficoTempi() {
    if (!dati) return;
    const scelti = selezione();
    const serie = serieTempi(dati.giri, { selezionati: scelti, scalaCompleta: stato.scalaCompleta, soste: dati.soste ?? [] });
    riempi(noteTempi);
    if (serie.puntiDisegnati === 0) {
      riempi(legendaTempi);
      const testo = scelti.length ? 'Nessun giro cronometrato per i piloti scelti.' : 'Seleziona almeno un pilota per vedere i tempi sul giro.';
      return smontaGrafico(graficoTempi.area, testo);
    }
    const fasce = giriLenti(dati.giri);
    riempi(legendaTempi, legendaSerie(serie.serie));
    montaGrafico(graficoTempi.area, (larghezza) => disegnaTempi(serie, { larghezza, fasce }));
    if (serie.fuoriScala > 0) {
      noteTempi.append(
        el(
          'p',
          { testid: 'nota-fuori-scala' },
          `${serie.fuoriScala} ${serie.fuoriScala === 1 ? 'giro è' : 'giri sono'} oltre la scala (più di ${formato.tempo(serie.soglia)}): di solito il primo giro, i giri di ingresso e uscita dai box e le neutralizzazioni. Sono segnati con un triangolo sopra il grafico, nella riga del pilota; il tempo esatto è nel suggerimento, oppure attiva "Scala completa".`,
        ),
      );
    }
    if (fasce.length) {
      noteTempi.append(
        el(
          'p',
          {},
          `Fasce grigie: giri lenti per tutto il gruppo (${fasce.length === 1 && fasce[0].da === fasce[0].a ? 'giro' : 'giri'} ${elencoGiri(fasce)}). È una stima ricavata dai tempi: la fonte non registra safety car, bandiere o pioggia.`,
        ),
      );
    }
  }

  function disegnaGraficoPosizioni() {
    if (!dati) return;
    const scelti = selezione();
    const serie = seriePosizioni(dati.giri, dati.risultati);
    if (serie.puntiDisegnati === 0) {
      riempi(legendaPosizioni);
      return smontaGrafico(graficoPosizioni.area, 'Nessuna posizione giro per giro per questa gara.');
    }
    const evidenza = scelti.map((id, indice) => ({ ...serie.serie.find((s) => s.id === id), indice })).filter((s) => s.id !== undefined);
    riempi(legendaPosizioni, evidenza.length ? legendaSerie(evidenza) : null);
    montaGrafico(graficoPosizioni.area, (larghezza) => disegnaPosizioni(serie, scelti, { larghezza }));
  }

  function mostraStint() {
    if (dati.soste === null || dati.stint === null) {
      notaStint.hidden = true;
      return smontaGrafico(graficoStint.area, 'Stint e pit stop non disponibili: la richiesta all’API non è riuscita.');
    }
    if (dati.soste.length === 0 && dati.stint.length === 0) {
      notaStint.hidden = true;
      return smontaGrafico(graficoStint.area, 'Dati su stint e pit stop non disponibili per questa gara: la fonte non riporta soste.');
    }
    notaStint.hidden = false;
    const preparati = stintPerGrafico(dati.stint, dati.soste);
    montaGrafico(graficoStint.area, (larghezza) => disegnaStint(preparati, { larghezza }));
  }

  function mostraSoste() {
    if (!dati.soste || dati.soste.length === 0) return riempi(tabellaSoste);
    const scelti = selezione();
    const righe = dati.soste.filter((s) => scelti.includes(s.driver.id)).sort((a, b) => scelti.indexOf(a.driver.id) - scelti.indexOf(b.driver.id) || a.stop - b.stop);
    riempi(
      tabellaSoste,
      el('h3', { class: 'border-t border-slate-200 px-4 pt-3 pb-1 text-sm font-semibold' }, 'Soste dei piloti in evidenza'),
      righe.length
        ? tabella({
            didascalia: 'Soste ai box dei piloti in evidenza',
            righe,
            colonne: [
              { titolo: 'Pilota', cella: (s) => s.driver.name },
              { titolo: 'Sosta', num: true, cella: (s) => s.stop },
              { titolo: 'Giro', num: true, cella: (s) => s.lap },
              { titolo: 'Durata in pit lane', num: true, cella: (s) => formato.durataSosta(s.durationMs) },
              { titolo: 'Ora locale', num: true, cella: (s) => s.timeOfDay ?? formato.VUOTO },
            ],
          })
        : messaggio('Nessuna sosta registrata per i piloti in evidenza.'),
    );
  }
}
