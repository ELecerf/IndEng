"""Configuration and common, policy-independent experimental inputs."""
from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import product
from math import isfinite
from pathlib import Path
from random import Random

from indeng.config.loader import load_scenario
from indeng.domain.models import Scenario

POLICIES = ("dbr", "kanban", "conwip")
VARIANTS = ("dbr_fifo", "dbr_adaptive", "kanban_shared", "conwip_weighted")


@dataclass(frozen=True)
class Design:
    name: str
    mix: bool = False
    burst: bool = False
    load: bool = False
    blue: bool = False
    identical: bool = False
    renewal: bool = False
    error: bool = False
    volume: int = 60


FACTORIAL = tuple(
    Design(f"mix{int(mix)}_demande{int(burst)}_charge{int(load)}", mix, burst, load)
    for mix, burst, load in product((False, True), repeat=3)
)
STABLE = Design("stable")
MIX = Design("mix", mix=True)
COMPLEMENTS = (
    Design("mix_bleu", blue=True),
    Design("mix_gammes_identiques", mix=True, identical=True),
    Design("temoin_gammes_identiques", identical=True),
    Design("renouvellement", renewal=True),
    Design("erreur_durees", error=True),
    Design("hausse_absorbable", volume=63),
    Design("surcharge", volume=72),
)


@dataclass(frozen=True)
class Settings:
    target: int = 2
    intermediate: tuple[int, ...] = (1, 1, 1)
    allocation: tuple[int, int, int] = (1, 1, 1)
    cap: int = 8
    cap_minutes: float = 80.0
    upstream: float = 16.0
    downstream: float = 16.0
    drum: str = "B"


@dataclass(frozen=True)
class Study:
    scenario: Scenario
    skus: tuple[str, ...]
    stations: tuple[str, ...]
    interval: float
    warmup_windows: int
    observation_windows: int
    review_windows: int
    notice_windows: int
    customer_delay: float
    replenishment_delay: float
    amplitude: float
    recovery_windows: int
    drum_window: float
    drum_period: float
    drum_gap: float
    defaults: dict[str, Settings]
    grids: dict[str, tuple[Settings, ...]]

    @property
    def window(self) -> float:
        return 60 * self.interval

    @property
    def shock(self) -> float:
        return self.warmup_windows * self.window

    @property
    def stop(self) -> float:
        return (self.warmup_windows + self.observation_windows) * self.window

    @property
    def review(self) -> float:
        return (self.warmup_windows + self.review_windows) * self.window

    @property
    def followup(self) -> float:
        return max(self.customer_delay, self.replenishment_delay)


def _number(value, name: str, minimum: float = 0.0) -> float:
    result = float(value)
    if not isfinite(result) or result < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return result


def _integer(value, name: str, minimum: int = 0) -> int:
    result = _number(value, name, minimum)
    if not result.is_integer():
        raise ValueError(f"{name} must be an integer")
    return int(result)


def _settings(values: dict, base: Settings, stations: tuple[str, ...]) -> Settings:
    unknown = values.keys() - Settings.__dataclass_fields__.keys()
    if unknown:
        raise ValueError(f"unknown flow settings: {sorted(unknown)}")
    data = vars(base) | values
    for name in ("target", "cap"):
        data[name] = _integer(data[name], name, 1)
    for name in ("upstream", "downstream", "cap_minutes"):
        data[name] = _number(data[name], name)
    for name, length in (("intermediate", len(stations) - 1), ("allocation", 3)):
        data[name] = tuple(_integer(n, name, 1) for n in data[name])
        if len(data[name]) != length:
            raise ValueError(f"{name} expects {length} values")
    if data["drum"] not in stations or data["cap_minutes"] <= 0:
        raise ValueError("invalid drum station or weighted CONWIP cap")
    return Settings(**data)


def load_study(path: str | Path) -> Study:
    scenario = load_scenario(path)
    raw = scenario.flow_control
    if not isinstance(raw, dict):
        raise ValueError("comparison requires a flow_control mapping")
    skus = scenario.demand.products
    stations = tuple(scenario.stations)
    if (
        len(skus) != 3 or len(set(skus)) != 3 or len(stations) != 4
        or scenario.scheduling != "fifo" or scenario.components
        or scenario.setup_default or scenario.setup_matrix
        or any(station.capacity != 1 for station in scenario.stations.values())
        or any(tuple(op.station for op in sku.routing) != stations
               or any(not isfinite(op.time) for op in sku.routing)
               for sku in scenario.products.values())
    ):
        raise ValueError("comparison requires three SKUs, a shared four-post flow-shop, FIFO and no setups")
    warmup = _integer(raw.get("warmup_windows", 4), "warmup_windows", 2)
    observation = _integer(raw.get("observation_windows", 8), "observation_windows", 3)
    review = _integer(raw.get("review_windows", 2), "review_windows", 1)
    notice = _integer(raw.get("notice_windows", 1), "notice_windows")
    amplitude = _number(raw.get("load_amplitude", 0.4), "load_amplitude")
    if review >= observation or notice > warmup or amplitude >= 1:
        raise ValueError("review must precede observation end, notice must fit warmup, amplitude must be < 1")
    defaults = {}
    grids = {}
    for policy in POLICIES:
        base = Settings(drum=stations[1])
        defaults[policy] = _settings(raw.get("policies", {}).get(policy, {}), base, stations)
        grid = raw.get("grids", {}).get(policy, [])
        grids[policy] = tuple(dict.fromkeys(
            [defaults[policy]] + [_settings(row, defaults[policy], stations) for row in grid]
        ))
    return Study(
        scenario, skus, stations, _number(scenario.demand.interval, "interval", 0.001),
        warmup, observation, review, notice,
        _number(raw.get("customer_delay", 0), "customer_delay"),
        _number(raw.get("replenishment_delay", 90), "replenishment_delay"),
        amplitude, _integer(raw.get("recovery_windows", 2), "recovery_windows", 1),
        _number(raw.get("drum_window", 240), "drum_window", 0.001),
        _number(raw.get("drum_period", 120), "drum_period", 0.001),
        _number(raw.get("drum_gap", 0.08), "drum_gap"), defaults, grids,
    )


@dataclass(frozen=True)
class Arrival:
    id: int
    at: float
    sku: str
    due: float


@dataclass(frozen=True)
class Inputs:
    study: Study
    design: Design
    seed: int
    arrivals: tuple[Arrival, ...]

    @property
    def new_sku(self) -> str:
        return f"{self.study.skus[2]}_nouvelle"

    def nominal(self, sku: str) -> tuple[float, ...]:
        if self.design.identical:
            return _common_route(self.study.skus, self.study.scenario)
        original = self.study.skus[2] if sku == self.new_sku else sku
        return tuple(op.time for op in self.study.scenario.products[original].routing)

    def planned_operation(self, sku: str, rank: int, index: int, now: float) -> float:
        if self.design.identical:
            nominal = _common_route(self.study.skus, self.study.scenario)[index]
        else:
            original = self.study.skus[2] if sku == self.new_sku else sku
            nominal = self.study.scenario.products[original].routing[index].time
        if self.design.load and now >= self.study.shock:
            return nominal * self._multiplier("planned", sku, rank, index)
        return nominal

    def actual(self, sku: str, rank: int, index: int, planned: float, now: float) -> float:
        if self.design.error and now >= self.study.shock:
            return planned * self._multiplier("actual", sku, rank, index)
        return planned

    def _multiplier(self, stream: str, sku: str, rank: int, index: int) -> float:
        positive_first = _positive_first(self.seed, stream, sku, rank // 2, index)
        sign = 1 if (rank % 2 == 0) == positive_first else -1
        return 1 + sign * self.study.amplitude


def _common_route(skus: tuple[str, ...], scenario: Scenario) -> tuple[float, ...]:
    return tuple(sum(scenario.products[sku].routing[index].time for sku in skus) / len(skus)
                 for index in range(len(scenario.stations)))


@lru_cache(maxsize=65536)
def _positive_first(seed: int, stream: str, sku: str, pair: int, index: int) -> int:
    return Random(f"{seed}|{stream}|{sku}|{pair}|{index}").getrandbits(1)


def make_inputs(study: Study, design: Design, seed: int) -> Inputs:
    arrivals = []
    total_windows = study.warmup_windows + study.observation_windows
    # Continue the input process through follow-up to preserve competition for stock.
    extra = 1 + int(study.followup / study.window)
    for window in range(total_windows + extra):
        after = window >= study.warmup_windows
        mix = (20, 20, 20)
        if after and design.mix:
            mix = (27, 12, 21)
        if after and design.blue:
            mix = (12, 36, 12)
        count = design.volume if after else 60
        counts = [int(round(count * n / 60)) for n in mix[:2]]
        counts.append(count - sum(counts))
        skus = study.skus
        if after and design.renewal:
            skus = (*skus[:2], f"{skus[2]}_nouvelle")
        sequence = [sku for sku, n in zip(skus, counts) for _ in range(n)]
        Random(f"{seed}|orders|{window}").shuffle(sequence)
        for index, sku in enumerate(sequence):
            offset = index / count
            if after and design.burst:
                offset = (index // 15 * 15 + index % 15 / 4) / count
            at = (window + offset) * study.window
            if at > study.stop + study.followup:
                break
            arrivals.append(Arrival(len(arrivals), at, sku, at + study.customer_delay))
    return Inputs(study, design, seed, tuple(arrivals))
