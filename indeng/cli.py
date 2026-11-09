from __future__ import annotations

import argparse
from pathlib import Path

from indeng.config.loader import load_scenario
from indeng.experiments.runner import run_experiment, run_single, summarize
from indeng.metrics.kpis import compute_kpis, station_utilization
from indeng.viz.plots import save_all_plots
from indeng.viz.topology import save_topology


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="indeng", description="TOC-based factory flow simulations"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="run a scenario from a YAML config")
    run_parser.add_argument("config", type=Path)
    run_parser.add_argument("--runs", type=int, default=1)
    run_parser.add_argument("--seed", type=int, default=None)
    run_parser.add_argument("--out", type=Path, default=Path("out"))
    run_parser.add_argument("--no-plots", action="store_true")
    graph_parser = subparsers.add_parser(
        "graph", help="render the routing topology of a scenario (Graphviz DOT/SVG)"
    )
    graph_parser.add_argument("config", type=Path)
    graph_parser.add_argument("--out", type=Path, default=Path("out"))
    graph_parser.add_argument(
        "--highlight", type=str, default=None, help="station to highlight (e.g. bottleneck)"
    )
    args = parser.parse_args(argv)

    if args.command == "run":
        scenario = load_scenario(args.config)
        runs = run_experiment(scenario, n_runs=args.runs, base_seed=args.seed)
        print(runs.to_string(index=False))
        print()
        print(summarize(runs).to_string())
        args.out.mkdir(parents=True, exist_ok=True)
        runs.to_csv(args.out / "kpis.csv", index=False)
        result, kpis = run_single(scenario, seed=int(runs["seed"].iloc[0]))
        result.events.to_csv(args.out / "events.csv", index=False)
        result.completions.to_csv(args.out / "completions.csv", index=False)
        if not args.no_plots:
            paths = save_all_plots(
                result, station_utilization(result), kpis.get("bottleneck"), args.out
            )
            for path in paths:
                print(f"saved {path}")
        return 0
    if args.command == "graph":
        scenario = load_scenario(args.config)
        paths = save_topology(scenario, args.out, highlight=args.highlight)
        for path in paths:
            print(f"saved {path}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
