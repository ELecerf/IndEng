# Taille de lot réelle au goulot : le U en OTD est-il visible quand les lots se forment vraiment ?

Scénario : `scenario-u-lots-goulot.json` · résultats : `results/u-lots-goulot/`
(`u_otd.png`, `courbe_u.csv` via `scripts/courbe_u.py`)

**Question** : la taille de lot était peut-être trop faible pour voir le U — l'OTD devrait
monter puis baisser quand il y a du regroupement.

## Protocole

Ligne 10 postes, goulot `poste_5`, W = 24 h, délai client 2–10 × W (48–240 h), sweep de
12 fenêtres 0,5–12 × W × 4 variantes × 20 graines :
- `unitaire` (témoin)
- `lots8_cap6` : lots de 8 à **tous** les postes, plafond d'attente 6 h (régime des
  campagnes précédentes — la taille ne se déclenchait quasiment jamais : lots 8 et 16
  donnaient des résultats identiques)
- `lot_goulot8` / `lot_goulot16` : lots de 8/16 **uniquement au goulot**, plafond 24 h —
  de vraies séries s'y forment (≈ 62 regroupements au goulot, contre ≈ 690 à tous les
  postes en cap 6 h)

## Résultats (OTD % moyenne, phase globale)

| ×W | unitaire | lot_goulot8 | lot_goulot16 | lots8_cap6 |
| --- | --- | --- | --- | --- |
| 0,5–1 | 0,0–2,2 | 0,0 | 0,0 | 0,0 |
| 2 | 38,7 | 11,8 | 11,8 | 0,0 |
| 3 | 61,0 | 65,2 | 65,2 | 0,0 |
| 4 | 73,6 | 80,3 | 80,4 | 27,7 |
| 5 | 81,9 | 86,0 | 86,0 | 58,8 |
| 6 | 86,7 | 87,2 | 87,2 | 65,3 |
| **7–9** | 90,1–93,1 | **88,5 (pic à 7×W)** | **88,5** | 67,0–68,2 |
| 10–12 | 93,5 | 87,9 | 87,9 | 67,9 |

En pic : `lot_goulot8` pic à 84,5 % à 8 ×W puis 83,4 % à 10–12 ×W ; `lots8_cap6` pic à
65,6 % à 8 ×W puis 63,9 %. **Conflits avec retard** (OF urgents bloqués derrière une série,
panneau 3 de `u_otd.png`) : 0,9 → 11,8 quand la fenêtre passe de 3 à 9 ×W pour
`lot_goulot8` ; retard P95 : 10 h (unitaire) vs 21 h (lot_goulot8) vs 59 h (lots8_cap6).

## Lecture

- **La taille de lot ne se déclenchait pas avant** : avec un plafond de 6 h, lots 8 et 16
  donnaient exactement les mêmes résultats — les lots partaient avant d'être pleins. Avec
  un plafond de 24 h au goulot, de vraies séries se forment et le pic d'OTD apparaît vers
  **7–9 × W (W ≈ 11–14 % de la fenêtre**, la zone 10–15 % visée).
- **Montée puis plateau, pas chute** : l'OTD des variantes avec lots stagne à ~88 %
  (pic 84 %) pendant que le témoin unitaire monte à 93,5 %. La baisse franche n'apparaît
  pas en fonction de la fenêtre parce que `lancement = max(arrivée, promesse − fenêtre)`
  rend la date de lancement **non croissante** en la fenêtre, et au-delà de 10 × W
  (= délai max) la fenêtre sature (lancement immédiat) : l'OTD vs fenêtre est donc
  monotone croissant puis plat.
- **Où est la branche droite du U ?** (a) en niveau, à fort encours, selon le mode de
  regroupement : à 12 × W, unitaire 93,5 % vs lots8 67,9 % vs transfert bloc 51,7 % vs
  train 0,9 % (campagne `courbe-u-otd`) ; (b) en fonction de la **charge** : OTD
  96 → 33 % quand ρ → 0,99 (`charge-otd-encours.md`) ; (c) dans les files et l'attention
  managériale vs fenêtre (`dashboard-u.md`, branche droite +43 % de files en pic).
  Mécanisme visible ici : les séries bloquent les OF urgents (conflits 0,9 → 11,8) et
  le retard P95 double, ce qui rogne le plateau de droite.
- Côté Goldratt : p. 5–6 (petits lots, rochers/eau), p. 12 Fig. 1 (U), p. 11 (touch ≈ 10 %
  du lead). Règle pratique : regrouper **au goulot** (le lot y gagne des heures de réglage,
  `lots-par-poste.md`) avec un plafond d'attente modéré, jamais de gros lots à tous les
  postes (la ligne s'étoile : encours 35–63 OF, OTD 0 %).

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-u-lots-goulot.json --out sdbr-mini-usine/results/u-lots-goulot
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/courbe_u.py \
  --results sdbr-mini-usine/results/u-lots-goulot --out sdbr-mini-usine/results/u-lots-goulot
```
