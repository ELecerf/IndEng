# Pourquoi le carnet absorbe à fenêtre croissante — et 3 configurations de demande à lead ≈ 20 × W (proposées, non lancées)

Doc de proposition : `configs-demande-lead-20xw.md` (aucune simulation lancée).

## 1. Pourquoi c'est le carnet qui absorbe (données `results/u-fenetre-immediate/`, size1, global)

Règle de lancement : `release = max(arrivée, promesse − fenêtre)`. Un OF de délai L passe
`(L − fenêtre)⁺` heures **dans le carnet (non lancé)**, puis `traversée` heures dans la ligne.

| ×W | carnet (OF) | encours ligne (OF) | traversée (h) | file moy (OF) |
| --- | --- | --- | --- | --- |
| 1 | 32,1 | 8,0 | 69 | 2,5 |
| 5 | 19,4 | 8,7 | 72 | 3,0 |
| 10 | 11,6 | 9,3 | 73 | 3,5 |
| 15 | 7,5 | 9,7 | 72 | 3,7 |

Lecture : quand la fenêtre croît, le carnet **se vide** (32 → 7,5 OF) et l'encours ligne ne
monte que faiblement (8,0 → 9,7 OF) avec une traversée quasi constante (~70 h). Pourquoi :
l'encours en ligne vaut `λ × traversée` (loi de Little) et la traversée est fixée par la
**charge du goulot** (ρ), pas par la fenêtre — le débit de la ligne est plafonné par le
goulot, donc on ne peut pas y pousser plus que `λ × traversée` OF : le surplus reste dans
le carnet. Autrement dit, lancer « tôt » ne remplit pas la ligne, cela déplace juste des OF
du carnet vers la file du goulot, et la file du goulot ne peut contenir que ce que le
goulot peut traiter. **L'encours maximal n'est atteint que quand fenêtre ≥ lead** (lancement
à la réception pour tous les OF) — d'où l'intérêt du cas extrême « fenêtre > lead ».
Conséquence pour le U : la branche droite en OTD n'apparaît pas en faisant croître la
fenêtre tant que fenêtre < lead ; elle apparaît quand fenêtre ≥ lead (tout est lancé) et
que la traversée à fort encours dépasse les délais client. Pour voir ça, il faut des
demandes à **grand lead** (peu de marge) — d'où les configurations ci-dessous.

## 2. Trois configurations de demande proposées (lead client centré sur 20–30 × W)

Rappel Goldratt : p. 11 (touch ≈ 10 % du lead), p. 13 (usines par lots : touch < 1 % du
délai). Avec lead moyen 20 × W, W vaut **5 % du lead en moyenne** (10 × W → 10 %, 30 × W →
3,3 %) : c'est le régime « usine par lots » de la branche droite du U.

### Config A — uniforme [10, 30] × W (moyenne 20 × W, symétrique)

```json
"requestedLeadWorkMultiple": [10, 30]
```
Bornes explicites 10–30 × W, moyenne 20 × W, touch moyen 5 %. Fenêtres proposées :
[2, 5, 8, 10, 15, 20, 25, 30, 35] × W — le point 35 × W est le cas « fenêtre > lead max »
(lancement immédiat de tous les OF).

### Config B — lognormale moyenne 20 × W, CV 0,25 (asymétrique, ~90 % dans [13, 28] × W)

```json
"requestedLeadWorkMultiple": [20, 60],
"requestedLeadDistribution": "lognormal",
"requestedLeadCV": 0.25
```
Médiane ≈ 19,2 × W, longue queue à droite (quelques OF à lead très long, jamais en retard).
Même sweep de fenêtres que A.

### Config C — lognormale centrée 30 × W, CV 0,3 (touch ≈ 3,3 %, régime « lots » p. 13)

```json
"requestedLeadWorkMultiple": [30, 90],
"requestedLeadDistribution": "lognormal",
"requestedLeadCV": 0.3
```
Moyenne 30 × W, médiane ≈ 28,7 × W, queue jusqu'à ~50 × W. Fenêtres proposées :
[5, 10, 15, 20, 25, 30, 35, 40, 50] × W (point 50 × W = lancement immédiat).

### Accompagnement commun aux 3 configs

- Limite de place entre postes : remplacer `"capacity": [null,...]` (file infinie) par une
  limite finie, ex. `"capacity": [4]*9` (ou `size`), pour que le blocage amont
  (`blocage_*`, `stocks_pleins`) apparaisse à fort encours — c'est la consommation de
  tampon qui fait monter l'encours en amont quand tout est lancé tôt.
- Ligne : réguliers 4 h vs goulot 6 h + 2 h (faible surcapacité), W = 42 h, transfert
  unitaire, variantes `size` = 1/4/8/16 sans attente (sémantique du 20/11), warmup 400 h,
  20 graines, phases sans surcharge puis avec un pic pour stresser.
- KPI : OTD ± IC95 vs ×W, encours, carnet, file, `taille_lot_moy`, `conflits_avec_retard`,
  `blocage`, `stocks_pleins`, retard P95 — figure via `scripts/courbe_u.py`.

Objectif : avec lead 10–30 × W, le plateau de l'OTD doit se situer vers fenêtre ≈ 10–20 × W
et le point fenêtre > lead (lancement immédiat, encours max = λ × traversée) doit montrer
la **baisse** de l'OTD due aux regroupements quand les files s'allongent (taille pratiquée ↑,
conflits ↑).
