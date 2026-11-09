from __future__ import annotations

from abc import ABC, abstractmethod

from indeng.domain.models import Job


class SchedulingRule(ABC):
    name: str

    @abstractmethod
    def select(self, queue: list[Job], station: str) -> Job:
        """Choose the next job to process at `station` among waiting `queue` jobs."""


class FIFORule(SchedulingRule):
    name = "fifo"

    def select(self, queue: list[Job], station: str) -> Job:
        return min(queue, key=lambda j: j.seq)


class SPTRule(SchedulingRule):
    name = "spt"

    def select(self, queue: list[Job], station: str) -> Job:
        return min(queue, key=lambda j: j.current_operation().time * j.qty)


class EDDRule(SchedulingRule):
    name = "edd"

    def select(self, queue: list[Job], station: str) -> Job:
        return min(queue, key=lambda j: j.due)


class DBRRule(SchedulingRule):
    name = "dbr"

    def select(self, queue: list[Job], station: str) -> Job:
        raise NotImplementedError(
            "DBR (Drum-Buffer-Rope) scheduling is scaffolded but not implemented yet"
        )


RULES = {rule.name: rule for rule in (FIFORule, SPTRule, EDDRule, DBRRule)}


def make_rule(name: str) -> SchedulingRule:
    return RULES[name]()
