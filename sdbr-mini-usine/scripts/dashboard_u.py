"""Tableau de bord du U de Goldratt : attention managériale et OTD vs fenêtre de lancement.

Lit les réplications d'une campagne run_hypotheses (sweep de fenêtres) et produit :
- dashboard.csv : KPI par (variante, graine, fenêtre), dont l'indice d'attention
- u_<variante>.png : nuage de points attention vs fenêtre + courbes OTD / files / composantes
- dashboard.md : tableau de synthèse (moyenne ± IC95 par variante × fenêtre)

Indice d'attention (0..2) = groupe flux + groupe ordonnancement :
  groupe flux  = moy(norm(ruptures_carnet), norm(changements))   [branche gauche : affamés, séries]
  groupe ordo  = moy(norm(opportunites), norm(file_moy))          [branche droite : files, lots]
avec norm = min-max par variante sur tout le sweep.

Usage : python dashboard_u.py --results sdbr-mini-usine/results/dashboard-u --out sdbr-mini-usine/results/dashboard-u
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

KPI = ["otd", "encours", "file", "ruptures", "ruptures_carnet", "changements",
       "conflits_avec_retard", "opportunites", "retard_moyen", "retard_p95"]


def norm(s):
    return (s - s.min()) / (s.max() - s.min()) if s.max() > s.min() else s * 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--phases", default="global,pic")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    phases = [p for p in args.phases.split(",") if p]

    r = pd.read_csv(args.results / "replications.csv")
    r = r[r.phase.isin(phases)]
    for v in sorted(r.variante.unique()):
        g = r[r.variante == v].copy()
        for c in ["ruptures_carnet", "changements", "opportunites", "file"]:
            g["n_" + c] = norm(g[c])
        g["attention_flux"] = (g["n_ruptures_carnet"] + g["n_changements"]) / 2
        g["attention_ordo"] = (g["n_opportunites"] + g["n_file"]) / 2
        g["attention"] = g["attention_flux"] + g["attention_ordo"]
        g.to_csv(args.out / f"dashboard_{v}.csv", index=False)

        glob = g[g.phase == "global"]
        mean = glob.groupby("fenetre")[KPI + ["attention", "attention_flux", "attention_ordo"]].mean()
        sem = glob.groupby("fenetre")["otd"].sem() * 1.96

        fig, axes = plt.subplots(2, 2, figsize=(13, 9), layout="constrained")
        ax = axes[0, 0]
        ax.scatter(glob.fenetre, glob.attention, s=12, alpha=0.35, label="réplications")
        ax.plot(mean.index, mean.attention, "o-", color="crimson", label="moyenne")
        ax.set(xlabel="fenêtre de lancement (h)", ylabel="indice d'attention (0-2)",
               title="Attention managériale vs fenêtre (nuage de points)")
        ax.legend(fontsize=8)
        ax = axes[0, 1]
        ax.scatter(glob.fenetre, glob.otd, s=12, alpha=0.35, label="réplications")
        ax.errorbar(mean.index, mean.otd, yerr=sem.reindex(mean.index).fillna(0),
                    fmt="o-", color="navy", label="moyenne ± IC95")
        ax.set(xlabel="fenêtre de lancement (h)", ylabel="OTD (%)", title="OTD vs fenêtre")
        ax.legend(fontsize=8)
        ax = axes[1, 0]
        ax.plot(mean.index, mean.file, "s-", label="file moyenne (OF)")
        ax.plot(mean.index, mean.encours, "^-", label="encours (OF)")
        ax.set(xlabel="fenêtre de lancement (h)", ylabel="OF", title="Files / encours vs fenêtre")
        ax.legend(fontsize=8)
        ax = axes[1, 1]
        for c, lab in [("n_ruptures_carnet", "ruptures carnet (norm)"), ("n_changements", "changements (norm)"),
                       ("n_opportunites", "opportunités (norm)"), ("n_file", "file (norm)")]:
            m = glob.groupby("fenetre")[c].mean()
            ax.plot(m.index, m.values, "o-", label=lab)
        ax.set(xlabel="fenêtre de lancement (h)", ylabel="composante normalisée", title="Composantes de l'attention")
        ax.legend(fontsize=8)
        fig.suptitle(f"U de Goldratt — variante {v}")
        fig.savefig(args.out / f"u_{v}.png", dpi=110)
        plt.close(fig)

        # tableau de synthèse markdown
        cols = ["otd", "attention", "encours", "file", "ruptures_carnet", "changements",
                "opportunites", "conflits_avec_retard", "retard_moyen"]
        md = f"# Tableau de bord — variante `{v}` (phase globale, {glob.graine.nunique()} graines)\n\n"
        md += "| fenêtre (h) | OTD % ± IC95 | attention (0-2) | encours OF | file OF | ruptures carnet | changements | opportunités | conflits retard | retard moy. h |\n"
        md += "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        for w, row in mean.iterrows():
            md += (f"| {w:g} | {row.otd:.1f} ± {sem.get(w, 0):.1f} | {row.attention:.2f} | {row.encours:.2f} "
                   f"| {row.file:.2f} | {row.ruptures_carnet:.0f} | {row.changements:.0f} | {row.opportunites:.0f} "
                   f"| {row.conflits_avec_retard:.2f} | {row.retard_moyen:.1f} |\n")
        md += f"\nFigures : `u_{v}.png` (attention en nuage de points, OTD, files, composantes). Données : `dashboard_{v}.csv`.\n"
        (args.out / f"dashboard_{v}.md").write_text(md)
    (args.out / "dashboard.csv").write_text(pd.concat([pd.read_csv(args.out / f"dashboard_{v}.csv") for v in sorted(r.variante.unique())]).to_csv(index=False))
    print("écrit :", args.out)


if __name__ == "__main__":
    main()
