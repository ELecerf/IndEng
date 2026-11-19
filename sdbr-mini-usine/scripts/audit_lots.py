"""Audit des lots au goulot, sur les commandes appariées du scénario combiné."""
from collections import defaultdict
import json
from pathlib import Path

import pandas as pd
from run_congestion import orders, simulate


def main():
    root = Path(__file__).resolve().parents[1]
    cfg = json.loads((root/"scenario-hypotheses.json").read_text())
    cfg.update(cfg["variants"]["combinaison"])
    rows = []
    for lead_max in (168, 480):
        cfg["requestedLead"] = [36, lead_max]
        a = cfg["warmup"] = 2*lead_max + 400
        b = a + 900
        periods = [(a,a+360),(a+360,a+540),(a+540,b)]
        cfg["arrivalEnd"] = b+lead_max
        schedule = [(a+360,.8),(a+540,1.35),(cfg["arrivalEnd"],.8)]
        for seed in range(1000,1040):
            jobs = orders(cfg,None,seed,schedule)
            for size in (1,4,8,16):
                for window in sorted({72,144,lead_max}):
                    trace = defaultdict(list)
                    trace["marges_concurrentes"] = {}
                    trace["opportunites"] = []
                    trace["paires_heures"] = [0.] * len(cfg["stations"])
                    phases = simulate(cfg,jobs,window,[16,16],size,"bloc",periods,trace)
                    lots = [(t,n) for t,p,n,_ in trace["lots"] if p==1 and a<=t<b]
                    starts = [(t,i,end,setup) for t,p,i,end,setup,_ in trace["starts"] if p==1]
                    positions = {row[0]:k for k,row in enumerate(starts)}
                    durations = [starts[positions[t]+n-1][2]-t for t,n in lots]
                    sizes = pd.Series([n for _,n in lots])
                    waits = [duration for (t,_),duration in zip(lots,durations)
                             for margin in trace["marges_concurrentes"][t]]
                    lost = sum(0<=margin<duration for (t,_),duration in zip(lots,durations)
                               for margin in trace["marges_concurrentes"][t])
                    counts = {}
                    for name,area in zip(cfg["stations"],trace["paires_heures"]):
                        counts[f"paires_moyennes_{name}"] = area/(b-a)
                    counts["paires_moyennes_usine"] = sum(trace["paires_heures"])/(b-a)
                    decisions = [e for e in trace["opportunites"] if a<=e[0]<b]
                    for name, events in [("usine",decisions)]+[(name,[e for e in decisions if e[1]==p])
                                                              for p,name in enumerate(cfg["stations"])]:
                        counts[f"opportunites_{name}"] = sum(e[2] for e in events)
                        counts[f"decisions_{name}"] = len(events)
                        counts[f"regroupements_{name}"] = sum(e[3]>1 for e in events)
                    cohort = [i for i,j in enumerate(jobs) if a<=j[1]<b]
                    rows.append(dict(delai_max=lead_max,graine=seed,plafond=size,fenetre=window,**counts,
                                     carnet=sum(m["carnet"]*(y-x) for m,(x,y) in zip(phases,periods))/(b-a),
                                     attente_lancement=sum(trace["releases"][i]-jobs[i][0] for i in cohort)/len(cohort),
                                     traversee=sum(trace["shipped"][i]-trace["releases"][i] for i in cohort)/len(cohort),
                                     avance_livraison=sum(jobs[i][1]-trace["shipped"][i] for i in cohort)/len(cohort),
                                     otd=100*sum(m["a_heure"] for m in phases)/sum(m["n"] for m in phases),
                                     encours=sum(m["encours"]*(y-x) for m,(x,y) in zip(phases,periods))/(b-a),
                                     lot_moyen=sizes.mean(),lot_p95=sizes.quantile(.95),
                                     pct_pleins=100*(sizes==size).mean(),engagement_p95=pd.Series(durations).quantile(.95),
                                     expositions=len(waits),marges_epuisees=lost,
                                     heures_reglage=sum(max(0,min(b,t+s)-max(a,t)) for t,_,_,s in starts)))
    data = pd.DataFrame(rows)
    out=root/"results"/"audit-lots"
    out.mkdir(parents=True,exist_ok=True)
    data.to_csv(out/"replications.csv",index=False)
    data.groupby(["delai_max","plafond","fenetre"]).mean().drop(columns="graine").to_csv(out/"synthese.csv")


if __name__=="__main__":
    main()
