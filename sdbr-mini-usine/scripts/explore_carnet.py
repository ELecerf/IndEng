"""Tester l'effet de la cadence de transmission du carnet client."""
from collections import defaultdict
from itertools import product
from pathlib import Path
from random import Random
from math import floor
import pandas as pd
from run_congestion import simulate


def run(seed, cadence, load, rule, window):
    # Flux de besoins Poisson. Un client transmet ensemble les commandes
    # d'une période, au moins 72 h avant la première échéance.
    rng=Random(seed)
    jobs=[]
    due=72+rng.expovariate(load/5.5)
    while due<1896:
        arrival=cadence*floor((due-72)/cadence)
        jobs.append((arrival,due,rng.choice("AB"),[h*rng.uniform(.75,1.25) for h in (1,5,1)]))
        due+=rng.expovariate(load/5.5)
    # L'ordre de réception au sein du même envoi est indépendant des échéances.
    if rule != "family_fifo_tri_promesse":
        rng.shuffle(jobs)
    c=dict(stations=["amont","usinage","aval"],bottleneck=1,warmup=480,arrivalEnd=1896,
           maxBatchWaitHours=0,dispatchRule="family_fifo" if rule=="family_fifo_tri_promesse" else rule,
           setupHours=[.5,1,.5])
    trace=defaultdict(list)
    trace["inversions"]=[]
    trace["paires_heures"]=[0.]*3
    m=simulate(c,jobs,window,[16,16],4,"bloc",[(480,1680)],trace)[0]
    inversions=sum(p==1 and 480<=t<1680 for t,p,*_ in trace["inversions"])
    return dict(otd=m["otd"],encours=m["encours"],paires=trace["paires_heures"][1]/1200,
                inversions=inversions,lot=sum(n for t,p,n,_ in trace["lots"] if p==1 and 480<=t<1680)/
                sum(1 for t,p,n,_ in trace["lots"] if p==1 and 480<=t<1680))


def campaign(stage, seeds, grid):
    rows=[]
    for cadence,load,rule in grid:
        for seed in seeds:
            late=run(seed,cadence,load,rule,72)
            early=run(seed,cadence,load,rule,72+cadence)
            rows.append(dict(stage=stage,cadence=cadence,charge=load,regle=rule,graine=seed,
                             **{k+"_72":v for k,v in late.items()},
                             **{k+"_immediat":v for k,v in early.items()},
                             **{"delta_"+k:early[k]-v for k,v in late.items()}))
    return pd.DataFrame(rows)


if __name__=="__main__":
    pilot=campaign("exploration",range(8000,8008),product([1,24,72,168],[.65,.9],["family_fifo","due"]))
    # Confirmer aussi les témoins pour la même charge sur des graines inédites.
    best=pilot.query("regle=='family_fifo'").groupby(["cadence","charge"]).delta_otd.mean().idxmin()
    check=campaign("confirmation",range(9000,9040),product(sorted({1,24,72,best[0]}),[best[1]],["family_fifo","due"]))
    out=Path(__file__).resolve().parents[1]/"results"/"carnet"
    out.mkdir(parents=True,exist_ok=True)
    controls=campaign("temoins",range(9000,9040),product([best[0]],[best[1]],["fifo","family_fifo_tri_promesse"]))
    data=pd.concat([pilot,check,controls])
    data.to_csv(out/"replications.csv",index=False)
    g=data.groupby(["stage","cadence","charge","regle"])
    summary=g.mean(numeric_only=True).drop(columns="graine")
    for key in ("delta_otd","delta_encours"):
        summary[key+"_marge95_approx"]=2*g[key].sem()
    summary.to_csv(out/"synthese.csv")
