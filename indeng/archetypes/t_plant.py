from indeng.archetypes.base import register
from indeng.domain.models import Plant, Scenario


@register("T")
def build_t(scenario: Scenario) -> Plant:
    raise NotImplementedError("archetype T is scaffolded but not implemented yet")
