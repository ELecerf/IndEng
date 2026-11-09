from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator

import numpy as np
import simpy

from indeng.domain.models import DemandSpec

Emit = Callable[[str, float], None]


class DemandGenerator(ABC):
    def __init__(self, spec: DemandSpec):
        self.spec = spec

    @abstractmethod
    def process(self, env: simpy.Environment, rng: np.random.Generator, emit: Emit) -> Iterator:
        """SimPy process calling emit(product, qty) whenever a new order is released."""

    def _pick_product(self, rng: np.random.Generator) -> str:
        products = self.spec.products
        if len(products) == 1:
            return products[0]
        return str(rng.choice(products))

    def _pick_qty(self, rng: np.random.Generator) -> float:
        if self.spec.kind == "random":
            return float(rng.integers(self.spec.qty_min, self.spec.qty_max + 1))
        return float(self.spec.qty)


class OnceDemand(DemandGenerator):
    def process(self, env: simpy.Environment, rng: np.random.Generator, emit: Emit) -> Iterator:
        yield env.timeout(0)
        for product in self.spec.products:
            emit(product, self._pick_qty(rng))


class ConstantDemand(DemandGenerator):
    def process(self, env: simpy.Environment, rng: np.random.Generator, emit: Emit) -> Iterator:
        while True:
            yield env.timeout(self.spec.interval)
            for product in self.spec.products:
                emit(product, self._pick_qty(rng))


class RandomDemand(DemandGenerator):
    def process(self, env: simpy.Environment, rng: np.random.Generator, emit: Emit) -> Iterator:
        while True:
            yield env.timeout(float(rng.exponential(1.0 / self.spec.rate)))
            emit(self._pick_product(rng), self._pick_qty(rng))


GENERATORS = {
    "once": OnceDemand,
    "constant": ConstantDemand,
    "random": RandomDemand,
}


def make_generator(spec: DemandSpec) -> DemandGenerator:
    return GENERATORS[spec.kind](spec)
