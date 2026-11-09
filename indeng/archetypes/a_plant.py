from indeng.archetypes.base import register
from indeng.domain.models import Plant, Scenario


@register("A")
def build_a(scenario: Scenario) -> Plant:
    raise NotImplementedError("archetype A is scaffolded but not implemented yet")
