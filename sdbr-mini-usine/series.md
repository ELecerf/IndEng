# Séries limitées par une fraction du délai médian

L’option `--scope all` applique la même fraction à tous les postes et écrit dans `results/series-tous-postes`. Le champ moteur `seriesScope` sélectionne all ou bottleneck. Dans les postes concernés, l’admissibilité immédiate des lots incomplets accompagne la règle de durée. La comparaison des deux périmètres modifie ainsi aussi l’attente des postes périphériques.

Sur 60 répétitions, à fenêtre 144 h, appliquer la règle à tous les postes donne des OTD de 86,46 %, 87,41 %, 89,99 %, 91,17 % et 91,35 % pour les plafonds 10 %, 25 %, 50 %, 100 % et libre. L’encours correspondant vaut 6,93, 6,54, 5,75, 5,43 et 5,39 OF. Le gain libre moins 10 % vaut 4,88 points, avec un intervalle approximatif à 95 % de [3,52 ; 6,24]. Les réglages de finition baissent de 51,56 à 34,03 h. Ceux de préparation restent proches de 67 h.

Sans plafond, avancer le lancement de 72 h à 168 h donne un gain d’OTD de 4,71 points [3,03 ; 6,39]. Les écarts sont appariés sur les mêmes graines. La généralisation à tous les postes améliore ici le service et réduit l’encours, avec une contribution possible de la suppression de l’attente de formation de lots aux postes périphériques.

Reproduction depuis la racine avec `.venv/bin/python sdbr-mini-usine/scripts/run_series.py`.

La campagne utilise 60 graines de 2000 à 2059, trois fenêtres de lancement et cinq plafonds. Les familles ont les mêmes durées moyennes. Le délai médian vaut 102 h, les plafonds 10,2, 25,5, 51 et 102 h. La valeur null autorise la poursuite sans plafond. Le champ seriesFraction active cette règle au goulot. Les autres postes gardent leur règle locale. Les stocks comptent 16 places et les lots quatre OF, avec transfert complet. Les temps sont lognormaux avec CV 1 et la demande comporte un pic à 135 % de la référence nominale.

À chaque frontière de lot, le poste poursuit sa famille si aucune autre n’attend ou si la durée écoulée depuis le début de série, augmentée du temps nominal du prochain lot, respecte le plafond. Sinon, il passe à la famille de l’OF concurrent le plus ancien. Le premier lot peut dépasser le seuil. L’admissibilité au goulot est immédiate, y compris pour un lot incomplet. La sélection ignore les échéances individuelles. Les durées observées vont du début d’une série au début de la suivante et incluent les périodes d’inactivité et de blocage. Une série traversant la borne de fin est suivie jusqu’au changement. Ces conventions expliquent certains dépassements des plafonds.

À fenêtre de 144 h, le passage de 10 % à sans plafond augmente l’OTD de 83,27 % à 88,32 %, avec un gain apparié de 5,05 points et un intervalle approximatif à 95 % de [2,55 ; 7,55]. Les réglages au goulot passent de 99,73 à 66,67 h sur la fenêtre de 900 h. Les conflits passent de 3,38 à 6,83, tandis que l’encours diminue de 8,40 à 7,00 OF. Des conflits supplémentaires coexistent avec un gain de service, dont une explication plausible est la capacité économisée sur les réglages.

Passer d’une fenêtre de 72 h à 168 h améliore l’OTD pour chaque plafond. Le gain vaut 6,54 points sans plafond, avec un intervalle approximatif de [4,75 ; 8,33]. Les résultats décrivent ce régime et ne permettent pas d’identifier un retard causé par une décision individuelle. Les tests existants passent, sans test ciblé exhaustif de la nouvelle stratégie.
