"""Flux continu, charge constante, trois fenêtres d'observation de même durée."""
from pathlib import Path
import json
import pandas as pd
from run_congestion import orders, simulate

root = Path(__file__).resolve().parents[1]
c = json.loads((root/"scenario-hypotheses.json").read_text())
c.update(requestedLead=[36,480], warmup=0, arrivalEnd=7680, dispatchRule="family_fifo")
periods = [(0,2400),(2400,4800),(4800,7200)]
rows = []
for seed in range(12000,12060):
    jobs = orders(c,.9,seed)
    for window in (144,480):
        metrics = simulate(c,jobs,window,[16,16],4,"bloc",periods)
        for (start,_),m in zip(periods,metrics):
            rows.append(dict(seed=seed,warmup=start,window=window,otd=m["otd"],encours=m["encours"]))
out = root/"results"/"warmup"
out.mkdir(parents=True,exist_ok=True)
d = pd.DataFrame(rows)
d.to_csv(out/"replications.csv",index=False)
for start,g in d.groupby("warmup"):
    for metric in ("otd","encours"):
        v = g.pivot(index="seed",columns="window",values=metric)
        diff = v[480]-v[144]
        print(start,metric,v.mean().round(2).tolist(),round(diff.mean(),2),round(2*diff.sem(),2))
