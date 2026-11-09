from __future__ import annotations

import pandas as pd

from indeng.config.loader import Scenario
from indeng.engine.sim import RunResult, SimEngine
from indeng.metrics.kpis import compute_kpis


def run_single(scenario: Scenario, seed: int) -> tuple[RunResult, dict]:
    result = SimEngine(scenario, seed=seed).run()
    return result, compute_kpis(result)


def run_experiment(
    scenario: Scenario, n_runs: int = 10, base_seed: int | None = None
) -> pd.DataFrame:
    base = scenario.seed if base_seed is None else base_seed
    rows = []
    for i in range(n_runs):
        seed = base + i
        _, kpis = run_single(scenario, seed)
        rows.append({"run": i, "seed": seed, **kpis})
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    numeric = df.select_dtypes("number")
    return pd.DataFrame({"mean": numeric.mean(), "std": numeric.std(ddof=0)})
