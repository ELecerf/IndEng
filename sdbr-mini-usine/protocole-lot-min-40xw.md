# Demande améliorée (préparée, NON lancée) : lot minimum 2/4/8/16, temps très variables, surcapacité +25 %, lead jusqu'à 40 × W, fenêtre variable

Scénario validé : `scenario-lot-min-40xw.json` — **campagne non exécutée** (en attente de ton feu vert).

## Demande reformulée (précise et exécutable)

1. **Taille de lot de production minimum** à tous les postes : `minLotSize` ∈ {2, 4, 8, 16}.
   Le poste **attend** d'avoir `minLotSize` OF de même famille avant de lancer la série
   (borne anti-blocage : `maxBatchWaitHours` = 24 h, au-delà il part avec ce qu'il a).
   La série reste **plafonnée** à `size` = 16 ; les arrivées de même famille pendant le
   traitement rejoignent la série jusqu'à `size`. Cohérence imposée par validation :
   `1 ≤ minLotSize ≤ size` par poste, tampons `capacity` = 16 ≥ size.
   (`minLotSize: 1` = comportement courant sans attente.)
2. **Temps de cycle très variables** : `processingDistribution: "lognormal"`, `processingCV: 0.6`.
3. **Surcapacité non-goulot de 25 %** : `line.overCapacity: 1.25` calcule
   `regularHours = (bottleneckHours + bottleneckSetup) / 1.25 − regularSetup` = 5,4 h
   (goulot 6 h + 2 h de réglage).
4. **Demandes client jusqu'à 40 × W** : `requestedLeadWorkMultiple: [10, 40]` ; les
   **fenêtres couvrent les pires cas** : sweep jusqu'à **45 × W** (> lead max = lancement
   immédiat de tous les OF).
5. **But** : faire varier la fenêtre et lire l'effet sur l'OTD pour chaque lot minimum.
6. **Test taille de lot liée à la fenêtre** : variante `sizeFromWindow: {"coef": 1, "max": 16}`
   → taille effective = `min(16, max(1, round(fenêtre / W)))` : plus la fenêtre est longue,
   plus on demande à regrouper (2 à 2×W, 8 à 8×W, 16 au-delà).
7. **2, 4, 8, 16 familles** : `line.familyCount: N` génère N familles `F1..FN` dans la même
   gamme (`bottleneckHours: [5, 7]`, tirage déterministe `familySeed`), mêmes distributions
   de temps (CV commun) ; variantes `fam2/fam8/fam16` à `minLotSize` = 8.
8. **Configurabilité** : tout passe par le bloc `line` + clés à plat du scénario
   (`minLotSize`, `sizeFromWindow`, `requestedLeadWorkMultiple`, `windowsWorkMultiple`...),
   résolu par `resolve_line` ; validation explicite dans `run_hypotheses.validate`.

## Config retenue (validée, simplifiée : 6 variantes × 9 fenêtres × 20 graines = 1080 sims)

Ligne 10 postes, goulot poste 5, W ≈ 54,4 h ; fenêtres [2,4,8,12,16,24,30,40,45]×W
(45×W > lead max 40×W = lancement immédiat) ; transfert unitaire ; tampons 16 ;
pic ρ = 1,30 / 480 h (congestion pour la branche droite) ; warmup 400 h.
Variantes : `temoin_size1`, `min2/min4/min8/min16`, `taille_liee_fenetre`.
Les variantes `fam2/fam8/fam16` (nombre de familles) sont retirées de cette campagne
(combinatoire trop forte) et prévues en campagne séparée à lot min fixé.

## Nouveautés moteur (testées, 51 tests OK)

- `policies.select_batch(..., size, min_size, wait, now, rule)` : attente du lot minimum
  (sauf expiration de `wait`) ; plafond `size` ; `min_size = 1` = aucun attente (rétrocompatible).
- `run_congestion.simulate` : `minLotSize` (entier ou liste par poste), validation
  `1 ≤ minLotSize ≤ size` ; l'extension de série pendant le traitement reste plafonnée à `size`.
- `line_config.resolve_line` : `line.familyCount` (familles générées, même gamme, seed fixe,
  `familyWeights` auto = [1]*N) et `line.overCapacity` (regularHours calculé).
- `run_hypotheses` : `sizeFromWindow` (taille par fenêtre via `effective_lot_sizes`) +
  validation ; `minLotSize` validé.
- Tests : `test_taille_lot_minimum_avec_attente`, `test_simulation_attend_la_taille_minimale`,
  `test_family_count_et_overcapacity`, `test_size_from_window`.

## KPI à lire au lancement

OTD ± IC95 vs ×W par variante, `taille_lot_moy`/`taille_lot_max`, `conflits_avec_retard`,
encours, carnet, file, retard P95, `blocage`/`stocks_pleins` — figure via `courbe_u.py`.

## Commande (non exécutée)

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-lot-min-40xw.json --out sdbr-mini-usine/results/lot-min-40xw
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/courbe_u.py \
  --results sdbr-mini-usine/results/lot-min-40xw --out sdbr-mini-usine/results/lot-min-40xw
```
