from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Operation:
    station: str
    time: float


@dataclass(frozen=True)
class Product:
    name: str
    routing: tuple[Operation, ...]


@dataclass(frozen=True)
class Workstation:
    name: str
    capacity: int = 1


@dataclass(frozen=True)
class DemandSpec:
    kind: str
    products: tuple[str, ...]
    interval: float = 1.0
    rate: float = 0.1
    qty: float = 1.0
    qty_min: int = 1
    qty_max: int = 10
    due_slack: float = 2.0


@dataclass(frozen=True)
class Plant:
    name: str
    stations: dict[str, Workstation]
    products: dict[str, Product]


@dataclass
class Job:
    seq: int
    product: str
    qty: float
    due: float
    released_at: float
    routing: tuple[Operation, ...]
    next_op: int = 0

    @property
    def id(self) -> int:
        return self.seq

    @property
    def done(self) -> bool:
        return self.next_op >= len(self.routing)

    def current_operation(self) -> Operation:
        return self.routing[self.next_op]

    def advance(self) -> None:
        self.next_op += 1


@dataclass
class Scenario:
    name: str
    archetype: str
    stations: dict[str, Workstation]
    products: dict[str, Product]
    demand: DemandSpec
    scheduling: str = "fifo"
    seed: int = 0
    horizon: float = 1000.0
    setup_default: float = 0.0
    setup_matrix: dict = field(default_factory=dict)

    def setup_time(self, station: str, from_product: str | None, to_product: str) -> float:
        if from_product is None or from_product == to_product:
            return 0.0
        return float(
            self.setup_matrix.get(station, {})
            .get(from_product, {})
            .get(to_product, self.setup_default)
        )

    def nominal_flow_time(self, product: str, qty: float) -> float:
        return sum(op.time for op in self.products[product].routing) * qty
