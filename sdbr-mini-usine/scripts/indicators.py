import pandas as pd

def indicators(trace, jobs, a, b, stations):
    overlap = lambda x,y: max(0,min(b,y)-max(a,x))
    shipped = trace["shipped"]
    ids = [i for i,j in enumerate(jobs) if a <= j[1] < b]
    late = pd.Series([max(0,shipped[i]-jobs[i][1]) for i in ids],dtype=float)
    cycle = pd.Series([shipped[i]-trace["releases"][i] for i in ids],dtype=float)
    lots = [lot for lot in trace["lots"] if a<=lot[0]<b]
    intervals = [row for row in trace["intervals"] if overlap(*row[:2])]
    result = dict(decisions=len(lots), occasions=sum(row[3] for row in lots),
                  retard_moyen=late.mean(),regroupements=sum(row[2]>1 for row in lots),
                  conflits=sum(bool(reds) for t,_,_,_,_,reds in trace["starts"] if a<=t<b),
                  encours_max=max((row[2] for row in intervals),default=0),
                  retard_p50=late.median(),retard_p95=late.quantile(.95),
                  traversee=cycle.mean(),traversee_p50=cycle.median(),traversee_p95=cycle.quantile(.95),
                  conflits_avec_retard=0)
    result["ruptures"] = sum(a<=t<b for t,_,_ in trace["starv"])
    result["ruptures_carnet"] = sum(a<=t<b and c for t,_,c in trace["starv"])
    result["changements"] = sum(a<=t<b for t,_ in trace["changes"])
    for p,name in enumerate(stations):
        starts = [row for row in trace["starts"] if row[1]==p]
        result[f"actif_{name}"] = sum(overlap(t,end) for t,_,_,end,_,_ in starts)/(b-a)
        result[f"blocage_{name}"] = sum(overlap(x,y)*blocked[p] for x,y,_,blocked in intervals)/(b-a)
        result[f"reglages_{name}"] = sum(a<=t<b and setup>0 for t,_,_,_,setup,_ in starts)
        result[f"heures_reglage_{name}"] = sum(overlap(t,t+setup) for t,_,_,_,setup,_ in starts)
        result[f"ruptures_{name}"] = sum(a<=t<b for t,pp,_ in trace["starv"] if pp==p)
        result[f"ruptures_carnet_{name}"] = sum(a<=t<b and c for t,pp,c in trace["starv"] if pp==p)
        result[f"changements_{name}"] = sum(a<=t<b for t,pp in trace["changes"] if pp==p)
        result["conflits_avec_retard"] += sum(any(shipped[j]>jobs[j][1] for j in reds)
                                              for t,_,_,_,_,reds in starts if a<=t<b)
    return result
