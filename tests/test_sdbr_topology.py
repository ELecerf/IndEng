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
