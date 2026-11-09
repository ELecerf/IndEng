from indeng.archetypes.base import register
from indeng.domain.models import Plant, Scenario


@register("V")
def build_v(scenario: Scenario) -> Plant:
    first_stations = {product.routing[0].station for product in scenario.products.values()}
    if len(first_stations) != 1:
        raise ValueError(
            "archetype V expects all products to share the same first station "
            "(single upstream flow diverging into product lines)"
        )
    return Plant(name=scenario.name, stations=scenario.stations, products=scenario.products)
