"""Campagne appariée de la ligne en I."""
import argparse
from collections import defaultdict
import json
from math import inf
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
from policies import RULES
from run_congestion import orders, simulate
from line_config import resolve_line


def validate(c):
    n = len(c["stations"])
    sizes = c["size"] if isinstance(c["size"],list) else [c["size"]]*n
    names=[name for name,_,_ in c["phases"]]
    if not (names and "global" not in names and len(set(names))==len(names)
            and isinstance(c["seed"],int) and isinstance(c["replications"],int)
            and len(sizes)==n and all(isinstance(s,int) and s>=1 for s in sizes)
            and isinstance(c["bottleneck"],int)
            and n >= 1 and 0 <= c["bottleneck"] < n and c["replications"] >= 2
            and c["dispatchRule"] in RULES and (c["transfer"] in {"bloc","unitaire"}
                or (isinstance(c["transfer"],int) and not isinstance(c["transfer"],bool) and c["transfer"]>=1))
            and len(c["capacity"]) == n-1 and all(v is None or v >= (sizes[i] if c["transfer"]=="bloc" else 1) for i,v in enumerate(c["capacity"]))
            and len(c["setupHours"]) == n and min(c["setupHours"]) >= 0
            and all(len(row)==n and min(row)>0 for row in c["processingHours"].values())
            and len(c["familyWeights"])==len(c["processingHours"]) and min(c["familyWeights"])>0
            and len(c["requestedLead"]) >= 1 and 0 < c["requestedLead"][0] <= c["requestedLead"][-1]
            and c.get("requestedLeadDistribution", "uniform") in {"uniform", "lognormal"}
            and (c.get("requestedLeadDistribution", "uniform") != "lognormal"
                 or (isinstance(c.get("requestedLeadCV", 0.5), (int, float))
                     and c["requestedLeadCV"] >= 0))
            and len(set(c["windows"]))==len(c["windows"])>=2 and min(c["windows"])>=0
            and c["warmup"]>=0 and c["maxBatchWaitHours"]>=0
            and (c.get("processingDistribution","uniform")!="uniform" or 0 <= c["variation"] < 1)
            and all(h>0 and load>0 for _,h,load in c["phases"])):
        raise ValueError("Vérifier dimensions des postes, stocks, lots, charges, délais et fenêtres")
    min_lot = c.get("minLotSize", 1)
    min_sizes = min_lot if isinstance(min_lot, list) else [min_lot]*n
    if (len(min_sizes) != n or any(type(s) is not int or s < 1 for s in min_sizes)
            or any(min_sizes[i] > sizes[i] for i in range(n))):
        raise ValueError("minLotSize invalide (entier >= 1 ou liste par poste, <= size)")
    if "sizeFromWindow" in c:
        spec = c["sizeFromWindow"]
        if (not isinstance(c["size"], int) or "workContentHours" not in c or not isinstance(spec, dict)
                or not isinstance(spec.get("coef"), (int, float)) or spec["coef"] <= 0
                or type(spec.get("max")) is not int or spec["max"] < 1):
            raise ValueError("sizeFromWindow exige size entier, workContentHours, et {coef>0, max>=1}")


from indicators import indicators


def effective_lot_sizes(c, window):
    """Taille de lot (plafond size, minimum minLotSize) pour une fenêtre donnée.

    sizeFromWindow = {"coef": k, "max": M} : size = min(M, max(1, round(k * fenêtre / W))),
    et minLotSize = size — plus la fenêtre est longue, plus on demande à regrouper.
    """
    if "sizeFromWindow" not in c:
        return c["size"], c.get("minLotSize", 1)
    spec = c["sizeFromWindow"]
    s = max(1, min(spec["max"], round(spec["coef"]*window/c["workContentHours"])))
    return s, s


def write_otd_report(means, configs, scenario, path):
    """Compare les variantes à fenêtres identiques, au global puis par phase."""
    phases = ["global", *dict.fromkeys(means.loc[means.phase != "global", "phase"])]
    with PdfPages(path, metadata={"Title": f"OTD selon la fenêtre — {scenario}"}) as pdf:
        linked = {name: c for name, c in configs.items() if "sizeFromWindow" in c}
        if linked:
            fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True, layout="constrained")
            fig.suptitle(f"{scenario} — Couplage du lot minimum et de la fenêtre")
            for name, config in linked.items():
                points = means[(means.phase == "global") & (means.variante == name)].sort_values("fenetre")
                x = points.fenetre / config["workContentHours"]
                lots = [effective_lot_sizes(config, w)[1] for w in points.fenetre]
                spec = config["sizeFromWindow"]
                label = f"{name} (coefficient {spec['coef']:g}, plafond {spec['max']})"
                axes[0].plot(x, points.otd, "o-", label=label)
                axes[1].plot(x, 100 - points.otd, "o-")
                axes[2].plot(x, lots, "o--")
            axes[0].set(ylabel="Livraisons à l’heure (%)", ylim=(-2, 102))
            axes[0].legend(fontsize=8)
            axes[1].set(ylabel="Livraisons en retard (%)", ylim=(-2, 102))
            axes[2].set(ylabel="Lot minimum demandé", xlabel="Fenêtre / contenu de travail W")
            for ax in axes:
                ax.grid(alpha=0.25)
            pdf.savefig(fig)
            plt.close(fig)
        for phase in phases:
            fig, ax = plt.subplots(figsize=(11, 7), layout="constrained")
            subset = means[means.phase == phase]
            for name in configs:
                points = subset[subset.variante == name].sort_values("fenetre")
                if points.empty:
                    continue
                ax.plot(points.fenetre, points.otd, marker="o", label=name)
            fig.suptitle(f"{scenario} — {phase}")
            ax.set(title="Part des commandes livrées à l’heure, moyenne des réplications",
                   xlabel="Fenêtre de lancement (heures)", ylabel="OTD (%)", ylim=(-2, 102))
            ax.grid(alpha=0.25)
            ax.legend(title="Variante", loc="upper left", bbox_to_anchor=(1, 1))
            pdf.savefig(fig)
            plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    base=json.loads(args.scenario.read_text())
    variants=base.pop("variants")
    rows=[]
    conflicts=[]
    args.out.mkdir(parents=True,exist_ok=True)
    try:
        configs={name:resolve_line(base|patch) for name,patch in variants.items()}
    except (KeyError,ValueError,TypeError) as error:
        parser.error(f"Configuration de ligne invalide ({error})")
    for name,c in configs.items():
        try:
            validate(c)
        except (KeyError,ValueError,TypeError,IndexError) as error:
            parser.error(f"Variante {name}, configuration invalide ({error})")
        start=c["warmup"]
        periods=[]
        schedule=[(start,c["phases"][0][2])]
        for _,duration,load in c["phases"]:
            periods.append((start,start+duration))
            start+=duration
            schedule.append((start,load))
        c["arrivalEnd"]=start+c["requestedLead"][-1]
        schedule.append((c["arrivalEnd"],schedule[-1][1]))
        for seed in range(c["seed"],c["seed"]+c["replications"]):
            jobs=orders(c,None,seed,schedule)
            for window in sorted(c["windows"]):
                trace=defaultdict(list)
                size_w, min_w = effective_lot_sizes(c, window)
                metrics=simulate(c|{"minLotSize":min_w},jobs,window,[inf if v is None else v for v in c["capacity"]],
                                 size_w,c["transfer"],periods,trace)
                for (label,_,_), (a,b), m in zip(c["phases"],periods,metrics):
                    rows.append(dict(variante=name,graine=seed,fenetre=window,phase=label,
                                     **(m | indicators(trace,jobs,a,b,c["stations"]))))
                a,b=c["warmup"],start
                n=sum(m["n"] for m in metrics)
                global_metrics=indicators(trace,jobs,a,b,c["stations"])
                for key in ("encours","charge_usinage","carnet","file"):
                    global_metrics[key]=sum(m[key]*(y-x) for m,(x,y) in zip(metrics,periods))/(b-a)
                recovery=float("nan")
                service_recovery=float("nan")
                if any(load>1 for _,_,load in c["phases"]):
                    end_peak=max(y for (_,y),(_,_,load) in zip(periods,c["phases"]) if load>1)
                    last=max((trace["shipped"][i] for i,j in enumerate(jobs) if j[0]<end_peak),default=end_peak)
                    recovery=max(0,last-end_peak)
                    consecutive=0
                    end=end_peak+48
                    while end<=b:
                        due=[i for i,j in enumerate(jobs) if end-48<=j[1]<end]
                        on_time=sum(trace["shipped"][i]<=jobs[i][1] for i in due)
                        consecutive=consecutive+1 if due and 100*on_time/len(due)>=metrics[0]["otd"] else 0
                        if consecutive==2:
                            service_recovery=end-end_peak
                            break
                        end+=48
                for t,p,i,_,_,reds in trace["starts"]:
                    if a<=t<b:
                        for j in reds:
                            conflicts.append((name,seed,window,t,p,i,j,jobs[j][1],trace["shipped"][j]))
                rows.append(dict(variante=name,graine=seed,fenetre=window,phase="global",n=n,
                                 otd=100*sum(m["a_heure"] for m in metrics)/n if n else float("nan"),
                                 evacuation_carnet_pic=recovery,recuperation_otd=service_recovery,**global_metrics))
    out=args.out
    (out/"configurations.json").write_text(json.dumps(configs,indent=2,ensure_ascii=False))
    data=pd.DataFrame(rows)
    data.to_csv(out/"replications.csv",index=False)
    pd.DataFrame(conflicts,columns=["variante","graine","fenetre","heure","poste","vert","rouge",
                                    "promesse_rouge","livraison_rouge"]).to_csv(out/"conflits.csv",index=False)
    groups=["variante","phase","fenetre"]
    means=data.groupby(groups).mean(numeric_only=True).drop(columns="graine").reset_index()
    means.to_csv(out/"synthese.csv",index=False)
    paired=[]
    for (name,phase),group in data.groupby(groups[:2]):
        for previous,current in zip(sorted(group.fenetre.unique()),sorted(group.fenetre.unique())[1:]):
            pivot=group.pivot(index="graine",columns="fenetre",values=["otd","encours"])
            delta=(pivot.otd[current]-pivot.otd[previous]).dropna()
            se=delta.sem()
            margin=1.96*se
            paired.append(dict(variante=name,phase=phase,de=previous,a=current,delta_otd=delta.mean(),
                               erreur_standard=se,ic_bas=delta.mean()-margin,ic_haut=delta.mean()+margin,
                               delta_encours=(pivot.encours[current]-pivot.encours[previous]).mean()))
    pd.DataFrame(paired).to_csv(out/"comparaisons.csv",index=False)
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout="constrained")
    for ax,key in zip(axes,["fenetre","encours","charge_usinage"]):
        for name,g in means[means.phase=="global"].groupby("variante"):
            ax.plot(g[key],g.otd,"o-",label=name)
        ax.set(xlabel=key,ylabel="OTD (%)")
    axes[-1].legend(fontsize=7)
    fig.savefig(out/"otd.png")
    plt.close(fig)
    write_otd_report(means, configs, args.scenario.stem, out / "rapport-otd.pdf")


if __name__=="__main__":
    main()
