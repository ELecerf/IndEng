# Tableau de bord — le U de Goldratt vu par la fenêtre de lancement

Scénario : `scenario-dashboard-u.json` · campagne : `results/dashboard-u/` (replications, synthese)
· **tableau de bord** : `results/dashboard-u/dashboard_*.md` + `dashboard_*.csv` + `u_*.png`,
générés par `scripts/dashboard_u.py`.

## 1. Protocole

Ligne 10 postes, goulot central `poste_5`, demande à pics (0,70 → 0,95 → 1,15 → 1,30 →
0,85), délai client relatif (`requestedLeadWorkMultiple: [2,7]` → [48, 168] h pour
W = 24 h), **13 tailles de fenêtres** de 0,5×W à 14×W (12 → 336 h ; au-delà du délai
client max, lancer = immédiat), 20 graines, 2 variantes (témoin ×1 et surcapacité
goulot ×1,5). Traitement unitaire, transfert unitaire.

## 2. KPIs et indice d'attention

Par (variante, graine, fenêtre) : OTD, encours, **file moyenne** (`file_moy`),
**ruptures de charge** (`ruptures`, `ruptures_carnet`), **changements de série**
(`changements`), **opportunités de regroupement** (`opportunites` : familles avec ≥2 OF
en file à chaque décision), conflits avec retard, retards P50/P95.

**Indice d'attention (0–2)** = groupe *flux* + groupe *ordonnancement* :
`moy(norm(ruptures_carnet), norm(changements)) + moy(norm(opportunites), norm(file))`
(norm = min-max par variante sur tout le balayage) — exactement les deux familles de
composantes demandées : ruptures/changements d'un côté, opportunités/files de l'autre.

## 3. Lecture du U (témoin ×1, phase globale, 20 graines)

| fenêtre | OTD % ± IC95 | attention | encours | file | retard moy. h |
| --- | --- | --- | --- | --- | --- |
| 12 h (0,5×W) | **0,0** | 1,57 | 12,8 | 9,0 | 85,5 |
| 48 h (2×W) | 30,8 ± 4,9 | 1,59 | 13,0 | 9,1 | 53,2 |
| 96 h (4×W) | 55,0 ± 6,8 | 1,60 | 13,0 | 9,2 | 31,0 |
| 120 h (5×W) | 59,0 ± 6,9 | 1,60 | 13,2 | 9,4 | 27,0 |
| 168 h (7×W) | 61,6 ± 6,4 | 1,61 | 13,4 | 9,5 | 23,8 |
| ≥ 168 h | 61,6 (plateau) | 1,61 | 13,4 | 9,5 | 23,8 |

- **Branche gauche du U très nette via l'OTD** : 0 % à 12 h → 61,6 % au plateau
  (≥ 5×W ≈ 120 h). En phase creux : 0 % → **99,3 %** dès ~6×W. C'est la Fig. 1 de
  Goldratt (p. 12–13) : tampon trop court → alésas non absorbés → tout est en retard.
- **Plateau large** à partir de ~5×W, conforme au « plateau » de la Fig. 1 et à la
  règle « tampon ≈ moitié du délai actuel » (p. 14) : ici délai client moyen 108 h,
  tampon utile ≈ 48–120 h (2–5×W).
- **Branche droite (fenêtres longues)** : visible sur les files/encours en pic —
  `file` passe de 6,2 à 8,9 OF (+43 %) de 12 h à 168 h — ce sont les « embouteillages »
  (p. 12) ; avec des promesses tirées par le client, l'OTD ne se dégrade pas à droite
  (le délai client apporte la marge), donc le U complet en OTD demanderait des
  promesses fixées par la capacité du goulot (mode « sous charge » du HTML).
- **Indice d'attention** : quasi plat en global (1,57 → 1,61) car ruptures et
  changements sont ici dominés par l'inactivité structurelle des postes hors goulot ;
  la composante `file` porte la branche droite. Nuage de points par réplication :
  `u_temoin_cap_x1.png`.
- **Surcapacité ×1,5** : le U monte et se décale — OTD 99,8 % dès ~6×W, encours ~5 OF
  (vs 13,4), retard ~0 : élever la contrainte (étape 4, p. 16–17) élargit le plateau
  vers le haut.

## 4. Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-dashboard-u.json --out sdbr-mini-usine/results/dashboard-u
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/dashboard_u.py \
  --results sdbr-mini-usine/results/dashboard-u --out sdbr-mini-usine/results/dashboard-u
```
