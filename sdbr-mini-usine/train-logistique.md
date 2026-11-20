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
plusieurs », sans considération de famille. Tests : `test_train_logistique_par_enoirs_sans_famille`, `test_train_vidange_optionnelle_sauf_fin`.

**Vidange optionnelle** (`trainVidange`, booléen, défaut `false`) : par défaut, un
train incomplet ne part **que quand plus aucune arrivée n'est à venir** (fin de
simulation) — sinon la dernière pièce ne pourrait jamais partir et la simulation
bloquerait sans événement futur. Si `trainVidange: true`, un train incomplet part
aussi dès que le poste amont est inactif (vidange à chaque poste).

## 2. Campagne (ligne 10 postes, goulot central, pic de charge)

Même ligne que `lots-par-poste.md` (goulot `poste_5` 6 h + 2 h réglage, 2 familles,
phases 0,70 → 0,95 → **pic 1,10** → 0,85, fenêtres 120/168 h, 20 graines, warm-up
400 h), traitement unitaire (`size=1`), transfert = N.

| transfer N | OTD global (IC95, fenêtre 168 h) | OTD pic | traversée P95 | retard P95 | encours moyen |
| --- | --- | --- | --- | --- | --- |
| 1 (unitaire) | **84,6 ± 6,4 %** | 85,2 % | 144 h | 26 h | 8,6 OF |
| 2 | 61,9 ± 6,5 % | 55,8 % | 172 h | 50 h | 12,2 OF |
| 4 | 14,1 ± 2,3 % | 7,6 % | 234 h | 112 h | 19,8 OF |
| 8 | **0,0 %** | 0,0 % | 361 h | 241 h | 34,9 OF |
| 16 | **0,0 %** | 0,0 % | 620 h | 507 h | 64,6 OF |
| 8 + `trainVidange: true` | 8,6 ± 2,2 % | 1,6 % | 311 h | 188 h | 26,3 OF |

Par défaut (train strict, vidange seulement en fin de simulation), la contrainte
logistique est maximale : à partir de N=8, l'OTD tombe à 0. Avec `trainVidange: true`,
les trains incomplets partent dès qu'un poste est inactif et la dégradation est
moindre (N=8 → 8,6 %) — ce qui illustre pourquoi la vidange doit rester optionnelle
pendant la simulation (sinon, à charge intermittente, le train partirait presque
toujours avec 1 OF et N ne contraindrait plus rien), tout en restant obligatoire
pour la dernière pièce (sinon blocage en fin de simulation).

## 3. Lecture

Effet **monotone et fort** : chaque fois que le train attend de se remplir (N plus
grand), les OF — y compris urgents — restent immobilisés en amont, la traversée et
l'encours explosent, et l'OTD s'effondre (84,6 % → 0 % de N=1 à N≥8 en mode strict ; en pic,
N ≥ 4 → OTD < 8 %). C'est la contrainte logistique modélisée : un petit train peu
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
