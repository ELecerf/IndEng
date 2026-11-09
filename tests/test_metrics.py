import pandas as pd

from indeng.config.loader import scenario_from_dict
from indeng.engine.sim import COMPLETION_COLUMNS, EVENT_COLUMNS, RunResult
from indeng.metrics.kpis import compute_kpis, station_utilization


def make_result(events=None, completions=None):
    scenario = scenario_from_dict(
        {
            "name": "m",
            "archetype": "V",
            "horizon": 10.0,
            "stations": [{"name": "s1", "capacity": 1}, {"name": "s2", "capacity": 1}],
            "products": {
                "P": {
                    "routing": [
                        {"station": "s1", "time": 1.0},
                        {"station": "s2", "time": 1.0},
                    ]
                }
            },
            "demand": {"kind": "once", "products": ["P"], "qty": 1},
        }
    )
    return RunResult(
        scenario=scenario,
        seed=0,
        horizon=10.0,
        events=pd.DataFrame(events, columns=EVENT_COLUMNS),
        completions=pd.DataFrame(completions, columns=COMPLETION_COLUMNS),
    )


def sample_result():
    events = [
        {
            "job_id": 0,
            "product": "P",
            "qty": 2.0,
            "station": "s1",
            "op_index": 0,
            "setup_start": 0.0,
            "start": 0.0,
            "end": 4.0,
        },
        {
            "job_id": 0,
            "product": "P",
            "qty": 2.0,
            "station": "s2",
            "op_index": 1,
            "setup_start": 4.0,
            "start": 5.0,
            "end": 6.0,
        },
    ]
    completions = [
        {
            "job_id": 0,
            "product": "P",
            "qty": 2.0,
            "released_at": 0.0,
            "completed_at": 6.0,
            "due": 5.0,
        }
    ]
    return make_result(events, completions)


def test_station_utilization_counts_setup_as_busy():
    utilization = station_utilization(sample_result())
    assert utilization["s1"] == 4.0 / 10.0
    assert utilization["s2"] == 2.0 / 10.0


def test_compute_kpis():
    kpis = compute_kpis(sample_result())
    assert kpis["makespan"] == 6.0
    assert kpis["n_completed"] == 1
    assert kpis["throughput_total"] == 2.0
    assert kpis["throughput_P"] == 2.0
    assert kpis["lead_time_P"] == 6.0
    assert kpis["avg_wip"] == 6.0 / 10.0
    assert kpis["bottleneck"] == "s1"
    assert kpis["n_late"] == 1
    assert kpis["late_rate"] == 1.0


def test_empty_result():
    result = make_result(events=[], completions=[])
    kpis = compute_kpis(result)
    assert kpis["n_completed"] == 0
    assert kpis["throughput_total"] == 0.0
    assert kpis["makespan"] == 0.0
    assert kpis["utilization_s1"] == 0.0
