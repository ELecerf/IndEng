from __future__ import annotations

from pathlib import Path

import yaml

from indeng.archetypes import ARCHETYPES
from indeng.domain.models import DemandSpec, Operation, Product, Scenario, Workstation
from indeng.scheduling.rules import RULES

DEMAND_KINDS = ("once", "constant", "random")


def load_scenario(path: str | Path) -> Scenario:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return scenario_from_dict(data)


def scenario_from_dict(data: dict) -> Scenario:
    if not isinstance(data, dict):
        raise ValueError("scenario must be a mapping")
    archetype = data.get("archetype")
    if archetype not in ARCHETYPES:
        raise ValueError(
            f"unknown archetype {archetype!r}; expected one of {sorted(ARCHETYPES)}"
        )
    scheduling = data.get("scheduling", "fifo")
    if scheduling not in RULES:
        raise ValueError(
            f"unknown scheduling rule {scheduling!r}; expected one of {sorted(RULES)}"
        )
    stations = _parse_stations(data.get("stations"))
    products = _parse_products(data.get("products"), stations)
    demand = _parse_demand(data.get("demand"), products)
    return Scenario(
        name=str(data.get("name", "unnamed")),
        archetype=archetype,
        stations=stations,
        products=products,
        demand=demand,
        scheduling=scheduling,
        seed=int(data.get("seed", 0)),
        horizon=float(data.get("horizon", 1000.0)),
        setup_default=float(data.get("setup_default", 0.0)),
        setup_matrix=data.get("setup_matrix") or {},
    )


def _parse_stations(raw) -> dict[str, Workstation]:
    if not raw:
        raise ValueError("scenario must define 'stations'")
    stations: dict[str, Workstation] = {}
    for entry in raw:
        name = str(entry["name"])
        capacity = int(entry.get("capacity", 1))
        if capacity < 1:
            raise ValueError(f"station {name!r}: capacity must be >= 1")
        if name in stations:
            raise ValueError(f"duplicate station {name!r}")
        stations[name] = Workstation(name=name, capacity=capacity)
    return stations


def _parse_products(raw, stations: dict[str, Workstation]) -> dict[str, Product]:
    if not raw:
        raise ValueError("scenario must define 'products'")
    products: dict[str, Product] = {}
    for name, spec in raw.items():
        routing_raw = spec.get("routing")
        if not routing_raw:
            raise ValueError(f"product {name!r} must define a non-empty 'routing'")
        ops = []
        for op in routing_raw:
            station = str(op["station"])
            if station not in stations:
                raise ValueError(
                    f"product {name!r}: unknown station {station!r} in routing"
                )
            time = float(op["time"])
            if time <= 0:
                raise ValueError(f"product {name!r}: operation time must be > 0")
            ops.append(Operation(station=station, time=time))
        products[str(name)] = Product(name=str(name), routing=tuple(ops))
    return products


def _parse_demand(raw, products: dict[str, Product]) -> DemandSpec:
    if not raw:
        raise ValueError("scenario must define 'demand'")
    kind = str(raw.get("kind"))
    if kind not in DEMAND_KINDS:
        raise ValueError(
            f"unknown demand kind {kind!r}; expected one of {list(DEMAND_KINDS)}"
        )
    spec_products = tuple(str(p) for p in raw.get("products", []))
    if not spec_products:
        raise ValueError("demand must list at least one product")
    for p in spec_products:
        if p not in products:
            raise ValueError(f"demand references unknown product {p!r}")
    spec = DemandSpec(
        kind=kind,
        products=spec_products,
        interval=float(raw.get("interval", 1.0)),
        rate=float(raw.get("rate", 0.1)),
        qty=float(raw.get("qty", 1.0)),
        qty_min=int(raw.get("qty_min", 1)),
        qty_max=int(raw.get("qty_max", 10)),
        due_slack=float(raw.get("due_slack", 2.0)),
    )
    if spec.interval <= 0:
        raise ValueError("demand interval must be > 0")
    if spec.rate <= 0:
        raise ValueError("demand rate must be > 0")
    if spec.qty_min < 1 or spec.qty_max < spec.qty_min:
        raise ValueError("demand qty_min/qty_max must satisfy 1 <= qty_min <= qty_max")
    return spec
