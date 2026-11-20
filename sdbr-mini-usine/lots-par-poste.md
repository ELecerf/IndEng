# Lots par poste : regrouper où, et pour quel effet sur l'OTD ?

Scénario : `scenario-lots-par-poste.json` · résultats : `results/lots-par-poste/`
Nouveauté moteur : **`size` accepte une liste d'une taille de lot par poste**
(avant : un seul entier pour tous les postes) — voir `scripts/run_congestion.py`
(`sizes[p]`) et le test `test_lot_a_taille_par_poste`.

Même ligne que `lots-series.md` : 10 postes, goulot central `poste_5` (6 h + 2 h de
réglage), 2 familles, pic de charge 1,10, transfert **unitaire**, fenêtres 120/168 h,
20 graines, warm-up 400 h.

## 1. Variantes testées (taille de lot par poste)

| variante | `size` par poste | idée |
| --- | --- | --- |
| `unitaire` | 1 partout | témoin flux d'une pièce |
| `partout_lot8` | 8 partout | lots à tous les postes |
| `sauf_goulot_lot8` | 8 partout **sauf 1 au goulot** | lots hors CCR uniquement |
| `goulot_seul_lot8` / `goulot_seul_lot16` | 1 partout **sauf 8/16 au goulot** | lots au CCR uniquement |

(règle `family_fifo` pour les variantes lotées, `due` pour le témoin)

## 2. Résultats (20 graines, fenêtre 168 h, phase globale)

| variante | OTD global (IC95) | OTD pic | conflits avec retard | retard P95 | réglages poste_5 | réglages postes 1–4, 6–10 |
| --- | --- | --- | --- | --- | --- | --- |
| `goulot_seul_lot8/16` | **91,9 ± 2,2 %** | 86,1 % | 10,35 | **13,9 h** | 137 h (−45 %) | ~117 h (inchangé) |
| `unitaire` | 84,6 ± 6,4 % | 85,2 % | 0,00 | 26,1 h | 247 h | ~122 h |
| `sauf_goulot_lot8` | 56,5 ± 2,2 % | 52,2 % | 6,05 | 59,3 h | 137 h | ~113 h (−8 %) |
| `partout_lot8` | 51,6 ± 2,2 % | 48,6 % | 4,80 | 65,4 h | 137 h | ~113 h |

## 3. Lecture

- **Regrouper au goulot améliore l'OTD (91,9 % vs 84,6 % en unitaire)** : chaque
  réglage économisé au CCR rend de la capacité à la contrainte (étapes 2 et 4 de la
  TOC, p. 16–17) → traversée P95 divisée par ~2. Les séries au goulot bloquent
  certes des rouges (10,35 conflits) mais, le CCR étant plus rapide, ils partent
  presque à l'heure.
- **Regrouper hors goulot dégrade l'OTD (56,5 %, et 51,6 % si on regroupe partout)** :
  les séries aux postes périphériques retardent les pièces en transit — un OF urgent
  attend derrière la série — sans rapporter de capacité système, puisque ces postes
  ont de la capacité protectrice (p. 3, 10 : « abolir les efficacités locales » — ici
  l'économie de réglage locale se paie en flow). Le P95 passe de 26 h à 59–65 h.
- **La taille au goulot (8 vs 16) ne change presque rien** : la série effective y est
  bornée par la file disponible ; c'est le *fait* de regrouper au CCR (moins de
  changeovers) qui compte.
- Bilan : dans cette configuration, la règle « lot au CCR, flux unitaire ailleurs »
  domine nettement (`goulot_seul` > `unitaire` > `sauf_goulot` > `partout`), à la
  fois en OTD et en temps de réglage au poste contraint.

## 4. Reproduction

```bash
.venv/bin/python -m pytest -q   # inclut test_lot_a_taille_par_poste
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-lots-par-poste.json --out sdbr-mini-usine/results/lots-par-poste
```
