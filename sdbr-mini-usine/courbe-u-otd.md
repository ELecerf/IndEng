# Le U de Goldratt vu par l'OTD : fenêtre courte / intermédiaire / longue avec regroupements

Scénario : `scenario-courbe-u-otd.json` · résultats : `results/courbe-u-otd/`
(scénario + `courbe_u.csv` + `u_otd.png` produits par `scripts/courbe_u.py`)

**Objectif** : voir le U en OTD vs fenêtre de lancement — mauvais OTD quand la fenêtre
est trop courte, meilleur OTD quand la fenêtre est intermédiaire (W ≈ 10–15 % de la
fenêtre, soit fenêtre ≈ 6,7–10 × W), mauvais OTD quand la fenêtre est trop longue
**à cause des regroupements** (lots, transferts par batch).

## Protocole

Ligne 10 postes, goulot central `poste_5` (6 h + 2 h de réglage), W = 24 h, délai client
2–10 × W (48–240 h), phases creux 0,70 / normal 0,95 / pic 1,15 / reprise 0,85.
Sweep de 12 fenêtres de 0,5 × W à 12 × W (12–288 h ; au-delà de 10 × W = délai max,
lancement immédiat = fort encours) × 4 variantes (unitaire, lots 8 `family_fifo`,
transfert `bloc` 8, train logistique N=8) × 20 graines appariées.

## Résultats (OTD % moyenne ± IC95, 20 graines)

Phase **global** (fenêtre en ×W) :

| ×W | unitaire | lots8 | transfert bloc8 | train8 |
| --- | --- | --- | --- | --- |
| 0,5–3 | 0,0 | 0,0 | 0,0 | 0,0 |
| 4 | 73,6 ± 7,6 | 27,7 ± 2,7 | 10,9 ± 1,8 | 0,0 |
| 5 | 81,9 ± 6,4 | 58,8 ± 3,6 | 32,6 ± 2,8 | 0,0 |
| 6 | 86,7 ± 4,9 | 65,3 ± 2,5 | 42,3 ± 3,1 | 0,0 |
| 7 | 90,1 ± 5,2 | 67,0 ± 2,3 | 47,9 ± 3,5 | 0,0 |
| **8** | 92,7 ± 4,3 | **68,2 ± 2,3** | **51,8 ± 3,6** | 0,1 |
| 9 | 93,1 ± 4,1 | 67,8 ± 2,5 | 52,0 ± 3,4 | 0,4 |
| 10 | 93,5 ± 4,0 | 67,9 ± 2,3 | 51,7 ± 3,1 | 0,9 |
| 12 | 93,5 ± 4,0 | 67,9 ± 2,3 | 51,7 ± 3,1 | 0,9 |

Phase **pic** : unitaire monte à 96,6 % (≥ 10 ×W) ; lots8 pic à **65,6 % à 8 ×W** puis
repli à 63,9 % (10–12 ×W) ; bloc8 pic à 46,7 % à 8 ×W puis 44,6 % ; train8 ≈ 0–1 %.
Encours global à 12 ×W : 9,0 OF (unitaire) → 13,7 (lots8) → 17,7 (bloc8) → 35,5 (train8).
Retard P95 global à 12 ×W : 10 h (unitaire) vs 59 h (lots8) / 117 h (bloc8) / 218 h (train8).

## Lecture : le U

- **Branche gauche (fenêtre trop courte)** : OTD = 0 % dès que la fenêtre ≤ 3 × W pour
  toutes les variantes — lancer à `promesse − fenêtre` avec une fenêtre plus courte que
  la traversée (W + files) rend tout retardé. Le témoin unitaire échappe partiellement
  dès 1–2 × W (délais clients longs).
- **Zone intermédiaire** : pour les variantes avec regroupements, le meilleur OTD est
  atteint vers **8 × W, c.-à-d. W ≈ 12 % de la fenêtre** (dans la zone 10–15 % visée,
  cohérente avec Goldratt p. 11 : le touch vaut ~10 % du lead) : lots8 68,2 %, bloc8
  51,8 % (global) ; en pic, lots8 65,6 % à 8 ×W puis légère baisse.
- **Branche droite (fenêtre trop longue, à cause des regroupements)** : à fenêtre
  ≥ 10 × W (lancement immédiat, encours maximal), le témoin unitaire atteint 93,5 %
  mais les variantes regroupées restent bloquées à 67,9 % (lots8), 51,7 % (bloc8),
  0,9 % (train8) : les attentes structurelles de remplissage des lots/blocs/trains
  s'ajoutent aux files du goulot et mangent toute la marge de la fenêtre (retard P95
  ×6 à ×22). Avec un délai client plus serré (2–7 × W, campagne
  `regroupements-transfer-otd` à fenêtre 240 h saturée) l'effet est encore plus net :
  81,6 % (unitaire) → 50,4 % (lots8) → 32,1 % (bloc8) → 0,0 % (train8).
- **Note méthodologique** : avec des promesses pilotées par le délai client
  (lancement = max(arrivée, promesse − fenêtre)), l'OTD est monotone croissant en la
  fenêtre jusqu'à saturation (fenêtre ≥ délai max) ; la branche droite du U de Goldratt
  apparaît alors comme un **écart de niveau à fort encours causé par les regroupements**
  (ci-dessus), et comme une vraie dégradation de l'OTD quand on balaie la **charge**
  (`charge-otd-encours.md` : OTD 96 → 33 % quand ρ → 0,99) ; dans les files et
  l'attention managériale, la branche droite est nette dès le sweep de fenêtres
  (`dashboard-u.md`).
- Côté Goldratt : p. 12 Fig. 1 (U attention vs tampon), p. 5–6 (petits lots, flux d'une
  pièce), p. 11 (touch ≈ 10 % du lead), p. 14 (tampon ≈ moitié du lead).

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-courbe-u-otd.json --out sdbr-mini-usine/results/courbe-u-otd
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/courbe_u.py \
  --results sdbr-mini-usine/results/courbe-u-otd --out sdbr-mini-usine/results/courbe-u-otd
```
