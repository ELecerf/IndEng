"""Répartition des capacités sur la ligne en I, comparaisons appariées."""
from collections import defaultdict
import json
from pathlib import Path
import pandas as pd
from run_congestion import orders, simulate

root=Path(__file__).resolve().parents[1]
cfg=json.loads((root/"scenario-hypotheses.json").read_text())
cfg.update(cfg["variants"]["combinaison"])
cfg.update(warmup=1600,arrivalEnd=3868,seriesScope="all")
profiles={"reserve_forte":[1,5,1],"reserve_50":[3,5,3],"reserve_20":[4,5,4],
          "reserve_5":[4.7,5,4.7],"amont_serre":[4.7,5,1],"aval_serre":[1,5,4.7]}
periods=[(1600,2320),(2320,2680),(2680,3700)]
rows=[]
for seed in range(3000,3060):
    reference=orders(cfg,None,seed,[(2320,.8),(2680,1.35),(3868,.8)])
    for profile,hours in profiles.items():
        c=cfg | {"processingHours":{f:hours for f in cfg["processingHours"]}}
        jobs=[(a,d,f,[v*h/base for v,h,base in zip(work,hours,cfg["processingHours"][f])])
              for a,d,f,work in reference]
        for fraction in (.1,1,None):
            c["seriesFraction"]=fraction
            for window in (72,168):
                trace=defaultdict(list)
                metrics=simulate(c,jobs,window,[16,16],4,"bloc",periods,trace)
                observed=[i for i,j in enumerate(jobs) if 1600<=j[1]<3700]
                row=dict(profil=profile,graine=seed,plafond="libre" if fraction is None else fraction,
                         fenetre=window,encours=sum(m["encours"]*(b-a) for m,(a,b) in zip(metrics,periods))/2100)
                for label,cohort in [("global",observed),
                    ("courts",[i for i in observed if jobs[i][1]-jobs[i][0]<80]),
                    ("longs",[i for i in observed if jobs[i][1]-jobs[i][0]>=124])]:
                    row["otd_"+label]=100*sum(trace["shipped"][i]<=jobs[i][1] for i in cohort)/len(cohort)
                for p in range(3):
                    row[f"actif_{p}"]=sum(max(0,min(3700,end)-max(1600,t))
                        for t,post,_,end,_,_ in trace["starts"] if post==p)/2100
                    row[f"blocage_{p}"]=sum(max(0,min(3700,b)-max(1600,a))*blocked[p]
                        for a,b,_,blocked in trace["intervals"])/2100
                rows.append(row)
out=root/"results"/"capacites"
out.mkdir(parents=True,exist_ok=True)
d=pd.DataFrame(rows)
d.to_csv(out/"replications.csv",index=False)
d.groupby(["profil","plafond","fenetre"]).mean().drop(columns="graine").to_csv(out/"synthese.csv")
(out/"configuration.json").write_text(json.dumps(dict(profiles=profiles,base=cfg,seeds=[3000,3059]),indent=2))
