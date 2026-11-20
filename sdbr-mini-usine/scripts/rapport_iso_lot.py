"""Prépare les données et la figure du rapport sur les minima à plafond constant."""
import argparse
from itertools import combinations
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from run_hypotheses import effective_lot_sizes

# Quantile bilatéral de Student à 95 %, neuf degrés de liberté.
T95 = 2.262157
MEASURES = ["otd", "encours", "traversee", "cv_traversee", "taille_lot_moy",
            "attente_lot_goulot_h", "cv_interarrivees"]


def interval(values):
    mean = values.mean()
    radius = T95 * values.sem()
    return mean, mean - radius, mean + radius


def prepare(source, out):
    configs = json.loads((source / "configurations.json").read_text())
    raw = pd.read_csv(source / "replications.csv")
    data = raw.loc[raw.phase == "global", ["variante", "graine", "fenetre", "n", *MEASURES]].copy()
    data["xW"] = [round(w / configs[v]["workContentHours"], 6)
                  for v, w in zip(data.variante, data.fenetre)]
    data["minimum"] = [effective_lot_sizes(configs[v], w)[1]
                       for v, w in zip(data.variante, data.fenetre)]
    grid = data.pivot(index=["graine", "xW"], columns="variante", values="otd")
    if (grid.shape != (90, 7) or grid.isna().any().any()
            or set(data.graine) != set(range(42, 52))
            or data.groupby("graine").n.nunique().max() != 1):
        raise ValueError("Plan apparié ou cohortes incomplets")
    if data.groupby(["graine", "xW", "minimum"])[MEASURES].nunique().max().max() != 1:
        raise ValueError("Résultats différents à paramètres effectifs identiques")
    out.mkdir(parents=True, exist_ok=True)
    data.to_csv(out / "replications.csv", index=False)
    groups = data.groupby(["variante", "xW", "fenetre", "minimum"])
    summary = groups[MEASURES].mean()
    margin = groups.otd.sem() * T95
    summary["ic_bas"] = summary.otd - margin
    summary["ic_haut"] = summary.otd + margin
    summary = summary.reset_index()
    summary.to_csv(out / "synthese.csv", index=False)
    ticks = sorted(data.xW.unique())
    lot_rows = ["Fenêtre / W & " + " & ".join(f"{x:g}" for x in ticks)]
    for name in ("progressif", "rapide"):
        minima = summary.loc[summary.variante == name].sort_values("xW").minimum
        lot_rows.append(name + " & " + " & ".join(map(str, minima)))
    (out / "minima.tex").write_text("\n".join(row + r" \\" for row in lot_rows) + "\n")
    differences = []
    for x, group in grid.groupby(level="xW"):
        for a, b in combinations(configs, 2):
            differences.append((x, a, b, *interval(group[a] - group[b])))
    pd.DataFrame(differences, columns=["xW", "A", "B", "delta_A_moins_B", "ic_bas", "ic_haut"]
                 ).to_csv(out / "ecarts-apparies.csv", index=False)

    fig, (ax, ci) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, layout="constrained",
                                 gridspec_kw={"height_ratios": [3, 1]})
    for i, name in enumerate(configs):
        g = summary[summary.variante == name]
        linked = "sizeFromWindow" in configs[name]
        style = dict(color=f"C{i}", linewidth=2.6 if linked else 1.2,
                     linestyle="--" if linked else "-",
                     marker={"progressif": "D", "rapide": "x"}.get(name, "."))
        ax.plot(g.xW, g.otd, label=name, **style)
        ci.plot(g.xW, g.ic_haut - g.otd, **style)
    ax.set(ylabel="Livraisons à l’heure (%)", ylim=(0, 100))
    ci.set(xlabel="Fenêtre de lancement / W", ylabel="Demi-largeur IC 95 %\n(points d’OTD)",
           xticks=sorted(data.xW.unique()), ylim=(0, None))
    for panel in (ax, ci):
        panel.grid(alpha=.25)
    ax.legend(ncol=4, fontsize=9)
    fig.savefig(out / "otd-fenetre.pdf")
    plt.close(fig)

    # Lignes du tableau LaTeX, au même format que les exports de données.
    lines = []
    for name, group in summary.groupby("variante", sort=False):
        best = group.loc[group.otd.idxmax()]
        pivot = data[data.variante == name].pivot(index="graine", columns="xW", values="otd")
        neighbors = []
        for j in [-1, 1]:
            index = pivot.columns.get_loc(best.xW) + j
            if 0 <= index < len(pivot.columns):
                x = pivot.columns[index]
                mean, low, high = interval(pivot[best.xW] - pivot[x])
                neighbors.append(f"{x:g} W : {mean:.1f} [{low:.1f}, {high:.1f}]")
        ties = ", ".join(f"{x:g}" for x in group.loc[group.otd == best.otd, "xW"])
        lines.append(f"{name} & {ties} & {best.otd:.1f} & " + " / ".join(neighbors) + r" \\")
    (out / "optima.tex").write_text("\n".join(lines) + "\n")
    rows = []
    for r in summary[summary.variante.isin(["fixe1", "progressif", "rapide"])
                     & summary.xW.isin([2, 8, 45])].itertuples():
        rows.append(f"{r.variante} & {r.xW:g} & {r.minimum} & {r.otd:.1f} & {r.encours:.1f} & "
                    f"{r.traversee:.0f} & {r.cv_traversee:.2f} & {r.taille_lot_moy:.1f} & "
                    f"{r.attente_lot_goulot_h:.0f}" + r" \\")
    (out / "mecanismes.tex").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.out)
