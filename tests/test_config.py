from pathlib import Path

import pytest

from indeng.archetypes import build_plant
from indeng.config.loader import load_scenario, scenario_from_dict

ROOT = Path(__file__).resolve().parents[1]


def base_dict():
    return {
        "name": "t",
        "archetype": "V",
        "stations": [{"name": "s1"}],
        "products": {"P": {"routing": [{"station": "s1", "time": 2.0}]}},
        "demand": {"kind": "once", "products": ["P"], "qty": 3},
    }


def test_load_v_minimal():
    scenario = load_scenario(ROOT / "config" / "scenarios" / "v_minimal.yaml")
    assert scenario.archetype == "V"
    assert set(scenario.stations) == {"prep", "line_a", "line_b"}
    assert scenario.stations["prep"].capacity == 2
    assert len(scenario.products["P1"].routing) == 2
    assert scenario.demand.kind == "random"
    assert scenario.setup_time("prep", "P1", "P2") == 3.0
    assert scenario.setup_time("prep", "P2", "P2") == 0.0
    assert scenario.setup_time("line_a", None, "P1") == 0.0


def test_unknown_station_in_routing_rejected():
    data = base_dict()
    data["products"]["P"]["routing"].append({"station": "nope", "time": 1.0})
    with pytest.raises(ValueError, match="unknown station"):
        scenario_from_dict(data)


def test_unknown_archetype_rejected():
    data = base_dict()
    data["archetype"] = "X"
    with pytest.raises(ValueError, match="archetype"):
        scenario_from_dict(data)


def test_unknown_scheduling_rejected():
    data = base_dict()
    data["scheduling"] = "xyz"
    with pytest.raises(ValueError, match="scheduling"):
        scenario_from_dict(data)


def test_unknown_demand_kind_rejected():
    data = base_dict()
    data["demand"]["kind"] = "weird"
    with pytest.raises(ValueError, match="demand kind"):
        scenario_from_dict(data)


def test_v_requires_shared_first_station():
    data = base_dict()
    data["stations"].append({"name": "s2"})
    data["products"]["Q"] = {"routing": [{"station": "s2", "time": 1.0}]}
    data["demand"]["products"] = ["P", "Q"]
    scenario = scenario_from_dict(data)
    with pytest.raises(ValueError, match="archetype V"):
        build_plant(scenario)
