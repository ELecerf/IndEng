# Train logistique : un seul paramètre `transfer` = N

Scénario : `scenario-train-logistique.json` · résultats : `results/train-logistique/`

## 1. Le paramètre unique

`transfer` accepte désormais un **entier N ≥ 1** (en plus des chaînes historiques
`"unitaire"` et `"bloc"`) :

- **N = 1** (ou `"unitaire"`) : chaque OF fini est transféré seul, dès que possible ;
- **N ≥ 2** : *train logistique* — les OF finis (toutes familles confondues) s'accumulent
  au poste et partent **par trains de N** au poste aval (et au quai d'expédition) ;
  un train part aussi quand le poste amont est totalement inactif (vidange), pour ne
  jamais bloquer la ligne à faible charge.

Un seul nombre suffit donc à décider « un OF à la fois » vs « attendre d'en avoir
plusieurs », sans considération de famille. Test : `test_train_logistique_par_enoirs_sans_famille`.

## 2. Campagne (ligne 10 postes, goulot central, pic de charge)

Même ligne que `lots-par-poste.md` (goulot `poste_5` 6 h + 2 h réglage, 2 familles,
phases 0,70 → 0,95 → **pic 1,10** → 0,85, fenêtres 120/168 h, 20 graines, warm-up
400 h), traitement unitaire (`size=1`), transfert = N.

| transfer N | OTD global (IC95, fenêtre 168 h) | OTD pic | traversée P95 | retard P95 | encours moyen |
| --- | --- | --- | --- | --- | --- |
| 1 (unitaire) | **84,6 ± 6,4 %** | 85,2 % | 144 h | 26 h | 8,6 OF |
| 2 | 68,9 ± 7,3 % | 64,3 % | 167 h | 45 h | 11,4 OF |
| 4 | 29,4 ± 4,5 % | 17,7 % | 217 h | 93 h | 16,8 OF |
| 8 | 8,6 ± 2,2 % | 1,6 % | 311 h | 188 h | 26,3 OF |
| 16 | 3,7 ± 1,6 % | 0,0 % | 482 h | 368 h | 42,0 OF |

## 3. Lecture

Effet **monotone et fort** : chaque fois que le train attend de se remplir (N plus
grand), les OF — y compris urgents — restent immobilisés en amont, la traversée et
l'encours explosent, et l'OTD s'effondre (84,6 % → 3,7 % de N=1 à N=16 ; en pic,
N ≥ 8 → OTD ≈ 0). C'est la contrainte logistique modélisée : un petit train peu
fréquent pénalise la performance de dates, indépendamment des familles.

À l'inverse, N = 1 (transfert unitaire) est le meilleur réglage ici — cohérent avec
Goldratt p. 5–6 (flux d'une pièce, petits lots) : il n'y a pas de « taille de train
optimale » intermédiaire, le coût croît avec N.

## 4. Reproduction

```bash
.venv/bin/python -m pytest -q   # 39 tests, dont test_train_logistique_par_enoirs_sans_famille
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-train-logistique.json --out sdbr-mini-usine/results/train-logistique
```
