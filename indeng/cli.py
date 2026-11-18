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
    comparison = subparsers.add_parser("compare-flow", help="compare DBR, kanban and CONWIP")
    comparison.add_argument("config", type=Path)
    comparison.add_argument("--out", type=Path, default=Path("out/flow"))
    comparison.add_argument("--seed", type=int)
    comparison.add_argument("--runs", type=int, default=30)
    comparison.add_argument("--calibration-runs", type=int, default=8)
    comparison.add_argument("--service-target", type=float, default=0.95)
    comparison.add_argument("--workers", type=int, default=1)
    comparison.add_argument("--core-only", action="store_true", help="factorial with the three base policies")
    comparison.add_argument("--variants", action="store_true", help="include variants in a standalone replay")
    group = comparison.add_mutually_exclusive_group()
    group.add_argument("--campaign", action="store_true", help="run calibration and the factorial campaign")
    group.add_argument("--scenario", default="mix", help="replay name (default: mix), or both")
    args = parser.parse_args(argv)

    if args.command == "compare-flow":
        from indeng.flow.experiment import write_end_card, campaign, replay
        from indeng.flow.model import COMPLEMENTS, FACTORIAL, MIX, STABLE, load_study

        if min(args.runs, args.calibration_runs, args.workers) < 1 or not 0 <= args.service_target <= 1:
            comparison.error("positive run counts and service target in [0, 1] required")
        study = load_study(args.config)
        seed = study.scenario.seed if args.seed is None else args.seed
        if args.campaign:
            campaign(study, args.out, seed=seed, runs=args.runs,
                     calibration_runs=args.calibration_runs, target=args.service_target,
                     workers=args.workers, core_only=args.core_only)
        else:
            designs = {design.name: design for design in (STABLE, MIX, *FACTORIAL, *COMPLEMENTS)}
            if args.scenario == "both":
                selected = (STABLE, MIX)
            elif args.scenario in designs:
                selected = (designs[args.scenario],)
            else:
                comparison.error(f"unknown scenario {args.scenario!r}; choose from {list(designs)} or both")
            for design in selected:
                rows = replay(study, design, seed, args.out, variants=args.variants)
                write_end_card(args.out / design.name / "end_card.csv", rows, (), design.name)
        print(f"saved {args.out}")
        return 0

    if args.command == "run":
        scenario = load_scenario(args.config)
        if scenario.flow_control is not None:
            run_parser.error("use indeng compare-flow for a flow_control scenario")
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
