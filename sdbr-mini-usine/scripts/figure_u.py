"""Figure publiable du U de Goldratt : OTD vs fenêtre (axe log2), zones de couleur, lot réalisé.

Lit une campagne run_hypotheses (replications.csv + configurations.json) et le CSV
zones_of.csv produit par zones_couleur.py, puis produit une figure 3 panneaux
(a)(b)(c) en PDF + SVG + PNG 300 dpi, un CSV de statistiques et un snippet LaTeX.

Panneaux : (a) OTD % ± IC95 vs log2(fenêtre/W) par variante, bande W ≈ 10-15 % de la
fenêtre, point de saturation ; (b) zones vert/jaune/rouge/noir (barres empilées) pour
la variante progressive ; (c) taille de lot réalisée (progressif) et encours (fixe1).

Usage : python figure_u.py --results sdbr-mini-usine/results/figure-u --out sdbr-mini-usine/results/figure-u
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OKABE_ITO = {"fixe1": "#000000", "fixe8": "#0072B2", "fixe16": "#D55E00",
             "progressif": "#E69F00", "rapide": "#009E73"}
ZONE_COLORS = [("vert", "#009E73"), ("jaune", "#E69F00"), ("rouge", "#D55E00"), ("noir", "#000000")]
LOG_TICKS = [1, 2, 4, 8, 16, 32]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--progressive", default="progressif")
    ap.add_argument("--temoin", default="fixe1")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    configs = json.loads((args.results / "configurations.json").read_text())
    work = next(iter(configs.values()))["workContentHours"]
    r = pd.read_csv(args.results / "replications.csv")
    g = (r[r.phase == "global"]
         .groupby(["variante", "fenetre"])
         .agg(otd=("otd", "mean"), ic95=("otd", lambda s: 1.96 * s.sem()),
              encours=("encours", "mean"), lot=("taille_lot_moy", "mean"))
         .reset_index())
    g["xW"] = g.fenetre / work
    g["x"] = np.log2(g.xW)
    g.sort_values(["variante", "xW"]).to_csv(args.out / "figure_u_stats.csv", index=False)

    zones = pd.read_csv(args.results / "zones_of.csv")
    z = zones.groupby("fenetre").agg(xW=("xW", "first"), n=("of", "count")).reset_index()
    for name, _ in ZONE_COLORS:
        z["pct_" + name] = zones.groupby("fenetre")["zone"].apply(lambda s: 100 * (s == name).mean()).values
    z["x"] = np.log2(z.xW)
    z = z.sort_values("xW")

    plt.rcParams.update({"font.size": 8, "axes.grid": True, "grid.alpha": 0.25,
                         "axes.axisbelow": True, "figure.dpi": 300})
    fig, axes = plt.subplots(1, 3, figsize=(17 / 2.54, 5.0), layout="constrained")

    ax = axes[0]
    for name, grp in g.groupby("variante"):
        grp = grp.sort_values("xW")
        ax.errorbar(grp.x, grp.otd, yerr=grp.ic95, marker="o", ms=3, lw=1.2, capsize=2,
                    color=OKABE_ITO.get(name, None), label=name)
    ax.axvspan(np.log2(1 / 0.15), np.log2(1 / 0.10), color="grey", alpha=0.15)
    ax.text((np.log2(1 / 0.15) + np.log2(1 / 0.10)) / 2, 55, "W ≈ 10–15 %\nde la fenêtre",
            ha="center", fontsize=7, color="dimgray")
    lead_max = configs[args.temoin]["requestedLead"][-1] / work
    ax.axvline(np.log2(lead_max), color="grey", ls="--", lw=1)
    ax.text(np.log2(lead_max) - 0.06, 90, "lancement\nimmédiat", fontsize=7, color="dimgray", ha="right")
    ax.text(0.05, 8, "branche\ngauche", fontsize=7, color="dimgray")
    ax.text(3.6, 8, "plateau", fontsize=7, color="dimgray")
    ax.text(5.15, 8, "branche\ndroite", fontsize=7, color="dimgray")
    ax.set(xlabel="fenêtre de lancement (× W, échelle log₂)", ylabel="OTD (%)",
           ylim=(-2, 104), xlim=(np.log2(0.9), np.log2(50)))
    ax.set_xticks([np.log2(v) for v in LOG_TICKS])
    ax.set_xticklabels([str(v) for v in LOG_TICKS])
    ax.legend(title="politique de lot", fontsize=7, title_fontsize=7, loc="upper left")
    ax.set_title("(a) OTD selon la fenêtre", loc="left", fontsize=9)

    ax = axes[1]
    bottom = None
    for name, color in ZONE_COLORS:
        vals = z["pct_" + name]
        ax.bar(z.x, vals, bottom=bottom, color=color, width=0.45,
               label={"vert": "vert (1er tiers)", "jaune": "jaune (2e tiers)",
                      "rouge": "rouge (3e tiers)", "noir": "noir (en retard)"}[name])
        bottom = vals if bottom is None else bottom + vals
    ax.set(xlabel="fenêtre de lancement (× W, échelle log₂)", ylabel="% des OF",
           ylim=(0, 100), xlim=(np.log2(0.9), np.log2(50)))
    ax.set_xticks([np.log2(v) for v in LOG_TICKS])
    ax.set_xticklabels([str(v) for v in LOG_TICKS])
    ax.legend(fontsize=7, loc="upper left")
    ax.set_title(f"(b) zones de fin des OF — « {args.progressive} »", loc="left", fontsize=9)

    ax = axes[2]
    prog = g[g.variante == args.progressive].sort_values("xW")
    tem = g[g.variante == args.temoin].sort_values("xW")
    ax.plot(prog.x, prog.lot, "o-", color=OKABE_ITO[args.progressive], lw=1.2,
            label=f"lot réalisé ({args.progressive})")
    ax.set(xlabel="fenêtre de lancement (× W, échelle log₂)", ylabel="taille de lot réalisée (OF)",
           xlim=(np.log2(0.9), np.log2(50)), ylim=(0, None))
    ax.set_xticks([np.log2(v) for v in LOG_TICKS])
    ax.set_xticklabels([str(v) for v in LOG_TICKS])
    ax2 = ax.twinx()
    ax2.plot(tem.x, tem.encours, "s--", color="#0072B2", lw=1.2, label=f"encours ({args.temoin})")
    ax2.set_ylabel("encours (OF)", color="#0072B2")
    ax2.tick_params(axis="y", colors="#0072B2")
    ax2.grid(False)
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [l.get_label() for l in lines], fontsize=7, loc="upper left")
    ax.set_title("(c) mécanisme : lot réalisé et encours", loc="left", fontsize=9)

    for fmt in ("pdf", "svg", "png"):
        fig.savefig(args.out / f"figure_u.{fmt}", dpi=300)
    snippet = ("\\begin{figure}[t]\n  \\centering\n"
               "  \\includegraphics[width=\\linewidth]{figure_u.pdf}\n"
               "  \\caption{OTD selon la fenêtre de lancement (échelle log$_2$) pour cinq politiques\n"
               "  de lot minimum (a) ; distribution des OF dans les tiers vert/jaune/rouge/noir\n"
               "  de la fenêtre pour la politique progressive (b) ; taille de lot réalisée et\n"
               "  encours (c). Moyennes sur 10 graines appariées, barres = IC 95 \\%.}\n"
               "  \\label{fig:u-goldratt}\n\\end{figure}\n")
    (args.out / "figure_u.tex").write_text(snippet)
    print(args.out / "figure_u.pdf")


if __name__ == "__main__":
    main()
