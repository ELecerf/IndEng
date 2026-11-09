from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from indeng.domain.models import Scenario

PALETTE = [
    "#E6194B",
    "#3CB44B",
    "#4363D8",
    "#F58231",
    "#911EB4",
    "#42D4F4",
    "#F032E6",
    "#469990",
    "#9A6324",
    "#800000",
]


def topology_dot(scenario: Scenario, highlight: str | None = None) -> str:
    lines = [
        "digraph plant {",
        "  rankdir=LR;",
        '  node [shape=box, style="rounded,filled", fillcolor=white];',
        '  "demande" [shape=oval, fillcolor=grey80];',
    ]
    for name, station in scenario.stations.items():
        if name == highlight:
            label = f"{name}\\ncap={station.capacity}\\nGOULOT"
            fill = "#FF6B6B"
        else:
            label = f"{name}\\ncap={station.capacity}"
            fill = "white"
        lines.append(f'  "{name}" [label="{label}", fillcolor="{fill}"];')
    for product_name in scenario.products:
        lines.append(
            f'  "{product_name}" [shape=box, style="rounded,filled", fillcolor="#BDD7EE"];'
        )
    offset = len(scenario.products)
    for i, (comp_name, component) in enumerate(scenario.components.items()):
        color = PALETTE[(offset + i) % len(PALETTE)]
        ops = component.routing
        lines.append(
            f'  "demande" -> "{ops[0].station}" [color="{color}", style=dashed, label="{comp_name}"];'
        )
        for j in range(len(ops) - 1):
            lines.append(
                f'  "{ops[j].station}" -> "{ops[j + 1].station}" [color="{color}", style=dashed, label="t={ops[j].time}"];'
            )
    for i, (product_name, product) in enumerate(scenario.products.items()):
        color = PALETTE[i % len(PALETTE)]
        ops = product.routing
        if not product.bom:
            lines.append(
                f'  "demande" -> "{ops[0].station}" [color="{color}", penwidth=2, label="{product_name}"];'
            )
        for comp_name, per_unit in product.bom:
            comp_last = scenario.components[comp_name].routing[-1].station
            lines.append(
                f'  "{comp_last}" -> "{ops[0].station}" [color="{color}", penwidth=2, label="{comp_name} x{per_unit}"];'
            )
        for j, op in enumerate(ops):
            target = ops[j + 1].station if j + 1 < len(ops) else product_name
            lines.append(
                f'  "{op.station}" -> "{target}" [color="{color}", penwidth=2, label="t={op.time}"];'
            )
    lines.append("}")
    return "\n".join(lines) + "\n"


def save_topology(
    scenario: Scenario, outdir: str | Path, highlight: str | None = None
) -> list[Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    dot_path = outdir / "topology.dot"
    dot_path.write_text(topology_dot(scenario, highlight), encoding="utf-8")
    svg_path = outdir / "topology.svg"
    renderer = Path(__file__).resolve().parents[2] / "scripts" / "render_dot.mjs"
    if shutil.which("node") and renderer.exists():
        try:
            subprocess.run(
                ["node", str(renderer), str(dot_path), str(svg_path)],
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    return [path for path in (dot_path, svg_path) if path.exists()]
