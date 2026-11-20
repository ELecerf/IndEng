"""Génère le rapport HTML autonome pour un manager : sdbr-mini-usine/rapport-manager.html.

Les figures (PNG) sont embarquées en base64 : le HTML est donc ouvrable tel quel,
sans serveur ni dossier courant. Le tableau « lot min = k × fenêtre/W » est recalculé
depuis results/lot-fenetre-coef/figure_u_stats.csv (moyennes sur les 10 graines).

Usage (depuis la racine du dépôt) :
    .venv/bin/python sdbr-mini-usine/scripts/rapport_html.py
    .venv/bin/python sdbr-mini-usine/scripts/rapport_html.py --out sdbr-mini-usine/rapport-manager.html
"""
import argparse
import base64
import html
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent  # dossier sdbr-mini-usine/

FIGURES = {
    "u_otd": "results/figure-u/slide_otd.png",
    "zones": "results/lot-fenetre-coef/slide_zones.png",
    "meca": "results/lot-fenetre-coef/slide_meca.png",
    "min_fixe": "results/lot-min-40xw/u_otd.png",
    "coef_otd": "results/lot-fenetre-coef/slide_otd.png",
    "iso_lot": "results/iso-lot/otd-fenetre.png",
    "surcharge": "results/surcharge-10-postes/otd.png",
    "dashboard": "results/dashboard-u/u_surcap_x1_5.png",
}


def img64(rel: str) -> str:
    data = (BASE / rel).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def coef_table() -> str:
    stats = pd.read_csv(BASE / "results/lot-fenetre-coef/figure_u_stats.csv")
    stats["xW"] = stats["xW"].round(1)
    cols = [2.0, 8.0, 16.0, 45.0]
    piv = stats[stats.xW.isin(cols)].pivot_table(index="variante", columns="xW", values="otd")
    order = ["temoin", "k025", "k05", "k1", "k2"]
    piv = piv.loc[[v for v in order if v in piv.index], cols]
    rows = "".join(
        "<tr><th>{}</th>{}</tr>".format(
            html.escape(v), "".join(f"<td>{piv.loc[v, c]:.1f}</td>" for c in cols))
        for v in piv.index)
    head = "".join(f"<th>{c:g}×W</th>" for c in cols)
    return f"<table class='num'><thead><tr><th>variante</th>{head}</tr></thead><tbody>{rows}</tbody></table>"


CSS = """
:root { --ink:#1a1a1a; --accent:#0072B2; --muted:#555; --bg:#fafafa; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; color: var(--ink);
       background: var(--bg); margin: 0; line-height: 1.5; }
header { background: #003A5D; color: #fff; padding: 2rem 1.5rem; }
header h1 { margin: 0 0 .3rem; font-size: 1.6rem; }
header p { margin: 0; opacity: .85; }
main { max-width: 1000px; margin: 0 auto; padding: 1.5rem; }
section { background: #fff; border: 1px solid #e3e3e3; border-radius: 8px;
          padding: 1.2rem 1.4rem; margin: 1.2rem 0; }
h2 { color: var(--accent); font-size: 1.25rem; margin-top: 0;
     border-bottom: 2px solid var(--accent); padding-bottom: .3rem; }
h3 { font-size: 1.05rem; margin-bottom: .3rem; }
figure { margin: 1rem 0; text-align: center; }
figure img { max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }
figcaption { font-size: .85rem; color: var(--muted); margin-top: .4rem; }
table { border-collapse: collapse; margin: .8rem 0; font-size: .92rem; }
table.num th, table.num td { padding: .3rem .7rem; border: 1px solid #ccc; text-align: right; }
table.num th { background: #eef4f8; }
table.claims td, table.claims th { padding: .35rem .6rem; border: 1px solid #ccc; text-align: left; vertical-align: top; }
table.claims th { background: #eef4f8; }
.lecons li, .pistes li { margin-bottom: .5rem; }
.kpi { display: flex; flex-wrap: wrap; gap: .8rem; margin: .8rem 0; }
.kpi div { background: #eef4f8; border-left: 4px solid var(--accent); border-radius: 4px;
           padding: .5rem .8rem; min-width: 150px; }
.kpi b { display: block; font-size: 1.15rem; color: #003A5D; }
footer { text-align: center; color: var(--muted); font-size: .8rem; padding: 1.5rem; }
code { background: #f0f0f0; padding: 0 .25rem; border-radius: 3px; font-size: .9em; }
@media print { header { background: #003A5D !important; -webkit-print-color-adjust: exact; }
               section { break-inside: avoid; } }
"""


def build() -> str:
    fig = {k: img64(v) for k, v in FIGURES.items()}
    table = coef_table()
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lancer plus tôt ne livre pas plus tôt — simulation S-DBR</title>
<style>{CSS}</style>
</head>
<body>
<header>
<h1>Lancer plus tôt ne livre pas plus tôt</h1>
<p>Ce que la simulation S-DBR de la mini-usine (10 postes) apprend aux managers —
vérification des écrits de Goldratt, <em>Standing on the Shoulders of Giants</em> (2006),
par Monte-Carlo (10 graines appariées, IC 95&nbsp;%).</p>
</header>
<main>

<section>
<h2>1. Pourquoi cette étude&nbsp;?</h2>
<p>Objectif managérial&nbsp;: tenir l'<b>OTD</b> (% d'ordres de fabrication livrés à l'heure).
La tentation est de <b>lancer tôt</b> pour «&nbsp;occuper&nbsp;» l'atelier. Goldratt répond&nbsp;:
on lance à <em>échéance − tampon</em> (la «&nbsp;corde&nbsp;» du DBR) — lancer plus tôt n'augmente
que l'<b>encours</b>, pas le débit.</p>
<p><b>Questions testées</b>&nbsp;: quelle taille de <b>fenêtre de lancement</b>&nbsp;? quelle
<b>politique de lots</b> (regroupements par famille)&nbsp;?</p>
<p><b>Méthode</b>&nbsp;: Monte-Carlo du simulateur HTML rejoué + moteur Python paramétrable,
campagnes à <b>graines appariées</b> (les mêmes 10 graines pour toutes les variantes).</p>
<div class="kpi">
<div><b>900 sims</b>campagne lot min = k × fenêtre/W</div>
<div><b>98,8 %</b>pic OTD à 5×W (k = 0,25)</div>
<div><b>17,2 %</b>OTD à 45×W (branche droite)</div>
<div><b>×8</b>encours à 45×W (22 → 175 OF)</div>
<div><b>14</b>affirmations de Goldratt vérifiées</div>
</div>
</section>

<section>
<h2>2. Ce que prédit Goldratt (2006) — et ce que la simulation confirme</h2>
<table class="claims">
<thead><tr><th>Affirmation (pages de l'article)</th><th>Mesure Monte-Carlo</th></tr></thead>
<tbody>
<tr><td>En surcharge, l'OTD chute «&nbsp;sous 90&nbsp;%&nbsp;» (p.&nbsp;9)</td>
<td>OTD = 87,3&nbsp;% à 99&nbsp;% de charge du goulot&nbsp;; &gt;&nbsp;99&nbsp;% jusqu'à 85&nbsp;%</td></tr>
<tr><td>Le temps opératoire ≈ 10&nbsp;% du délai total (p.&nbsp;11)</td>
<td>touch ≈ 8–16&nbsp;% du délai client selon la charge</td></tr>
<tr><td>Zones vert/jaune/rouge/noir du tampon (p.&nbsp;15)</td>
<td>53&nbsp;% des OF dans le 1<sup>er</sup> tiers, 87&nbsp;% dans les 2 premiers (tampon 90&nbsp;h)</td></tr>
<tr><td>Règle des 5–10&nbsp;% de rouges pour piloter le tampon (p.&nbsp;16)</td>
<td>90&nbsp;h → 12,6&nbsp;% de rouges&nbsp;; 120&nbsp;h → 4,7&nbsp;%&nbsp;: la bande 5–10&nbsp;% est entre les deux</td></tr>
<tr><td>Capacité protectrice hors goulot (p.&nbsp;10)</td>
<td>À 90&nbsp;% sur le goulot, les autres postes tournent à ≈ 37–40&nbsp;%</td></tr>
<tr><td>Le débit est fixé par la contrainte, pas par les efficacités locales (p.&nbsp;3, 16–17)</td>
<td>Débit identique quelle que soit la politique&nbsp;; cibler un mauvais poste à 90&nbsp;% fait tomber l'OTD à 0,1&nbsp;%</td></tr>
</tbody>
</table>
<p><small>14 affirmations vérifiées quantitativement (README §&nbsp;4, campagnes <code>results/</code>).</small></p>
</section>

<section>
<h2>3. Le modèle simulé</h2>
<ul>
<li><b>Ligne de 10 postes en série</b>, goulot central (5–7&nbsp;h + 2&nbsp;h de réglage, postes
réguliers 5,4&nbsp;h&nbsp;: surcapacité ×1,25), tampons interpostes finis (16 OF).</li>
<li><b>Travail total</b> W ≈ 54,3&nbsp;h par OF&nbsp;; 4 familles de produits (mêmes gammes).</li>
<li><b>Demande</b>&nbsp;: arrivées Poisson (CV 1), délai client lognormal, moyenne 12×W, entre
10 et 40×W&nbsp;; phases de charge 0,70 / 0,95 / 1,30 / 0,85.</li>
<li><b>Lancement</b>&nbsp;: à <code>max(arrivée, échéance − fenêtre)</code>, fenêtre balayée de
1 à 45×W.</li>
<li><b>Lots</b>&nbsp;: regroupement par famille à chaque poste, plafond <code>size</code> = 16,
lot minimum paramétrable avec attente bornée (168&nbsp;h)&nbsp;; transfert unitaire.</li>
<li><b>Répétitions</b>&nbsp;: 10 graines appariées, warm-up 400&nbsp;h.</li>
</ul>
</section>

<section>
<h2>4. Résultat 1 — le «&nbsp;U&nbsp;» de l'OTD selon la fenêtre de lancement</h2>
<figure><img src="{fig['u_otd']}" alt="OTD vs fenêtre de lancement, échelle log2, 5 politiques de lot">
<figcaption>OTD ± IC95 selon la fenêtre (×W, échelle log₂), 10 graines appariées. Bande grise&nbsp;:
W ≈ 10–15&nbsp;% de la fenêtre. Campagne <code>figure-u</code>.</figcaption></figure>
<ul>
<li><b>Branche gauche</b> (fenêtre trop courte)&nbsp;: ruptures de charge, changements de série,
OTD effondré (1,7&nbsp;% à 1×W).</li>
<li><b>Pic</b>&nbsp;: 98,5&nbsp;% à 8×W pour la politique progressive — soit
W ≈ 12,5&nbsp;% de la fenêtre, la bande 10–15&nbsp;% de Goldratt.</li>
<li><b>Branche droite</b>&nbsp;: à 45×W, les regroupements dominent → 17,2&nbsp;% seulement.</li>
<li>Sans lot minimum (fixe1, courbe noire), l'OTD reste à 100&nbsp;%&nbsp;: la branche droite vient
des <b>lots</b>, pas de la fenêtre seule.</li>
</ul>
</section>

<section>
<h2>5. Résultat 2 — dans quel tiers de la fenêtre les OF se terminent-ils&nbsp;?</h2>
<figure><img src="{fig['zones']}" alt="Zones vert/jaune/rouge/noir empilées selon la fenêtre">
<figcaption>Distribution des OF dans les tiers vert/jaune/rouge/noir de la fenêtre
(politique k025). Campagne <code>lot-fenetre-coef</code>.</figcaption></figure>
<ul>
<li>Zones de Goldratt (p.&nbsp;15)&nbsp;: vert = 1<sup>er</sup> tiers, jaune = 2<sup>e</sup>,
rouge = 3<sup>e</sup>, noir = en retard.</li>
<li>Fenêtre 5–8×W&nbsp;: ≈ 90&nbsp;% des OF en vert/jaune, 1,5–4&nbsp;% en retard.</li>
<li>Fenêtre 45×W&nbsp;: <b>83&nbsp;% d'OF noirs</b> (fin à 1,7× la fenêtre après le lancement).</li>
<li><b>Leçon</b>&nbsp;: piloter au <b>nombre de rouges/noirs</b> (règle des 5–10&nbsp;%, p.&nbsp;16),
pas au réordonnancement fin dans une même zone (p.&nbsp;14–15).</li>
</ul>
</section>

<section>
<h2>6. Résultat 3 — le mécanisme&nbsp;: lots réalisés et encours</h2>
<figure><img src="{fig['meca']}" alt="Taille de lot réalisée et encours selon la fenêtre">
<figcaption>Taille de lot réalisée (k025) et encours (témoin) selon la fenêtre.
Campagne <code>lot-fenetre-coef</code>.</figcaption></figure>
<ul>
<li>Plus la fenêtre est longue, plus le lot pratiqué grossit (1,4 → 11,8 OF) et plus
l'encours explose (22 → 175 OF, ×8) — loi de Little vérifiée (encours = débit × traversée).</li>
<li>Au goulot, l'attente pour <b>remplir le lot minimum</b> atteint 220–870&nbsp;h
(≈ 4–16×W)&nbsp;; les conflits (OF urgents dépassés par un lot) passent de ≈ 0 à 160–200.</li>
</ul>
</section>

<section>
<h2>7. Résultat 4 — imposer un lot minimum fixe (2 / 4 / 8 / 16)</h2>
<figure><img src="{fig['min_fixe']}" alt="OTD vs fenêtre pour des lots min fixes 2/4/8/16">
<figcaption>OTD vs fenêtre pour des lots min fixes, attente de remplissage 168&nbsp;h.
Campagne <code>lot-min-40xw</code> (10 graines).</figcaption></figure>
<ul>
<li>Les lots se forment vraiment (taille pratiquée 11,6/16) et l'OTD s'effondre à grande
fenêtre&nbsp;: <b>min16 → 13&nbsp;% à 40–45×W</b>&nbsp;; min8 trace un U (0&nbsp;% → 74&nbsp;% à
30×W → 65&nbsp;%).</li>
<li><b>Leçon</b>&nbsp;: ne pas attendre pour former de gros lots au goulot — chaque heure
d'attente pour remplir un lot est une heure de retard pour tout le lot.</li>
</ul>
</section>

<section>
<h2>8. Résultat 5 — dimensionner le lot minimum par la fenêtre&nbsp;: lot min = k × fenêtre/W</h2>
<figure><img src="{fig['coef_otd']}" alt="OTD vs fenêtre pour k = 0,25 / 0,5 / 1 / 2 et témoin">
<figcaption>OTD ± IC95 selon la fenêtre pour k ∈ {{0,25&nbsp;; 0,5&nbsp;; 1&nbsp;; 2}} et le témoin.
Campagne <code>lot-fenetre-coef</code>.</figcaption></figure>
<p>OTD (%) à quelques fenêtres (moyennes sur 10 graines)&nbsp;:</p>
{table}
<ul>
<li>Seul <b>k = 0,25</b> (lot min = fenêtre/4W) trace le U complet (pic 98,8&nbsp;% à 5×W).</li>
<li>La règle «&nbsp;lot min = fenêtre/W&nbsp;» (k = 1) est ≈ 4× trop agressive&nbsp;:
OTD ≈ 0 dès 2×W (1,9&nbsp;% contre 64,8&nbsp;% pour le témoin).</li>
<li>À la fenêtre optimale, le lot minimum supportable est <b>≤ 2 OF</b>.</li>
</ul>
</section>

<section>
<h2>9. Résultat 6 — comparaison appariée&nbsp;: lots fixes vs lot lié à la fenêtre</h2>
<figure><img src="{fig['iso_lot']}" alt="OTD vs fenêtre, lots min fixes et progressifs, graines appariées">
<figcaption>Campagne <code>iso-lot</code>&nbsp;: mêmes graines (42–51) pour chaque politique,
10 répétitions.</figcaption></figure>
<ul>
<li><b>Lot min 1 + fenêtre 8×W</b>&nbsp;: OTD 100&nbsp;% de 8 à 45×W — l'optimum.</li>
<li>Lot min progressif (k = 0,25)&nbsp;: 98,5&nbsp;% à 8×W mais <b>17,2&nbsp;% à 45×W</b>&nbsp;;
écart apparié à 45×W&nbsp;: <b>+82,8 points</b> [IC 80,3&nbsp;; 85,4] pour le lot min 1.</li>
<li>Au-delà de 40×W = lead max&nbsp;: lancement immédiat, toutes les variantes au même niveau
de base (13&nbsp;% quand le lot min atteint le plafond 16).</li>
</ul>
</section>

<section>
<h2>10. Résultat 7 — la surcharge tue l'OTD, quoi que l'on fasse</h2>
<figure><img src="{fig['surcharge']}" alt="OTD et encours selon la charge offerte au goulot">
<figcaption>Campagne <code>surcharge-10-postes</code>&nbsp;: OTD vs charge offerte ρ du goulot.</figcaption></figure>
<figure><img src="{fig['dashboard']}" alt="Tableau de bord du U : attention managériale">
<figcaption>Tableau de bord (campagne <code>dashboard-u</code>, surcapacité ×1,5)&nbsp;:
ruptures, changements de série, opportunités de regroupement, OTD vs fenêtre.</figcaption></figure>
<ul>
<li>Quand ρ → 1, l'OTD passe de 96&nbsp;% à 33&nbsp;% et l'encours est ×5&nbsp;: effet non
linéaire des fluctuations (p.&nbsp;14, «&nbsp;jeu de dés&nbsp;»).</li>
<li><b>Leçon</b>&nbsp;: en surcharge, <b>gérer la charge en amont</b> (carnet, délais client),
pas la fenêtre.</li>
</ul>
</section>

<section>
<h2>11. Leçons pour un manager</h2>
<ol class="lecons">
<li><b>Ne lancez pas plus tôt que la fenêtre utile</b>&nbsp;: la corde (fenêtre = échéance −
tampon) borne l'encours&nbsp;; au-delà, on achète du retard, pas du débit (loi de Little vérifiée).</li>
<li><b>Dimensionnez la fenêtre pour que W ≈ 10–15&nbsp;% de la fenêtre</b>
(ici pic à 5–8×W, OTD ≈ 98–100&nbsp;%).</li>
<li><b>Pilotez au tampon par les zones vert/jaune/rouge/noir</b> et à la règle des 5–10&nbsp;%
de rouges&nbsp;; le réordonnancement fin dans une zone n'apporte presque rien.</li>
<li><b>Pas de grand lot minimum imposé</b>&nbsp;: attendre pour remplir un lot bloque le goulot
(220–870&nbsp;h mesurées)&nbsp;; à la fenêtre optimale, lot min ≤ 2.
Règle testée&nbsp;: lot min ≈ fenêtre/(4W), pas fenêtre/W.</li>
<li><b>Protégez la capacité hors goulot</b> (≈ 25&nbsp;% de surcapacité)&nbsp;: le débit est
fixé par le goulot, pas par l'occupation des autres postes.</li>
<li><b>En surcharge (ρ → 1), l'OTD s'effondre</b> (96 → 33&nbsp;%) quel que soit le réglage&nbsp;:
agir sur la charge, pas sur la fenêtre.</li>
</ol>
</section>

<section>
<h2>12. Pistes d'amélioration et limites du modèle</h2>
<ul class="pistes">
<li><b>Attention managériale non modélisée</b> (Fig.&nbsp;1, p.&nbsp;12–13)&nbsp;: ajouter pannes,
expediting et saturation d'attention — un fort encours masque les vrais problèmes
(«&nbsp;rochers et eau&nbsp;», p.&nbsp;6).</li>
<li><b>Boucle vicieuse dynamique</b> (p.&nbsp;14)&nbsp;: retard → «&nbsp;on lance plus tôt&nbsp;»
→ plus d'encours → plus de retard.</li>
<li><b>Promesses pilotées par le client</b>&nbsp;: avec <code>lancement = max(arrivée, échéance −
fenêtre)</code>, l'OTD vs fenêtre est monotone jusqu'à la saturation (fenêtre ≥ lead max)&nbsp;;
la branche droite apparaît alors comme un <em>écart de niveau</em> entre politiques de lots,
pas comme une pente. Une pente «&nbsp;en chute&nbsp;» suppose des promesses pilotées par la
capacité du goulot.</li>
<li><b>DBR ou CCPM&nbsp;?</b>&nbsp;: le DBR suppose touch &lt; 10&nbsp;% du délai promis (p.&nbsp;18)&nbsp;;
au-delà (10–30&nbsp;%), passer en CCPM.</li>
<li><b>Moteur déjà en place</b>&nbsp;: lots à tous les postes, trains logistiques
(<code>transfer</code> = N), lot minimum avec attente bornée, familles, surcapacité relative,
tableaux de bord (ruptures, changements de série, opportunités de regroupement).</li>
</ul>
</section>

<section>
<h2>13. Reproduction et références</h2>
<ul>
<li>Tests&nbsp;: <code>.venv/bin/python -m pytest -q</code> (57 tests).</li>
<li>Campagnes&nbsp;: <code>sdbr-mini-usine/scenario-*.json</code> →
<code>.venv/bin/python sdbr-mini-usine/scripts/run_hypotheses.py &lt;scénario&gt; --out &lt;dir&gt;</code>.</li>
<li>Figures&nbsp;: <code>scripts/figure_u.py</code>, <code>scripts/figure_slides.py</code>,
<code>scripts/zones_couleur.py</code>, <code>scripts/courbe_u.py</code>,
<code>scripts/dashboard_u.py</code>, et ce rapport&nbsp;:
<code>scripts/rapport_html.py</code>.</li>
<li>Résultats et analyses&nbsp;: <code>sdbr-mini-usine/results/*/</code> et les
<code>sdbr-mini-usine/*.md</code> (README §&nbsp;1–24, <code>pistes-extension.md</code>,
<code>figure-u.md</code>, <code>lot-fenetre-coef.md</code>, <code>lot-min-40xw.md</code>…).</li>
<li>Référence&nbsp;: E.&nbsp;M.&nbsp;Goldratt, <em>Standing on the Shoulders of Giants</em>, 2006
(pages citées&nbsp;: 3, 6, 8–18) — <code>goldratt-standing-on-the-shoulders-of-giants.pdf</code>.</li>
<li>Livraison&nbsp;: branche <code>vibe/sdbr-mini-usine-eddd3f</code>, PR&nbsp;#2.</li>
</ul>
</section>

</main>
<footer>Rapport généré par <code>sdbr-mini-usine/scripts/rapport_html.py</code> —
projet IndEng, branche <code>vibe/sdbr-mini-usine-eddd3f</code> (PR&nbsp;#2).</footer>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=BASE / "rapport-manager.html")
    args = ap.parse_args()
    page = build()
    args.out.write_text(page, encoding="utf-8")
    size = args.out.stat().st_size / 1e6
    print(f"{args.out} ({size:.1f} Mo)")


if __name__ == "__main__":
    main()
