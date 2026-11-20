# Résultats : lot minimum 2/4/8/16, fenêtres 2–45 × W, lead [10, 40] × W, 10 graines

Scénario : `scenario-lot-min-40xw.json` (6 variantes × 9 fenêtres × 10 graines = 540 sims,
lancé en ~4 min) · résultats : `results/lot-min-40xw/` (`u_otd.png` 4 panneaux,
`courbe_u.csv`) · protocole : `protocole-lot-min-40xw.md`

## Config

Ligne 10 postes (réguliers 5,4 h calculés par `overCapacity: 1.25`, goulot 6 h + 2 h,
W ≈ 54,3 h), 4 familles (même gamme [5,7] h), CV 0,6 lognormal, lead uniforme
[10, 40]×W, fenêtres [2,4,8,12,16,24,30,40,45]×W (45 > 40 = lancement immédiat),
tampons 16, transfert unitaire, `size` = 16, attente bornée 24 h, pic ρ = 1,30 / 480 h.
Variantes : `temoin_size1`, `min2/4/8/16`, `taille_liee_fenetre` (`sizeFromWindow` coef 1
max 16 → lot = min(16, round(fenêtre/W))).

## Résultats (phase globale, OTD % ± IC95)

| ×W | temoin | min2 | min4 | min8 | min16 | liée fenêtre | lot pratiqué (min8) | encours (min8) | traversée (min8) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 57 ± 8 | 2 ± 1 | 0 | 0 | 0 | 0 ± 1 | 2,4 | 23,0 | 330 h |
| 4 | 94 ± 7 | 67 ± 8 | 1 ± 1 | 0 | 0 | 0 ± 1 | 2,4 | 25,3 | 330 h |
| 8 | 100 | 100 | 97 ± 3 | 97 ± 4 | 97 ± 4 | 97 ± 4 | 2,6 | 29,8 | 330 h |
| 12 | 100 | 100 | 100 | 100 | 100 | 100 | 2,8 | 33,9 | 330 h |
| 24 | 100 | 100 | 100 | 100 | 100 | 100 | 3,3 | 44,4 | 334 h |
| 40–45 | 100 | 100 | 100 | 100 | 100 | 100 | 3,7 | 49,0 | 343 h |

## Lecture

- **Branche gauche accentuée par les lots minimum** : à 2–4 × W, l'OTD s'effondre avec
  `minLotSize` (0 % pour min ≥ 4) — attendre le lot minimum avec une fenêtre courte
  fait tout rater (conflits 6–20 à 2 × W pour les variantes à lots). Le témoin atteint
  déjà 57 % à 2 × W.
- **Plateau à 100 % dès 8–12 × W, y compris à 40–45 × W (lancement immédiat)** : la
  traversée maximale atteint ~343 h ≈ **6,3 × W**, encore < lead min 10 × W = 543 h →
  aucun retard. **Pas de branche droite en OTD** à lead 10–40 × W, même avec pic 1,30.
- **L'encours, lui, explose avec la fenêtre quand on attend les lots** : 23 → 49 OF pour
  min8 (contre 8,8 → 27,8 pour le témoin) — l'attente de lot min fait accumuler le WIP
  en ligne (c'est la branche droite du U, visible ici en encours/traversée, pas en OTD).
- `min4/min8/min16` quasi identiques : avec 4 familles, la file par famille atteint
  rarement 4 en 24 h (borne d'attente) → le minimum ne bite que pour min2. La taille
  pratiquée croît avec la fenêtre (2,4 → 3,7) via l'extension en cours de traitement.
- `taille_liee_fenetre` se comporte comme min8 dès 8 × W (lot demandé = 8 à 8 × W, 16
  au-delà) : lot pratiqué 1,6 → 3,7, même encours 49 à 40–45 × W.
- Pour faire chuter l'OTD à droite, il faudrait traversée > lead à fort encours :
  lead min ~5 × W (mais la fenêtre sature alors à 5 × W) ou un pic bien plus fort.

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-lot-min-40xw.json --out sdbr-mini-usine/results/lot-min-40xw
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/courbe_u.py \
  --results sdbr-mini-usine/results/lot-min-40xw --out sdbr-mini-usine/results/lot-min-40xw
```
