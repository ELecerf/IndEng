# Test reformulé : lots à tous les postes, fenêtre jusqu'à 20 × W — que se passe-t-il quand les files grossissent ?

Scénario : `scenario-u-20xw.json` · résultats : `results/u-20xw/`
(`u_otd.png`, `courbe_u.csv` via `scripts/courbe_u.py`)

## Demande de test reformulée

Hypothèse initiale : « les lots autorisés sont grands, mais à faible encours les
regroupements sont de facto modestes et les OF urgents en patissent peu ; quand on
agrandit la fenêtre, les encours et les regroupements augmentent, les séries bloquent
les OF urgents et l'OTD baisse — monter jusqu'à 20 × W. »

Traduction précise dans le moteur (`policies.select_batch`) : la taille **réalisée** d'un
lot = `min(size, nombre de pièces de la même famille en attente)` au moment de la décision,
sinon départ après `maxBatchWaitHours` avec ce qui est arrivé. Donc oui : plus les files
sont longues, plus les lots se remplissent — le regroupement croît automatiquement avec
l'encours.

Contraintes de protocole (apprises des campagnes précédentes) :
1. pour balayer jusqu'à 20 × W **sans saturation**, il faut un délai client max > 20 × W
   (sinon fenêtre ≥ délai max ⇒ lancement immédiat, courbe plate) → délai **lognormal**,
   moyenne 12 × W = 288 h, CV 1,5 (médiane ≈ 6,6 × W, queue longue > 20 × W) : beaucoup de
   promesses courtes (la congestion fait rater) + une queue longue (pas de saturation) ;
2. un **pic de charge fort** (ρ = 1,30 pendant 480 h) pour faire gonfler files et encours ;
3. métriques : OTD, encours, file, regroupements, **conflits_avec_retard**, retard P95.

Protocole : ligne 10 postes, goulot `poste_5`, W = 24 h, 13 fenêtres de 1 à 20 × W × 4
variantes × 20 graines : `unitaire`, `lots8_cap12` et `lots16_cap12` (lots à **tous** les
postes, cap 12 h), `lot_goulot16_cap24` (lot 16 au goulot seul, cap 24 h).

## Résultats (OTD % moyenne, phase globale)

| ×W | unitaire | lots8/16 tous postes | lot 16 goulot seul |
| --- | --- | --- | --- |
| 1–5 | 2,6–51,6 | 0 | 0–66,4 |
| 7–8 | 61,4–64,0 | 30,3–37,8 | 71,2–72,5 |
| 10–12 | 70,8–72,2 | 43,1–44,7 | **73,3 (pic à 10×W)** |
| 15–20 | 76,0–**80,0** | 44,5–45,0 (plateau) | 72,7–72,9 |

Mécanismes mesurés (global) :

| ×W | conflits lots8 (tous postes) | conflits lot16 goulot | encours lots8 | encours unitaire | P95 retard lot16 goulot |
| --- | --- | --- | --- | --- | --- |
| 1 | 0,6 | 0,1 | 22,4 | 12,6 | 134 h |
| 8 | 28,9 | 20,1 | 23,3 | 13,7 | 81 h |
| 12 | 41,0 | 24,4 | 23,6 | 14,1 | 81 h |
| 20 | **52,9** | **27,8** | 24,2 | 14,8 | **90 h** |

## Lecture

- **Mécanisme confirmé** : les conflits avec retard (OF urgents bloqués derrière une
  série) croissent de façon monotone avec la fenêtre (0,6 → 52,9 pour les lots à tous les
  postes ; 0,1 → 27,8 au goulot), l'encours et les files augmentent (22,4 → 24,2 OF ;
  en pic 27,9 → 33,2 OF), et le retard P95 repart à la hausse en branche droite
  (81 → 90 h au goulot). Le nombre de regroupements est ~constant (~730 lots) mais leur
  **taille réalisée** croît avec les files — c'est le « de facto » de l'hypothèse.
- **L'OTD baisse en niveau, pas en pente** : à 20 × W, unitaire 80,0 % vs lots au goulot
  72,9 % vs lots à tous les postes 45,0 %. La branche droite du U apparaît ici comme un
  **écart de niveau** : à fort encours, les séries mangent la marge et l'OTD reste bas.
- **Pourquoi pas de chute littérale en fonction de la fenêtre** : avec
  `lancement = max(arrivée, promesse − fenêtre)`, la date de lancement est non croissante
  en la fenêtre et la courbe sature à fenêtre = délai max ; l'OTD vs fenêtre est donc
  monotone croissant puis plat (vérifié sur 6 configurations). La chute de l'OTD à fort
  encours existe bien, mais en fonction de la **charge** (`charge-otd-encours.md` :
  96 → 33 % quand ρ → 0,99) et en écart entre modes de regroupement à fenêtre fixée.
- Note : lots 8 et 16 à tous les postes donnent des résultats identiques — la file par
  famille atteint rarement 16, c'est le plafond (12 h) qui départage ; la taille ne bite
  que quand la file dépasse `size`.
- Côté Goldratt : p. 5–6 (gros lots = rochers cachés sous l'eau), p. 12 Fig. 1 (U),
  p. 13 (touch < 1 % du délai en production par lots).

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-u-20xw.json --out sdbr-mini-usine/results/u-20xw
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/courbe_u.py \
  --results sdbr-mini-usine/results/u-20xw --out sdbr-mini-usine/results/u-20xw
```
