# Résultats : fenêtre seule jusqu'à 15 × W, lots sans attente plafonnés à size (lancement immédiat au-delà du lead)

Scénario : `scenario-u-fenetre-immediate.json` · résultats : `results/u-fenetre-immediate/`
(`u_otd.png` 4 panneaux via `scripts/courbe_u.py`, `courbe_u.csv`) · protocole : `protocole-u-fenetre-immediate.md`

## Sémantique des lots implémentée (demande du 20/11)

`size` = **plafond** de série par poste ; **pas d'attente** pour former le lot : le poste
regroupe ce qu'il a (`min(size, OF de même famille en file)` — 2 OF avec size=8 → lot de 2) ;
les arrivées de même famille **pendant le traitement rejoignent la série en cours**, sans
dépasser `size`. Nouvelle métrique : `taille_lot_moy` / `taille_lot_max` (séries réalisées,
global et par poste). Tests : `test_lot_sans_attente_plafonne_a_size`,
`test_arrivee_rejoint_la_serie_en_cours_jusqu_a_size` (47 tests OK).

## Protocole

Ligne 10 postes, réguliers 4 h vs goulot 6 h + 2 h (surcapacité ≈ 1,5), tampons finis
`capacity = 4`, W = 42 h, délai client **lognormal moyenne 8 × W, CV 1,5** (médiane ≈ 4,4 × W,
queue longue 20 × W > 15 × W → les points à 12 et 15 × W sont distincts, pas de saturation
totale), fenêtres **1 à 15 × W** (11 points), variantes `size` = 1/4/8/16 en
`family_fifo`, **transfert unitaire**, charges hors surcharge (0,70 / 0,95 / 0,85),
warmup 400 h, 20 graines.

## Résultats (phase globale, OTD % ± IC95 ; taille de lot pratiquée moyenne / max)

| ×W | size1 OTD | size16 OTD | lot pratiqué (global) | lot au goulot | conflits (size16) | encours size1 | P95 retard size16 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2,9 ± 0,5 | 3,2 ± 0,5 | 1,42 / 11 | 2,16 | 0,5 | 8,0 | 53 h |
| 2 | 64,6 ± 5,2 | 77,6 ± 2,3 | 1,43 | 2,20 | 1,6 | 8,1 | 35 h |
| 3 | 80,9 ± 2,8 | **83,8 ± 1,3** (pic) | 1,43 | 2,21 | 2,7 | 8,3 | 34 h |
| 5 | **85,4 ± 1,2** (pic) | 82,9 | 1,43 | 2,22 | 4,7 | 8,7 | 34 h |
| 8 | 85,2 | 83,5 | 1,42 | 2,26 | 4,7 | 8,8 | 35 h |
| 12 | 84,3 | 82,3 | 1,44 | 2,33 | 5,3 | 9,6 | 38 h |
| 15 | 84,1 | 82,3 | **1,46** | **2,38** | **6,0** | 9,6 | **40 h** |

## Lecture

- **Hausse puis plateau puis légère baisse** : pic à 3–5 × W (W ≈ 20–33 % de la fenêtre avec
  ce délai lognormal), puis −1,3 à −1,5 pts à 15 × W (dans la marge de l'IC95, mais le signe
  est cohérent avec la montée des conflits ×12 (0,5 → 6,0), du P95 (34 → 40 h à droite) et
  de la taille pratiquée au goulot (2,16 → 2,38)).
- **La taille de lot pratiquée croît bien avec la fenêtre/encours** — c'est la nouvelle
  métrique qui le montre — mais faiblement (encours 8 → 9,6 OF seulement) car à fenêtre
  croissante, c'est surtout le **carnet** (OF non lancés) qui grossit, pas les files en
  ligne : les files par poste restent courtes (~1 OF), donc les lots pratiqués restent
  petits (~1,4 en moyenne ; max 11 au plus profond avec size=16).
- **Influence de `size`** : size 4/8/16 quasi identiques (le plafond ne bite presque jamais
  sans attente ; seules les séries max diffèrent : 4 / 8 / 11). À iso-fenêtre, l'effet
  regroupement sur l'OTD vient donc de la **taille pratiquée** (file), pas du plafond.
- Le cas « fenêtre > lead » (lancement immédiat) n'est pas atteint ici (queue longue du
  délai lognormal) ; les points 12–15 × W montrent déjà la direction de la branche droite.

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-u-fenetre-immediate.json --out sdbr-mini-usine/results/u-fenetre-immediate
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/courbe_u.py \
  --results sdbr-mini-usine/results/u-fenetre-immediate --out sdbr-mini-usine/results/u-fenetre-immediate
```
