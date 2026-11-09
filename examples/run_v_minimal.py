from pathlib import Path

from indeng import compute_kpis, load_scenario, run_experiment, summarize
from indeng.engine.sim import SimEngine
from indeng.metrics.kpis import station_utilization
from indeng.viz.plots import save_all_plots

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    scenario = load_scenario(ROOT / "config" / "scenarios" / "v_minimal.yaml")
    runs = run_experiment(scenario, n_runs=5)
    print(summarize(runs).to_string())
    result = SimEngine(scenario, seed=scenario.seed).run()
    kpis = compute_kpis(result)
    paths = save_all_plots(
        result, station_utilization(result), kpis.get("bottleneck"), ROOT / "examples" / "out"
    )
    for path in paths:
        print(f"saved {path}")


if __name__ == "__main__":
    main()
