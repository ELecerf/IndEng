from __future__ import annotations

import pandas as pd

from indeng.engine.sim import RunResult


def station_utilization(result: RunResult) -> pd.Series:
    capacities = {
        name: station.capacity for name, station in result.scenario.stations.items()
    }
    events = result.events
    if events.empty:
        return pd.Series(
            {name: 0.0 for name in capacities}, name="utilization", dtype=float
        )
    busy = (
        events.assign(busy=events["end"] - events["setup_start"])
        .groupby("station")["busy"]
        .sum()
    )
    return pd.Series(
        {
            name: float(busy.get(name, 0.0)) / (result.horizon * capacity)
            for name, capacity in capacities.items()
        },
        name="utilization",
    )


def compute_kpis(result: RunResult) -> dict:
    scenario = result.scenario
    horizon = result.horizon
    completions = result.completions
    utilization = station_utilization(result)
    kpis: dict = {"horizon": horizon}
    for name, value in utilization.items():
        kpis[f"utilization_{name}"] = float(value)
    for product in scenario.products:
        kpis.setdefault(f"throughput_{product}", 0.0)
        kpis.setdefault(f"lead_time_{product}", 0.0)
    if completions.empty:
        kpis.update(
            makespan=0.0,
            n_completed=0,
            throughput_total=0.0,
            avg_wip=0.0,
            n_late=0,
            late_rate=0.0,
            bottleneck=str(utilization.idxmax()) if not utilization.empty else None,
        )
        return kpis
    comp = completions.copy()
    comp["lead_time"] = comp["completed_at"] - comp["released_at"]
    kpis["makespan"] = float(comp["completed_at"].max())
    kpis["n_completed"] = int(len(comp))
    kpis["throughput_total"] = float(comp["qty"].sum())
    kpis["avg_wip"] = float(comp["lead_time"].sum() / horizon)
    kpis["n_late"] = int((comp["completed_at"] > comp["due"]).sum())
    kpis["late_rate"] = kpis["n_late"] / len(comp)
    kpis["bottleneck"] = str(utilization.idxmax())
    for product, group in comp.groupby("product"):
        kpis[f"throughput_{product}"] = float(group["qty"].sum())
        kpis[f"lead_time_{product}"] = float(group["lead_time"].mean())
    return kpis
