from indeng.archetypes.base import register
from indeng.domain.models import Plant, Scenario


@register("A")
def build_a(scenario: Scenario) -> Plant:
    if not any(product.bom for product in scenario.products.values()):
        raise ValueError(
            "archetype A expects products assembled from components "
            "(define 'components' and a per-product BOM)"
        )
    last_stations = {product.routing[-1].station for product in scenario.products.values()}
    if len(last_stations) != 1:
        raise ValueError(
            "archetype A expects all products to converge on the same final "
            "(assembly) station"
        )
    return Plant(
        name=scenario.name,
        stations=scenario.stations,
        products=scenario.products,
        components=scenario.components,
    )
