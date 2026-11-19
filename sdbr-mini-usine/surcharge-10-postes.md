# Campagne « surcharge » — ligne de 10 postes à goulot central

Scénario : `scenario-surcharge-10-postes.json` · résultats : `results/surcharge-10-postes/`
Moteur : `scripts/run_hypotheses.py` (poussé sur cette branche), 20 graines (42–61),
comparaisons appariées par graine avec IC 95 % (`comparaisons.csv`).

**Question posée** : Goldratt affirme que lancer trop tôt nuit à la performance de
dates (Fig. 1 et boucle « retard → lancer plus tôt → embouteillages », p. 12–14 de
l'article) — est-ce vérifié, et dans quelle mesure, quand on fait varier la
surcapacité du goulot ?

## 1. Protocole

- **Ligne** : 10 postes en série (`poste_1`…`poste_10`), goulot central = `poste_5`
  (index 4). Deux familles A/B : 2 h par poste périphérique, **6 h au goulot** ;
  réglage 1 h hors goulot, 0 au goulot. Lot = 1 (flux unitaire), règle de priorité
  `due` (proche de la priorité par tampon S-DBR). Durées lognormales, CV = 0,3.
- **Demande irrégulière à pics** (charge nominale offerte au goulot, par paliers) :
  creux 0,70 (480 h) → normal 0,95 (480 h) → **pic 1,15 (240 h)** → **gros pic 1,30
  (240 h)** → reprise 0,85 (720 h) ; warm-up 400 h. Promesse client = arrivée +
  U(48, 168) h.
- **Fenêtres de lancement testées** : 36 / 72 / 120 / **168 h** — 168 h ≥ délai client
  max, donc lancement **immédiat** à la réception (la corde est complètement relâchée).
  Lancement = max(arrivée, échéance − fenêtre).
- **Surcapacités du goulot** : ×1 (6 h), ×1,25 (4,8 h), ×1,5 (4 h au poste goulot
  uniquement). Les charges des paliers sont recalibrées (× heures′/6) pour que le
  **taux d'arrivée absolu soit identique** par graine : la demande est la même dans
  les trois variantes, seul le goulot est plus rapide — comparaison appariée pure.

## 2. Résultats (moyennes sur 20 graines)

### OTD global (% livré ≤ promesse)

| Variante (surcapacité goulot) | fenêtre 36 h | 72 h | 120 h | 168 h (immédiat) |
| --- | --- | --- | --- | --- |
| témoin ×1 | 17,4 | 49,2 | 62,8 | 67,5 |
| ×1,25 | 50,7 | 93,1 | 98,3 | 98,5 |
| ×1,5 | 72,3 | 99,4 | 100,0 | 100,0 |

### OTD par phase, témoin ×1 (fenêtres 36 → 168 h)

| Phase (charge offerte goulot mesurée) | 36 h | 72 h | 120 h | 168 h |
| --- | --- | --- | --- | --- |
| creux (0,73) | 49,2 | 94,7 | 99,8 | 100,0 |
| normal (0,99) | 28,9 | 83,5 | 95,3 | 96,8 |
| pic (1,18) | 8,7 | 46,3 | 78,9 | 85,1 |
| **gros pic (1,27)** | **1,4** | **16,3** | **34,2** | **45,4** |
| reprise (0,83) | 5,8 | 19,7 | 28,9 | 34,7 |

Même tableau avec surcapacité ×1,5 : gros pic 53,7 → 97,9 → 100 → 100.

### Deltas appariés d'OTD entre fenêtres (points, IC 95 %, global, témoin ×1)

| passage | Δ OTD | IC 95 % |
| --- | --- | --- |
| 36 → 72 h | **+31,8** | [26,1 ; 37,5] |
| 72 → 120 h | **+13,6** | [10,3 ; 16,9] |
| 120 → 168 h (immédiat) | **+4,7** | [2,6 ; 6,8] |

### Encours, conflits et récupération (témoin ×1)

| fenêtre | encours atelier global | encours max (pic) | carnet global | conflits (démarrage vert devant un rouge) | évacuation carnet après pic | récupération OTD après pic |
| --- | --- | --- | --- | --- | --- | --- |
| 36 h | 14,0 OF | 33,8 | 11,0 | ~0 | 278 h | 588 h |
| 72 h | 14,1 OF | 33,6 | 5,8 | ~0 | 244 h | 432 h |
| 120 h | 14,2 OF | 33,4 | 1,5 | 0,10 | 215 h | 427 h |
| 168 h (immédiat) | 14,2 OF | 34,0 | **0** | **0,55** | 205 h | 394 h |

Avec surcapacité ×1,5 : encours global 5,2 OF, max ~15 OF, retard P95 ≈ 0 pour les
fenêtres ≥ 120 h ; aucun palier ne dépasse 100 % de charge, donc les métriques de
récupération ne s'appliquent pas (le « pic » n'en est plus un).

## 3. Réponse à la question : lancer trop tôt nuit-il à l'OTD ?

**En partie seulement — et le résultat dépend de qui fixe la promesse.**

1. **Dans ce modèle (promesse = délai demandé par le client, U(48,168) h), lancer
   plus tôt n'abîme jamais l'OTD : elle augmente significativement à chaque pas de
   fenêtre (+31,8, +13,6, +4,7 points, IC 95 % excluant 0)**, avec rendements
   décroissants. Mécanisme : chaque OF a plus de marge (échéance − lancement) avant
   sa promesse. Le coût du lancement immédiat n'est pas dans l'OTD mais dans
   l'**encours max (~34 OF au goulot), les conflits « vert devant rouge » (×5 à ×∞
   vs fenêtres courtes) et la traversée P95 (199 h vs 179 h)** — c'est le versant
   droit de la Fig. 1 de Goldratt (p. 12–14) : embouteillages et attention
   managériale, que ce moteur ne traduit pas encore en perte d'OTD (voir
   `pistes-extension.md` : pannes + file d'attention finie).
2. **Ce qui détruit l'OTD en cas de pic, c'est la surcharge du goulot, pas la
   fenêtre** : en gros pic (charge offerte 1,27), l'OTD tombe à **1,4–45,4 % même
   en lançant immédiatement** — conforme à Goldratt p. 9 (« surcharges temporaires →
   performance < 90 % », ici bien pire) ; la file s'accumule et la phase de reprise
   reste à 5,8–34,7 % (la queue met 205–278 h à s'évacuer, l'OTD 394–588 h à
   récupérer).
3. **La mesure qui sauve l'OTD est la surcapacité du goulot (TOC, étape 4 « élever
   la contrainte », p. 16–17)** : à demande identique, ×1,25 → OTD global 98,5 %,
   ×1,5 → 100 % (et 100 % dès 72 h de fenêtre en gros pic). La fenêtre ne rattrape
   pas une surcharge ; la capacité du tambour, si.
4. **Le versant gauche de la Fig. 1 est bien présent** : fenêtre trop courte (36 h,
   inférieure à la traversée) → alésas non absorbés → OTD global 17,4 % (témoin),
   50,7 % (×1,25), 72,3 % (×1,5). La fenêtre utile se situe entre ~72 h et le délai
   client (plateau), conformément à « tampon ≈ moitié du délai actuel » (p. 14).

**Conclusion** : Goldratt a raison sur le mécanisme (trop d'encours → embouteillages
→ attention saturée → retards, p. 12–14) mais, dans un modèle où la promesse est
tirée par le client, « lancer trop tôt » se paie en encours/attention, pas en OTD ;
c'est la **surcharge du goulot** qui fait s'effondrer l'OTD (p. 9), et la
**surcapacité du goulot** qui la restaure (p. 16–17). Pour que le versant droit
nuise aussi à l'OTD, il faut des promesses fixées par la capacité du goulot (mode
« promesse sous charge » du simulateur HTML) ou modéliser l'attention finie —
deux pistes déjà consignées dans `pistes-extension.md`.

## 4. Reproduction

```bash
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-surcharge-10-postes.json --out sdbr-mini-usine/results/surcharge-10-postes
# sorties : replications.csv, synthese.csv, comparaisons.csv, conflits.csv, configurations.json, otd.png
```
