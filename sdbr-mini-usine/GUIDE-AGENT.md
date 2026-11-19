# Mener une expérience sur la ligne en I

## Démarrer

Lire ce guide, puis HYPOTHESES.md pour les définitions des indicateurs. Le moteur Python des campagnes se trouve dans scripts/run_congestion.py. La page HTML possède son propre moteur. Les changements de topologie Python sont accessibles par run_hypotheses.py.

Depuis la racine du dépôt, exécuter

```sh
.venv/bin/python -m pytest -q
MPLCONFIGDIR=/tmp/mpl-sdbr .venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py sdbr-mini-usine/scenario-topologie.json --out /tmp/sdbr-topologie
```

Si .venv manque, créer un environnement Python et installer le dépôt avec `python -m pip install -e '.[dev]'`. Adapter le chemin du Python dans les commandes. Un avertissement de cache de police peut apparaître sur une machine restreinte. Vérifier le code de sortie et la présence des fichiers avant de conclure à un échec.

L’exemple contient cinq postes, un goulot en début, milieu ou fin selon la variante, deux familles symétriques et trois fenêtres. Le scénario est une base d’expérience à adapter. Conserver ses résultats dans un nouveau dossier pour les retrouver.

## Modifier un paramètre

Copier scenario-topologie.json. Dans la copie, laisser une seule variante `"temoin":{}` pour un essai simple. Changer stationCount dans line pour allonger la ligne. Choisir bottleneckIndex entre zéro et stationCount moins un. Une ligne de huit postes avec goulot au dernier poste utilise donc 8 et 7.

Pour comparer deux positions, créer deux variantes. Recopier le bloc line complet dans chaque variante et changer seulement bottleneckIndex. Le remplacement est superficiel : un bloc line partiel supprime les autres champs de line. Changer aussi familyWeights si les familles changent.

La durée normale est la moyenne du traitement d’un OF à chacun des postes périphériques. bottleneckHours donne la moyenne au poste choisi comme référence. Les réglages se déplacent avec le rôle du poste. Vérifier les capacités effectivement consommées après simulation.

Pour comparer des longueurs, noter que l’ajout de postes augmente le travail total par OF. Pour comparer un effet d’ordre à contenu de travail identique, déplacer le goulot sur une ligne de longueur fixe.

## Vérifier les ordres de grandeur avant une longue campagne

1. Calculer le travail moyen par OF. L’exemple comporte 4 × 3 + 5 = 17 h de traitement hors réglages. Le délai minimal client de 36 h laisse une marge nominale de 19 h avant attente et réglages.
2. Comparer les capacités. Un poste à 3 h a 5/3 fois la capacité hors réglages du goulot à 5 h, soit 67 % de réserve.
3. Lire la référence de charge. Pour deux familles équiprobables, le générateur ajoute au goulot le réglage multiplié par 0,5. Ici la référence vaut 5 + 2 × 0,5 = 6 h par OF. À 80 %, l’intervalle moyen d’arrivée est 6/0,8 = 7,5 h.
4. Comparer les fenêtres aux délais clients. Avec [36,168], 168 h lance immédiatement. Une fenêtre de 144 h lance déjà immédiatement 82 % des commandes. Une faible différence d’encours peut donc être attendue.
5. Comparer les séries à la marge. seriesFraction 0.5 correspond à 51 h, la moitié de 102 h. Le plafond est souple et examiné aux frontières de lots. Un lot de quatre OF au goulot prend nominalement 20 h hors réglage.
6. Vérifier les stocks. En transfert bloc, chaque stock doit pouvoir recevoir le lot maximal. size vaut quatre dans l’exemple. bufferCapacity vaut seize.

Le moteur utilise des heures continues. La promesse vaut réception plus délai demandé. Le lancement vaut max(réception, promesse moins fenêtre). La fin de production est l’expédition. Les commandes achevées très tôt quittent donc l’encours de l’atelier.

## Lire les résultats dans cet ordre

1. configurations.json enregistre les postes et gammes résolus. Vérifier longueur, position, délais, capacités et graines avant toute interprétation.
2. synthese.csv contient les moyennes. Sélectionner phase global et comparer les fenêtres au sein d’une variante. Le nom charge_usinage désigne le travail au poste choisi comme goulot, quelle que soit sa position.
3. comparaisons.csv donne les écarts fenêtre large moins fenêtre courte, appariés par graine. delta_otd s’exprime en points de pourcentage. Un intervalle incluant zéro laisse le signe incertain.
4. replications.csv conserve les résultats individuels. Inspecter les graines avant d’attribuer une moyenne à un phénomène général.
5. otd.png montre les relations agrégées. Utiliser les comparaisons appariées pour évaluer le changement de fenêtre.

Le compteur conflits de ce lanceur repose sur les couleurs. Pour étudier les inversions de promesses avec toutes les couleurs, consulter concurrence.md et run_competition.py. Ce script possède une campagne prédéfinie à trois postes. Pour les tailles de lots et les paires disponibles, consulter HYPOTHESES.md et audit_lots.py, également prédéfini. Adapter explicitement ces campagnes avant une comparaison de topologies.

## Conclure sur Goldratt

Documenter chaque maillon observé :

- Le lancement avancé augmente-t-il effectivement l’encours ? Rapporter la différence.
- Les paires regroupables augmentent-elles au poste concerné ? Préciser la jauge et son unité.
- La politique produit-elle plus d’inversions de promesses ou des engagements plus longs ?
- Quels OF exposés deviennent tardifs ? Distinguer les commandes courtes et longues.
- Quel est le bilan d’OTD avec son intervalle apparié ?

Un OF exposé puis tardif justifie un examen événementiel. Un rejeu de la décision avec les mêmes aléas permet d’évaluer le retard imputable à cette décision. Les réglages économisés peuvent aussi sauver des commandes. Rapporter les effets mesurés et les limites de l’expérience.

## Dépanner

Une erreur de dimensions signifie généralement une liste de CV, une gamme ou un stock incompatible avec la longueur. Utiliser un CV scalaire pour commencer. Une erreur de blocage impose de vérifier que le transfert tient dans le stock aval. Une période sans promesses produit un OTD vide : augmenter la durée observée ou revoir les délais. Un changement de fenêtre sans variation d’encours appelle la vérification de l’expédition anticipée et des dates de lancement.

Les anciennes campagnes du dossier fournissent des résultats pour leurs propres horizons, règles et graines. Comparer directement les politiques dans une même campagne appariée. Ajouter une nouvelle famille, un calendrier ou une politique demande de documenter les conventions et de vérifier la chronologie.
