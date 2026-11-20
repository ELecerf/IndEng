# Dimensionner le lot minimum par la fenêtre : lot min = k × fenêtre / W

Campagne `lot-fenetre-coef` : on fait varier le **coefficient k** de la règle
`sizeFromWindow` (`lot min effectif = min(16, max(1, round(k × fenêtre/W)))`, `minimumOnly`)
pour trouver quelle règle de dimensionnement fait apparaître le **U complet de l'OTD**
(hausse → plateau → baisse) en ne faisant varier que la fenêtre de lancement.

## Protocole

- `scenario-lot-fenetre-coef.json`, base identique à `scenario-figure-u.json` :
  ligne 10 postes, `familyCount` 4, W ≈ 54,3 h, goulot [5, 7] h + 2 h de réglage,
  surcapacité ×1,25 (réguliers 5,4 h), tampons interpostes 16, lead client [10, 40]×W
  lognormal (CV 0,6), arrivées CV 1,0, `size` = 16, transfert unitaire,
  `maxBatchWaitHours` = 168 h, warmup 400 h, phases de charge 0,70 / 0,95 / 1,30 / 0,85.
- 5 variantes : `temoin` (`minLotSize` 1) et `k025` / `k05` / `k1` / `k2`
  (`sizeFromWindow` coef 0,25 / 0,5 / **1 = lot min = fenêtre/W, l'exemple proposé** / 2,
  `max` 16, `minimumOnly`).
- 18 fenêtres [1 ; 1,5 ; 2 ; 3 ; 4 ; 5 ; 6 ; 7 ; 8 ; 10 ; 12 ; 16 ; 20 ; 24 ; 30 ; 35 ; 40 ; 45]×W
  × 10 graines appariées (42–51) = **900 simulations** (~20 min).
- Résultats : `results/lot-fenetre-coef/` (CSV + `rapport-otd.pdf`), figure 3 panneaux
  `figure_u.pdf/.svg/.png` (axe log₂, zones de couleur de `k025`), `figure_u_stats.csv`.

## Résultats : OTD global (%) selon la fenêtre (×W)

| ×W | temoin | k025 | k05 | k1 | k2 |
|---:|---:|---:|---:|---:|---:|
| 1 | 1,7 | 1,7 | 1,7 | 1,7 | 0,0 |
| 2 | 64,8 | 64,8 | 64,8 | **1,9** | 0,0 |
| 4 | 96,4 | 96,4 | 74,4 | 2,5 | 0,0 |
| 5 | 98,8 | **98,8** | 67,9 | 2,8 | 0,0 |
| 6 | 99,8 | 94,8 | 85,0 | 2,3 | 0,0 |
| 8 | 100,0 | **98,5** | 82,2 | 0,3 | 0,0 |
| 12 | 100,0 | 98,5 | 74,1 | 0,1 | 0,0 |
| 16 | 100,0 | 97,7 | 34,3 | 0,2 | 0,2 |
| 24 | 100,0 | 94,8 | 0,6 | 0,0 | 0,0 |
| 30 | 100,0 | **73,8** | 4,0 | 4,0 | 4,0 |
| 35 | 100,0 | 38,0 | 12,9 | 12,9 | 12,9 |
| 40 | 100,0 | 23,1 | 13,1 | 13,1 | 13,1 |
| 45 | 100,0 | **17,2** | 13,1 | 13,1 | 13,1 |

### Lecture

- **k = 0,25 est le seul coefficient qui trace le U complet** : montée 1,7 % → **pic 98,8 %
  à 5×W** (98,5 % à 8×W), plateau 95–98 % jusqu'à 24×W, puis branche droite
  73,8 % (30×W) → 38 % → 23 % → **17,2 % à 45×W**. Au pic, W = 1/5 à 1/8 de la fenêtre,
  soit **W ≈ 12,5–20 % de la fenêtre** — la bande W ≈ 10–15 % de Goldratt.
- **k = 0,5 décale le U vers la gauche et l'approfondit** : pic 85 % à 6×W, effondrement
  34 % dès 16×W, quasi 0 % au-delà de 20×W.
- **k = 1 — la règle proposée « lot min = fenêtre/W » — est ~4× trop agressive** : dès 2×W
  (lot min = 2 avec attente jusqu'à 168 h), l'OTD tombe à 1,9 % contre 64,8 % pour le témoin ;
  elle reste à 0–4 % sur toute la plage. À fenêtre ≥ 16×W le lot min atteint le plafond 16 :
  k1/k2/k05 convergent alors vers la politique min16 fixe (**13,1 %**, conforme à
  `lot-min-40xw.md`).
- **k = 2** : OTD ≈ 0 % partout (lot min 2 dès 1×W).
- **témoin** (lot min 1) : 100 % dès 7×W, plat — pas de branche droite, comme attendu.

## Mécanisme (mesuré)

| ×W | attente lot au goulot k1 (h) | lot pratiqué k025 → k1 | encours k1 / temoin (OF) | conflits k025 → k1 |
|---:|---:|---:|---:|---:|
| 2 | 223 | 1,4 → 2,8 | 14 / 8 | 2 → 28 |
| 8 | 801 | 2,8 → 8,1 | 68 / 11 | 14 → 39 |
| 16 | 735 | 5,8 → 7,3 | 124 / 14 | 37 → 26 |
| 30 | 423 | 11,1 → 10,0 | 166 / 21 | 197 → 119 |
| 45 | 323 | 11,8 → 11,6 | 175 / 22 | 171 → 160 |

- Le goulot **attend pour remplir le lot minimum** : 220–870 h (≈ 4–16×W) pour k1.
- L'encours explose (×8 : 175 OF contre 22 au témoin à 45×W) et la taille de lot pratiquée
  atteint 11,6–11,8 (plafond 16 jamais atteint en pratique).
- Les **conflits** (OF urgents dépassés par un lot) passent de ~0 à 160–200.
- Par phase, la dégradation touche d'abord la phase **« creux »** (OTD 0 % à 45×W pour k025) :
  faible arrivée ⇒ l'attente de remplissage du lot min est longue relativement aux échéances.
- Zones de couleur (k025) : à 5–8×W, ~90 % des OF finissent en vert/jaune ; à 45×W,
  **82,8 % en noir** (frac moyenne 1,7, c.-à-d. fin à 1,7× la fenêtre après le lancement).

## Conclusion

- Oui, on peut dimensionner le lot minimum par la fenêtre — le mécanisme `sizeFromWindow`
  le fait déjà — mais **le coefficient doit être petit** : k = 0,25 (lot min = fenêtre / 4W)
  donne le U complet avec un pic à fenêtre ≈ 5–8×W ; k = 1 (lot min = fenêtre/W, l'exemple
  proposé) est trop grand d'un facteur ~4 et ne produit que la branche gauche (OTD ≈ 0).
- Interprétation : à la fenêtre optimale, le lot minimum supportable est **≤ 2 OF** ;
  « lot min = fenêtre/W » vaut déjà 5–8 OF à cette fenêtre, ce qui suffit à bloquer le
  goulot 400–800 h et à tuer l'OTD.
- La borne d'attente `maxBatchWaitHours` = 168 h est ce qui rend la règle crédible
  (les lots se remplissent vraiment) ; avec 24 h, aucun lot min > 1 ne se forme.
