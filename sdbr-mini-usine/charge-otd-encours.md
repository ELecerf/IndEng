# OTD vs encours sous distributions statistiques — balayage de charge

Scénario : `scenario-charge-otd-encours.json` · résultats : `results/charge-otd-encours/`
Runner : `scripts/run_congestion.py` (grille `loads`), 20 graines, warm-up 400 h,
fenêtre de lancement **fixe** 120 h (= 5 × W).

**Question** : avec les distributions statistiques en place (arrivées Poisson, durées
opératoires lognormales CV 0,3, délai client lognormal de moyenne 108 h CV 0,6),
retrouve-t-on la **dégradation de l'OTD à fort encours** ?

## Protocole

Ligne 10 postes, goulot central `poste_5` (6 h + 2 h réglage), 2 familles, charge
offerte au goulot balayée de 0,60 à 0,99, fenêtre constante 120 h, lot 1, transfert
unitaire. Deux runs : CV des durées = 0,3 (lognormal) et CV = 0 (déterministe), pour
voir le rôle des fluctuations de process (le délai client et les arrivées restent
aléatoires dans les deux cas).

## Résultats (moyennes 20 graines)

| charge ρ | OTD % (CV 0,3) | OTD % (CV 0) | encours OF (CV 0,3) | encours OF (CV 0) | retard moyen h |
| --- | --- | --- | --- | --- | --- |
| 0,60 | 96,2 ± 0,6 | 96,5 ± 0,5 | 3,2 | 3,2 | 0,2 |
| 0,70 | 95,5 ± 0,6 | 95,8 ± 0,5 | 4,1 | 4,0 | 0,3 |
| 0,80 | 92,2 ± 1,9 | 93,2 ± 2,4 | 5,4 | 5,3 | 0,8 |
| 0,85 | 87,2 ± 3,8 | 88,4 ± 5,4 | 6,5 | 6,5 | 2,0 |
| 0,90 | **79,2 ± 5,8** | 80,7 ± 6,6 | 8,2 | 8,2 | 5,2 |
| 0,95 | **53,9 ± 11,0** | 56,7 ± 11,5 | 12,5 | 12,3 | 20,6 |
| 0,99 | **33,2 ± 10,7** | 34,3 ± 11,5 | 18,0 | 18,1 | 49,6 |

- **Corrélation OTD vs encours (Pearson) : −0,994** (CV 0,3) et −0,993 (CV 0) — la
  dégradation de l'OTD quand l'encours monte est quasi déterministe dans ce modèle.
- La dégradation **accélère fortement près de ρ → 1** : de ρ=0,90 à 0,99, l'encours
  passe de 8,2 à 18,0 OF (×2,2) et l'OTD de 79 % à 33 % (−46 points), le retard moyen
  de 5 à 50 h — la non-linéarité de Kingman (files en M/G/1), exactement le mécanisme
  « fluctuations statistiques + événements dépendants » de Goldratt (p. 14).
- Dès ρ = 0,85–0,90, l'OTD passe **sous les 90 %** — conforme à Goldratt p. 9
  (« surcharges → performance de dates < 90 % »).
- Le CV des durées opératoires (0,3 vs 0) change peu ici : la variabilité dominante est
  celle des **arrivées (Poisson) et du délai client (lognormal)** ; avec fenêtre fixe,
  c'est elle qui fait monter l'encours et tomber l'OTD.

## Conclusion

**Oui** : avec les distributions statistiques en place, on retrouve nettement la
dégradation de l'OTD à fort encours (OTD 96 % → 33 % quand l'encours passe de 3 à
18 OF, corrélation −0,99), avec un coude marqué au-delà de ~90 % de charge du
goulot. La fenêtre étant constante (120 h), cette dégradation provient des files
(attentes), pas du tampon — ce qui valide le couple « tampon temporel + capacité
protectrice hors goulot » de Goldratt (p. 9–14, 16) : garder le goulot sous ~90 % et
les autres postes en dessous laisse l'OTD dans les hautes dizaines de %.

## Reproduction

```bash
.venv/bin/python sdbr-mini-usine/scripts/run_congestion.py \
  sdbr-mini-usine/scenario-charge-otd-encours.json --out sdbr-mini-usine/results/charge-otd-encours/cv0.3
# variante déterministe : processingCV = 0.0 -> results/charge-otd-encours/cv0
```
