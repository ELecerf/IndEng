from __future__ import annotations

from collections.abc import Callable

from indeng.domain.models import Plant, Scenario

ARCHETYPES: dict[str, Callable[[Scenario], Plant]] = {}


def register(name: str) -> Callable:
    def decorator(builder: Callable[[Scenario], Plant]) -> Callable[[Scenario], Plant]:
        ARCHETYPES[name] = builder
        return builder

    return decorator


def build_plant(scenario: Scenario) -> Plant:
    builder = ARCHETYPES.get(scenario.archetype)
    if builder is None:
        raise ValueError(
            f"unknown archetype {scenario.archetype!r}; expected one of {sorted(ARCHETYPES)}"
        )
    return builder(scenario)
