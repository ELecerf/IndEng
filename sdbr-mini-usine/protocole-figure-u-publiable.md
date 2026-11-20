# Prompt amélioré (exécuté : voir figure-u.md et results/figure-u/) : figure publiable/académique du U de Goldratt

Objectif : produire une **figure publiable/académique du U de Goldratt** (OTD vs fenêtre
de lancement) sur la ligne S-DBR 10 postes, avec lot mini progressif, et un **protocole
de test renforcé** pour que le U soit indiscutable.

## 1. Protocole statistique renforcé

- **10 graines appariées** (décision du 20/11 : 10 seeds pour le test) (mêmes arrivées, familles, promesses et durées entre politiques
  à fenêtre donnée) → IC95 de Student resserrés.
- Fenêtres : sweep fin **1–45×W** (retenu : 1, 1,5, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 30, 35, 40, 45 — dense en petites fenêtres),
  incluant le **point de saturation** (≥ lead max 40×W = lancement immédiat).
- Variantes : `fixe1` (témoin), `fixe8`, `fixe16`, `progressif` (k = 0,25), `rapide` (k = 1) —
  plafond `size` = 16 et attente 168 h identiques partout (iso-lot).
- Pic ρ = 1,30 conservé ; métriques : OTD global + par phase, **zones de couleur**,
  encours, taille de lot réalisée, conflits avec retard, attente-lot au goulot.
- IC95 de Student **appariés par graine** ; documenter l'absence de correction pour
  comparaisons multiples (ou ajouter Bonferroni sur les écarts adjacents au maximum).

## 2. Figure publiable (vectorielle)

- **3 panneaux (a)(b)(c)**, format ~17×12 cm (double colonne), export **PDF + SVG + PNG 300 dpi**, axe des abscisses en **échelle log₂** (ticks 1, 2, 4, 8, 16, 32) :
  - **(a)** OTD % vs fenêtre en ×W, une courbe par politique avec barres d'IC95, bande grise
    « W ≈ 10–15 % de la fenêtre », annotations des 3 régimes (branche gauche / plateau /
    branche droite), point de saturation repéré ;
  - **(b)** distribution des OF en **zones vert/jaune/rouge/noir** (barres empilées 100 %) vs ×W
    pour la variante `progressif` ;
  - **(c)** taille de lot **réalisée** et/ou encours vs ×W (mécanique de la branche droite).
- Palette **compatible daltonisme**, grille légère, police ≥ 8 pt, **pas de titre dans la
  figure** (la légende LaTeX porte le titre), axes en français auto-explicatifs.
- Livrer aussi le **snippet LaTeX** (figure + légende) et le **CSV des statistiques**
  (moyennes, IC, écarts appariés).

## 3. Outillage et test

- Nouveau script `figure_u.py` (run_hypotheses + zones_couleur + figure vectorielle 3 panneaux) ;
  tests unitaires sur le calcul des zones et des IC appariés.
- Reproduction en une commande documentée.

## 4. Critères de succès

Sur le panneau (a), le U est visible à l'œil nu pour `progressif`/`fixe16` (montée → plateau
→ baisse) pendant que le témoin `fixe1` reste plat à 100 % ; sur (b), la bascule vers
rouge/noir apparaît nettement à droite (grande fenêtre).
