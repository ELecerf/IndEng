"""SimPy flow-shop with physical inventory and interchangeable release policies."""
from __future__ import annotations

import json
from collections import Counter, deque
from dataclasses import dataclass
from math import nextafter, inf
from typing import NamedTuple

import numpy as np
import simpy

from indeng.domain.models import Job, Operation
from indeng.flow.drum import Calendar, Reservation
from indeng.flow.model import Arrival, Inputs, Settings
from indeng.scheduling.rules import make_rule


class Piece(NamedTuple):
    id: int
    sku: str


@dataclass
class Need:
    id: int
    sku: str
    at: float
    target: float
    job: Job | None = None
    drum: int | None = None
    reservation: Reservation | None = None
    weight: float = 0.0
    returned: float | None = None
    cancelled: bool = False
    urgency: float = 0.0


@dataclass
class Task:
    piece: Piece
    index: int
    planned: float
    need: Need | None


@dataclass
class Result:
    kpis: dict
    events: list[dict]
    orders: list[dict]
    replenishments: list[dict]


class FlowEngine:
    def __init__(self, inputs: Inputs, policy: str, settings: Settings, *,
                 revised: Settings | None = None, replay: bool = False):
        self.inputs = inputs
        self.study = inputs.study
        self.policy = policy
        self.settings = settings
        self.revised = revised
        self.replay = replay
        self.kanban = policy.startswith("kanban")
        self.shared = policy == "kanban_shared"
        self.dbr = policy.startswith("dbr")
        self.weighted = policy == "conwip_weighted"
        self.env = simpy.Environment()
        self.rule = make_rule(self.study.scenario.scheduling)
        self.stations = self.study.stations
        self.skus = self.study.skus + ((inputs.new_sku,) if inputs.design.renewal else ())
        self.drum = self.stations.index(settings.drum)
        self.weight_station = self.drum
        self.stock = [{sku: deque() for sku in self.skus} for _ in self.stations]
        self.vacancy = [{sku: deque() for sku in self.skus} for _ in self.stations[:-1]]
        self.busy: list[Task | None] = [None for _ in self.stations]
        self.queues: list[list[Job]] = [[] for _ in self.stations]
        self.calendars = [Calendar() for _ in self.stations]
        self.backlog = {sku: deque() for sku in self.skus}
        self.waiting = {sku: deque() for sku in self.skus}
        self.open = Counter()
        self.needs: list[Need] = []
        self.active: dict[int, Need] = {}
        self.in_transit: dict[int, Piece] = {}
        self.weight_used = 0.0
        self.planned_ranks = Counter()
        self.actual_ranks = Counter()
        self.piece_count = 0
        self.delivered_at: dict[int, float] = {}
        self.obsolete: list[Piece] = []
        self.events: list[dict] = []
        self.reasons: list[str | None] = [None for _ in self.stations]
        self.signal = self.env.event()
        self.last = 0.0
        self.areas = [Counter() for _ in range(self.study.warmup_windows + self.study.observation_windows)]
        self.peaks = [0 for _ in self.areas]
        self.sequence = 0

    @property
    def now(self) -> float:
        return self.env.now

    def _event(self, event: str, *, sku=None, station=None, job_id=None, reason=None, **data):
        if not self.replay:
            return
        if self.kanban:
            queues = [sum(len(queue) for queue in loop.values()) for loop in self.vacancy]
            queues.append(sum(map(len, self.waiting.values())))
        else:
            queues = [len(queue) for queue in self.queues]
        self.events.append({
            "policy": self.policy, "scenario": self.inputs.design.name, "seed": self.inputs.seed,
            "sim_time": self.now, "event": event, "job_id": job_id, "sku": sku,
            "station": station, "reason": reason,
            "queue_lengths": json.dumps(dict(zip(self.stations, queues))),
            "stock_by_sku": json.dumps({
                name: {sku: len(self.stock[i][sku]) for sku in self.skus}
                for i, name in enumerate(self.stations)
            }),
            "details": json.dumps(data, ensure_ascii=False, sort_keys=True),
        })

    def _notify(self):
        if not self.signal.triggered:
            self.signal.succeed()

    def _clock(self, at, action):
        yield self.env.timeout(max(0, at - self.now))
        action()
        self._notify()

    def _target(self, sku):
        if self.inputs.design.renewal:
            if sku == self.study.skus[2] and self.now >= self.study.shock:
                return 0
            notice = self.study.shock - self.study.notice_windows * self.study.window
            if sku == self.inputs.new_sku and self.now < notice:
                return 0
        return self.settings.target

    def _allocation(self, sku):
        return self.settings.allocation[self.study.skus.index(sku) if sku in self.study.skus else 2]

    def _card_cap(self, index, sku):
        cap = self._target(sku) if index == len(self.stations) - 1 else self.settings.intermediate[index]
        return cap * self._allocation(sku)

    def _stock_target(self, sku):
        if self.kanban:
            return self._card_cap(len(self.stations) - 1, sku)
        return self._target(sku)

    def _make_piece(self, sku):
        self.piece_count += 1
        piece = Piece(self.piece_count, sku)
        return piece

    def _planned(self, sku, index):
        varied = self.inputs.design.load and self.now >= self.study.shock
        rank_key = (sku, index, varied)
        rank = self.planned_ranks[rank_key]
        self.planned_ranks[rank_key] += 1
        return self.inputs.planned_operation(sku, rank, index, self.now)

    def _deliver(self, sku):
        while self.backlog[sku] and self.stock[-1][sku]:
            order = self.backlog[sku].popleft()
            piece = self.stock[-1][sku].popleft()
            self.delivered_at[order.id] = self.now
            self._event("delivery", sku=sku, station=self.stations[-1], job_id=piece.id,
                        order_id=order.id, promised=order.due)
            if self.kanban:
                self._event("card_return", sku=sku, station=self.stations[-1], job_id=piece.id,
                            reason="finished_stock_withdrawal", free=self._free_card(len(self.stations) - 1, sku))

    def _arrive(self, order: Arrival):
        self._integrate()
        self.backlog[order.sku].append(order)
        self._event("order", sku=order.sku, order_id=order.id, promised=order.due)
        self._deliver(order.sku)
        self._notify()

    def _balance_needs(self):
        for sku in self.skus:
            desired = max(0, self._stock_target(sku) + len(self.backlog[sku])
                          - len(self.stock[-1][sku]))
            queue = self.waiting[sku]
            # A newer need still outside the plant can be withdrawn at a policy review.
            while queue and self.open[sku] > desired:
                need = queue.pop()
                need.cancelled = True
                if need.reservation:
                    calendar = self.calendars[need.drum]
                    calendar.slots.remove(need.reservation.slot)
                self.open[sku] -= 1
                self._event("need_cancel", sku=sku, need_id=need.id, reason="target_revision")
            for _ in range(desired - self.open[sku]):
                self.sequence += 1
                need = Need(self.sequence, sku, self.now, self.now + self.study.replenishment_delay)
                self.needs.append(need)
                self.open[sku] += 1
                queue.append(need)
                self._event("need", sku=sku, need_id=need.id, target=need.target)
                if not self.kanban:
                    self._build_job(need)
                if self.dbr:
                    self._reserve(need)

    def _build_job(self, need):
        if need.job is None:
            routing = tuple(Operation(station, self._planned(need.sku, i))
                            for i, station in enumerate(self.stations))
            need.job = Job(need.id, need.sku, 1, need.target, self.now, routing)
        return need.job

    def _reserve(self, need):
        job = self._build_job(need)
        index = self.drum
        need.drum = index
        reservation = self.calendars[index].reserve(
            job_id=job.id, now=self.now, target=need.target, duration=job.routing[index].time,
            upstream=self.settings.upstream, downstream=self.settings.downstream,
            nominal_upstream=sum(op.time for op in job.routing[:index]),
        )
        need.reservation = reservation
        need.urgency = self.settings.upstream / 3
        self._event("slot_reserved", sku=need.sku, station=self.stations[index], job_id=job.id,
                    reason="target_infeasible" if reservation.constrained else "target_feasible",
                    start=reservation.slot.start, end=reservation.slot.end,
                    planned_return=reservation.planned_return, target=need.target,
                    release=reservation.release)
        self.env.process(self._clock(reservation.release, lambda: self._release(need)))

    def _release(self, need):
        if need.cancelled:
            return
        self._integrate()
        job = self._build_job(need)
        self.waiting[need.sku].remove(need)
        job.released_at = self.now
        self.active[job.id] = need
        piece = self._make_piece(need.sku)
        self.in_transit[job.id] = piece
        self.weight_used += need.weight
        self.queues[0].append(job)
        self._event("release", sku=need.sku, station=self.stations[0], job_id=job.id,
                    need_id=need.id, piece_id=piece.id, wip=len(self.active),
                    weight=self.weight_used, cap=self.settings.cap_minutes if self.weighted else self.settings.cap)
        self._notify()

    def _conwip_release(self):
        while any(self.waiting.values()):
            need = min((queue[0] for queue in self.waiting.values() if queue), key=lambda v: v.id)
            if self.weighted:
                job = self._build_job(need)
                weight = job.routing[self.weight_station].time
                if weight > self.settings.cap_minutes:
                    raise ValueError("weighted CONWIP cap is below a single planned load")
                if self.weight_used + weight > self.settings.cap_minutes + 1e-9:
                    break
                need.weight = weight
            elif len(self.active) >= self.settings.cap:
                break
            self._release(need)

    def _priority(self, job, index):
        need = self.active[job.id]
        if need.drum is None or index > need.drum:
            return (3, job.id, job.id)
        start = need.reservation.slot.start
        if index == need.drum:
            return (0, start, job.id)
        remaining = sum(op.time for op in job.routing[index:need.drum])
        if start - self.now - remaining <= need.urgency:
            return (1, start, job.id)
        return (3, job.id, job.id)

    def _push_task(self, index):
        queue = self.queues[index]
        if not queue:
            return None
        fifo = self.rule.select(queue, self.stations[index])
        job = fifo
        if self.dbr and self.policy != "dbr_fifo":
            job = min(queue, key=lambda j: self._priority(j, index))
            if job is not fifo:
                need = self.active[job.id]
                self._event("priority_change", sku=job.product, station=self.stations[index],
                            job_id=job.id, reason="slot_threatened", displaced=fifo.id,
                            slot=need.reservation.slot.start)
        queue.remove(job)
        need = self.active[job.id]
        if self.dbr and index < need.drum and self._priority(job, index)[0] == 1:
            self._event("slot_at_risk", sku=job.product, station=self.stations[index],
                        job_id=job.id, reason="slot_threatened", slot=need.reservation.slot.start)
        if index == need.drum:
            slot = need.reservation.slot
            if self.now > slot.start + 1e-9:
                self._event("slot_late", sku=job.product, station=self.stations[index],
                            job_id=job.id, reason="slot_threatened", slot=slot.start)
            elif self.now < slot.start - 1e-9:
                self._event("slot_early", sku=job.product, station=self.stations[index],
                            job_id=job.id, reason="drum_ready", slot=slot.start)
        return Task(self.in_transit[job.id], index, job.current_operation().time, need)

    def _free_card(self, index, sku):
        if self.shared:
            cap = ((self.settings.target if index == len(self.stations) - 1
                    else self.settings.intermediate[index]) * sum(self.settings.allocation))
            stock = sum(map(len, self.stock[index].values()))
            return cap - stock - int(self.busy[index] is not None)
        task = self.busy[index]
        cap = self._card_cap(index, sku)
        if index == len(self.stations) - 1 and self._target(sku) == 0 and self.backlog[sku]:
            cap = self.settings.target * self._allocation(sku)
        return cap - len(self.stock[index][sku]) - int(task is not None and task.piece.sku == sku)

    def _intermediate_active(self, sku):
        return self._target(sku) > 0 or bool(self.backlog[sku])

    def _local_needs(self, index):
        for sku, queue in self.vacancy[index].items():
            target = self._card_cap(index, sku) if self._intermediate_active(sku) else 0
            busy = self.busy[index]
            vacancy = target - len(self.stock[index][sku]) - int(
                busy is not None and busy.piece.sku == sku)
            vacancy = max(0, vacancy)
            while len(queue) > vacancy:
                queue.pop()
            for _ in range(vacancy - len(queue)):
                self.sequence += 1
                queue.append(self.sequence)

    def _kanban_candidates(self, index, pull):
        last = index == len(self.stations) - 1
        if last:
            return sorted((queue[0].id, sku) for sku, queue in self.waiting.items() if queue)
        loop = self.vacancy[index]
        if not self.shared:
            return sorted((queue[0], sku) for sku, queue in loop.items() if queue)
        return ([(priority, sku) for sku, priority in sorted(pull.items(), key=lambda entry: entry[1])]
                + sorted((queue[0], sku) for sku, queue in loop.items() if queue and sku not in pull))

    def _shared_card_available(self, index, sku):
        free = self._free_card(index, sku)
        # Keep a path open for each other active SKU with no physical piece in this loop.
        # Extra pieces may borrow cards when those SKUs already hold a piece.
        task = self.busy[index]
        protected = self.skus
        if self.inputs.design.renewal and (
            self.now < self.study.shock or self.backlog[self.study.skus[2]]
        ):
            protected = self.study.skus
        missing = sum(other != sku and self._intermediate_active(other)
                      and not self.stock[index][other]
                      and (task is None or task.piece.sku != other)
                      for other in protected)
        return free > missing

    def _upstream_requests(self, index, candidates):
        if not index:
            return {}
        return {sku: priority for priority, sku in candidates
                if self._free_card(index, sku) > 0 and not self.stock[index - 1][sku]}

    def _kanban_task(self, index, pull):
        last = index == len(self.stations) - 1
        candidates = self._kanban_candidates(index, pull)
        upstream_pull = {}
        reason = "no_demand"
        selected = None
        for priority, sku in candidates:
            allowed = (self._shared_card_available(index, sku) if self.shared and not last
                       else self._free_card(index, sku) > 0)
            if not allowed:
                if reason == "no_demand":
                    reason = "no_local_card"
                continue
            if index and not self.stock[index - 1][sku]:
                upstream_pull[sku] = priority
                reason = "no_upstream_piece"
                continue
            selected = (sku, priority)
            break
        if selected is None:
            return None, upstream_pull, reason
        sku, priority = selected
        need = self.waiting[sku].popleft() if last else None
        if not last and self.vacancy[index][sku]:
            self.vacancy[index][sku].popleft()
        piece = self.stock[index - 1][sku].popleft() if index else self._make_piece(sku)
        if index:
            self._event("card_return", sku=sku, station=self.stations[index - 1], job_id=piece.id,
                        reason="intermediate_withdrawal", free=self._free_card(index - 1, sku))
        self._event("card_take", sku=sku, station=self.stations[index], job_id=piece.id,
                    need_id=priority, free=self._free_card(index, sku) - 1)
        return Task(piece, index, self._planned(sku, index), need), upstream_pull, reason

    def _quarantine(self):
        if not self.inputs.design.renewal or self.now < self.study.shock:
            return
        old = self.study.skus[2]
        if self.backlog[old] or self.open[old] or any(task and task.piece.sku == old for task in self.busy):
            return
        for index, stock in enumerate(self.stock):
            while stock[old]:
                piece = stock[old].popleft()
                self.obsolete.append(piece)
                self._event("obsolete", sku=old, station=self.stations[index], job_id=piece.id)

    def _dispatch(self):
        self._integrate()
        self._balance_needs()
        if not self.dbr and not self.kanban:
            self._conwip_release()
        self._quarantine()
        self._record_peak()
        pull = {}
        for index in reversed(range(len(self.stations))):
            if self.kanban and index < len(self.vacancy):
                self._local_needs(index)
            if self.busy[index] is not None:
                pull = (self._upstream_requests(index, self._kanban_candidates(index, pull))
                        if self.shared else {})
                continue
            if self.kanban:
                task, pull, reason = self._kanban_task(index, pull)
            else:
                task = self._push_task(index)
                reason = self._push_idle_reason(index)
            if task is not None:
                self.busy[index] = task
                self.env.process(self._process(task))
                reason = None
                pull = (self._upstream_requests(index, self._kanban_candidates(index, pull))
                        if self.shared else {})
            if reason != self.reasons[index]:
                self.reasons[index] = reason
                if reason:
                    self._event("idle", station=self.stations[index], reason=reason)
        if self.replay:
            self._event("state", backlog_by_sku={sku: len(queue) for sku, queue in self.backlog.items()},
                        machines={station: {"piece_id": task.piece.id if task else None,
                                             "sku": task.piece.sku if task else None,
                                             "idle_reason": self.reasons[index]}
                                  for index, (station, task) in enumerate(zip(self.stations, self.busy))},
                        launch_queue=sum(map(len, self.waiting.values())))

    def _push_idle_reason(self, index):
        if index and (any(need.job.next_op < index for need in self.active.values())
                      or any(self.waiting.values())):
            return "no_upstream_piece"
        if any(self.waiting.values()):
            return "release_planned_later" if self.dbr else "conwip_limit"
        return "no_demand"

    def _process(self, task):
        index, sku = task.index, task.piece.sku
        varied = self.inputs.design.error and self.now >= self.study.shock
        key = (sku, index, varied)
        rank = self.actual_ranks[key]
        self.actual_ranks[key] += 1
        actual = self.inputs.actual(sku, rank, index, task.planned, self.now)
        need = task.need
        job_id = task.piece.id if self.kanban else need.id
        self._event("start", sku=sku, station=self.stations[index], job_id=job_id,
                    piece_id=task.piece.id, planned=task.planned, actual=actual)
        yield self.env.timeout(actual)
        self._integrate()
        self.busy[index] = None
        self._event("finish", sku=sku, station=self.stations[index], job_id=job_id,
                    piece_id=task.piece.id)
        last = index == len(self.stations) - 1
        if self.kanban or last:
            self.stock[index][sku].append(task.piece)
            self._event("stock_in", sku=sku, station=self.stations[index], job_id=job_id,
                        piece_id=task.piece.id)
        if last:
            need.returned = self.now
            self.open[sku] -= 1
            if not self.kanban:
                self.active.pop(need.id)
                self.in_transit.pop(need.id)
                self.weight_used = max(0.0, self.weight_used - need.weight)
            self._event("replenished", sku=sku, station=self.stations[index], job_id=job_id,
                        need_id=need.id, target=need.target, piece_id=task.piece.id)
            if not self.kanban and not self.dbr:
                self._event("conwip_return", sku=sku, station=self.stations[index], job_id=job_id,
                            wip=len(self.active), weight=self.weight_used)
            self._deliver(sku)
        elif not self.kanban:
            need.job.advance()
            self.queues[index + 1].append(need.job)
        self._notify()

    def _review(self):
        self._integrate()
        self.settings = self.revised
        self.drum = self.stations.index(self.settings.drum)
        self._event("settings_review", settings=vars(self.settings))

    def _drum_review(self):
        end = self.now
        start = max(0, end - self.study.drum_window)
        counts = Counter(order.sku for order in self.inputs.arrivals if start <= order.at < end)
        loads = [sum(count * self.nominals[sku][index] for sku, count in counts.items()) / (end - start)
                 for index in range(len(self.stations))]
        candidate = max(range(len(loads)), key=loads.__getitem__)
        if candidate != self.drum and loads[candidate] - loads[self.drum] >= self.study.drum_gap:
            previous = self.drum
            self.drum = candidate
            self._event("drum_change", station=self.stations[candidate],
                        previous=self.stations[previous], observed_loads=loads)

    def _record_peak(self):
        index = int(self.now / self.study.window)
        if index < len(self.areas):
            backlog = sum(map(len, self.backlog.values()))
            self.peaks[index] = max(self.peaks[index], backlog)

    def _queued_load(self, index):
        if self.kanban:
            if index == len(self.stations) - 1:
                waiting = self.waiting
            else:
                waiting = self.vacancy[index]
            return sum((min(len(queue), len(self.stock[index - 1][sku])) if index else len(queue))
                       * self.nominals[sku][index] for sku, queue in waiting.items())
        return sum(job.routing[index].time for job in self.queues[index])

    def _integrate(self):
        stop = min(self.now, self.study.stop)
        if stop <= self.last:
            return
        current = self.last
        self.last = stop
        wip = sum(task is not None for task in self.busy) if self.kanban else len(self.active)
        stock = [sum(map(len, level.values())) for level in self.stock]
        backlog = sum(map(len, self.backlog.values()))
        values = {"wip": wip, "intermediate": sum(stock[:-1]), "finished": stock[-1],
                  "obsolete": len(self.obsolete), "backlog": backlog,
                  "stock_total": wip + sum(stock) + len(self.obsolete)}
        for index, station in enumerate(self.stations):
            reason = self.reasons[index] or "no_demand"
            if self.busy[index] is not None:
                values[f"busy_{station}"] = 1
            else:
                values[f"{reason}_{station}"] = 1
            if index in (1, 2):
                values[f"queue_work_{station}"] = self._queued_load(index)
        while current < stop:
            index = min(len(self.areas) - 1, int(current / self.study.window))
            # Assign exact window boundaries to the next window despite floating-point division.
            if current >= (index + 1) * self.study.window:
                index += 1
            end = min(stop, (index + 1) * self.study.window)
            for key, value in values.items():
                self.areas[index][key] += value * (end - current)
            self.peaks[index] = max(self.peaks[index], backlog)
            current = end

    def _run_events(self):
        self.nominals = {sku: self.inputs.nominal(sku) for sku in self.skus}
        for order in self.inputs.arrivals:
            self.env.process(self._clock(order.at, lambda order=order: self._arrive(order)))
        self.env.process(self._clock(self.study.shock, lambda: self._event("shock")))
        if self.inputs.design.renewal:
            notice = self.study.shock - self.study.notice_windows * self.study.window
            self.env.process(self._clock(notice, lambda: self._event("sku_notice", sku=self.inputs.new_sku)))
        if self.revised is not None:
            self.env.process(self._clock(self.study.review, self._review))
        if self.policy == "dbr_adaptive":
            at = self.study.drum_period
            while at <= self.study.stop + self.study.followup:
                self.env.process(self._clock(at, self._drum_review))
                at += self.study.drum_period
        self.env.process(self._control())
        self.env.run(until=nextafter(self.study.stop + self.study.followup, inf))
        self._integrate()
        self._event("end")

    def _control(self):
        while True:
            # Coalesce arrivals and operation completions at the same timestamp before dispatch.
            yield self.env.timeout(0)
            self.signal = self.env.event()
            self._dispatch()
            yield self.signal

    def run(self):
        self._run_events()
        assert self.piece_count == len(self.delivered_at) + len(self.obsolete) + sum(
            len(queue) for level in self.stock for queue in level.values()
        ) + (sum(task is not None for task in self.busy) if self.kanban else len(self.active))
        assert len(self.inputs.arrivals) == len(self.delivered_at) + sum(map(len, self.backlog.values()))
        committed = Counter(need.sku for need in self.active.values())
        if self.kanban and self.busy[-1] is not None:
            committed[self.busy[-1].piece.sku] += 1
        assert all(self.open[sku] == len(self.waiting[sku]) + committed[sku] for sku in self.skus)
        periods = {"avant": (1, self.study.warmup_windows),
                   "observation": (self.study.warmup_windows, len(self.areas)),
                   "apres_revision": (self.study.warmup_windows + self.study.review_windows, len(self.areas))}
        kpis = {f"{period}_{key}": value for period, (start, end) in periods.items()
                for key, value in self._metrics(start, end).items()}
        baseline = max(self.peaks[1:self.study.warmup_windows])
        after = self.peaks[self.study.warmup_windows:]
        sustained = self.study.recovery_windows
        recovery = next((index for index in range(len(after) - sustained + 1)
                         if max(after[index:index + sustained]) <= baseline), None)
        kpis["recovery_minutes"] = None if recovery is None else recovery * self.study.window
        kpis["recovery_threshold"] = baseline
        orders = []
        replenishments = []
        if self.replay:
            orders = [{"order_id": order.id, "sku": order.sku, "arrival": order.at,
                       "promised": order.due, "delivered": self.delivered_at.get(order.id)}
                      for order in self.inputs.arrivals]
            replenishments = [self._replenishment_row(need) for need in self.needs]
        return Result(kpis, self.events, orders, replenishments)

    def _metrics(self, start, end):
        t0, t1 = start * self.study.window, end * self.study.window
        cohort = [order for order in self.inputs.arrivals if t0 <= order.at < t1]
        dates = [(order.due, self.delivered_at.get(order.id)) for order in cohort]
        followup = self.study.stop + self.study.followup
        delays = [max(0, (followup if delivered is None else delivered) - due)
                  for due, delivered in dates]
        totals = Counter()
        for window in self.areas[start:end]:
            totals.update(window)
        duration = t1 - t0
        metrics = {key: value / duration for key, value in totals.items()}
        for station in self.stations:
            for reason in ("busy", "no_demand", "no_upstream_piece", "no_local_card",
                           "release_planned_later", "conwip_limit"):
                key = f"{reason}_{station}"
                metrics[f"minutes_{key}"] = totals[key]
        for station in self.stations[1:3]:
            metrics[f"queue_hours_{station}"] = metrics.pop(f"queue_work_{station}", 0) / 60
        # The backlog area measures delay accumulated within the window, including open orders.
        metrics.update(
            service=sum(delivered is not None and delivered <= due + 1e-9
                        for due, delivered in dates) / len(dates),
            orders=len(dates), orders_open=sum(delivered is None for _, delivered in dates),
            lateness_p95_lower_bound=float(np.quantile(delays, 0.95)),
            delivered_per_hour=sum(t0 <= date < t1 for date in self.delivered_at.values()) * 60 / duration,
            backlog_peak=max(self.peaks[start:end]), backlog_piece_minutes=totals["backlog"],
            backlog_drift_per_hour=((self.peaks[end - 1] - self.peaks[start]) * 60
                                    / ((end - start - 1) * self.study.window)
                                    if end - start > 1 else None),
        )
        relevant = [need for need in self.needs if t0 <= need.at < t1 and not need.cancelled]
        metrics["replenishments_open"] = sum(need.returned is None for need in relevant)
        metrics["replenishment_on_target"] = (sum(need.returned is not None
            and need.returned <= need.target + 1e-9 for need in relevant) / len(relevant) if relevant else None)
        return metrics

    @staticmethod
    def _replenishment_row(need):
        reservation = need.reservation
        return {
            "need_id": need.id, "sku": need.sku, "need_at": need.at, "target": need.target,
            "slot_start": reservation.slot.start if reservation else None,
            "slot_end": reservation.slot.end if reservation else None,
            "planned_release": reservation.release if reservation else None,
            "planned_return": reservation.planned_return if reservation else None,
            "actual_return": need.returned, "cancelled": need.cancelled,
            "return_minus_target": None if need.returned is None else need.returned - need.target,
        }
