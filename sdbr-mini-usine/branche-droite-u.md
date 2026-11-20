# Branche droite du U : fenêtre jusqu'à 100 × W (valeur ajoutée ≈ 1 % du délai)

Scénario : `scenario-branche-droite-u.json` · campagne + dashboard :
`results/branche-droite-u/` (replications + `u_temoin.png` + `dashboard_*.md/csv`)

**Reformulation testée** : la branche droite du U (Fig. 1, p. 12–13) correspond aux très
grands tampons — fenêtre ≈ 100 × W, soit un temps opératoire (valeur ajoutée) ≈ 1 %
du délai théorique (p. 13 : en production par lots, le touch < 1 % du lead time). Mais
la fenêtre sature au délai client (`release = max(arrivée, échéance − fenêtre)`) : pour
que la branche droite soit atteignable, il faut que **la demande client soit du même
ordre**, d'où ici `requestedLeadWorkMultiple: [50,150]` (délai 1200–3600 h = 50–150×W)
et des fenêtres balayées de 0,5×W à 100×W (12 → 2400 h). W = 24 h.

## Résultats (témoin, phase globale, 20 graines, axe en multiples de W)

| fenêtre (×W) | OTD % | encours OF | file OF | ruptures carnet | changements | opportunités | indice attention (0-2) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0,5 | **0,0** | 0,30 | 0,01 | 158 | 71 | 169 | 0,12 |
| 1 | 25,1 | 0,31 | 0,01 | 163 | 73 | 176 | 0,12 |
| 2 | 100,0 | 0,33 | 0,01 | 175 | 79 | 188 | 0,13 |
| 8 | 100,0 | 0,46 | 0,02 | 238 | 114 | 256 | 0,18 |
| 32 | 100,0 | 1,24 | 0,13 | 570 | 303 | 638 | 0,45 |
| 50 | 100,0 | 2,09 | 0,32 | 874 | 487 | 1020 | 0,71 |
| 100 | 100,0 | **6,10** | **2,76** | 1486 | 935 | 1909 | **1,35** |

## Lecture

- **Branche gauche (petites fenêtres)** : OTD 0 % à 0,5×W → 100 % dès 2×W — le délai
  client étant énorme, la marge masque tout ; le U en OTD se réduit ici à sa branche
  gauche + plateau (avec des promesses client serrées, c'est l'inverse : plateau à
  droite, chute à gauche — cf. `dashboard-u.md`).
- **Branche droite (grandes fenêtres)** : encours et files croissent **quasi
  linéairement avec la fenêtre** (0,30 → 6,10 OF ; loi de Little : encours ≈ débit ×
  temps passé en atelier ≈ min(fenêtre, délai)) et l'**indice d'attention monte de
  0,12 à 1,35** (ruptures, changements de série, opportunités de regroupement montent
  avec la congestion) — c'est la branche droite du U : à 100×W, W ne vaut plus que
  **1 % du lead time** (p. 13), tout est lancé quasi immédiatement, les files
  s'allongent → « embouteillages » (p. 12).
- **Le U complet** = branche gauche en OTD/lateness + branche droite en
  encours/attention ; la fenêtre utile reste le plateau (quelques ×W), conforme à
  « tampon ≈ moitié du délai actuel » (p. 14).

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-branche-droite-u.json --out sdbr-mini-usine/results/branche-droite-u
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/dashboard_u.py \
  --results sdbr-mini-usine/results/branche-droite-u --out sdbr-mini-usine/results/branche-droite-u
```
