"""Distribution des OF par zone de couleur (tiers de la fenêtre de lancement).

Pour chaque OF de la cohorte (promesse dans [warmup, fin des phases)), on calcule
frac = (expédition − libération) / (promesse − libération) :
vert <= 1/3, jaune <= 2/3, rouge <= 1, noir > 1 (livré en retard).
Agrégé par taille de fenêtre (×W) pour une variante donnée (ex. lot mini progressif).

Usage : python zones_couleur.py scenario-iso-lot.json --variante progressif --out results/iso-lot
"""
import argparse
import json
from collections import defaultdict
from math import inf
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from line_config import resolve_line
from run_congestion import orders, simulate
from run_hypotheses import effective_lot_sizes, validate


def zone_couleur(frac):
    if frac <= 1/3:
        return "vert"
    if frac <= 2/3:
        return "jaune"
    if frac <= 1:
        return "rouge"
    return "noir"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scenario", type=Path)
    ap.add_argument("--variante", default="progressif")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    base = json.loads(args.scenario.read_text())
    variants = base.pop("variants")
    c = resolve_line(base | variants[args.variante])
    validate(c)
    args.out.mkdir(parents=True, exist_ok=True)
    work = c["workContentHours"]

    start = c["warmup"]
    periods = []
    schedule = [(start, c["phases"][0][2])]
    for _, duration, load in c["phases"]:
        periods.append((start, start + duration))
        start += duration
        schedule.append((start, load))
    c["arrivalEnd"] = start + c["requestedLead"][-1]
    schedule.append((c["arrivalEnd"], schedule[-1][1]))
    obs_end = start  # cohorte : promesses dans [warmup, fin des phases)

    rows = []
    for seed in range(c["seed"], c["seed"] + c["replications"]):
        jobs = orders(c, None, seed, schedule)
        for window in sorted(c["windows"]):
            trace = defaultdict(list)
            size_w, min_w = effective_lot_sizes(c, window)
            simulate(c | {"minLotSize": min_w}, jobs, window,
                     [inf if v is None else v for v in c["capacity"]],
                     size_w, c["transfer"], periods, trace)
            for i, (a, due, fam, _) in enumerate(jobs):
                if not (c["warmup"] <= due < obs_end):
                    continue
                rel = trace["releases"][i]
                ship = trace["shipped"][i]
                frac = (ship - rel) / (due - rel)
                rows.append(dict(graine=seed, fenetre=window, xW=window / work, of=i,
                                 lot_min=min_w, frac=frac, zone=zone_couleur(frac),
                                 en_retard=bool(ship > due)))
    data = pd.DataFrame(rows)
    data.to_csv(args.out / "zones_of.csv", index=False)

    def pct(series, z):
        return 100 * (series == z).mean()

    summ = data.groupby("fenetre").agg(
        xW=("xW", "first"), lot_min=("lot_min", "first"), n=("of", "count"),
        frac_moy=("frac", "mean"), frac_p50=("frac", "median"), frac_p90=("frac", lambda s: s.quantile(.9)),
        pct_vert=("zone", lambda s: pct(s, "vert")),
        pct_jaune=("zone", lambda s: pct(s, "jaune")),
        pct_rouge=("zone", lambda s: pct(s, "rouge")),
        pct_noir=("zone", lambda s: pct(s, "noir")),
        pct_retard=("en_retard", lambda s: 100 * s.mean()),
    ).reset_index().sort_values("xW")
    summ.to_csv(args.out / "zones_couleur.csv", index=False)

    fig, axes = plt.subplots(2, 1, figsize=(9, 9), sharex=True, layout="constrained")
    ax = axes[0]
    bottom = None
    for col, color, lab in [("pct_vert", "#2ca02c", "vert (1er tiers)"),
                            ("pct_jaune", "#bcbd22", "jaune (2e tiers)"),
                            ("pct_rouge", "#d62728", "rouge (3e tiers)"),
                            ("pct_noir", "#000000", "noir (en retard)")]:
        ax.bar(summ.xW, summ[col], bottom=bottom, color=color, label=lab, width=0.65)
        bottom = summ[col] if bottom is None else bottom + summ[col]
    for x, m in zip(summ.xW, summ.lot_min):
        ax.text(x, 103, f"min={m:.0f}", ha="center", fontsize=7, color="dimgray")
    ax.set(ylabel="% des OF", ylim=(0, 112),
           title=f"Zone de fin des OF dans la fenêtre — variante « {args.variante} » (lot mini demandé indiqué)")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.25, axis="y")
    ax2 = axes[1]
    ax2.plot(summ.xW, summ.frac_moy, "o-", color="navy", label="fraction moyenne de la fenêtre consommée")
    ax2.plot(summ.xW, summ.frac_p90, "s--", color="purple", label="P90 de la fraction")
    for y, color in [(1/3, "#2ca02c"), (2/3, "#bcbd22"), (1, "#d62728")]:
        ax2.axhline(y, color=color, ls=":", lw=1)
    ax2b = ax2.twinx()
    ax2b.plot(summ.xW, summ.pct_retard, "^--", color="crimson", label="% livrés en retard")
    ax2b.set_ylabel("% en retard", color="crimson")
    ax2b.tick_params(axis="y", colors="crimson")
    ax2.set(xlabel="fenêtre de lancement (× W)", ylabel="(expédition − libération) / (promesse − libération)")
    ax2.set(ylim=(0, max(1.2, summ.frac_p90.max() * 1.1)))
    ax2.grid(alpha=0.25)
    lines = ax2.get_lines() + ax2b.get_lines()
    ax2.legend(lines, [l.get_label() for l in lines], fontsize=8, loc="upper left")
    fig.savefig(args.out / "zones_couleur.png")
    print(args.out / "zones_couleur.csv")


if __name__ == "__main__":
    main()
