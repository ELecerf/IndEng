"""Finite-capacity drum reservations in simulation minutes."""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field


@dataclass(frozen=True, order=True)
class Slot:
    start: float
    end: float
    job_id: int


@dataclass(frozen=True)
class Reservation:
    slot: Slot
    release: float
    planned_return: float
    constrained: bool


@dataclass
class Calendar:
    slots: list[Slot] = field(default_factory=list)

    def reserve(self, *, job_id: int, now: float, target: float, duration: float,
                upstream: float, downstream: float, nominal_upstream: float) -> Reservation:
        # Historical reservations cannot constrain a future slot.
        self.slots = [slot for slot in self.slots if slot.end > now]
        earliest = now + max(upstream, nominal_upstream)
        latest_end = target - downstream
        end = latest_end
        for slot in reversed(self.slots):
            if slot.end <= end - duration:
                break
            if slot.start < end:
                end = slot.start
        start = end - duration
        constrained = start < earliest
        if constrained:
            start = now + nominal_upstream
            for slot in self.slots:
                if start + duration <= slot.start:
                    break
                start = max(start, slot.end)
            end = start + duration
        slot = Slot(start, end, job_id)
        self.slots.insert(bisect_left(self.slots, slot), slot)
        return Reservation(slot, max(now, start - upstream), end + downstream, constrained)
