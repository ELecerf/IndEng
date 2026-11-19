"""Durée de série au goulot en fraction du délai client médian."""
from collections import defaultdict
import json
import argparse
from pathlib import Path
import pandas as pd
from run_congestion import orders, simulate

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--scope",choices=["bottleneck","all"],default="bottleneck")
parser.add_argument("--setup-scale",type=float,default=1)
parser.add_argument("--out",type=Path)
args=parser.parse_args()
if args.setup_scale < 0:
    parser.error("Le multiplicateur de réglage doit être positif ou nul.")
c=json.loads((root/"scenario-hypotheses.json").read_text())
c.update(c["variants"]["combinaison"])
c.update(warmup=800,arrivalEnd=1868)
c["seriesScope"]=args.scope
periods=[(800,1160),(1160,1340),(1340,1700)]
rows=[]
for seed in range(2000,2060):
    demand_config = c | {"setupHours":[1,2,1]}
    jobs=orders(demand_config,None,seed,[(1160,.8),(1340,1.35),(1868,.8)])
    c["setupHours"]=[h*args.setup_scale for h in demand_config["setupHours"]]
    for fraction in (.1,.25,.5,1,None):
        c["seriesFraction"]=fraction
        for window in (72,144,168):
            trace=defaultdict(list)
            trace["series"]=[]
            metrics=simulate(c,jobs,window,[16,16],4,"bloc",periods,trace)
            series=[b-a for a,b,p in trace["series"] if p==1 and 800<=a<1700]
            starts=[e for e in trace["starts"] if e[1]==1 and 800<=e[0]<1700]
            rows.append(dict(graine=seed,plafond="libre" if fraction is None else fraction,fenetre=window,
                             otd=100*sum(m["a_heure"] for m in metrics)/sum(m["n"] for m in metrics),
                             encours=sum(m["encours"]*(b-a) for m,(a,b) in zip(metrics,periods))/900,
                             serie_moyenne=pd.Series(series).mean(),serie_p95=pd.Series(series).quantile(.95),
                             reglages=sum(e[4] for e in starts),conflits=sum(bool(e[5]) for e in starts),
                             **{f"reglages_poste_{p}":sum(max(0,min(1700,t+s)-max(800,t))
                                 for t,post,_,_,s,_ in trace["starts"] if post==p) for p in range(len(c["stations"]))},
                             conflits_usine=sum(bool(e[5]) for e in trace["starts"] if 800<=e[0]<1700)))
out=args.out or root/"results"/("series-tous-postes" if args.scope=="all" else "series")
out.mkdir(parents=True,exist_ok=True)
d=pd.DataFrame(rows)
d.to_csv(out/"replications.csv",index=False)
d.groupby(["plafond","fenetre"]).mean().drop(columns="graine").to_csv(out/"synthese.csv")
(out/"configuration.json").write_text(json.dumps(dict(scope=args.scope,setup_scale=args.setup_scale,
    setups=c["setupHours"],arrival_reference_setups=[1,2,1],seeds=[2000,2059]),indent=2))
