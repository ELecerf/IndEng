# Répartition des capacités

Reproduire avec `.venv/bin/python sdbr-mini-usine/scripts/run_capacity.py` depuis la racine. Les 2 160 simulations utilisent 60 graines, six profils, trois plafonds (10 %, 100 %, libre) et deux fenêtres (72 et 168 h). Les phases durent 720, 360 et 1020 h après 1600 h de mise en régime. Les horizons diffèrent de la campagne précédente, dont les moyennes ne sont donc pas directement comparables.

Les gammes moyennes sont [1,5,1], [3,5,3], [4,5,4], [4.7,5,4.7], [4.7,5,1] et [1,5,4.7]. La capacité périphérique hors réglage dépasse celle du goulot respectivement de 400 %, 67 %, 25 % et 6,4 %. Les noms internes reserve_50, reserve_20 et reserve_5 sont des identifiants approximatifs. Les ratios exacts dépendent de l’inverse des durées. La charge et les tirages sont conservés entre profils, avec multiplication des mêmes facteurs aléatoires par les nouvelles moyennes. Les réglages restent [1,2,1]. Les stocks ont 16 places, les lots quatre OF et le CV vaut un. La règle de série agit à chaque poste.

Au lancement dès réception, sans plafond, les OTD globaux valent 86,0 %, 81,6 %, 74,4 % et 64,6 % du profil le plus déséquilibré au plus équilibré. Les OTD des commandes courtes (délai inférieur à 80 h) valent 75,6 %, 67,5 %, 55,4 % et 42,1 %. L’amont seul serré donne 75,6 % global et 58,1 % pour les courts. L’aval seul serré donne 76,2 % et 59,1 %.

Dans tous les profils, passer du plafond 10 % au plafond libre améliore l’OTD global et celui des commandes courtes. Avec les postes périphériques à 4,7 h, le gain global vaut 9,84 points, intervalle approximatif apparié à 95 % [8,63 ; 11,05]. Le lancement à 168 h contre 72 h donne +13,28 points [11,93 ; 14,63] sans plafond. La baisse des réserves dégrade fortement le service mais ne renverse pas le signe de ces effets.

Modifier les durées périphériques augmente aussi le travail total par OF, de 7 h à 14,4 h. Les résultats combinent cette hausse du contenu de travail avec les conséquences de la répartition des capacités. Les catégories court et long reposent sur le délai demandé, et les familles ont des temps moyens identiques.
