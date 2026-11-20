# Configuration A lancée : lead uniforme [10, 30] × W, fenêtres 2 → 35 × W

Scénario : `scenario-demande-a-20xw.json` · résultats : `results/demande-a-20xw/`
(`u_otd.png` 4 panneaux, `courbe_u.csv` via `scripts/courbe_u.py`)

## Protocole (config A de `configs-demande-lead-20xw.md`)

Ligne 10 postes, réguliers 4 h vs goulot 6 h + 2 h (W = 42 h), tampons finis
`capacity = 4`, **transfert unitaire**, lots sans attente `size` = 1/4/8/16 (`family_fifo`),
**délai client uniforme [10, 30] × W** (420–1260 h, moyenne 20 × W → touch = W/lead ≈ 5 %
en moyenne, 3,3–10 % selon les OF), fenêtres **2, 3, 5, 8, 10, 15, 20, 25, 30, 35 × W**
(30 et 35 × W ≥ lead max = lancement immédiat), charges 0,70 / 0,95 / 0,85 (pas de pic),
warmup 400 h, 20 graines.

## Résultats (phase globale)

| ×W | OTD size1 | OTD size16 | lot pratiqué size16 (moy/max) | conflits size16 | encours size1 | carnet size1 | traversée |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 89,0 ± 5,2 | 95,3 ± 2,2 | 1,34 / 8 | 0,6 | 5,6 | 84,2 | 63 h |
| 3 | 99,4 | 100,0 | 1,35 / 9 | 0,1 | 5,8 | 80,3 | 63 h |
| 5 | 100,0 | 100,0 | 1,36 / 9 | 0,0 | 6,3 | 72,1 | 63 h |
| 10 | 100,0 | 100,0 | 1,39 / 10 | 0,0 | 7,6 | 49,6 | 63 h |
| 20 | 100,0 | 100,0 | 1,43 / 12 | 0,0 | 9,7 | 12,9 | 64 h |
| 30 | 100,0 | 100,0 | 1,47 / 11 | 0,0 | 9,8 | **0,0** | 62 h |
| 35 | 100,0 | 100,0 | 1,47 / 11 | 0,0 | 9,8 | **0,0** | 62 h |

## Lecture

- **Branche gauche seule visible** : à 2 × W, OTD 89 % (size1) — en dessous, lancer à
  `promesse − fenêtre` avec une fenêtre < traversée rendrait tout en retard.
- **Plateau à 100 % dès 3–5 × W, y compris au-delà de lead max (30–35 × W)** : la traversée
  à encours max vaut ~62 h ≈ **1,5 × W**, très inférieure au lead minimal (10 × W = 420 h)
  → aucun OF en retard, même en lançant tout à la réception. **Pas de branche droite en OTD
  ici** : avec des promesses à 20 × W en moyenne et une ligne peu chargée (ρ ≤ 0,95), le
  touch (~5 % du lead) suffit largement.
- **Le carnet confirme la saturation** : carnet 84 → 0 OF quand la fenêtre atteint 30 × W
  (≥ lead max ⇒ lancement immédiat pour tous), pendant que l'encours ligne plafonne à
  ~9,8 OF = λ × traversée (loi de Little) — lancer tôt ne remplit pas la ligne au-delà.
- **Taille de lot pratiquée** : croît légèrement avec la fenêtre (1,34 → 1,47 ; max 12
  avec size16 à 20–25 × W) mais les conflits restent ~0 car les promesses sont lâches.
  `size` 4/8/16 quasi identiques (le plafond ne bite presque jamais sans attente).

## Conclusion et piste suivante

Avec lead ≈ 20 × W et ρ ≤ 0,95, la branche droite du U en OTD **n'apparaît pas** : il
faudrait que la traversée à fort encours dépasse le lead des OF, soit ~10 × W — il faut
donc une **surcharge** (pic ρ ≥ 1,3 assez long pour gonfler la file du goulot) ou un lead
plus serré. Piste proposée (config A + pic) : mêmes paramètres + phase `pic` 480 h à
ρ = 1,30, fenêtres jusqu'à 35 × W — la traversée en pic doit dépasser 10 × W pour que le
point « fenêtre > lead » fasse chuter l'OTD. Alternative : config B/C (lead lognormal
20–30 × W) pour la variabilité, ou lead resserré ~3–5 × W (mais la fenêtre sature alors
plus tôt).

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-demande-a-20xw.json --out sdbr-mini-usine/results/demande-a-20xw
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/courbe_u.py \
  --results sdbr-mini-usine/results/demande-a-20xw --out sdbr-mini-usine/results/demande-a-20xw
```
