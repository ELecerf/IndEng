# Simulateur S-DBR « mini-usine » — analyse Monte-Carlo à la lumière de Goldratt

Ce dossier est dédié à l'analyse du simulateur HTML autonome **S-DBR mini-usine**
(Drum-Buffer-Rope) et à la vérification expérimentale des écrits d'Eliyahu Goldratt,
en particulier son article *Standing on the Shoulders of Giants — Production concepts
versus production applications: The Hitachi Tool Engineering Example* (2006), fourni
à côté de ce README.

## Contenu du dossier

```
sdbr-mini-usine/
├── README.md                                          ← ce fichier (analyse)
├── simulateur-sdbr-mini-usine.html                    ← la simulation autonome (ressource d'origine)
├── goldratt-standing-on-the-shoulders-of-giants.pdf   ← article de Goldratt (2006, 19 p.)
├── pistes-extension.md                                ← limites reformulées + pistes d'extension
├── scenario-surcharge-10-postes.json                  ← campagne 10 postes / pics / surcapacités goulot
├── surcharge-10-postes.md                             ← analyse de cette campagne (lancer tôt vs OTD)
├── scenario-lots-series.json                          ← campagne lots/séries au goulot (transfert unitaire)
├── lots-series.md                                     ← analyse : séries bloquant les OF urgents
├── scenario-lots-par-poste.json                       ← lots à taille par poste (size = liste)
├── lots-par-poste.md                                  ← analyse : regrouper au goulot vs hors goulot
├── scenario-train-logistique.json                     ← train logistique : un seul paramètre transfer = N
├── train-logistique.md                                ← analyse : l'OTD s'effondre quand le train grossit
├── scripts/
│   └── run_montecarlo.mjs                             ← rejoue le Monte-Carlo du HTML sous Node
└── results/
    ├── surcharge-10-postes/                           ← campagne 10 postes (CSV, IC95, otd.png)
    ├── lots-series/                                   ← campagne lots/séries (CSV, conflits.csv, otd.png)
    ├── lots-par-poste/                                ← campagne lots par poste (CSV, otd.png)
    ├── train-logistique/                              ← campagne train logistique N=1..16 (CSV, otd.png)
    ├── montecarlo_replications.csv                    ← 2700 lignes (30 réplications × 18 scénarios × 5 politiques)
    ├── montecarlo_summary.csv                         ← moyenne ± demi-IC95 par scénario × indicateur
    └── montecarlo_summary.md                          ← tableaux prêts à lire
```

## 1. Le modèle du simulateur HTML

Fichier autonome (aucune ressource externe) : trois postes en série —
**Préparation → Usinage → Finition** — capacité 1 chacun.

- **Gammes** : deux familles (● = [2, 5, 2] h ; □ = [1,5, 5,5, 2] h), soit ~9 h nominal
  par OF sur les trois postes ; les durées réelles varient de ±25 % ; changement de
  famille = 1 h de réglage.
- **Arrivées** : processus de Poisson (taux réglé par la charge offerte cible au poste
  choisi) ; délai demandé par le client ~ uniforme autour d'une moyenne (120 h dans le
  panneau Monte-Carlo).
- **Promesse** : `échéance = max(demandé client, arrivée + tampon S-DBR)` ;
  **lancement (corde) = échéance − tampon**.
- **Priorités par tampon** (buffer management) : pénétration = 1 − (reste/tampon) ;
  vert < 1/3, jaune < 2/3, rouge ≥ 2/3, noir passé l'échéance — exactement le code
  couleur de Goldratt (p. 15).
- **Politiques comparées** : A = lancement immédiat + FIFO, B = fenêtre (corde) + FIFO,
  C = fenêtre + priorité au tampon restant croissant.
- **Panneau Monte-Carlo** : N réplications × 120 OF mesurés (cohorte = 120 derniers OF,
  warm-up 150 h), indicateurs : OTD promis, service demandé, % de rouges parmi les
  expédiés, encours moyen atelier, débit, files et occupation par poste, quantiles de
  traversée ; moyenne ± demi-largeur d'IC 95 % (approximation de la loi de Student
  utilisée par le HTML).

## 2. Protocole de reproduction

Le script `scripts/run_montecarlo.mjs` extrait le `<script>` du HTML **tel quel**
(source unique de vérité) et rejoue la campagne Monte-Carlo sous Node :

```bash
node sdbr-mini-usine/scripts/run_montecarlo.mjs --reps 30
# options : --html <chemin> --out <dir> --reps N
```

Trois familles de scénarios (graine 42, 30 réplications × 120 OF, warm-up 150 h,
tampon 90 h sauf mention contraire, goulot = Usinage) :

1. **Balayage de charge** : charge offerte au poste Usinage de 60 % à 99 % ;
2. **Balayage du tampon S-DBR** : 30 → 180 h à charge 90 % ;
3. **Balayage du poste ciblé** : 90 % sur Préparation / Usinage / Finition.

À chaque réplication, les 5 politiques (C, FIFO-fenêtre, A, B, C appariées) sont
jouées avec la même graine, comme dans le panneau du HTML.

## 3. Résultats (moyenne ± demi-IC95, politique C · Fenêtre/tampon)

### 3.1 Charge offerte au poste Usinage (tampon 90 h)

| Charge | Occ. Usinage | OTD promis | Service | Rouges | Encours atelier | Débit | Traversée P50 | Traversée P90 | Délai client P50 | % dans 2/3 tampon |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 60 % | 62,5 % | 100,0 % | 100,0 % | 0,0 % | 1,66 OF | 0,11 OF/h | 13,5 h | 23,3 h | 44,4 h | 100 % |
| 80 % | 83,0 % | 100,0 % | 100,0 % | 1,4 % | 3,29 OF | 0,14 OF/h | 20,8 h | 36,6 h | 51,5 h | 98,6 % |
| 85 % | 87,3 % | 99,3 % | 99,2 % | 5,4 % | 4,20 OF | 0,15 OF/h | 25,3 h | 44,8 h | 56,9 h | 94,6 % |
| 90 % | 91,2 % | 96,8 % | 96,4 % | 12,6 % | 5,44 OF | 0,16 OF/h | 32,7 h | 55,4 h | 63,8 h | 87,4 % |
| 95 % | 94,1 % | 92,9 % | 92,1 % | 23,7 % | 7,03 OF | 0,16 OF/h | 42,4 h | 68,9 h | 73,5 h | 76,3 % |
| 99 % | 95,9 % | **87,3 %** | 86,4 % | 35,7 % | 8,60 OF | 0,17 OF/h | 51,9 h | 80,9 h | 82,7 h | 64,3 % |

### 3.2 Taille du tampon S-DBR (charge 90 % sur Usinage)

| Tampon | OTD promis | % rouges | % expédiés dans 1er 1/3 | % dans 2/3 | Verdict règle 5–10 % (comme `bufferRule()` du HTML) |
| --- | --- | --- | --- | --- | --- |
| 30 h | 53,3 % | 67,8 % | 4,6 % | 32,2 % | Allonger le tampon |
| 60 h | 87,9 % | 32,2 % | 32,2 % | 67,8 % | Allonger le tampon |
| 90 h | 96,8 % | 12,6 % | 53,2 % | 87,4 % | Allonger le tampon |
| 120 h | 99,9 % | 4,7 % | 68,3 % | 95,3 % | Réduire le tampon |
| 150 h | 100,0 % | 1,8 % | 81,4 % | 98,2 % | Réduire le tampon |
| 180 h | 100,0 % | 0,1 % | 88,1 % | 99,9 % | Réduire le tampon |

### 3.3 Poste ciblé à 90 % (la vraie contrainte est le poste le plus chargé)

| Poste ciblé | Charge offerte P/U/F | Occupation P/U/F | OTD promis | Encours atelier | File moyenne Usinage |
| --- | --- | --- | --- | --- | --- |
| Préparation | 94 / **239** / 104 % | 91 / **100** / 43 % | **0,1 %** | 61,2 OF | 54,5 OF |
| Usinage | 37 / 94 / 41 % | 37 / 91 / 40 % | 96,8 % | 5,44 OF | 3,66 OF |
| Finition | 84 / **217** / 94 % | 84 / **100** / 43 % | **0,2 %** | 53,6 OF | 49,2 OF |

### 3.4 Politiques de lancement (mêmes promesses, mêmes graines appariées)

| Scénario | Politique | OTD | Encours atelier | Encours total (carnet inclus) | Débit | Délai client P50 |
| --- | --- | --- | --- | --- | --- | --- |
| Charge 90 % Usinage | A · Immédiat/FIFO | 98,9 % | 5,39 OF | 5,39 OF (carnet 0) | 0,16 OF/h | 31,4 h |
| Charge 90 % Usinage | B · Fenêtre/FIFO | 96,8 % | 5,45 OF | 10,54 OF (carnet 5,1) | 0,16 OF/h | 63,8 h |
| Charge 90 % Usinage | C · Fenêtre/tampon | 96,8 % | 5,44 OF | 10,53 OF (carnet 5,1) | 0,16 OF/h | 63,8 h |
| Surcharge réelle (Préparation ciblée, Usinage à 239 %) | A · Immédiat/FIFO | 0,0 % | **71,9 OF** | 71,9 OF | 0,17 OF/h | 416,6 h |
| Surcharge réelle | C · Fenêtre/tampon | 0,1 % | 61,2 OF | 74,3 OF (carnet 13,1) | 0,17 OF/h | 431,1 h |

Données complètes : `results/montecarlo_summary.md` et `results/montecarlo_summary.csv`.

## 4. Les écrits de Goldratt se vérifient-ils ? (article de 2006, pages entre parenthèses)

| # | Affirmation de Goldratt (PDF) | Prédiction | Mesure Monte-Carlo | Verdict |
| --- | --- | --- | --- | --- |
| 1 | En surcharge, la performance de dates chute « < 90 % » (p. 9) | OTD < 90 % quand la charge offerte approche 100 % du goulot | OTD = **87,3 %** à 99 % de charge sur Usinage ; 92,9 % à 95 % ; > 99 % jusqu'à 85 % | **Confirmé** |
| 2 | Améliorer le flux révèle de la capacité excédentaire, « jusqu'à 50 % » (p. 10) | Hors goulot, l'occupation doit rester bien sous 100 % (capacité protectrice) | À 90 % sur Usinage : Préparation 36,6 %, Finition 39,6 % d'occupation | **Confirmé** (~60 % de marge) |
| 3 | Le débit est fixé par la contrainte, pas par les efficacités locales (p. 3, 16–17) | Débit identique quelle que soit la politique de lancement | Débit = 0,16 OF/h pour A, B et C à 90 % ; 0,17 OF/h en surcharge pour toutes | **Confirmé** |
| 4 | Libérer tôt « pour occuper les postes amont » allonge les files sans gain de débit, et pousse vers la pente droite de la courbe (embouteillages) (p. 14) | Politique A : encours/délai client plus élevés en surcharge, débit inchangé | En surcharge : encours atelier A = 71,9 OF vs 61,2 (fenêtre), délai client 417 h vs 431 h, débit identique | **Confirmé** (la corde borne l'encours atelier) |
| 5 | Le temps opératoire ne représente qu'environ 10 % du délai ; le reste est de l'attente en file (p. 11) | touch ≪ traversée | touch moyen = **9,51 h/OF** ; à 90 % de charge, traversée P50 = 32,7 h (dont ~70 % d'attente) et délai client P50 = 63,8 h → touch ≈ 15,7 % du délai client ; vs la promesse (~120 h) : **7,9 %** | **Confirmé** (ordre de grandeur 10 %) |
| 6 | Hypothèse du DBR : touch < 10 % du délai promis, sinon CCPM (p. 18 ; seuils 10 %/30 % du widget du HTML) | DBR applicable ici | 9,51 / 120 ≈ 7,9 % < 10 % → zone « DBR » du simulateur | **Confirmé** (à la limite, comme le widget 90 h → 10,6 % = zone jaune) |
| 7 | Zones du tampon : vert < 1/3, jaune < 2/3, rouge ≥ 2/3, noir après échéance (p. 15) | « beaucoup » d'OF terminés dans le 1er tiers, « la majorité » dans les 2 premiers tiers | À 90 h / 90 % de charge : **53 %** dans le 1er tiers, **87 %** dans les 2/3 ; 100 % à faible charge | **Confirmé** |
| 8 | Règle de gestion du tampon : réduire si rouges < 5 %, allonger si > 10 % (p. 16) | La bande 5–10 % encadre le tampon utile | 90 h → 12,6 % de rouges (« allonger ») ; 120 h → 4,7 % (« réduire ») : la bande 5–10 % se situe entre 90 et 120 h, et l'OTD n'atteint les hautes 90 % que quand les rouges passent sous ~10 % | **Confirmé** |
| 9 | Tampon trop court → alésas non absorbés, retards massifs ; tampon très long → lancements précoces, encours élevés, « embouteillages » (p. 12–13, Fig. 1) | OTD effondré côté court, rendements décroissants côté long | OTD 53,3 % à 30 h → 100 % à 150 h ; mais débit constant (0,16 OF/h) et carnet nul à 180 h : au-delà du plateau, allonger le tampon n'achète plus rien | **Confirmé** (plateau visible entre 90 et 150 h) |
| 10 | Le tambour = la ressource la plus chargée pilote l'usine ; les promesses ne se donnent que sur la capacité non allouée du goulot (p. 16–17) | Cibler un poste non contraint à 90 % doit déplacer la contrainte vers Usinage et faire s'effondrer l'OTD | Préparation à 90 % → charge offerte Usinage 239 %, occupation 100 %, OTD **0,1 %**, encours 61 OF, traversée P50 ~400 h | **Confirmé** |
| 11 | Fluctuations statistiques + événements dépendants : les files s'accumulent de façon non linéaire près de 100 % (jeu de dés, p. 14 note) | Encours et traversée explosent quand ρ → 1 | Encours atelier 1,66 → 8,60 OF et traversée P50 13,5 → 51,9 h de 60 % à 99 % de charge (loi de Little vérifiée : encours ≈ débit × traversée) | **Confirmé** |
| 12 | Rochers et eau : un encours élevé masque les problèmes (p. 6) | À forte charge, la file devant le goulot rend la surcharge visible | File moyenne Usinage : 0,47 OF à 60 % → 6,70 OF à 99 % ; en ciblant le mauvais poste, 54 OF s'accumulent devant Usinage | **Confirmé** (le widget « eau/rochers » illustre la même idée) |
| 13 | Résultats Hitachi : DDP 40 % → 85 %, WIP et délais divisés par deux, +20 % expédié avec la même main-d'œuvre (p. 17) | Ordres de grandeur reproductibles en jouant sur le tampon seul | Même capacité, tampon 30 h → 120 h : OTD 53 % → 99,9 % (+47 points) sans ajouter de ressource | **Confirmé** (même direction, mêmes ordres de grandeur) |
| 14 | « Ne pas chercher à être plus précis que le bruit » dans la séquence au sein d'une même couleur (p. 14–15) | La priorité fine (tampon vs FIFO) ne change guère l'OTD quand la fenêtre est bonne | B (FIFO) vs C (tampon) : OTD 96,81 % toutes deux à 90 % — le gain vient de la fenêtre et de la taille du tampon, pas du réordonnancement fin | **Confirmé** (nuance : avec un seul goulot et une gamme unique, les deux règles coïncident presque) |

**Conclusion** : les mécanismes centraux de l'article — tambour = ressource la plus
chargée, corde = lancement à échéance − tampon, gestion des zones vert/jaune/rouge/noir,
règle des 5–10 % de rouges, capacité protectrice hors goulot, effet non linéaire des
fluctuations près de 100 % de charge, hypothèse touch < 10 % du délai pour le DBR —
sont **tous reproduits quantitativement** par les scénarios Monte-Carlo du simulateur.

## 5. Limites du modèle (et donc de la vérification)

- Trois postes en série, capacité 1, une gamme commune : pas de ressource CCR multiple,
  pas d'assemblage (voir l'archétype A du package `indeng` pour cela), pas de pannes
  (seules les durées varient, ±25 %, et les arrivées sont Poisson) — la divergence près
  de 100 % de charge est donc moins brutale que dans un système à forte variance.
- La promesse vaut `max(demandé client, arrivée + tampon)` : avec une demande moyenne
  de 120 h > tampon de 90 h, la corde ne limite l'encours atelier que partiellement
  (le carnet absorbe le reste — d'où l'écart encours atelier 5,4 OF vs encours total
  10,5 OF en politique B/C). En mode « délai commercial minimal » (promesse fixée),
  la corde borne exactement le temps passé en atelier à la taille du tampon.
- Politiques B et C quasi indiscernables ici (goulot unique) : la priorité par tampon
  prend tout son sens avec plusieurs ressources en concurrence.
- La cohorte mesurée est les 120 derniers OF après 150 h de warm-up ; les IC 95 %
  utilisent l'approximation de Student embarquée dans le HTML.
- Ces limites sont reformulées et assorties de propositions d'extension (attention
  managériale et surcharges, regroupements/tailles de lot, passage à une grande
  usine dans `indeng`) dans [`pistes-extension.md`](pistes-extension.md).

## 6. Reproduction

```bash
# ouvrez la simulation dans un navigateur
xdg-open sdbr-mini-usine/simulateur-sdbr-mini-usine.html   # ou double-clic

# rejouez la campagne Monte-Carlo hors navigateur (Node >= 18, aucune dépendance)
node sdbr-mini-usine/scripts/run_montecarlo.mjs --reps 30
# sorties : sdbr-mini-usine/results/montecarlo_{replications.csv,summary.csv,summary.md}
```

## 7. Campagne « surcharge » — ligne de 10 postes à goulot central

Voir [`surcharge-10-postes.md`](surcharge-10-postes.md) : ligne de 10 postes, goulot
central, demande par paliers avec pics (charge 0,70 → 1,30 du goulot), fenêtres de
lancement 36–168 h (168 h = lancement immédiat) croisées avec 3 niveaux de
surcapacité du goulot (×1 / ×1,25 / ×1,5), 20 graines appariées. Résultat : en
promesse client, lancer plus tôt n'abîme pas l'OTD (+5 à +32 points par pas) — le
coût passe par l'encours/attention ; c'est la **surcharge du goulot** qui fait
s'effondrer l'OTD en pic (1–45 %) et la **surcapacité du goulot** qui la restaure
(100 % à ×1,5), conformément à Goldratt p. 9 et 16–17.

## 8. Campagne « lots et séries au goulot » (transfert unitaire)

Voir [`lots-series.md`](lots-series.md) : avec `transfer: unitaire`, des variantes
`size` = 4/8/16 + règle `family_fifo` créent au goulot des **séries** (lots d'une même
famille traités en bloc) qui bloquent les OF urgents de l'autre famille — mesuré par
`conflits_avec_retard` (510/517 rouges bloqués livrés en retard). Résultat : les lots
économisent 45 % de réglages au goulot (247 → 137 h) mais coûtent **−33 points d'OTD**
(84,6 → 51,6 %) et un retard P95 ×2,5 — conforme à Goldratt p. 5–6 et 13 (petits lots,
flux d'une pièce) et p. 15–17 (au CCR, l'urgence rouge prime sur la série).

## 9. Lots à taille par poste (`size` = liste)

Le moteur accepte désormais **`size` comme liste d'une taille de lot par poste**
(`run_congestion.py`, test `test_lot_a_taille_par_poste`). Campagne
[`lots-par-poste.md`](lots-par-poste.md) : regrouper **uniquement au goulot** donne la
meilleure OTD (91,9 % vs 84,6 % en unitaire, réglages CCR −45 %), tandis que
regrouper **hors goulot** la dégrade (56,5 %, P95 ×2,3) — l'économie de réglage locale
ne rapporte de la capacité que si elle s'applique à la contrainte (TOC p. 3, 10, 16–17).

## 10. Train logistique — un seul paramètre `transfer` = N

`transfer` accepte un entier N : les OF finis partent **par trains de N, toutes
familles confondues** (départ au plein de N, ou vidange quand le poste amont est
inactif). Campagne [`train-logistique.md`](train-logistique.md) : sur la ligne
10 postes avec pic, l'OTD chute de **84,6 % (N=1) à 3,7 % (N=16)**, traversée P95
144 → 482 h — la contrainte logistique pénalise d'autant plus que le train est
gros ; N=1 (unitaire) domine, conforme à Goldratt p. 5–6.
