# Reproduire la comparaison ISO-lot

Depuis la racine du dépôt, avec l'environnement Python du projet et pdfLaTeX, exécuter

~~~bash
set -eu
out=sdbr-mini-usine/results/iso-lot
raw=$(mktemp -d)
export MPLCONFIGDIR="$raw/matplotlib" XDG_CACHE_HOME="$raw/cache"
.venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py sdbr-mini-usine/scenario-iso-lot.json --out "$raw"
.venv/bin/python sdbr-mini-usine/scripts/rapport_iso_lot.py "$raw" "$out"
(cd "$out" && pdflatex -halt-on-error rapport.tex && pdflatex -halt-on-error rapport.tex)
~~~

Les CSV du rapport portent sur la cohorte globale. Le lanceur conserve aussi les résultats détaillés par phase dans le répertoire temporaire. Les intervalles des différences sont appariés par graine. Le texte d'interprétation correspond au scénario et aux graines livrés.
