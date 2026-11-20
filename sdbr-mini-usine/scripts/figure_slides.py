"""Figures par panneau au format paysage pour la présentation beamer (rapport-manager.tex).

Lit une campagne run_hypotheses (replications.csv + configurations.json + zones_of.csv)
et produit trois PNG lisibles en slide 16:9 :
  slide_otd.png   : OTD % +/- IC95 vs log2(fenetre/W) pour toutes les variantes,
                    bande W ~ 10-15 % de la fenetre, ligne lancement immediat
  slide_zones.png : zones vert/jaune/rouge/noir empilees pour la variante progressive
  slide_meca.png  : taille de lot realisee (progressive) + encours (temoin), axe jumeau

Usage : python figure_slides.py --results sdbr-mini-usine/results/lot-fenetre-coef \
          --out sdbr-mini-usine/results/lot-fenetre-coef --progressive k025 --temoin temoin
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OKABE_ITO = ["#000000", "#E69F00", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#56B4E9"]
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

    plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.25,
                         "axes.axisbelow": True, "figure.dpi": 200})

    # --- panneau OTD ---
    fig, ax = plt.subplots(figsize=(7.4, 4.1), layout="constrained")
    for i, (name, grp) in enumerate(g.groupby("variante")):
        grp = grp.sort_values("xW")
        ax.errorbar(grp.x, grp.otd, yerr=grp.ic95, marker="o", ms=4, lw=1.4, capsize=3,
                    color=OKABE_ITO[i % len(OKABE_ITO)], label=name)
    ax.axvspan(np.log2(1 / 0.15), np.log2(1 / 0.10), color="grey", alpha=0.15)
    ax.text((np.log2(1 / 0.15) + np.log2(1 / 0.10)) / 2, 8,
            "W = 10-15 %\nde la fenetre", ha="center", fontsize=9, color="dimgray")
    lead_max = configs[args.temoin]["requestedLead"][-1] / work
    ax.axvline(np.log2(lead_max), color="grey", ls="--", lw=1)
    ax.text(np.log2(lead_max) - 0.05, 88, "lancement immediat", fontsize=9,
            color="dimgray", ha="right")
    ax.set(xlabel="fenetre de lancement (x W, echelle log2)", ylabel="OTD (%)",
           ylim=(-2, 104), xlim=(np.log2(0.9), np.log2(50)))
    ax.set_xticks([np.log2(v) for v in LOG_TICKS])
    ax.set_xticklabels([str(v) for v in LOG_TICKS])
    ax.legend(title="politique de lot", fontsize=9, title_fontsize=9, loc="upper left")
    ax.set_title("OTD selon la fenetre de lancement (10 graines appariees, IC 95 %)",
                 loc="left", fontsize=12)
    fig.savefig(args.out / "slide_otd.png")
    plt.close(fig)

    # --- panneau zones ---
    zones = pd.read_csv(args.results / "zones_of.csv")
    z = zones.groupby("fenetre").agg(xW=("xW", "first")).reset_index()
    for name, _ in ZONE_COLORS:
        z["pct_" + name] = zones.groupby("fenetre")["zone"].apply(lambda s: 100 * (s == name).mean()).values
    z["x"] = np.log2(z.xW)
    z = z.sort_values("xW")
    fig, ax = plt.subplots(figsize=(7.4, 4.1), layout="constrained")
    bottom = None
    labels = {"vert": "vert (1er tiers)", "jaune": "jaune (2e tiers)",
              "rouge": "rouge (3e tiers)", "noir": "noir (en retard)"}
    for name, color in ZONE_COLORS:
        vals = z["pct_" + name]
        ax.bar(z.x, vals, bottom=bottom, color=color, width=0.45, label=labels[name])
        bottom = vals if bottom is None else bottom + vals
    ax.set(xlabel="fenetre de lancement (x W, echelle log2)", ylabel="% des OF",
           ylim=(0, 100), xlim=(np.log2(0.9), np.log2(50)))
    ax.set_xticks([np.log2(v) for v in LOG_TICKS])
    ax.set_xticklabels([str(v) for v in LOG_TICKS])
    ax.legend(fontsize=9, loc="upper left")
    ax.set_title(f"Dans quel tiers de la fenetre chaque OF se termine-t-il ? ({args.progressive})",
                 loc="left", fontsize=12)
    fig.savefig(args.out / "slide_zones.png")
    plt.close(fig)

    # --- panneau mecanisme ---
    fig, ax = plt.subplots(figsize=(7.4, 4.1), layout="constrained")
    prog = g[g.variante == args.progressive].sort_values("xW")
    tem = g[g.variante == args.temoin].sort_values("xW")
    ax.plot(prog.x, prog.lot, "o-", color="#E69F00", lw=1.6, ms=4,
            label=f"taille de lot realisee ({args.progressive})")
    ax.set(xlabel="fenetre de lancement (x W, echelle log2)",
           ylabel="taille de lot realisee (OF)", xlim=(np.log2(0.9), np.log2(50)), ylim=(0, None))
    ax.set_xticks([np.log2(v) for v in LOG_TICKS])
    ax.set_xticklabels([str(v) for v in LOG_TICKS])
    ax2 = ax.twinx()
    ax2.plot(tem.x, tem.encours, "s--", color="#0072B2", lw=1.6, ms=4,
             label=f"encours ({args.temoin})")
    ax2.set_ylabel("encours (OF)", color="#0072B2")
    ax2.tick_params(axis="y", colors="#0072B2")
    ax2.grid(False)
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [l.get_label() for l in lines], fontsize=9, loc="upper left")
    ax.set_title("Mecanisme : plus la fenetre est longue, plus on regroupe et plus l'encours monte",
                 loc="left", fontsize=12)
    fig.savefig(args.out / "slide_meca.png")
    plt.close(fig)
    print(args.out / "slide_otd.png")


if __name__ == "__main__":
    main()
