from collections import defaultdict
import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"sdbr-mini-usine"/"scripts"))
from line_config import resolve_line
from run_congestion import simulate


@pytest.mark.parametrize("count,position",[(1,0),(2,0),(2,1),(5,0),(5,2),(5,4),(8,7)])
def test_route_and_bottleneck(count,position):
    c=resolve_line(dict(line=dict(stationCount=count,bottleneckIndex=position,
        families={"A":dict(regularHours=1,bottleneckHours=5)}),
        warmup=0,arrivalEnd=100,maxBatchWaitHours=0))
    trace=defaultdict(list)
    simulate(c,[(0,90,"A",c["processingHours"]["A"])],100,[float("inf")]*(count-1),1,"bloc",[(0,100)],trace)
    assert trace["shipped"][0]==count+4
    assert [e[1] for e in trace["starts"]]==list(range(count))
    assert trace["starts"][position][3]-trace["starts"][position][0]==5


def test_lot_a_taille_par_poste():
    c=resolve_line(dict(line=dict(stationCount=3,bottleneckIndex=2,
        families={"A":dict(regularHours=1,bottleneckHours=2)}),
        warmup=0,arrivalEnd=100,maxBatchWaitHours=0,dispatchRule="family_fifo"))
    jobs=[(0,90,"A",c["processingHours"]["A"]) for _ in range(4)]
    trace=defaultdict(list)
    simulate(c,jobs,100,[float("inf")]*2,[4,1,1],"unitaire",[(0,100)],trace)
    lots={p:[l for l in trace["lots"] if l[1]==p] for p in range(3)}
    assert any(l[2]>1 for l in lots[0])
    assert all(l[2]==1 for p in (1,2) for l in lots[p])
