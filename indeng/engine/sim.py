from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import simpy

from indeng.archetypes import build_plant
from indeng.config.loader import Scenario
from indeng.demand.generators import make_generator
from indeng.domain.models import Job, Workstation
from indeng.scheduling.rules import make_rule

EVENT_COLUMNS = [
    "job_id",
    "product",
    "qty",
    "station",
    "op_index",
    "setup_start",
    "start",
    "end",
]
COMPLETION_COLUMNS = [
    "job_id",
    "product",
    "qty",
    "released_at",
    "completed_at",
    "due",
]


@dataclass
class RunResult:
    scenario: Scenario
    seed: int
    horizon: float
    events: pd.DataFrame
    completions: pd.DataFrame


@dataclass
class _StationState:
    station: Workstation
    queue: list[Job] = field(default_factory=list)
    wakeup: simpy.Event | None = None


class SimEngine:
    def __init__(self, scenario: Scenario, seed: int | None = None):
        self.scenario = scenario
        self.seed = scenario.seed if seed is None else seed

    def run(self) -> RunResult:
        scenario = self.scenario
        rng = np.random.default_rng(self.seed)
        env = simpy.Environment()
        plant = build_plant(scenario)
        rule = make_rule(scenario.scheduling)
        states = {name: _StationState(station) for name, station in plant.stations.items()}
        events: list[dict] = []
        completions: list[dict] = []
        seq = 0

        def release(job: Job) -> None:
            state = states[job.current_operation().station]
            state.queue.append(job)
            if state.wakeup is not None and not state.wakeup.triggered:
                state.wakeup.succeed()

        def component_done(assembly: Job) -> None:
            assembly.pending -= 1
            if assembly.pending <= 0:
                release(assembly)

        def emit(product: str, qty: float) -> None:
            nonlocal seq
            due = env.now + scenario.nominal_flow_time(product, qty) * scenario.demand.due_slack
            prod = plant.products[product]
            job = Job(
                seq=seq,
                product=product,
                qty=qty,
                due=due,
                released_at=env.now,
                routing=prod.routing,
            )
            seq += 1
            if prod.bom:
                job.pending = len(prod.bom)
                for comp_name, per_unit in prod.bom:
                    comp = plant.components[comp_name]
                    component_job = Job(
                        seq=seq,
                        product=comp_name,
                        qty=per_unit * qty,
                        due=due,
                        released_at=env.now,
                        routing=comp.routing,
                        kind="component",
                        on_complete=lambda done=job: component_done(done),
                    )
                    seq += 1
                    release(component_job)
            else:
                release(job)

        def server_loop(state: _StationState) -> Iterator:
            last_product: str | None = None
            while True:
                if not state.queue:
                    if state.wakeup is None:
                        state.wakeup = env.event()
                    yield state.wakeup
                    state.wakeup = None
                    continue
                job = rule.select(state.queue, state.station.name)
                state.queue.remove(job)
                op = job.current_operation()
                setup = scenario.setup_time(state.station.name, last_product, job.product)
                last_product = job.product
                setup_start = env.now
                if setup > 0:
                    yield env.timeout(setup)
                start = env.now
                yield env.timeout(op.time * job.qty)
                end = env.now
                events.append(
                    {
                        "job_id": job.seq,
                        "product": job.product,
                        "qty": job.qty,
                        "station": state.station.name,
                        "op_index": job.next_op,
                        "setup_start": setup_start,
                        "start": start,
                        "end": end,
                    }
                )
                job.advance()
                if job.done:
                    if job.kind == "product":
                        completions.append(
                            {
                                "job_id": job.seq,
                                "product": job.product,
                                "qty": job.qty,
                                "released_at": job.released_at,
                                "completed_at": end,
                                "due": job.due,
                            }
                        )
                    elif job.on_complete is not None:
                        job.on_complete()
                else:
                    release(job)

        generator = make_generator(scenario.demand)
        env.process(generator.process(env, rng, emit))
        for state in states.values():
            for _ in range(state.station.capacity):
                env.process(server_loop(state))

        env.run(until=scenario.horizon)
        return RunResult(
            scenario=scenario,
            seed=self.seed,
            horizon=scenario.horizon,
            events=pd.DataFrame(events, columns=EVENT_COLUMNS),
            completions=pd.DataFrame(completions, columns=COMPLETION_COLUMNS),
        )
