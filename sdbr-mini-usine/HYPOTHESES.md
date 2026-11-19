# Tester une hypothèse sur l’encours et l’OTD

Depuis la racine du dépôt, avec Python 3.11 ou supérieur, installer les dépendances avec `python -m pip install -e '.[dev]'` dans un environnement virtuel. Pour reproduire l’expérience fournie, exécuter

```sh
python sdbr-mini-usine/scripts/run_hypotheses.py sdbr-mini-usine/scenario-hypotheses.json --out /tmp/experience-sdbr
```

1. Écrire une prédiction avant de regarder les résultats. Exemple : « Avec maintien de famille, passer de 144 h au lancement immédiat augmente l’encours et réduit les livraisons à l’heure. »
2. Ouvrir `comparaisons.csv`, sélectionner `famille,global,144,240`. Les deux deltas ont le sens fenêtre large moins fenêtre courte. Examiner le signe de l’encours puis l’intervalle d’OTD en points. Un intervalle contenant zéro laisse le sens de l’effet incertain.
3. Copier le JSON, ajouter dans `variants` une entrée `"fifo_pur":{"dispatchRule":"fifo"}`, puis relancer la commande avec la copie et un autre dossier de sortie. Chaque variante hérite du témoin. Comparer sur les mêmes graines. Le FIFO pur traite un OF à la fois, donc pour isoler l’ordre seul comparer les règles avec `size: 1`.
4. Consulter `replications.csv` puis `conflits.csv`. Retrouver un rouge par variante, graine et numéro d’OF. Comparer ses dates et les résultats par phase. Un rouge dépassé puis livré en retard fournit un cas à examiner. Pour imputer son retard au dépassement, rejouer une intervention qui change cette décision, avec les mêmes aléas.
5. Signaler le nombre de graines, les deux fenêtres, les deltas d’encours et d’OTD, l’incertitude, puis le mécanisme observé ou encore indéterminé. Confirmer tout résultat choisi après exploration sur de nouvelles graines.

## Configurer la ligne

Les temps sont en heures. Le JSON fourni est un exemple complet. Les familles suivent toutes les stations dans l’ordre. `processingHours` donne les moyennes par famille et poste, `familyWeights` les poids selon l’ordre des familles du JSON, `setupHours` le temps d’un changement de famille à chaque poste. `bottleneck` est un indice commençant à zéro. `processingDistribution` accepte lognormal avec `processingCV` scalaire ou par poste, ou uniform avec `variation` pour la demi-largeur relative. Les incidents indépendants sont inclus dans la durée tirée.

`requestedLead` donne les bornes uniformes du délai client. Chaque phase comporte un nom, une durée et une charge nominale du goulot. Les arrivées sont poissoniennes. La référence nominale inclut le réglage moyen pour des OF indépendants. La fenêtre lance à max(réception, échéance moins fenêtre). Les fenêtres dépassant le délai maximal sont équivalentes. La mise en régime dure `warmup` heures. Chaque fenêtre réutilise exactement les OF et durées de la graine. Le suivi va jusqu’à livraison.

`size` limite le lot à chaque poste, `maxBatchWaitHours` autorise un lot incomplet après attente. `transfer` vaut bloc ou unitaire. Les capacités intermédiaires comptent les places en file, null signifie illimité. Un poste conserve les pièces achevées et reste bloqué si le lot ne peut entrer en aval. Les règles due, fifo, family_fifo et batch_fifo choisissent respectivement par échéance parmi les lots admissibles, par arrivée en unitaire, par continuité de famille puis arrivée, ou par arrivée parmi les familles admissibles. Pour ajouter une stratégie, modifier `policies.py` et étendre le test des échéances interdites.

## Lire les sorties

Les configurations résolues et les graines accompagnent les résultats. L’OTD est le pourcentage livré au plus tard à la promesse parmi les échéances de la période. La ligne globale pondère les phases par leurs commandes. Retard inclut les zéros et traversée va du lancement à la livraison. Les quantiles sont calculés par répétition. Encours et carnet sont des moyennes temporelles. Actif et blocage sont des fractions du temps de chaque poste. Les heures de réglage sont incluses dans le temps actif.

Décisions compte les constitutions de lots. Occasions additionne, à chaque décision, les familles ayant au moins deux OF disponibles. Regroupements compte les lots engagés de plusieurs OF. Ces mesures passives peuvent compter une occasion à plusieurs décisions successives. Les conflits comptent les démarrages verts devant au moins un rouge d’une autre famille prêt avant sa date promise. Les couleurs découpent en tiers le délai réel lancement–promesse. Le journal comporte une ligne par paire vert–rouge. Le compteur avec retard compte une fois le démarrage si au moins un rouge finit en retard.

La récupération de l’OTD est le temps après le dernier pic jusqu’à deux périodes consécutives de 48 h au moins au niveau d’OTD de la première phase. Une valeur vide indique une observation censurée ou une expérience sans surcharge. L’évacuation du carnet mesure le temps nécessaire pour livrer toutes les commandes reçues avant la fin du pic. Les petits effectifs par période rendent la récupération bruitée.

Le graphique utilise les moyennes globales. La charge d’usinage est le travail apporté hors réglages divisé par le temps disponible. Un déplacement sur l’axe encours peut aussi résulter de la variabilité ou des réglages. Estimer l’effet de changer la fenêtre avec les différences entre répétitions appariées et leur intervalle normal approximatif à 95 %. Les intervalles exploratoires concernent chaque comparaison individuellement.

Le générateur `demand.py` tire les commandes. `run_congestion.py` exécute les événements et expose une trace facultative. `policies.py` décide du lancement et de la sélection locale. `indicators.py` lit la trace après simulation et `run_hypotheses.py` construit les expériences et leurs sorties. Le modèle en I ne représente ni assemblage ni saturation de l’attention humaine.
