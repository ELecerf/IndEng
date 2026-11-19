# Sensibilité aux changements de série

Depuis la racine, exécuter `.venv/bin/python sdbr-mini-usine/scripts/run_series.py --scope all --setup-scale 0.5 --out /tmp/reglages-05`. Remplacer 0.5 par 0, 0.25, 1, 2 ou 4 pour reproduire la grille. Les réglages de référence valent [1,2,1] h pour préparation, usinage et finition.

Les 5 400 simulations utilisent les mêmes 60 graines, OF, promesses et temps opératoires, avec plafonds à tous les postes. La cadence des arrivées est calculée avec les réglages de référence pour tous les cas. Modifier les réglages change ainsi la charge effective. La qualification nominale du pic à 135 % conserve sa référence initiale.

À fenêtre 144 h, les OTD 10 % puis libre valent respectivement 93,90 et 93,55 % sans réglage, 92,80 et 93,02 % au quart, 90,71 et 92,69 % à moitié, 86,46 et 91,35 % à référence, 73,98 et 88,57 % au double, 40,20 et 82,01 % au quadruple.

Les écarts appariés libre moins 10 % ont des intervalles approximatifs à 95 % de [−0,85 ; 0,14], [−0,40 ; 0,84], [1,05 ; 2,91], [3,52 ; 6,24], [12,15 ; 17,03] et [37,34 ; 46,29]. Sans réglages, les séries longues produisent un petit effet défavorable incertain. Avec des réglages élevés, les économies de capacité dominent et le coût des plafonds courts devient élevé. Dans chaque combinaison de durée de réglage et de plafond, le lancement à 168 h donne un meilleur OTD moyen que celui à 72 h.

Les résultats explorent conjointement l’intérêt des séries longues et les effets de charge résultant des réglages. Ils ne suffisent pas à déterminer le seul effet de séquencement à charge effective égale. Les essais antérieurs à référence avaient un intervalle trop large publié pour le gain de 4,88 points. L’intervalle recalculé est [3,52 ; 6,24].
