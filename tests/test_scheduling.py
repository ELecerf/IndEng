import pytest

from indeng.domain.models import Job, Operation
from indeng.scheduling.rules import make_rule

ROUTING = (Operation("s1", 2.0),)


def job(seq, qty, due):
    return Job(seq=seq, product="P", qty=qty, due=due, released_at=0.0, routing=ROUTING)


def test_fifo_picks_oldest():
    jobs = [job(2, 1, 100), job(0, 5, 1), job(1, 1, 50)]
    assert make_rule("fifo").select(jobs, "s1").seq == 0


def test_spt_picks_shortest_processing():
    jobs = [job(0, 5, 100), job(1, 1, 1)]
    assert make_rule("spt").select(jobs, "s1").seq == 1


def test_edd_picks_earliest_due():
    jobs = [job(0, 1, 100), job(1, 1, 10)]
    assert make_rule("edd").select(jobs, "s1").seq == 1


def test_dbr_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        make_rule("dbr").select([job(0, 1, 1)], "s1")
