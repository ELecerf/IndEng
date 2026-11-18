"""Paired replays, calibration and factorial experiments."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import nullcontext
from dataclasses import asdict
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from indeng.flow.engine import FlowEngine
from indeng.flow.model import (
    COMPLEMENTS, FACTORIAL, MIX, POLICIES, STABLE, VARIANTS, Design, Study, make_inputs,
)

EVENT_COLUMNS = ("policy", "scenario", "seed", "sim_time", "event", "job_id", "sku",
                 "station", "reason", "queue_lengths", "stock_by_sku", "details")


def write_csv(path, rows, columns=None):
    rows = list(rows)
    if columns is None:
        columns = list(dict.fromkeys(key for row in rows for key in row))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def replay(study: Study, design: Design, seed: int, out: Path, settings=None, *,
           variants=False):
    inputs = make_inputs(study, design, seed)
    settings = study.defaults if settings is None else settings
    policies = POLICIES + VARIANTS if variants else POLICIES
    rows = []
    for policy in policies:
        selected = settings[policy.split("_")[0]]
        result = FlowEngine(inputs, policy, selected, replay=True).run()
        rows.append({"scenario": design.name, "seed": seed, "policy": policy,
                     "settings": json.dumps(asdict(selected)), **result.kpis})
        directory = out / design.name / policy
        write_csv(directory / "kpis.csv", rows[-1:])
        write_csv(directory / "events.csv", result.events, EVENT_COLUMNS)
        write_csv(directory / "orders.csv", result.orders)
        write_csv(directory / "replenishments.csv", result.replenishments)
    write_csv(out / design.name / "summary.csv", rows)
    return rows


def write_end_card(out, replay_rows, campaign_rows, scenario):
    metrics = ("service", "stock_total", "delivered_per_hour", "backlog_peak")
    rows = []
    for row in replay_rows:
        policy = row["policy"]
        phase = "gele" if policy in POLICIES else "variantes"
        sample = [run for run in campaign_rows
                  if (run["scenario"], run["phase"], run["policy"]) == (scenario, phase, policy)]
        for metric in metrics:
            key = f"observation_{metric}"
            rows.append({"policy": policy, "metric": metric, "replay_seed": row["seed"],
                         "replay_value": row[key], "campaign_n": len(sample),
                         "campaign_mean": np.mean([run[key] for run in sample]) if sample else None})
    write_csv(out, rows)


def _batch(task):
    study, design, seed, specs = task
    inputs = make_inputs(study, design, seed)
    return [
        (label, FlowEngine(inputs, policy, settings, revised=revised).run().kpis)
        for label, policy, settings, revised in specs
    ]


def _evaluate(pool, study, design, seeds, specs):
    tasks = ((study, design, seed, specs) for seed in seeds)
    results = map(_batch, tasks) if pool is None else pool.map(_batch, tasks)
    return zip(seeds, results)


def _calibrate(pool, study, design, seeds, target, *, frozen=None):
    specs = []
    for policy in POLICIES:
        for index, candidate in enumerate(study.grids[policy]):
            initial = candidate if frozen is None else frozen[policy]
            revised = None if frozen is None else candidate
            specs.append(((policy, index), policy, initial, revised))

    scores = defaultdict(list)
    period = "observation" if frozen is None else "apres_revision"
    for seed, results in _evaluate(pool, study, design, seeds, specs):
        for label, kpis in results:
            scores[label].append((kpis[f"{period}_service"], kpis[f"{period}_stock_total"]))

    selected = {}
    rows = []
    for policy in POLICIES:
        candidates = []
        for index, config in enumerate(study.grids[policy]):
            service, stock = np.mean(scores[policy, index], axis=0)
            candidates.append({
                "scenario": design.name, "phase": "stable" if frozen is None else "revision",
                "policy": policy, "candidate": index, "service": service, "stock": stock,
                "target_met": bool(service >= target), "settings": json.dumps(asdict(config)),
                "n": len(seeds),
            })
        feasible = [row for row in candidates if row["target_met"]]
        if feasible:
            chosen = min(feasible, key=lambda row: (row["stock"], -row["service"]))
        else:
            chosen = min(candidates, key=lambda row: (-row["service"], row["stock"]))
        selected[policy] = study.grids[policy][chosen["candidate"]]
        frontier = _frontier(candidates)
        for row in candidates:
            row["selected"] = row is chosen
            row["pareto"] = row in frontier
        rows.extend(candidates)
    return selected, rows


def _frontier(candidates):
    frontier = []
    best = -1.0
    for row in sorted(candidates, key=lambda row: (row["stock"], -row["service"])):
        if row["service"] > best + 1e-12:
            frontier.append(row)
            best = row["service"]
    return frontier


def _matched_targets(calibration, target):
    """Report budgets shared by all policies, without interpolating untested settings."""
    groups = defaultdict(list)
    for row in calibration:
        groups[row["phase"], row["scenario"]].append(row)
    for (phase, scenario), group in groups.items():
        budget_min = max(min(row["stock"] for row in group if row["policy"] == policy)
                         for policy in POLICIES)
        budgets = sorted({row["stock"] for row in group if row["stock"] >= budget_min})
        for policy in POLICIES:
            frontier = _frontier([row for row in group if row["policy"] == policy])
            for budget in budgets:
                point = max((row for row in frontier if row["stock"] <= budget),
                            key=lambda row: row["service"])
                yield {"phase": phase, "scenario": scenario, "policy": policy,
                       "basis": "stock_budget", "target": budget, "tested_service": point["service"],
                       "tested_stock": point["stock"], "candidate": point["candidate"]}
            for service in (target, min(max(row["service"] for row in group if row["policy"] == name)
                                         for name in POLICIES)):
                point = next((row for row in frontier if row["service"] >= service), None)
                yield {"phase": phase, "scenario": scenario, "policy": policy,
                       "basis": "minimum_service", "target": service,
                       "tested_service": point["service"] if point else None,
                       "tested_stock": point["stock"] if point else None,
                       "candidate": point["candidate"] if point else None}


def _paired(rows):
    table = {(row["scenario"], row["phase"], row["policy"], row["seed"]): row for row in rows}
    groups = defaultdict(set)
    for scenario, phase, policy, seed in table:
        groups[scenario, phase].add(policy)
    comparisons = []
    for (scenario, phase), policies in groups.items():
        for first, second in combinations([p for p in POLICIES if p in policies], 2):
            comparisons.append(((scenario, phase, first), (scenario, phase, second), "entre_politiques"))
        for policy in POLICIES:
            if phase == "revision":
                comparisons.append(((scenario, phase, policy), (scenario, "gele", policy), "revision_moins_gele"))
            if phase == "gele" and scenario != FACTORIAL[0].name:
                baseline = "temoin_gammes_identiques" if scenario == "mix_gammes_identiques" else FACTORIAL[0].name
                comparisons.append(((scenario, phase, policy), (baseline, phase, policy), "choc_moins_reference"))
        if phase == "variantes":
            for policy in VARIANTS:
                comparisons.append(((scenario, phase, policy), (scenario, "gele", policy.split("_")[0]),
                                    "variante_moins_base"))
    seeds = sorted({key[-1] for key in table})
    rng = np.random.default_rng(539)
    metrics = ("service", "stock_total", "backlog_peak", "backlog_piece_minutes",
               "delivered_per_hour", "lateness_p95_lower_bound")
    for first, second, contrast in comparisons:
        pairs = [(table[(*first, seed)], table[(*second, seed)]) for seed in seeds
                 if (*first, seed) in table and (*second, seed) in table]
        if not pairs:
            continue
        # Revision is evaluated on the same post-review time window for both runs.
        period = "apres_revision" if first[1] == "revision" or second[1] == "revision" else "observation"
        sample = rng.integers(len(pairs), size=(3000, len(pairs))) if len(pairs) > 1 else None
        for metric in metrics:
            key = f"{period}_{metric}"
            values = np.array([a[key] - b[key] for a, b in pairs])
            interval = [None, None] if sample is None else np.quantile(values[sample].mean(axis=1), [0.025, 0.975])
            yield {
                "contrast": contrast, "scenario": first[0], "phase": first[1], "policy": first[2],
                "reference_scenario": second[0], "reference_phase": second[1], "reference_policy": second[2],
                "metric": key, "n": len(pairs), "mean_difference": values.mean(),
                "ci95_low": interval[0], "ci95_high": interval[1],
            }


def campaign(study: Study, out: Path, *, seed: int, runs: int, calibration_runs: int,
             target: float, workers: int, core_only: bool = False):
    pilot_seeds = tuple(range(seed + runs, seed + runs + calibration_runs))
    seeds = tuple(range(seed, seed + runs))
    evaluation = []
    calibration = []
    designs = FACTORIAL if core_only else (*FACTORIAL, *COMPLEMENTS)
    context = ProcessPoolExecutor(max_workers=workers) if workers > 1 else nullcontext()
    with context as pool:
        print("Calibration en régime stable", flush=True)
        frozen, rows = _calibrate(pool, study, STABLE, pilot_seeds, target)
        calibration.extend(rows)
        for design in designs:
            print(f"Campagne · {design.name}", flush=True)
            revised, rows = _calibrate(pool, study, design, pilot_seeds, target, frozen=frozen)
            calibration.extend(rows)
            specs = [(("gele", policy), policy, frozen[policy], None) for policy in POLICIES]
            specs += [(("revision", policy), policy, frozen[policy], revised[policy]) for policy in POLICIES]
            if not core_only:
                specs += [(("variantes", policy), policy, frozen[policy.split("_")[0]], None)
                          for policy in VARIANTS]
            config = {label: (start, update) for label, _, start, update in specs}
            for run_seed, results in _evaluate(pool, study, design, seeds, specs):
                for (phase, policy), kpis in results:
                    start, update = config[phase, policy]
                    row = {"scenario": design.name, "phase": phase, "policy": policy, "seed": run_seed,
                           "initial_settings": json.dumps(asdict(start)),
                           "revised_settings": json.dumps(asdict(update)) if update else None, **kpis}
                    evaluation.append(row)
                    write_csv(out / "runs" / design.name / phase / policy / f"{run_seed}.csv", [row])
    write_csv(out / "calibration.csv", calibration)
    write_csv(out / "service_stock.csv", _matched_targets(calibration, target))
    write_csv(out / "runs.csv", evaluation)
    write_csv(out / "paired_differences.csv", _paired(evaluation))
    table = pd.DataFrame(evaluation)
    summary = table.groupby(["scenario", "phase", "policy"], sort=False)
    means = summary.mean(numeric_only=True).drop(columns="seed")
    means.insert(0, "n", summary.size())
    means["recovery_rate"] = 1 - summary["recovery_minutes"].agg(lambda column: column.isna().mean())
    means.to_csv(out / "summary.csv")
    metadata = {"evaluation_seeds": seeds, "pilot_seeds": pilot_seeds, "service_target": target,
                "settings": {policy: asdict(config) for policy, config in frozen.items()},
                "window_minutes": study.window, "shock_at": study.shock,
                "revision_at": study.review, "observation_end": study.stop, "replay_seed": seed,
                "stable_service_target_attained_by_all": all(row["target_met"] for row in calibration
                    if row["phase"] == "stable" and row["selected"])}
    (out / "protocol.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    for design, campaign_design in ((STABLE, FACTORIAL[0]), (MIX, FACTORIAL[4])):
        rows = replay(study, design, seed, out / "replay", frozen, variants=not core_only)
        write_end_card(out / "replay" / design.name / "end_card.csv",
                  rows, evaluation, campaign_design.name)
