# IndEng

Simulations à événements discrets (SimPy) de flux d'usine et de règles
d'ordonnancement fondées sur la **Théorie des Contraintes** (TOC / Goldratt).

Le dépôt partait d'un proof-of-concept unique (`Archetype1`, conservé tel quel
dans `examples/legacy/`) et devient un package modulaire `indeng`.

## Installation

```bash
pip install -e .        # package indeng
pip install -e .[dev]   # + pytest
```

## Démarrage rapide

```bash
indeng run config/scenarios/v_minimal.yaml --runs 5 --out out
# ou
python -m indeng run config/scenarios/v_minimal.yaml --runs 5 --out out
# ou
python examples/run_v_minimal.py
```

Produit dans `out/` : `kpis.csv` (un run par ligne), `events.csv`,
`completions.csv`, et les graphiques `gantt.png`, `production.png`,
`utilization.png`.

## Topologie des gammes (Graphviz)

Visualiser la structure V / A / T d'un scénario (postes, gammes par produit,
temps d'opération, goulot surligné) :

```bash
indeng graph config/scenarios/v_minimal.yaml --out out --highlight line_b
# produit out/topology.dot (source Graphviz) et out/topology.svg
```

Le rendu SVG passe par `scripts/render_dot.mjs`, qui utilise **@viz-js/viz**
(Graphviz compilé en WebAssembly, donc pas besoin du binaire `dot` système) :

```bash
npm install @viz-js/viz      # une fois, à la racine du dépôt
```

Exemples prêts à l'emploi : `config/scenarios/v_minimal.yaml` (V),
`a_demo.yaml` (A, convergent), `t_demo.yaml` (T). Les rendus sont versionnés
dans `results/<scenario>/topology.svg` (affichage direct sur GitHub).

## Vocabulaire TOC couvert

- **Archétypes d'usine** : V (un flux amont diverge vers plusieurs lignes
  produit), A (plusieurs composants convergent vers peu de produits),
  T (sous-assemblages convergents puis divergence finale). Seul **V** est
  implémenté ; A et T sont scaffoldés.
- **Goulot / CCR** (Capacity-Constrained Resource) : poste de plus forte
  utilisation, rapporté comme `bottleneck` dans les KPIs.
- **DBR** (Drum-Buffer-Rope) : règle d'ordonnancement scaffoldée
  (`scheduling: dbr`) mais pas encore implémentée.
- **Temps de changement de série** : `setup_default` + `setup_matrix`
  (temps dépendant de la séquence produit -> produit, par poste).

## Architecture

```
config/scenarios/*.yaml   scénarios déclaratifs (topologie, gammes, capacités,
                          setups, demande, règle d'ordonnancement)
indeng/
  config/     chargement + validation des scénarios (YAML -> Scenario)
  domain/     entités : Product, Operation, Workstation, Plant, Job, Scenario
  demand/     générateurs de demande : once, constant, random (Poisson)
  scheduling/ règles d'ordonnancement interchangeables : fifo, spt, edd, dbr*
  archetypes/ archétypes V / A / T (* scaffoldés) -> Plant
  engine/     moteur SimPy : boucle d'événements, files d'attente par poste,
              serveurs = capacity, collecte des événements
  metrics/    KPIs TOC : throughput, WIP moyen (loi de Little), lead time,
              utilisation par poste, goulot, taux de retard
  experiments/ runner Monte-Carlo (N graines -> moyenne / écart-type)
  viz/        Gantt des postes, courbe de production cumulée, utilisation
  cli.py      `indeng run <config> [--runs N] [--out DIR] [--no-plots]`
examples/     run_v_minimal.py + legacy/ (Archetype1 original)
tests/        tests unitaires et scénarios déterministes (graine fixée)
```

## Ajouter un module

1. **Nouvelle règle d'ordonnancement** : sous-classer `SchedulingRule` dans
   `indeng/scheduling/rules.py`, l'ajouter à `RULES`, puis `scheduling: <name>`
   dans le YAML. Aucun changement au moteur.
2. **Nouveau générateur de demande** : sous-classer `DemandGenerator` dans
   `indeng/demand/generators.py`, l'enregistrer dans `GENERATORS`.
3. **Nouvel archétype** : créer `indeng/archetypes/x_plant.py` avec
   `@register("X")` renvoyant un `Plant`, l'importer dans `archetypes/__init__.py`.
4. **Nouveau scénario** : copier `config/scenarios/v_minimal.yaml`, ajuster la
   topologie ; la validation du loader attrape les incohérences (station
   inconnue, produit inconnu, etc.).

## Reproductibilité

Chaque run fixe sa graine (`seed` du scénario + numéro du run), donc un même
scénario donne des résultats identiques. `indeng run ... --runs N` lance un
Monte-Carlo et agrège moyenne / écart-type.

## Tests

```bash
pytest
```
