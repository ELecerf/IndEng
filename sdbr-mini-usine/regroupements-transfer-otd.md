# OTD à fort encours avec regroupements et transferts par batch

Scénario : `scenario-regroupements-transfer-otd.json` · résultats :
`results/regroupements-transfer-otd/`

**Hypothèse testée** : à fort encours (grande fenêtre de lancement), l'OTD devrait
rester mauvais quand il y a des regroupements (lots) et/ou des transferts par batch —
les séries et les trains bloquent les OF urgents.

## Protocole

Ligne 10 postes, goulot central `poste_5`, pic de charge (1,15), délai client
2–7×W (48–168 h). Croisement de 3 fenêtres (2×W = 48 h, 5×W = 120 h, 10×W = 240 h —
au-delà du délai max ⇒ lancement immédiat, fort encours) × 5 modes : unitaire (témoin),
lots size 8 (`family_fifo`), transfert `bloc` de 8, train logistique N=8, et le combo
lots 8 + train 8. 20 graines.

## Résultats (moyennes 20 graines)

| variante | fenêtre | OTD global % | encours OF | file OF | conflits avec retard | retard P95 h |
| --- | --- | --- | --- | --- | --- | --- |
| unitaire | 48 h | 41,6 | 8,9 | 5,2 | 0 | 85 |
| unitaire | 120 h | 78,3 | 9,0 | 5,2 | 0 | 40 |
| **unitaire** | **240 h (fort encours)** | **81,6 ± 6,5** | 9,1 | 5,3 | 0,00 | 34 |
| lots 8 | 240 h | **50,4 ± 2,5** | 13,8 | 8,2 | 4,65 | 70 |
| transfert bloc 8 | 240 h | **32,1 ± 2,8** | 17,9 | 8,7 | 4,55 | 133 |
| train 8 | 240 h | **0,0** | 35,5 | 16,4 | 0,00 | 247 |
| lots 8 + train 8 | 240 h | **0,0** | 35,9 | 12,6 | 22,70 | 252 |

(En pic : unitaire 240 h → OTD 83,5 % ; lots 8 → 47 % ; bloc 8 → 24 % ; train 8 → 0 %.)

## Lecture

- **Confirmé** : à fort encours (fenêtre 240 h), l'OTD unitaire reste haut (81,6 %)
  mais s'effondre avec les regroupements (lots 8 → 50,4 %, transfert bloc → 32,1 %)
  et s'annule carrément avec un transfert par train de 8 (0,0 %, retard P95 247 h).
- Mécanisme : les séries (lots) et les transferts par batch ajoutent des **attentes
  structurelles** (remplissage du lot/train) à la traversée — à fort encours, ces
  attentes s'ajoutent aux files du goulot et mangent toute la marge de la fenêtre ;
  d'où aussi un encours plus élevé (9 → 36 OF, loi de Little) et des conflits
  vert-devant-rouge (jusqu'à 22,7 avec le combo).
- Côté Goldratt : p. 5–6 et 13 (petits lots, flux d'une pièce — les gros lots rendent le
  touch < 1 % du délai et créent les priorités « hot/red hot »), p. 12 (embouteillages à
  fort encours). Règle pratique : à fort encours, éviter lots et transferts par batch ;
  au contraire, au goulot, le lot peut être utile (capacité gagnée, cf.
  `lots-par-poste.md`) — mais jamais combiné à un transfert par batch.

## Reproduction

```bash
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py \
  sdbr-mini-usine/scenario-regroupements-transfer-otd.json --out sdbr-mini-usine/results/regroupements-transfer-otd
```
