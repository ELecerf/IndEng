// Rejoue hors navigateur l'expérience Monte-Carlo du simulateur S-DBR autonome.
// La logique de simulation est extraite telle quelle du <script> du fichier HTML
// (source unique de vérité), puis exécutée sous Node.
//
// Usage :
//   node sdbr-mini-usine/scripts/run_montecarlo.mjs [--html <chemin.html>] [--out <dir>] [--reps N]
//
// Produit dans <out> (défaut : ../results) :
//   montecarlo_replications.csv  (une ligne par réplication x politique)
//   montecarlo_summary.csv       (moyenne ± demi-largeur IC 95 % par scénario x indicateur)
//   montecarlo_summary.md        (tableaux Markdown prêts à copier)

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
function argValue(name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : fallback;
}
const HTML = path.resolve(argValue('--html', path.join(here, '..', 'simulateur-sdbr-mini-usine.html')));
const OUT = path.resolve(argValue('--out', path.join(here, '..', 'results')));
const REPS = Number(argValue('--reps', '30'));

const html = fs.readFileSync(HTML, 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) throw new Error('Bloc <script> introuvable dans ' + HTML);
const factory = new Function(
  m[1] + '\n;return { rng, gauss, ganttOrders, ganttRun, ganttMonteCarlo, penetration, zoneOf, bufferRule, curveMetrics };'
);
const sim = factory();

const NAMES = ['Préparation', 'Usinage', 'Finition'];
const MEAN_WORK = [1.75, 5.25, 2]; // durée standard moyenne par poste + setup/2 géré à part
const SETUP = 1;
const REQUESTED_LEAD = 120; // délai moyen demandé par les clients (champ du panneau MC)
const COUNT = 120;          // OF mesurés par réplication (champ "OF mesurés")
const WARMUP = 150;         // warm-up en heures (champ "Warm-up")
const BASE_SEED = 42;       // graine du panneau MC

// Politiques comparées par le panneau MC du HTML : [label, lancement immédiat, règle]
const POLICIES = [
  ['A · Immédiat/FIFO', true, 'fifo'],
  ['B · Fenêtre/FIFO', false, 'fifo'],
  ['C · Fenêtre/tampon', false, 'buffer'],
];

function baseOpt(buffer) {
  return {
    requestedLeadMean: REQUESTED_LEAD,
    promiseLead: 90,
    buffer,
    setup: SETUP,
    rule: 'buffer',
    fixed: false,
    capacity: false,
  };
}

function quantile(sorted, p) {
  if (!sorted.length) return null;
  return sorted[Math.min(sorted.length - 1, Math.ceil(p * sorted.length) - 1)];
}

// Miroir de ganttMonteCarlo() du HTML, enrichi : encours total (carnet + atelier)
// et délai client (expédition - arrivée).
function monteCarlo(seed, opt, rate, warmup, count) {
  const orders = sim.ganttOrders(seed, count + Math.ceil(rate * warmup * 2) + 32, opt.requestedLeadMean, rate);
  const last = orders.findIndex((o, i) => i >= count - 1 && orders[i - count + 1].arrival >= warmup);
  if (last < 0) throw new Error('Prolonger la génération des arrivées.');
  const end = orders[last].arrival, duration = end - warmup;
  const run = sim.ganttRun(orders.slice(0, last + 1), opt, Infinity);
  const cohort = run.jobs.slice(-count), shipped = cohort.filter(j => j.ship != null);
  const portion = (a, b) => Math.max(0, Math.min(end, b) - Math.max(warmup, a));
  const busy = [0, 0, 0], waiting = [0, 0, 0];
  for (const bar of run.bars) {
    busy[bar.p] += portion(bar.start, bar.end);
    waiting[bar.p] += portion(bar.start - bar.wait, bar.start);
  }
  const offered = [0, 1, 2].map(p => 100 * cohort.reduce((s, j) => s + j.actual[p] + opt.setup / 2, 0) / duration);
  const delays = shipped.map(j => j.ship - j.release).sort((a, b) => a - b);
  const leads = shipped.map(j => j.ship - j.arrival).sort((a, b) => a - b);
  return {
    otd: 100 * shipped.filter(j => j.ship <= j.due).length / (cohort.filter(j => j.due != null).length || 1),
    promised: cohort.filter(j => j.due != null).length,
    service: 100 * shipped.filter(j => j.ship <= j.requested).length / count,
    red: 100 * shipped.filter(j => j.ship > j.due - opt.buffer / 3).length / (shipped.length || 1),
    wip: run.jobs.reduce((a, j) => a + (j.release == null ? 0 : portion(j.release, j.ship ?? Infinity)), 0) / duration,
    wip_total: run.jobs.reduce((a, j) => a + portion(j.arrival, j.ship ?? Infinity), 0) / duration,
    throughput: run.jobs.filter(j => j.ship > warmup && j.ship <= end).length / duration,
    delays, lead_p50: quantile(leads, 0.5), lead_p90: quantile(leads, 0.9),
    busy: busy.map(v => 100 * v / duration), waiting: waiting.map(v => v / duration), offered,
  };
}

function runReplication(replicationSeed, opt, rate) {
  const result = monteCarlo(replicationSeed, { ...opt }, rate, WARMUP, COUNT);
  const fifo = monteCarlo(replicationSeed, { ...opt, rule: 'fifo' }, rate, WARMUP, COUNT);
  const paired = POLICIES.map(([, immediate, rule]) =>
    monteCarlo(replicationSeed, { ...opt, capacity: false, immediate, rule }, rate, WARMUP, COUNT)
  );
  return { result, fifo, paired };
}

function flatten(scenarioLabel, opt, rate, rep, replicationSeed, run, policyLabel, meanTouch) {
  const delays = run.delays.slice().sort((a, b) => a - b);
  const n = delays.length || 1;
  const b = opt.buffer;
  return {
    scenario: scenarioLabel,
    policy: policyLabel,
    rep,
    seed: replicationSeed,
    buffer_h: b,
    rate_OF_per_h: +rate.toFixed(4),
    otd_pct: run.promised ? +run.otd.toFixed(2) : '',
    service_pct: +run.service.toFixed(2),
    red_pct: run.delays.length ? +run.red.toFixed(2) : '',
    wip_OF: +run.wip.toFixed(3),
    wip_total_OF: +run.wip_total.toFixed(3),
    carnet_OF: +(run.wip_total - run.wip).toFixed(3),
    throughput_OF_per_h: +run.throughput.toFixed(4),
    traverse_p50_h: quantile(delays, 0.5) ?? '',
    traverse_p90_h: quantile(delays, 0.9) ?? '',
    delai_client_p50_h: run.lead_p50 ?? '',
    delai_client_p90_h: run.lead_p90 ?? '',
    touch_share_delai_pct: run.lead_p50 ? +(100 * meanTouch / run.lead_p50).toFixed(1) : '',
    frac_dans_1_3_tampon: +(delays.filter(d => d <= b / 3).length / n * 100).toFixed(2),
    frac_dans_2_3_tampon: +(delays.filter(d => d <= 2 * b / 3).length / n * 100).toFixed(2),
    charge_offerte_prep_pct: +run.offered[0].toFixed(2),
    charge_offerte_usinage_pct: +run.offered[1].toFixed(2),
    charge_offerte_finition_pct: +run.offered[2].toFixed(2),
    occupation_prep_pct: +run.busy[0].toFixed(2),
    occupation_usinage_pct: +run.busy[1].toFixed(2),
    occupation_finition_pct: +run.busy[2].toFixed(2),
    file_prep_OF: +run.waiting[0].toFixed(3),
    file_usinage_OF: +run.waiting[1].toFixed(3),
    file_finition_OF: +run.waiting[2].toFixed(3),
  };
}

// Moyenne ± demi-largeur d'IC 95 % : même formule que la fonction estimate() du HTML.
function estimate(values) {
  const vals = values.filter(v => v !== '' && v != null && Number.isFinite(+v));
  if (vals.length < 2) return { mean: null, half: null, n: vals.length };
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  const df = vals.length - 1;
  const critical = 1.96 + 2.374 / df + 2.82 / (df * df);
  const half = critical * Math.sqrt(vals.reduce((a, v) => a + (v - mean) ** 2, 0) / df / vals.length);
  return { mean, half, n: vals.length };
}

const rows = [];
function runScenario(scenarioLabel, station, targetPct, buffer) {
  const opt = baseOpt(buffer);
  const rate = targetPct / 100 / (MEAN_WORK[station] + SETUP / 2);
  for (let i = 0; i < REPS; i++) {
    const replicationSeed = (BASE_SEED + Math.imul(i, 0x9e3779b9)) >>> 0;
    const { result, fifo, paired } = runReplication(replicationSeed, opt, rate);
    rows.push(flatten(scenarioLabel, opt, rate, i, replicationSeed, result, 'C · Fenêtre/tampon', meanTouch));
    rows.push(flatten(scenarioLabel, opt, rate, i, replicationSeed, fifo, 'Fenêtre/FIFO (référence)', meanTouch));
    paired.forEach((run, k) => rows.push(flatten(scenarioLabel, opt, rate, i, replicationSeed, run, POLICIES[k][0], meanTouch)));
    if ((i + 1) % 10 === 0) process.stdout.write(`  ${scenarioLabel} : ${i + 1}/${REPS} réplications\n`);
  }
}

// Temps opératoire moyen d'un OF (somme des durées réelles + setup/2), mesuré sur un grand échantillon.
const sampleOrders = sim.ganttOrders(BASE_SEED, 20000, REQUESTED_LEAD, 0.15);
const meanTouch = sampleOrders.reduce((s, o) => s + o.actual.reduce((a, b) => a + b, 0), 0) / sampleOrders.length + SETUP / 2;

console.log(`HTML : ${HTML}`);
console.log(`Touch moyen estimé : ${meanTouch.toFixed(2)} h/OF (hors attente) · ${REPS} réplications x ${COUNT} OF, warm-up ${WARMUP} h`);

// Scénario 1 : balayage de la charge offerte au poste ciblé (goulot = Usinage par défaut), tampon 90 h.
console.log('Scénario 1 : charge offerte au poste Usinage, tampon 90 h');
for (const load of [60, 70, 80, 85, 90, 95, 99]) {
  runScenario(`charge_${load}pct_usinage`, 1, load, 90);
}

// Scénario 2 : balayage du tampon S-DBR à charge 90 % sur Usinage.
console.log('Scénario 2 : tampon S-DBR à charge 90 % sur Usinage');
for (const buffer of [30, 45, 60, 75, 90, 120, 150, 180]) {
  runScenario(`tampon_${buffer}h_charge90`, 1, 90, buffer);
}

// Scénario 3 : quel poste est chargé à 90 % (la vraie contrainte est le poste le plus chargé).
console.log('Scénario 3 : poste ciblé à 90 %, tampon 90 h');
for (const station of [0, 1, 2]) {
  runScenario(`poste_${NAMES[station]}_90pct`, station, 90, 90);
}

fs.mkdirSync(OUT, { recursive: true });

// --- CSV réplications ---
const repCols = Object.keys(rows[0]);
const csvEsc = v => (String(v).includes(',') || String(v).includes('"') || String(v).includes('\n') ? '"' + String(v).replace(/"/g, '""') + '"' : v);
const repCsv = [repCols.join(';')].concat(rows.map(r => repCols.map(c => csvEsc(r[c])).join(';'))).join('\n') + '\n';
fs.writeFileSync(path.join(OUT, 'montecarlo_replications.csv'), repCsv);

// --- Résumé moyenne ± IC95 par scénario x politique x indicateur ---
const INDICATORS = [
  ['otd_pct', 'OTD promis (%)'],
  ['service_pct', 'Service demandé (%)'],
  ['red_pct', '% rouges parmi expédiés'],
  ['wip_OF', 'Encours moyen atelier (OF)'],
  ['wip_total_OF', 'Encours total carnet+atelier (OF)'],
  ['carnet_OF', 'Carnet moyen (OF)'],
  ['throughput_OF_per_h', 'Débit (OF/h)'],
  ['traverse_p50_h', 'Traversée P50 (h)'],
  ['traverse_p90_h', 'Traversée P90 (h)'],
  ['delai_client_p50_h', 'Délai client P50 (h)'],
  ['delai_client_p90_h', 'Délai client P90 (h)'],
  ['touch_share_delai_pct', 'Part du touch dans le délai client P50 (%)'],
  ['frac_dans_1_3_tampon', '% expédiés dans le 1er 1/3 du tampon'],
  ['frac_dans_2_3_tampon', '% expédiés dans les 2/3 du tampon'],
  ['charge_offerte_prep_pct', 'Charge offerte Préparation (%)'],
  ['charge_offerte_usinage_pct', 'Charge offerte Usinage (%)'],
  ['charge_offerte_finition_pct', 'Charge offerte Finition (%)'],
  ['occupation_prep_pct', 'Occupation Préparation (%)'],
  ['occupation_usinage_pct', 'Occupation Usinage (%)'],
  ['occupation_finition_pct', 'Occupation Finition (%)'],
  ['file_prep_OF', 'File moyenne Préparation (OF)'],
  ['file_usinage_OF', 'File moyenne Usinage (OF)'],
  ['file_finition_OF', 'File moyenne Finition (OF)'],
];
const summary = [];
const scenarios = [...new Set(rows.map(r => r.scenario))];
for (const sc of scenarios) {
  const policies = [...new Set(rows.filter(r => r.scenario === sc).map(r => r.policy))];
  for (const pol of policies) {
    const sub = rows.filter(r => r.scenario === sc && r.policy === pol);
    for (const [col, label] of INDICATORS) {
      const e = estimate(sub.map(r => r[col]));
      summary.push({
        scenario: sc, policy: pol, indicateur: label,
        moyenne: e.mean == null ? '' : +e.mean.toFixed(3),
        demi_ic95: e.half == null ? '' : +e.half.toFixed(3),
        n: e.n,
      });
    }
  }
}
const sumCols = Object.keys(summary[0]);
const sumCsv = [sumCols.join(';')].concat(summary.map(r => sumCols.map(c => csvEsc(r[c])).join(';'))).join('\n') + '\n';
fs.writeFileSync(path.join(OUT, 'montecarlo_summary.csv'), sumCsv);

// --- Markdown ---
function fmt(e) { return e.mean == null ? '—' : `${e.mean.toFixed(2)} ± ${e.half.toFixed(2)}`; }
let md = `# Résultats Monte-Carlo — simulateur S-DBR mini-usine\n\n`;
md += `Graine de base ${BASE_SEED} · ${REPS} réplications × ${COUNT} OF mesurés · warm-up ${WARMUP} h · arrivées de Poisson · touch moyen ${meanTouch.toFixed(2)} h/OF (hors attentes).\n\n`;
md += `Valeurs : moyenne ± demi-largeur de l'IC à 95 % (même formule que le panneau du HTML).\n\n`;
for (const sc of scenarios) {
  md += `## ${sc}\n\n`;
  const policies = [...new Set(rows.filter(r => r.scenario === sc).map(r => r.policy))];
  const cols = ['otd_pct', 'service_pct', 'red_pct', 'wip_OF', 'wip_total_OF', 'throughput_OF_per_h', 'traverse_p50_h', 'traverse_p90_h', 'delai_client_p50_h', 'frac_dans_2_3_tampon', 'occupation_usinage_pct'];
  const head = ['Politique', 'OTD %', 'Service %', 'Rouges %', 'Encours atelier OF', 'Encours total OF', 'Débit OF/h', 'Trav. P50 h', 'Trav. P90 h', 'Délai client P50 h', '% dans 2/3 tampon', 'Occup. Usinage %'];
  md += '| ' + head.join(' | ') + ' |\n| ' + head.map(() => '---').join(' | ') + ' |\n';
  for (const pol of policies) {
    const sub = rows.filter(r => r.scenario === sc && r.policy === pol);
    const cell = c => fmt(estimate(sub.map(r => r[c])));
    md += `| ${pol} | ${cols.map(cell).join(' | ')} |\n`;
  }
  md += '\n';
}

md += `## Règle des 5–10 % de rouges (gestion du tampon, politique C)\n\n`;
md += 'Verdict identique à la fonction `bufferRule()` du HTML : < 5 % de rouges → réduire le tampon, > 10 % → allonger, sinon conserver.\n\n';
md += '| Tampon (h) | OTD % | Rouges % | % dans 1er 1/3 | % dans 2/3 | Verdict règle 5–10 % |\n| --- | --- | --- | --- | --- | --- |\n';
for (const sc of scenarios.filter(s => s.startsWith('tampon_'))) {
  const sub = rows.filter(r => r.scenario === sc && r.policy.startsWith('C'));
  const g = c => estimate(sub.map(r => r[c]));
  const red = g('red_pct');
  const verdict = red.mean == null ? '—' : red.mean < 5 ? 'Réduire le tampon' : red.mean > 10 ? 'Allonger le tampon' : 'Conserver le tampon';
  md += `| ${sub[0].buffer_h} | ${fmt(g('otd_pct'))} | ${fmt(red)} | ${fmt(g('frac_dans_1_3_tampon'))} | ${fmt(g('frac_dans_2_3_tampon'))} | ${verdict} |\n`;
}
md += '\n';

md += `## Politiques de lancement : charge 90 % sur Usinage vs surcharge réelle (poste Préparation ciblé)\n\n`;
md += '| Scénario | Politique | OTD % | Encours atelier OF | Encours total OF | Carnet OF | Débit OF/h | Délai client P50 h |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n';
for (const sc of ['charge_90pct_usinage', 'poste_Préparation_90pct']) {
  for (const pol of ['A · Immédiat/FIFO', 'B · Fenêtre/FIFO', 'C · Fenêtre/tampon']) {
    const sub = rows.filter(r => r.scenario === sc && r.policy === pol);
    const g = c => fmt(estimate(sub.map(r => r[c])));
    md += `| ${sc} | ${pol} | ${g('otd_pct')} | ${g('wip_OF')} | ${g('wip_total_OF')} | ${g('carnet_OF')} | ${g('throughput_OF_per_h')} | ${g('delai_client_p50_h')} |\n`;
  }
}
md += '\n';
md += `## Occupation des trois postes par scénario (politique C · Fenêtre/tampon)\n\n`;
md += '| Scénario | Charge offerte P/U/F (%) | Occupation P/U/F (%) | File moyenne P/U/F (OF) |\n| --- | --- | --- | --- |\n';
for (const sc of scenarios) {
  const sub = rows.filter(r => r.scenario === sc && r.policy.startsWith('C'));
  const g = c => fmt(estimate(sub.map(r => r[c])));
  md += `| ${sc} | ${g('charge_offerte_prep_pct')} / ${g('charge_offerte_usinage_pct')} / ${g('charge_offerte_finition_pct')} | ${g('occupation_prep_pct')} / ${g('occupation_usinage_pct')} / ${g('occupation_finition_pct')} | ${g('file_prep_OF')} / ${g('file_usinage_OF')} / ${g('file_finition_OF')} |\n`;
}
md += '\n';
fs.writeFileSync(path.join(OUT, 'montecarlo_summary.md'), md);

console.log(`\nÉcrit : ${path.join(OUT, 'montecarlo_replications.csv')} (${rows.length} lignes)`);
console.log(`Écrit : ${path.join(OUT, 'montecarlo_summary.csv')} (${summary.length} lignes)`);
console.log(`Écrit : ${path.join(OUT, 'montecarlo_summary.md')}`);
