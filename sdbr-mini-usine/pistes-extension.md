# Pistes d'extension du simulateur S-DBR — remarques et propositions

Ce fichier reformule deux limites constatées sur `simulateur-sdbr-mini-usine.html`
(voir l'analyse Monte-Carlo dans [README.md](README.md)) et propose des façons de
les prendre en compte. Les références de pages renvoient à
`goldratt-standing-on-the-shoulders-of-giants.pdf` (Goldratt, 2006).

## 1. Reformulation des remarques

### 1.1 Ce que le simulateur montre bien

La mécanique des flux autour d'un goulot à capacité constante est reproduite
quantitativement (campagne Monte-Carlo, 30 réplications × 120 OF) :

- OTD qui chute sous 90 % en surcharge : **87,3 % à 99 %** de charge offerte sur
  Usinage, > 99 % jusqu'à 85 % (p. 9) ;
- explosion non linéaire de l'encours et de la traversée près de 100 % de charge
  (loi de Little : encours 1,66 → 8,60 OF, traversée P50 13,5 → 51,9 h de 60 % à
  99 %) ;
- capacité protectrice hors goulot (à 90 % sur Usinage : Préparation 37 %,
  Finition 40 % d'occupation, p. 10) ;
- règle des 5–10 % de rouges pour dimensionner le tampon (p. 16) et zones
  vert/jaune/rouge/noir (p. 15).

### 1.2 Remarque 1 — surcharge à capacité de goulot constante : l'attention managériale n'est pas modélisée

Avec 3 postes et un goulot à capacité constante, une surcharge ne se traduit que
par une file plus longue. Le simulateur ne met pas en évidence le mécanisme que
Goldratt décrit dans les grandes usines :

- **Fig. 1 (p. 12–13)** : trop d'encours → embouteillages (« traffic jams ») → plus
  d'OF rouges/noirs simultanés → **attention managériale saturée** → retards
  aggravés au-delà de ce que la file seule explique. Le HTML contient la courbe
  d'attention en qualitatif (`curveMetrics` / `attention(t)`), mais aucune
  dynamique : pas de pannes, pas d'expéditing, pas de saturation d'attention ;
- **rochers et eau (p. 6)** : un encours élevé masque les vrais problèmes
  (widget `initWater`, mais statique) ;
- **boucle vicieuse (p. 14)** : retard → « on lance plus tôt » → plus d'encours →
  plus de retard. Dans le sim, cette boucle n'apparaît qu'en statique (politiques
  A vs B appariées), jamais en dynamique ;
- **Hitachi (p. 8, 17)** : 20 000 SKU, demande sporadique, lancements de nouvelles
  gammes tous les 6 mois — c'est précisément cet environnement instable où le
  DBR réussit (DDP 40 % → 85 %) et où le Lean échoue, entre autres à cause de
  l'encours qui masque les problèmes.

### 1.3 Remarque 2 — pas de regroupements ni de tailles de lot

Le simulateur traite chaque OF individuellement (lot = 1) ; le seul effet de lot
est le temps de réglage de 1 h au changement de famille dans `ganttRun`
(`setup` si la famille change). Il ne met donc pas en évidence le paradoxe des
lots décrit par Goldratt (p. 5 et 13) : regrouper par famille économise des
réglages mais allonge et disperse les délais des OF en attente de leur lot, et en
production par lots le touch tombe sous 1 % du délai total, la priorité réelle
devenant « hot / red hot / drop everything ».

## 2. Propositions pour prendre ces remarques en compte

### 2.1 Court terme — dans le HTML autonome

1. **Paramètre `lot`** (taille de lot minimale par famille et par poste) : un OF
   attend que son lot soit plein ou qu'un délai maximal passe. Métriques MC à
   ajouter : délai P90, encours, part des réglages dans le temps occupé. Objectif :
   montrer que lot = 1 (flux tiré) domine, conformément à p. 5/13.
2. **Pannes + file d'attention finie** : panne aléatoire par poste ; chaque OF
   rouge/noir actif consomme de l'attention ; si l'attention est saturée, la
   réparation est différée → la panne s'allonge → perte de capacité. Métriques :
   % de temps en saturation d'attention, durée moyenne des pannes, OTD. Objectif :
   reproduire la pente droite de la Fig. 1 et montrer que la corde (moins de
   rouges) préserve de l'attention pour les vrais problèmes.
3. **Surcharges transitoires** : demande par paliers (ex. 110 % puis 70 % de la
   capacité du goulot, p. 8–9) au lieu d'un taux de Poisson constant. Métriques :
   OTD pendant/après la surcharge, temps de vidange de l'encours, comparaison
   « lancer plus tôt en réaction » vs « garder la corde ».

### 2.2 Moyen terme — dans le package `indeng` (SimPy)

Porter une usine à 10–20 postes (les archétypes V/A existent déjà dans
`indeng/archetypes/`) avec un CCR et des pannes, et mesurer le **nombre d'OF
simultanément rouges/noirs en fonction de l'encours** : c'est à cette échelle que
« l'excès d'encours nuit à l'attention managériale et à la résolution des
problèmes importants » devient flagrant. Cela rejoint la PR ouverte
« Comparer DBR, kanban et CONWIP dans IndEng » : la robustesse du système
temporel aux pannes (p. 10–11 — une panne ne consomme pas la capacité des postes
amont/aval) se mesure exactement avec ce dispositif.

### 2.3 Impact sur le GIF AVANT/APRÈS envisagé

Ces remarques rendent l'angle **« rochers et eau » (p. 6)** plus percutant que
le split-screen Gantt : AVANT = eau haute (encours élevé), rochers cachés,
urgences partout ; APRÈS = on baisse l'eau (la corde), les rochers émergent et
sont traités un par un, l'OTD remonte. Le générateur de frames pourrait s'appuyer
sur les snapshots de `ganttRun` + la métrique « OF rouges/noirs simultanés »
proposée en 2.1/2.2.

## 3. Où trouver les points d'ancrage dans le code

| Élément | Fichier / fonction |
| --- | --- |
| Courbe attention (qualitative) | `simulateur-sdbr-mini-usine.html` : `curveMetrics`, `attention` |
| Widget rochers/eau | `initWater` |
| Réglage par changement de famille (seul effet de lot) | `ganttRun` : `setup = state.last[p] !== j.family ? opt.setup : 0` |
| Panneau Monte-Carlo (métriques actuelles) | `ganttMonteCarlo`, `mcGo` dans `initSim` |
| Rejeu hors navigateur | `scripts/run_montecarlo.mjs` |
| Archétypes V/A pour une « grande usine » | `indeng/archetypes/v_plant.py`, `a_plant.py` |
