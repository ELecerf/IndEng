from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from indeng.engine.sim import RunResult


def plot_gantt(result: RunResult, path: str | Path) -> Path:
    events = result.events
    path = Path(path)
    stations = list(dict.fromkeys(events["station"]))
    products = list(dict.fromkeys(events["product"]))
    colors = {product: f"C{i}" for i, product in enumerate(products)}
    fig, ax = plt.subplots(figsize=(12, max(3, 0.8 * len(stations) + 1)))
    for row, station in enumerate(stations):
        subset = events[events["station"] == station]
        for _, event in subset.iterrows():
            ax.barh(
                row,
                event["end"] - event["setup_start"],
                left=event["setup_start"],
                color=colors[event["product"]],
                edgecolor="black",
                linewidth=0.3,
            )
    ax.set_yticks(range(len(stations)))
    ax.set_yticklabels(stations)
    ax.set_xlabel("time")
    ax.set_title(f"Gantt - {result.scenario.name}")
    handles = [plt.Rectangle((0, 0), 1, 1, color=color) for color in colors.values()]
    ax.legend(handles, list(colors), loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def plot_production_curve(result: RunResult, path: str | Path) -> Path:
    path = Path(path)
    fig, ax = plt.subplots(figsize=(10, 4))
    for product, group in result.completions.groupby("product"):
        ordered = group.sort_values("completed_at")
        ax.step(ordered["completed_at"], ordered["qty"].cumsum(), where="post", label=product)
    ax.set_xlabel("time")
    ax.set_ylabel("cumulative qty produced")
    ax.set_title(f"Production - {result.scenario.name}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def plot_utilization(utilization: pd.Series, bottleneck: str | None, path: str | Path) -> Path:
    path = Path(path)
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = [
        "tomato" if name == bottleneck else "steelblue" for name in utilization.index
    ]
    ax.bar(utilization.index, utilization.values, color=colors)
    ax.set_ylabel("utilization")
    ax.set_ylim(0, 1.05)
    ax.set_title("Station utilization (red = bottleneck)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def save_all_plots(
    result: RunResult, utilization: pd.Series, bottleneck: str | None, outdir: str | Path
) -> list[Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    return [
        plot_gantt(result, outdir / "gantt.png"),
        plot_production_curve(result, outdir / "production.png"),
        plot_utilization(utilization, bottleneck, outdir / "utilization.png"),
    ]
