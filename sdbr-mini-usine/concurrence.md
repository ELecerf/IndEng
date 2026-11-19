# Mesurer les inversions d’échéances

Reproduction avec `.venv/bin/python sdbr-mini-usine/scripts/run_competition.py`. La campagne couvre 60 graines, sept fenêtres et les séries sans plafond à tous les postes. Le reste correspond à la campagne series-tous-postes à réglages de référence.

À chaque démarrage, le journal énumère les OF d’autres familles prêts dans la file dont la promesse est antérieure à celle de l’OF démarré. Les dates promises peuvent être déjà dépassées. Les couleurs interviennent uniquement dans les anciens compteurs. Les OF réservés appartiennent à la famille du lot engagé, donc les concurrents d’une autre famille figurent dans la file libre du modèle.

Une paire indique une exposition. Plusieurs opérations peuvent exposer le même OF, et une opération peut exposer plusieurs OF. Les heures imposées additionnent la durée de l’opération sur toutes les paires, donc elles sont exprimées en heures-OF. Les victimes sont dédupliquées par répétition, période et poste. Les échéances franchies sont les paires pour lesquelles la promesse de l’OF attendant tombe pendant l’opération concurrente. Le retard final est une association observée. Son attribution causale nécessite un rejeu de décision.

Au goulot, passer de 72 h à 168 h augmente les démarrages inversant les échéances de 35,45 à 42,43 sur 900 h. L’écart moyen de promesse dans les paires passe de 27,42 à 51,98 h. Les OF exposés sont environ trente dans les deux cas. Parmi eux, le nombre livré en retard diminue de 14,43 à 9,93. L’OTD global passe de 86,74 % à 91,45 %.

Au lancement immédiat, les inversions au goulot passent de 11,22 sur les 360 h avant le pic à 14,07 sur les 180 h du pic, puis 17,15 sur les 360 h de reprise. Cela représente 3,12, 7,82 et 4,76 démarrages pour 100 h. Le pic est la période où la concurrence se manifeste le plus fortement dans l’ordre. Les victimes livrées en retard concernent les OF exposés à cette période, tandis que l’OTD par phase porte sur les promesses de cette phase.
