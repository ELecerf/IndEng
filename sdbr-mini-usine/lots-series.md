# Lots et séries au goulot : les OF urgents bloqués par les regroupements

Scénario : `scenario-lots-series.json` · résultats : `results/lots-series/`
Moteur : `scripts/run_hypotheses.py`, 20 graines (42–61), transfert **unitaire**.

**Question** : comment créer, dans un scénario, des *séries substantielles* au poste
goulot qui empêchent des OF urgents (rouges) de finir à l'heure — et que valent les
lots face au flux unitaire ?

## 1. Recette pour créer des séries bloquantes (transfert unitaire)

Avec `transfer: "unitaire"`, chaque OF quitte le poste un par un ; c'est le couple
**`size` + `dispatchRule`** qui crée les séries au poste goulot :

- `size > 1` + `dispatchRule: "family_fifo"` : le goulot constitue un lot de jusqu'à
  `size` OF de la **même famille**, traité en bloc consécutif (un seul réglage, puis
  toute la série, qui peut se prolonger tant que la famille reste éligible). Pendant
  la série, les OF de l'autre famille — même urgents — restent en file ;
- `maxBatchWaitHours` **modéré (6 h)** : assez pour qu'un lot se forme en congestion,
  assez court pour que le goulot ne reste jamais inactif en creux (piège constaté en
  smoke test : `maxBatchWaitHours: 24` avec `size≥4` affame le poste à faible charge →
  OTD ~0 par famine, artefact à éviter — TOC : ne jamais laisser le goulot inactif) ;
- **vrai temps de réglage au goulot (2 h)** : le lot a un bénéfice local réel
  (moins de réglages) auquel on peut comparer son coût en OTD ;
- **deux familles + un pic de charge (ρ = 1,10)** : la file du goulot contient les
  deux familles et des OF passent en zone rouge ;
- **fenêtres larges (120/168 h)** : le témoin unitaire atteint alors une OTD élevée,
  donc la chute d'OTD observée avec les lots est attribuable aux séries, pas au tampon.

Métriques clés (déjà produites par le moteur) : `conflits` = démarrages *verts* alors
qu'un *rouge* d'une autre famille attendait ; `conflits_avec_retard` = ce rouge a fini
en retard ; `conflits.csv` détaille chaque événement (promesse vs livraison du rouge).

## 2. Protocole retenu

Ligne 10 postes, goulot central `poste_5` (6 h/OF, réglage 2 h ; 2 h ailleurs, réglage
1 h), familles A/B 50/50, durées lognormales CV 0,3, délai client U(48,168) h, phases
creux 0,70 (480 h) → normal 0,95 (480 h) → **pic 1,10 (240 h)** → reprise 0,85 (720 h),
warm-up 400 h, 20 graines. Variantes (transfert unitaire partout) :

| variante | size | règle |
| --- | --- | --- |
| `unitaire` (témoin) | 1 | due |
| `lot4_famille` / `lot8_famille` / `lot16_famille` | 4 / 8 / 16 | family_fifo |
| `lot8_echeance` | 8 | due (lot de la famille la plus urgente) |

## 3. Résultats (moyennes 20 graines, fenêtre 168 h)

| variante | OTD global (IC95) | OTD pic | conflits avec retard | retard P95 | regroupements | réglages goulot (h) |
| --- | --- | --- | --- | --- | --- | --- |
| **unitaire** | **84,6 ± 6,4 %** | 85,2 % | **0,00** | 26,1 h | 0 | 247 |
| lot4/8/16 famille | 51,5–51,6 ± 2,2 % | 48,3–48,6 % | **4,80** | ~65 h | ~686 | ~137 |
| lot8 échéance | 47,2 ± 3,4 % | 42,7 % | 1,85 | 59,2 h | ~669 | ~159 |

Détail causal (`conflits.csv`, 517 conflits) : **510 des 517 rouges bloqués derrière
une série ont été livrés en retard (98,6 %)** — le mécanisme « série au goulot → OF
urgent de l'autre famille en retard » est direct et quasi systématique.

## 4. Interprétation

- **Les lots échangent du temps de réglage contre de l'OTD** : −45 % d'heures de
  réglage au goulot (247 → 137 h), mais −33 points d'OTD global et retard P95 ×2,5.
  La taille exacte du lot (4/8/16) importe peu ici : la série effective est bornée par
  la file disponible et prolongée par `family_fifo` tant que la famille reste éligible.
- **La règle de priorité change le motif, pas le fond** : `due` (lot de la famille la
  plus urgente) réduit les conflits-avec-retard (4,8 → 1,9) mais l'OTD reste basse —
  la continuité de famille au CCR sacrifie quand même des urgences.
- **Côté Goldratt** : conforme à p. 5–6 (Ohno : les réglages ne sont pas figés, viser
  les petits lots / flux d'une pièce, « economical batch quantity » n'est pas
  économique) et p. 13 (en lots > 10, le touch < 1 % du délai et la priorité réelle
  devient « hot / red hot »). La TOC ajoute (p. 15–17) : **au CCR, l'urgence (rouge)
  prime sur la continuité de famille** — exploiter/subordonner la contrainte, ne pas
  la laisser tourner en longues séries pour économiser des réglages.
- Le témoin unitaire avec règle `due` atteint 84,6 % d'OTD globale (100 % des pics
  non surchargés) avec 0 conflit : à ce niveau de variabilité, le flux d'une pièce
  domine le lot au goulot.

## 5. Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-lots-series.json --out sdbr-mini-usine/results/lots-series
```
