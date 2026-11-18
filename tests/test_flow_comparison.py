import json
from dataclasses import replace
from pathlib import Path

import pytest

from indeng.flow.drum import Calendar, Slot
from indeng.flow.engine import FlowEngine
from indeng.flow.model import (
    COMPLEMENTS, FACTORIAL, MIX, POLICIES, STABLE, Arrival, load_study, make_inputs,
)


@pytest.fixture(scope="module")
def study():
    return load_study(Path(__file__).parents[1] / "config/scenarios/flow_comparison.yaml")


def test_drum_booked_backwards_or_at_first_feasible_gap():
    args = dict(job_id=1, now=475, target=600, duration=15, upstream=45,
                downstream=30, nominal_upstream=20)
    booking = Calendar().reserve(**args)
    assert booking.slot == Slot(555, 570, 1)
    assert (booking.release, booking.planned_return) == (510, 600)
    # The first available gap after preparation is now 09:45.
    late = Calendar([Slot(495, 585, 2)]).reserve(**args)
    assert late.constrained
    assert late.slot == Slot(585, 600, 1)
    assert (late.release, late.planned_return) == (540, 630)
    # A fallback can release now with less than the requested upstream buffer.
    fallback = Calendar().reserve(**(args | {"target": 500}))
    assert fallback.slot == Slot(495, 510, 1)
    assert fallback.release == 475


def test_experimental_factors_change_only_intended_inputs(study):
    base = make_inputs(study, FACTORIAL[0], 11)
    mix = make_inputs(study, MIX, 11)
    burst = make_inputs(study, FACTORIAL[2], 11)
    load = make_inputs(study, FACTORIAL[1], 11)
    assert [order.at for order in base.arrivals] == [order.at for order in mix.arrivals]
    assert [order.sku for order in base.arrivals[:720]] == [order.sku for order in burst.arrivals[:720]]
    assert base.arrivals == load.arrivals
    for index, expected in enumerate((4, 10, 8, 4)):
        assert sum(base.nominal(sku)[index] for sku in study.skus) / 3 == expected
        assert sum(load.planned_operation("verte", rank, index, study.shock)
                   for rank in range(40)) / 40 == pytest.approx(expected)
    assert len({group.name for group in FACTORIAL}) == 8


@pytest.mark.parametrize("policy", POLICIES)
def test_empty_finished_stock_creates_and_closes_exactly_one_extra_need(study, policy):
    inputs = make_inputs(study, STABLE, 24)
    one_order = Arrival(0, 0, "rouge", 100)
    # Measurement windows need at least one arrival. Keep them far from the first order.
    arrivals = (one_order, Arrival(1, study.window + 1, "bleue", study.window + 101),
                Arrival(2, study.shock + 1, "bleue", study.shock + 101),
                Arrival(3, study.review + 1, "bleue", study.review + 101))
    inputs = replace(inputs, arrivals=arrivals)
    settings = replace(study.defaults[policy], target=1)
    result = FlowEngine(inputs, policy, settings, replay=True).run()
    initial_red = [need for need in result.replenishments
                   if need["sku"] == "rouge" and need["need_at"] == 0]
    assert len(initial_red) == 2   # One for the customer and one for the configured target.
    assert all(need["actual_return"] is not None for need in initial_red)
    assert len([need for need in result.replenishments if need["sku"] == "rouge"]) == 2
    assert result.orders[0]["delivered"] > 0
    assert len([event for event in result.events if event["event"] == "delivery"
                and json.loads(event["details"])["order_id"] == 0]) == 1


def test_kanban_cards_return_on_withdrawal_with_same_piece(study):
    result = FlowEngine(make_inputs(study, MIX, 2), "kanban", study.defaults["kanban"], replay=True).run()
    events = result.events
    for index, event in enumerate(events):
        if event["event"] != "card_return":
            continue
        assert json.loads(event["details"])["free"] > 0
        if event["reason"] == "intermediate_withdrawal":
            next_event = events[index + 1]
            assert next_event["event"] == "card_take"
            assert event["job_id"] == next_event["job_id"]
            assert study.stations.index(next_event["station"]) == study.stations.index(event["station"]) + 1
        else:
            assert (events[index - 1]["event"], events[index - 1]["job_id"]) == ("delivery", event["job_id"])


@pytest.mark.parametrize("policy", ["conwip", "conwip_weighted"])
def test_conwip_caps_and_replay_is_reproducible(study, policy):
    inputs = make_inputs(study, FACTORIAL[-1], 7)
    settings = replace(study.defaults["conwip"], cap=3, cap_minutes=37)
    first = FlowEngine(inputs, policy, settings, replay=True).run()
    second = FlowEngine(inputs, policy, settings, replay=True).run()
    assert first == second
    releases = [json.loads(event["details"]) for event in first.events if event["event"] == "release"]
    measure = "weight" if policy.endswith("weighted") else "wip"
    assert releases and all(row[measure] <= row["cap"] + 1e-9 for row in releases)
    returns = [event["job_id"] for event in first.events if event["event"] == "conwip_return"]
    finished = [event["job_id"] for event in first.events if event["event"] == "stock_in"]
    assert returns == finished


def test_renewal_preserves_kanban_flow_and_adaptive_drum_uses_observed_mix(study):
    renewal = FlowEngine(make_inputs(study, COMPLEMENTS[3], 4), "kanban_shared",
                         study.defaults["kanban"], replay=True).run()
    assert renewal.kpis["observation_service"] > 0.95
    assert any(event["event"] == "obsolete" for event in renewal.events)
    blue_mix = FlowEngine(make_inputs(study, COMPLEMENTS[0], 4), "dbr_adaptive",
                          study.defaults["dbr"], replay=True).run()
    assert any(event["event"] == "drum_change" and event["station"] == "C"
               and event["sim_time"] > study.shock for event in blue_mix.events)
