"""Recherche en flux continu avec demande constante ou cyclique, warmup en heures."""
from itertools import product
from pathlib import Path
import json
import pandas as pd
from demand import orders
from run_congestion import simulate

root=Path(__file__).resolve().parents[1]
base=json.loads((root/"scenario-hypotheses.json").read_text())
keys=["postes","goulot","charge","amplitude","regle"]


def pair(seed,n,p,load,amp,rule):
    hours=[2.5]*n
    hours[p]=5
    c=base|dict(stations=list(map(str,range(n))),bottleneck=p,processingHours={f:hours for f in "AB"},
                setupHours=[1]*n,requestedLead=[36,480],warmup=2400,arrivalEnd=7680,
                dispatchRule=rule,maxBatchWaitHours=0)
    profile=[(min(t+120,7680),load*(1+amp*(-1)**(t//120))) for t in range(0,7680,120)]
    jobs=orders(c,None,seed,profile)
    obs=[]
    for w in (144,480):
        phases=simulate(c,jobs,w,[16]*(n-1),4,"bloc",[(2400,4800),(4800,7200)])
        obs.append(dict(otd=100*sum(m["a_heure"] for m in phases)/sum(m["n"] for m in phases),
                        encours=sum(m["encours"] for m in phases)/2,
                        debut=phases[0]["otd"],fin=phases[1]["otd"]))
    return dict(zip(keys,[n,p,load,amp,rule]))|dict(graine=seed,otd_144=obs[0]["otd"],
        encours_144=obs[0]["encours"])|{"delta_"+k:obs[1][k]-v for k,v in obs[0].items()}


def campaign(grid,seeds):
    return pd.DataFrame([pair(s,*config) for config in grid for s in seeds])


if __name__=="__main__":
    grid=[(n,p,r,a,"family_fifo") for n in [3,5] for p in [0,n//2,n-1]
          for r,a in product([.75,.9],[0,.9])]
    pilot=campaign(grid,range(14000,14004))
    ranked=pilot.groupby(keys).mean().sort_values("delta_otd")
    n,p,r,a,rule=ranked.query("delta_encours>0").index[0]
    checks={(n,p,r,a,rule),(n,p,r,0,rule),(n,p,r,a,"due"),(n,p,r,.5,rule),
            (n,p,.75,a,rule),(3,1,r,a,rule),(5,0,r,a,rule),(5,4,r,a,rule)}
    confirm=campaign(sorted(checks),range(15000,15024))
    data=pd.concat([pilot.assign(etape="exploration"),confirm.assign(etape="confirmation")])
    out=root/"results"/"topologies-warmup"
    out.mkdir(parents=True,exist_ok=True)
    data.to_csv(out/"replications.csv",index=False)
    g=data.groupby(["etape",*keys])
    summary=g.mean().drop(columns="graine")
    for field in ["delta_otd","delta_encours"]:
        summary[field+"_marge95"]=g[field].sem()*g.size().map({4:3.182,24:2.069})
    summary.to_csv(out/"synthese.csv")
