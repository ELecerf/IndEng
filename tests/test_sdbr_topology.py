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


def test_train_logistique_par_enoirs_sans_famille():
    c=resolve_line(dict(line=dict(stationCount=2,bottleneckIndex=1,
        families={"A":dict(regularHours=1,bottleneckHours=5),"B":dict(regularHours=1,bottleneckHours=5)}),
        warmup=0,arrivalEnd=100,maxBatchWaitHours=0))
    jobs=[(0,50,f,c["processingHours"][f]) for f in "ABABAB"]
    trace=defaultdict(list)
    simulate(c,jobs,100,[float("inf")],1,3,[(0,100)],trace)
    assert list(trace["shipped"].values())==[18,18,18,33,33,33]
    trace2=defaultdict(list)
    simulate(c,jobs,100,[float("inf")],1,1,[(0,100)],trace2)
    assert list(trace2["shipped"].values())==[6,11,16,21,26,31]


def test_train_vidange_optionnelle_sauf_fin():
    base=dict(line=dict(stationCount=2,bottleneckIndex=1,
        families={"A":dict(regularHours=1,bottleneckHours=5),"B":dict(regularHours=1,bottleneckHours=5)}),
        warmup=0,arrivalEnd=100,maxBatchWaitHours=0)
    jobs=[(t,t+50,f,[1,5]) for t,f in [(0,"A"),(30,"B"),(60,"A")]]
    strict=defaultdict(list)
    simulate(resolve_line(base),jobs,100,[float("inf")],2,2,[(0,100)],strict)
    assert list(strict["shipped"].values())==[41,41,66]
    vidange=defaultdict(list)
    simulate(resolve_line(base|{"trainVidange":True}),jobs,100,[float("inf")],2,2,[(0,100)],vidange)
    assert list(vidange["shipped"].values())==[6,36,66]
