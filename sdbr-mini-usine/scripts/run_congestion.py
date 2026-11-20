"""Campagne appariée sur une ligne en I à stocks intermédiaires finis."""
import argparse
from dataclasses import dataclass, field
from itertools import product
import json
from math import exp, inf, isfinite, log1p, sqrt
from pathlib import Path
from random import Random

import pandas as pd
from collections import Counter
from policies import RULES, release_time, select_batch
from line_config import resolve_line


@dataclass
class Post:
    queue: list = field(default_factory=list)
    pending: list = field(default_factory=list)
    finished: list = field(default_factory=list)
    active: object = None
    end: float = inf
    family: str = ""
    blocked: bool = False
    series_start: float = 0.


from demand import orders


def simulate(cfg, jobs, window, capacity, size, transfer, periods=(), trace=None):
    cfg = resolve_line(cfg)
    count = len(cfg["stations"])
    sizes = [size]*count if isinstance(size, int) else list(size)
    if len(sizes) != count or any(type(s) is not int or s < 1 for s in sizes):
        raise ValueError("size doit être un entier >= 1 ou une liste d'une taille de lot par poste")
    if isinstance(transfer, bool) or not (transfer in ("bloc", "unitaire")
            or (isinstance(transfer, int) and transfer >= 1)):
        raise ValueError("transfer vaut 'bloc', 'unitaire' ou un entier N >= 1 (train logistique de N OF, toutes familles)")
    train = transfer if isinstance(transfer, int) else None
    if (not 0 <= cfg["bottleneck"] < count or len(capacity) != count-1
            or len(cfg["setupHours"]) != count or any(len(j[3]) != count for j in jobs)):
        raise ValueError("Dimensions des postes, du goulot, des stocks ou des gammes incohérentes")
    rule = cfg.get("dispatchRule", "due")
    if rule not in RULES:
        raise ValueError(f"dispatchRule inconnu {rule}")
    releases = {i: release_time(a,d,window) for i, (a,d,_,_) in enumerate(jobs)}
    incoming = sorted((t,i) for i,t in releases.items())
    posts = [Post() for _ in cfg["stations"]]
    shipped = {}
    pointer = wip = 0
    t = 0
    area = blocked_hours = full_hours = 0
    blocked_by_post = [0.] * len(posts)
    decisions = conflicts = 0
    starv = [0]*count
    starv_carnet = [0]*count
    changes = [0]*count
    queue_area = [0.]*count
    start, stop = cfg["warmup"], cfg["arrivalEnd"]
    phases = [dict(encours=0., carnet=0., goulot_actif=0., goulot_bloque=0., file=0.,
                   choix=0, regroupements=0, conflits=0,
                   ruptures=0, ruptures_carnet=0, changements=0) for _ in periods]
    goulot = posts[cfg["bottleneck"]]
    while len(shipped) < len(jobs):
        phase = next((m for (a,b),m in zip(periods,phases) if a <= t < b), None)
        while pointer < len(incoming) and incoming[pointer][0] <= t:
            posts[0].queue.append((t, incoming[pointer][1]))
            pointer += 1
            wip += 1
        for p, post in enumerate(posts):
            if post.end == t:
                post.finished.append(post.active)
                post.active, post.end = None, inf
                if not post.queue and not post.pending and start <= t < stop:
                    starv[p] += 1
                    if phase is not None:
                        phase["ruptures"] += 1
                    carnet = any(r > t for r in releases.values())
                    if carnet:
                        starv_carnet[p] += 1
                        if phase is not None:
                            phase["ruptures_carnet"] += 1
                    if trace is not None:
                        trace["starv"].append((t, p, carnet))
        # Un départ en aval peut libérer de la place en amont au même instant.
        moved = True
        while moved:
            moved = False
            for p in reversed(range(len(posts))):
                post = posts[p]
                post.blocked = False
                if post.finished and (train is not None or transfer == "unitaire" or not post.pending):
                    termine = post.active is None and not post.queue and not post.pending
                    if train is None:
                        if p == len(posts)-1 or len(posts[p+1].queue) + len(post.finished) <= capacity[p]:
                            if p == len(posts)-1:
                                shipped.update((i,t) for i in post.finished)
                                wip -= len(post.finished)
                            else:
                                posts[p+1].queue.extend((t,i) for i in post.finished)
                                moved = True
                            post.finished.clear()
                        else:
                            post.blocked = True
                    else:
                        free = inf if p == len(posts)-1 else capacity[p] - len(posts[p+1].queue)
                        vidange_ok = termine and (cfg.get("trainVidange", False) or pointer >= len(incoming))
                        if len(post.finished) >= train or vidange_ok:
                            take = min(len(post.finished), train, free)
                            if take > 0:
                                if p == len(posts)-1:
                                    shipped.update((i,t) for i in post.finished[:take])
                                    wip -= take
                                else:
                                    posts[p+1].queue.extend((t,i) for i in post.finished[:take])
                                del post.finished[:take]
                                moved = True
                            else:
                                post.blocked = True
                if post.active is not None or post.blocked:
                    continue
                if not post.pending:
                    local_queue = post.queue
                    if "seriesFraction" in cfg and (cfg.get("seriesScope","bottleneck") == "all" or p == cfg["bottleneck"]):
                        fraction = cfg["seriesFraction"]
                        limit = inf if fraction is None else fraction*sum(cfg["requestedLead"])/2
                        same = sorted(e for e in post.queue if jobs[e[1]][2] == post.family)
                        other = sorted(e for e in post.queue if jobs[e[1]][2] != post.family)
                        estimated = sum(cfg["processingHours"][jobs[j][2]][p] for _,j in same[:sizes[p]])
                        if same and (not other or t-post.series_start+estimated <= limit):
                            local_queue = same
                        elif other:
                            local_queue = other
                        selected_rule, wait = "batch_fifo", 0
                    else:
                        selected_rule, wait = rule, cfg["maxBatchWaitHours"]
                    post.pending = select_batch(local_queue, lambda i: jobs[i][2], lambda i: jobs[i][1],
                                                post.family, t, sizes[p], wait, selected_rule)
                    if not post.pending:
                        continue
                    if trace is not None:
                        counts = Counter(jobs[j][2] for _,j in post.queue)
                        trace["lots"].append((t,p,len(post.pending),sum(v>=2 for v in counts.values())))
                        trace["opportunites2"].append((t, p, sum(v >= 2 for v in counts.values())))
                        if "opportunites" in trace:
                            oldest = {}
                            for arrival,j in post.queue:
                                family = jobs[j][2]
                                oldest[family] = min(oldest.get(family,arrival),arrival)
                            eligible = sum(count >= 2 and (count >= sizes[p] or
                                           oldest[f]+cfg["maxBatchWaitHours"] <= t)
                                           for f,count in counts.items()) if sizes[p]>1 and rule!="fifo" else 0
                            trace["opportunites"].append((t,p,eligible,len(post.pending)))
                        if "marges_concurrentes" in trace and p == cfg["bottleneck"]:
                            family = jobs[post.pending[0][1]][2]
                            margins = [jobs[j][1]-t-sum(jobs[j][3][p:]) for _,j in post.queue
                                       if jobs[j][2] != family]
                            trace["marges_concurrentes"][t] = margins
                    if phase is not None:
                        phase["choix"] += len(post.queue) > 1
                        phase["regroupements"] += len(post.pending) > 1
                    selected = {i for _,i in post.pending}
                    post.queue = [e for e in post.queue if e[1] not in selected]

                _, i = post.pending.pop(0)
                due, family = jobs[i][1:3]
                setup = cfg["setupHours"][p] if post.family and post.family != family else 0
                if family != post.family:
                    if post.family:
                        changes[p] += 1
                        if phase is not None:
                            phase["changements"] += 1
                        if trace is not None:
                            trace["changes"].append((t, p))
                    if trace is not None and post.family and "series" in trace:
                        trace["series"].append((post.series_start,t,p))
                    post.series_start = t
                post.active, post.family = i, family
                post.end = t + setup + jobs[i][3][p]
                if trace is not None and "inversions" in trace:
                    for arrival,j in post.queue:
                        if jobs[j][2] != family and jobs[j][1] < due:
                            trace["inversions"].append((t,p,i,j,arrival,post.end-t))
                if trace is not None:
                    reds = [j for _,j in post.queue if jobs[j][2] != family and
                            releases[j]+2*(jobs[j][1]-releases[j])/3 <= t < jobs[j][1]] if t < releases[i]+(due-releases[i])/3 else []
                    trace["starts"].append((t,p,i,post.end,setup,reds))
                if start <= t < stop:
                    decisions += 1
                    if t < releases[i] + (due-releases[i])/3:
                        conflict = any(
                            jobs[j][2] != family and releases[j]+2*(jobs[j][1]-releases[j])/3 <= t < jobs[j][1]
                            for _,j in post.queue
                        )
                        conflicts += conflict
                        if phase is not None:
                            phase["conflits"] += conflict
        future = [p.end for p in posts]
        if pointer < len(incoming):
            future.append(incoming[pointer][0])
        for post in posts:
            if post.active is None and not post.blocked:
                future.extend(a+cfg["maxBatchWaitHours"] for a,_ in post.queue
                              if a+cfg["maxBatchWaitHours"] > t)
        if len(shipped) == len(jobs):
            break
        nxt = min(future)
        if nxt == inf:
            raise RuntimeError("Ligne bloquée sans événement futur")
        dt = max(0, min(nxt,stop)-max(t,start))
        if trace is not None and "paires_heures" in trace and periods and any(s >= 2 for s in sizes) and rule != "fifo":
            duration = max(0, min(nxt, periods[-1][1])-max(t, periods[0][0]))
            for index, post in enumerate(posts):
                by_family = Counter(jobs[j][2] for _,j in post.queue)
                trace["paires_heures"][index] += duration * sum(n*(n-1)//2 for n in by_family.values())
        if trace is not None:
            trace["intervals"].append((t,nxt,wip,tuple(post.blocked for post in posts)))
        for (a,b), m in zip(periods, phases):
            duration = max(0, min(nxt,b)-max(t,a))
            m["encours"] += wip*duration
            m["file"] += sum(len(p.queue) for p in posts)*duration
            m["goulot_actif"] += (goulot.active is not None)*duration
            m["goulot_bloque"] += goulot.blocked*duration
        area += wip*dt
        blocked_hours += sum(p.blocked for p in posts)*dt
        for i,p in enumerate(posts):
            blocked_by_post[i] += p.blocked*dt
            queue_area[i] += len(p.queue)*dt
        full_hours += sum(len(p.queue) == c for p,c in zip(posts[1:],capacity))*dt
        t = nxt
    if periods:
        if trace is not None:
            trace.update(shipped=shipped, releases=releases)
        for (a,b), m in zip(periods, phases):
            m["carnet"] = sum(max(0, min(b,releases[i])-max(a,j[0])) for i,j in enumerate(jobs))
            cohort = [i for i,j in enumerate(jobs) if a <= j[1] < b]
            late = [max(0, shipped[i]-jobs[i][1]) for i in cohort]
            for key in ("encours", "carnet", "file", "goulot_actif", "goulot_bloque"):
                m[key] /= b-a
            m.update(n=len(late), a_heure=sum(d==0 for d in late),
                     otd=100*sum(d==0 for d in late)/len(late) if late else float("nan"),
                     retard_moyen=sum(late)/len(late) if late else float("nan"),
                     charge_usinage=sum(j[3][cfg["bottleneck"]] for j in jobs if a <= j[0] < b)/(b-a))
        return phases
    cohort = [i for i,j in enumerate(jobs) if j[0]>=start]
    late = [max(0, shipped[i]-jobs[i][1]) for i in cohort]
    if not cohort:
        raise ValueError("Aucune commande dans la période mesurée.")
    horizon = stop-start
    result = dict(n=len(late), otd=100*sum(d==0 for d in late)/len(late),
                retard_moyen=sum(late)/len(late), encours=area/horizon,
                blocage=blocked_hours, goulot_bloque=blocked_by_post[cfg["bottleneck"]],
                stocks_pleins=full_hours, choix=decisions, conflits=conflicts)
    for i, name in enumerate(cfg["stations"]):
        result[f"ruptures_{name}"] = starv[i]
        result[f"ruptures_carnet_{name}"] = starv_carnet[i]
        result[f"changements_{name}"] = changes[i]
        result[f"file_{name}"] = queue_area[i]/horizon
    result["ruptures"] = sum(starv)
    result["ruptures_carnet"] = sum(starv_carnet)
    result["changements"] = sum(changes)
    result["file_moy"] = sum(queue_area)/horizon
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.scenario.read_text())
    if not 0 <= cfg["warmup"] < cfg["arrivalEnd"]:
        parser.error("La fin des arrivées doit suivre la stabilisation.")
    count = len(cfg["stations"])
    if (count < 1 or not 0 <= cfg["bottleneck"] < count or
            len(cfg["setupHours"]) != count or any(x < 0 for x in cfg["setupHours"]) or
            any(len(v) != count or min(v) <= 0 for v in cfg["processingHours"].values()) or
            len(cfg["familyWeights"]) != len(cfg["processingHours"]) or
            not cfg["familyWeights"] or min(cfg["familyWeights"]) <= 0 or
            not 0 <= cfg["variation"] < 1 or cfg["replications"] < 2 or
            not cfg["loads"] or min(cfg["loads"]) <= 0 or
            min(cfg["batchSizes"]) < 1 or cfg["maxBatchWaitHours"] < 0 or
            not all(t in ("bloc", "unitaire") or (isinstance(t, int) and not isinstance(t, bool) and t >= 1)
                    for t in cfg["transfers"]) or
            cfg["referenceWindow"] not in cfg["windows"] or min(cfg["windows"]) < 0):
        parser.error("Paramètres de ligne ou de campagne incohérents.")
    for caps, size, mode in product(cfg["capacities"].values(), cfg["batchSizes"], cfg["transfers"]):
        if len(caps) != len(cfg["stations"])-1 or any(c is not None and c < (size if mode == "bloc" else 1) for c in caps):
            parser.error("Chaque stock doit pouvoir recevoir un lot de transfert entier.")
    rows = []
    for load, seed in product(cfg["loads"], range(cfg["seed"],cfg["seed"]+cfg["replications"])):
        jobs = orders(cfg,load,seed)
        for (name,caps), size, mode, window in product(cfg["capacities"].items(),cfg["batchSizes"],cfg["transfers"],cfg["windows"]):
            rows.append(dict(charge=load,graine=seed,stock=name,lot=size,transfert=mode,fenetre=window,
                             **simulate(cfg,jobs,window,[inf if c is None else c for c in caps],size,mode)))
    data = pd.DataFrame(rows)
    keys = ["charge","stock","lot","transfert"]
    ref = data[data.fenetre == cfg["referenceWindow"]].set_index(keys+["graine"]).otd
    data["delta_otd"] = data.otd - ref.reindex(pd.MultiIndex.from_frame(data[keys+["graine"]])).to_numpy()
    group = data.groupby(keys+["fenetre"])
    mean = group[["otd","retard_moyen","encours","blocage","goulot_bloque","stocks_pleins","conflits","delta_otd"]].mean()
    mean["se_delta_otd"] = group.delta_otd.std() / sqrt(cfg["replications"])
    args.out.mkdir(parents=True,exist_ok=True)
    data.to_csv(args.out/"replications.csv",index=False)
    mean.to_csv(args.out/"synthese.csv")
    print(mean.round(2).to_string())


if __name__ == "__main__":
    main()
