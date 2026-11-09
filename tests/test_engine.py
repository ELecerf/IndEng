from pandas.testing import assert_frame_equal

from indeng.config.loader import scenario_from_dict
from indeng.engine.sim import SimEngine


def tiny_scenario(**overrides):
    data = {
        "name": "tiny",
        "archetype": "V",
        "seed": 7,
        "horizon": 10.0,
        "stations": [{"name": "s1", "capacity": 1}],
        "products": {"P": {"routing": [{"station": "s1", "time": 2.0}]}},
        "demand": {"kind": "once", "products": ["P"], "qty": 3},
    }
    data.update(overrides)
    return scenario_from_dict(data)


def test_single_order_exact_timing():
    result = SimEngine(tiny_scenario()).run()
    assert len(result.completions) == 1
    row = result.completions.iloc[0]
    assert row["released_at"] == 0.0
    assert row["completed_at"] == 6.0
    event = result.events.iloc[0]
    assert event["start"] == 0.0
    assert event["end"] == 6.0


def test_deterministic_with_same_seed():
    scenario = tiny_scenario(
        horizon=50.0,
        demand={"kind": "random", "products": ["P"], "rate": 0.5, "qty_min": 1, "qty_max": 5},
    )
    first = SimEngine(scenario, seed=7).run()
    second = SimEngine(scenario, seed=7).run()
    assert_frame_equal(first.completions, second.completions)
    assert_frame_equal(first.events, second.events)


def _two_product_data(capacity):
    return {
        "name": "cap",
        "archetype": "V",
        "horizon": 10.0,
        "stations": [{"name": "s1", "capacity": capacity}],
        "products": {
            "P1": {"routing": [{"station": "s1", "time": 1.0}]},
            "P2": {"routing": [{"station": "s1", "time": 1.0}]},
        },
        "demand": {"kind": "once", "products": ["P1", "P2"], "qty": 1},
    }


def test_capacity_allows_parallel_processing():
    result = SimEngine(scenario_from_dict(_two_product_data(2)), seed=0).run()
    assert sorted(result.completions["completed_at"]) == [1.0, 1.0]


def test_single_capacity_serializes():
    result = SimEngine(scenario_from_dict(_two_product_data(1)), seed=0).run()
    assert sorted(result.completions["completed_at"]) == [1.0, 2.0]


def test_archetype_a_assembly_waits_for_components():
    data = {
        "name": "a",
        "archetype": "A",
        "horizon": 50.0,
        "stations": [{"name": "cut", "capacity": 1}, {"name": "asm", "capacity": 1}],
        "components": {"comp": {"routing": [{"station": "cut", "time": 2.0}]}},
        "products": {
            "P": {"components": {"comp": 1}, "routing": [{"station": "asm", "time": 3.0}]}
        },
        "demand": {"kind": "once", "products": ["P"], "qty": 2},
    }
    result = SimEngine(scenario_from_dict(data), seed=0).run()
    assert len(result.completions) == 1
    row = result.completions.iloc[0]
    assert row["product"] == "P"
    assert row["completed_at"] == 4.0 + 6.0
    assert set(result.events["product"]) == {"comp", "P"}
    comp_events = result.events[result.events["product"] == "comp"]
    assert (comp_events["end"] - comp_events["start"]).iloc[0] == 4.0


def test_setup_time_applied_on_product_change():
    data = _two_product_data(1)
    data["setup_default"] = 2.0
    result = SimEngine(scenario_from_dict(data), seed=0).run()
    events = result.events.sort_values("setup_start").reset_index(drop=True)
    assert events.loc[0, "setup_start"] == 0.0
    assert events.loc[0, "start"] == 0.0
    assert events.loc[0, "end"] == 1.0
    assert events.loc[1, "setup_start"] == 1.0
    assert events.loc[1, "start"] - events.loc[1, "setup_start"] == 2.0
    assert events.loc[1, "end"] == 4.0
