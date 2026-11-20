# Zones de couleur des OF selon la fenêtre (variante « progressif », lot mini croissant)

Script : `sdbr-mini-usine/scripts/zones_couleur.py` · figures : `zones_couleur.png`,
données : `zones_couleur.csv` (synthèse par fenêtre) et `zones_of.csv` (par OF).

Pour chaque OF de la cohorte (promesse dans [400 h, 2800 h), 1793 OF × 10 graines),
`frac = (expédition − libération) / (promesse − libération)` : **vert ≤ 1/3**, jaune ≤ 2/3,
rouge ≤ 1, **noir > 1** (livré en retard). Variante `progressif` de
`scenario-iso-lot.json` (lot mini demandé = min(16, round(0,25 × fenêtre/W)), annoté `min=`
sur le graphique).

| ×W | lot min | vert % | jaune % | rouge % | noir % | retard % | frac moyenne |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 1 | 0,0 | 18,6 | 45,6 | **35,8** | 35,8 | 0,99 |
| 4 | 1 | 18,6 | 66,6 | 10,8 | 4,0 | 4,0 | 0,50 |
| 8 | 2 | 23,8 | 67,6 | 7,1 | 1,5 | 1,5 | 0,45 |
| 12 | 3 | 32,3 | 62,9 | 3,3 | 1,5 | 1,5 | 0,41 |
| 16 | 4 | 28,0 | 63,7 | 6,1 | 2,2 | 2,2 | 0,44 |
| 24 | 6 | 14,9 | 59,3 | 20,7 | 5,1 | 5,1 | 0,55 |
| 30 | 8 | 3,0 | 38,5 | 32,5 | **26,0** | 26,0 | 0,81 |
| 40 | 10 | 0,7 | 4,8 | 17,5 | **77,0** | 77,0 | 1,56 |
| 45 | 11 | 0,0 | 0,9 | 16,3 | **82,8** | 82,8 | 1,68 |

**Lecture** : le U en couleurs — fenêtre trop courte (2×W) : les OF finissent en rouge/noir
(36 % en retard) ; zone intermédiaire 4–16×W : ~85–90 % en vert/jaune, 1,5–4 % de retard ;
à partir de 24×W et surtout 30–45×W, quand le lot mini demandé grossit avec la fenêtre,
les OF basculent massivement en rouge puis noir (83 % de retard à 45×W, frac moyenne
1,68 > 1 : expédition après la promesse). Les séries de plus en plus grosses à fort
encours consomment toute la fenêtre puis la dépassent.

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/zones_couleur.py \
  sdbr-mini-usine/scenario-iso-lot.json --variante progressif --out sdbr-mini-usine/results/iso-lot
```
