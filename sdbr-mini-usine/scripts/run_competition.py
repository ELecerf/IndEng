"""Inversions d'échéances et exposition à l'attente, jauge passive."""
from collections import defaultdict
import json
from pathlib import Path
import pandas as pd
from run_congestion import orders,simulate

root=Path(__file__).resolve().parents[1]
c=json.loads((root/"scenario-hypotheses.json").read_text())
c.update(c["variants"]["combinaison"])
c.update(warmup=800,arrivalEnd=1868,seriesScope="all",seriesFraction=None)
rows=[]
events=[]
for seed in range(2000,2060):
    jobs=orders(c,None,seed,[(1160,.8),(1340,1.35),(1868,.8)])
    for window in (36,48,72,96,120,144,168):
        trace=defaultdict(list)
        trace["inversions"]=[]
        metrics=simulate(c,jobs,window,[16,16],4,"bloc",[(800,1160),(1160,1340),(1340,1700)],trace)
        starts={(p,i):t for t,p,i,_,_,_ in trace["starts"]}
        for label,a,b in [("avant",800,1160),("pic",1160,1340),("reprise",1340,1700),("global",800,1700)]:
            cohort=[i for i,j in enumerate(jobs) if a<=j[1]<b]
            for p in range(3):
                inv=[e for e in trace["inversions"] if e[1]==p and a<=e[0]<b]
                victims={e[3] for e in inv}
                expiring=sum(t<=jobs[j][1]<t+duration for t,_,_,j,_,duration in inv)
                rows.append(dict(graine=seed,fenetre=window,phase=label,poste=p,paires=len(inv),
                    demarrages=len({(e[0],e[2]) for e in inv}),victimes=len(victims),
                    victimes_en_retard=sum(trace["shipped"][j]>jobs[j][1] for j in victims),
                    echeances_franchies=expiring,
                    heures_imposees=sum(e[5] for e in inv),
                    otd=100*sum(trace["shipped"][i]<=jobs[i][1] for i in cohort)/len(cohort),
                    ecart_echeance_moyen=sum(jobs[i][1]-jobs[j][1] for _,_,i,j,_,_ in inv)/len(inv) if inv else 0))
        for t,p,i,j,arrival,duration in trace["inversions"]:
            if 800<=t<1700:
                events.append((seed,window,t,p,i,j,jobs[i][1],jobs[j][1],t-arrival,
                               starts[p,j]-t,duration,trace["shipped"][j]-jobs[j][1]))
out=root/"results"/"concurrence"
out.mkdir(parents=True,exist_ok=True)
d=pd.DataFrame(rows)
d.to_csv(out/"replications.csv",index=False)
d.groupby(["fenetre","phase","poste"]).mean().drop(columns="graine").to_csv(out/"synthese.csv")
pd.DataFrame(events,columns=["graine","fenetre","heure","poste","of_servi","of_attend",
    "promesse_servi","promesse_attend","attente_deja","attente_restante","duree_operation",
    "retard_signe_final"]).to_csv(out/"evenements.csv",index=False)
