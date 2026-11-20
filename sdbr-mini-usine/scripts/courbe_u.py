"""Courbe en U de l'OTD vs fenêtre de lancement (en multiples de W).

Lit les réplications d'une campagne run_hypotheses (sweep de fenêtres) et produit :
- u_otd.png : OTD moyenne ± IC95 et encours vs fenêtre/W, par variante, phases global/pic ;
  bande grisée = zone W ≈ 10-15 % de la fenêtre (fenêtre 6,7-10 × W)
- courbe_u.csv : OTD ± IC95 et encours par (variante, phase, fenêtre)

Usage : python courbe_u.py --results sdbr-mini-usine/results/courbe-u-otd --out sdbr-mini-usine/results/courbe-u-otd
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PHASES = ["global", "pic"]
BAND = (1 / 0.15, 1 / 0.10)  # fenêtre (×W) pour W = 10-15 % de la fenêtre


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    configs = json.loads((args.results / "configurations.json").read_text())
    work = next(iter(configs.values()))["workContentHours"]
    r = pd.read_csv(args.results / "replications.csv")
    r = r[r.phase.isin(PHASES)].copy()
    r["xW"] = r.fenetre / work

    rows = []
    for (v, phase), g in r.groupby(["variante", "phase"]):
        for fenetre, gg in g.groupby("fenetre"):
            rows.append(dict(variante=v, phase=phase, fenetre=fenetre, xW=round(fenetre / work, 4),
                             otd=gg.otd.mean(), otd_ic95=1.96 * gg.otd.sem(),
                             encours=gg.encours.mean(), retard_p95=gg.retard_p95.mean(),
                             taille_lot_moy=gg.taille_lot_moy.mean() if "taille_lot_moy" in gg else float("nan"),
                             conflits_avec_retard=gg.conflits_avec_retard.mean()))
    pd.DataFrame(rows).sort_values(["variante", "phase", "fenetre"]).to_csv(args.out / "courbe_u.csv", index=False)

    fig, axes = plt.subplots(2, 4, figsize=(21, 9), layout="constrained")
    for row, phase in enumerate(PHASES):
        for col, (key, label, title) in enumerate([
                ("otd", "OTD (%)", f"OTD vs fenêtre — phase {phase}"),
                ("encours", "encours (OF)", f"Encours vs fenêtre — phase {phase}"),
                ("conflits_avec_retard", "conflits avec retard", f"Conflits (séries bloquant OF urgents) — phase {phase}"),
                ("taille_lot_moy", "taille de lot pratiquée", f"Taille de lot pratiquée vs fenêtre — phase {phase}")]):
            ax = axes[row, col]
            for name, g in r[r.phase == phase].groupby("variante"):
                m = g.groupby("xW")[key].mean()
                if key == "otd":
                    e = 1.96 * g.groupby("xW")[key].sem().reindex(m.index).fillna(0)
                    ax.errorbar(m.index, m.values, yerr=e, fmt="o-", ms=4, capsize=2, label=name)
                else:
                    ax.plot(m.index, m.values, "s-", ms=4, label=name)
            ax.axvspan(*BAND, color="grey", alpha=0.2)
            if row == 0 and col == 0:
                ax.text(sum(BAND) / 2, ax.get_ylim()[1] * 0.02, "W ≈ 10-15 % de la fenêtre",
                        ha="center", fontsize=8, color="dimgray")
            ax.set(xlabel="fenêtre de lancement (× W)", ylabel=label, title=title)
            ax.legend(fontsize=8)
    fig.suptitle(f"U de Goldratt vu par l'OTD — fenêtre en multiples de W (W = {work:g} h)")
    fig.savefig(args.out / "u_otd.png")


if __name__ == "__main__":
    main()
