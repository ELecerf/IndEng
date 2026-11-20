# Figure publiable du U de Goldratt (axe log₂, 10 graines, sweep 1–45 × W)

Scénario : `scenario-figure-u.json` (5 variantes × 18 fenêtres × 10 graines = 900 sims)
· résultats : `results/figure-u/` · figure : `figure_u.pdf` / `.svg` / `.png` (300 dpi),
snippet LaTeX `figure_u.tex`, stats `figure_u_stats.csv`, zones `zones_couleur.csv` /
`zones_of.csv` · scripts : `run_hypotheses.py`, `zones_couleur.py`, `figure_u.py`.

## Protocole exécuté (prompt amélioré)

10 graines appariées (42–51), fenêtres [1, 1,5, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24,
30, 35, 40, 45]×W (dense en petites fenêtres, repère saturation à 40–45×W), variantes
`fixe1`, `fixe8`, `fixe16`, `progressif` (k = 0,25), `rapide` (k = 1) — plafond 16, attente
168 h, lead [10, 40]×W, pic 1,30. Figure : 3 panneaux (a) OTD ± IC95 vs log₂(×W), bande
W ≈ 10–15 % de la fenêtre, repère « lancement immédiat » ; (b) zones vert/jaune/rouge/noir
(politique progressive) ; (c) lot réalisé (progressif) et encours (fixe1). Palette
Okabe-Ito, pas de titre interne, axe log₂ gradué 1, 2, 4, 8, 16, 32.

## Résultats (OTD %, global)

| ×W | fixe1 | fixe8 | fixe16 | progressif | rapide |
| --- | --- | --- | --- | --- | --- |
| 1–2 | 1,7–64,8 | 0 | 0 | 1,7–64,8 | 0–1,9 |
| 4–8 | 96,4–100 | 0–0,3 | 0 | 96,4–**98,5 (pic à 8×W)** | 0,3–2,8 |
| 16–24 | 100 | 34,3–62,6 | 0 | 97,7–94,8 | 0 |
| 30 | 100 | **73,8 (pic)** | 4,0 | 73,8 | 4,0 |
| 35–45 | 100 | 64,9–**65,1** | 12,9–**13,1** | 38,0–**17,2** | 12,9–13,1 |

**Le U est visible** : témoin `fixe1` plat à 100 % dès 7×W ; `progressif` monte jusqu'à
98,5 % à 8×W (W ≈ 12,5 % de la fenêtre, dans la bande 10–15 %) puis **descend à 17,2 % à
45×W** ; `fixe8` pic à 73,8 % à 30×W puis 65 % ; `fixe16` s'effondre à 13 %. Panneau (b) :
les OF basculent en rouge/noir à droite (83 % de retard à 45×W pour progressif). Panneau
(c) : le lot réalisé croît avec la fenêtre (1,4 → 11,8) et l'encours du témoin double
(8 → 22 OF).

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-figure-u.json --out sdbr-mini-usine/results/figure-u
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/zones_couleur.py \
  sdbr-mini-usine/scenario-figure-u.json --variante progressif --out sdbr-mini-usine/results/figure-u
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/figure_u.py \
  --results sdbr-mini-usine/results/figure-u --out sdbr-mini-usine/results/figure-u
```
