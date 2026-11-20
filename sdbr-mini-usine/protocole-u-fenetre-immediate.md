# Protocole préparé (NON lancé) : OTD en U selon la fenêtre seule, avec fenêtre > lead (lancement immédiat)

Scénario : `scenario-u-fenetre-immediate.json` — **validé, pas encore simulé**.
Commande prévue :

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-u-fenetre-immediate.json --out sdbr-mini-usine/results/u-fenetre-immediate
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/courbe_u.py \
  --results sdbr-mini-usine/results/u-fenetre-immediate --out sdbr-mini-usine/results/u-fenetre-immediate
```

## Objectif

En ne faisant varier **que la taille de la fenêtre** (transferts unitaires), obtenir :
hausse de l'OTD → plateau → baisse, le cas extrême « fenêtre > lead » (lancement immédiat
de tous les OF, y compris lointains) montrant l'impact sur l'encours et la tentation de
regrouper au détriment des OF rouges.

## Choix de paramétrage et pourquoi

| levier | choix | raison |
| --- | --- | --- |
| surcapacité non-goulots | postes réguliers **4 h** vs goulot **6 h + 2 h réglage** (ratio ≈ 1,5, contre 3 avant) | peu de surcapacité ⇒ à fort encours, des files se forment à **tous** les postes ⇒ traversée plus longue ⇒ retards |
| tampons inter-postes | `capacity = 4` (finis, au lieu de infinis) | blocage amont mesurable (`blocage`, `stocks_pleins` = consommation de tampon) |
| délai client | uniforme **2–6 × W** (84–252 h, W = 42 h) | assez serré pour que la traversée à fort encours fasse rater des promesses |
| fenêtres | **1–10 × W** (42–420 h) ; au-delà de 6 × W = lead max ⇒ **lancement immédiat** (points 6, 8, 10 × W) | le point « fenêtre > lead » est le cas extrême demandé |
| lots | variantes `size` = **1 / 4 / 8 / 16**, `family_fifo`, `maxBatchWaitHours` = 6, transfert **unitaire** | taille réalisée = min(size, file famille) : les lots grossissent avec l'encours |
| charge | creux 0,70 / normal 0,95 / reprise 0,85 — **pas de pic** (hors surcharge) | isole l'effet fenêtre |
| protocole | warmup 400 h, 20 graines appariées, CV 0,3 lognormal | comparabilité avec les campagnes précédentes |

W = 42 h (9 × 4 + 6), lead = [84, 252] h, fenêtres = [42, 84, 126, 168, 210, 252, 336, 420] h.
Validation `resolve_line` + `validate` OK pour les 4 variantes (aucune simulation lancée).

## KPI à lire

OTD (global) ± IC95 vs fenêtre en ×W, mais aussi : `encours`, `file_moy`, `regroupements`,
**`conflits_avec_retard`** (OF rouges bloqués derrière une série), `blocage` / `stocks_pleins`
(consommation des tampons), `retard_p95`, `ruptures`.

## Point de vigilance (déjà documenté)

Avec `lancement = max(arrivée, promesse − fenêtre)`, toute fenêtre ≥ lead max donne
lancement immédiat : les points 6, 8, 10 × W sont **identiques** et l'OTD vs fenêtre est
monotone jusqu'à saturation. La baisse ne peut apparaître que **juste avant** la saturation,
si la traversée explose avec l'encours (d'où faible surcapacité + tampons finis + gros lots).
Si le plateau persiste malgré tout, la baisse de l'OTD à fort encours reste démontrée en
fonction de la **charge** (`charge-otd-encours.md`) — le U complet en OTD vs fenêtre
nécessiterait des promesses pilotées par la capacité et non par le délai client.
