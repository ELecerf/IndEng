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


def test_echelles_relatilles_somme_temps_operatoires():
    base=dict(line=dict(stationCount=3,bottleneckIndex=1,
        families={"A":dict(regularHours=2,bottleneckHours=6),"B":dict(regularHours=2,bottleneckHours=6)}),
        familyWeights=[1,1],requestedLeadWorkMultiple=[2,4],windowsWorkMultiple=[1,2],
        warmup=0,arrivalEnd=100,maxBatchWaitHours=0)
    c=resolve_line(base)
    assert c["workContentHours"]==10.0
    assert c["requestedLead"]==[20.0,40.0]
    assert c["windows"]==[10.0,20.0]
    assert "requestedLeadWorkMultiple" not in c and "windowsWorkMultiple" not in c
    assert resolve_line(c)==c
    base2=dict(base)
    base2.pop("windowsWorkMultiple")
    base2["windowsLeadFraction"]=[0.5,1.0]
    c2=resolve_line(base2)
    assert c2["windows"]==[15.0,30.0]


def test_delai_client_lognormal_moyenne_preservee():
    import statistics
    from demand import orders
    c=resolve_line(dict(line=dict(stationCount=1,bottleneckIndex=0,
        families={"A":dict(regularHours=1,bottleneckHours=1)}),
        familyWeights=[1],requestedLead=[50],requestedLeadDistribution="lognormal",requestedLeadCV=1.0,
        processingDistribution="lognormal",processingCV=0.3,
        warmup=0,arrivalEnd=200000,maxBatchWaitHours=0))
    leads=[j[1]-j[0] for j in orders(c,0.01,7)]
    assert len(leads)>500
    assert abs(statistics.mean(leads)-50)/50 < 0.1
    assert statistics.median(leads) < 40


def test_compteurs_ruptures_et_changements():
    c=resolve_line(dict(line=dict(stationCount=2,bottleneckIndex=1,
        families={"A":dict(regularHours=1,bottleneckHours=5),"B":dict(regularHours=1,bottleneckHours=5)}),
        warmup=0,arrivalEnd=300,maxBatchWaitHours=0,requestedLead=[100,100]))
    jobs=[(0,100,"A",c["processingHours"]["A"]),(0,200,"B",c["processingHours"]["B"])]
    court=simulate(c,jobs,36,[float("inf")],1,1,[(0,300)])
    long=simulate(c,jobs,200,[float("inf")],1,1,[(0,300)])
    assert court[0]["ruptures"]>long[0]["ruptures"]
    assert court[0]["ruptures_carnet"]>=1
    assert long[0]["ruptures_carnet"]==0
    assert court[0]["changements"]>=1 and long[0]["changements"]>=1


def test_compteur_opportunites_et_file():
    c=resolve_line(dict(line=dict(stationCount=2,bottleneckIndex=1,
        families={"A":dict(regularHours=1,bottleneckHours=5)}),
        warmup=0,arrivalEnd=300,maxBatchWaitHours=0,requestedLead=[100,100]))
    jobs=[(0,150,"A",c["processingHours"]["A"]) for _ in range(4)]
    trace=defaultdict(list)
    res=simulate(c,jobs,200,[float("inf")],1,1,[(0,300)],trace)
    assert any(n>=1 for _,_,n in trace["opportunites2"])
    assert res[0]["file"]>0
