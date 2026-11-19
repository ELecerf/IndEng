from math import exp, isfinite, log1p, sqrt
from random import Random
from line_config import resolve_line

def orders(cfg, load, seed, profile=None):
    cfg = resolve_line(cfg)
    distribution = cfg.get("processingDistribution", "uniform")
    cv = cfg.get("processingCV", 0.15)
    cvs = cv if isinstance(cv, list) else [cv]*len(cfg["stations"])
    if distribution not in {"uniform", "lognormal"} or len(cvs) != len(cfg["stations"]) or any(
            not isfinite(v) or v < 0 for v in cvs):
        raise ValueError("Distribution ou coefficients de variation invalides")
    sigmas = [sqrt(log1p(v*v)) for v in cvs]
    arrivals, demand, work = (Random(3 * seed + i) for i in range(3))
    families = list(cfg["processingHours"])
    weights = cfg["familyWeights"]
    bottleneck = cfg["bottleneck"]
    shares = [w / sum(weights) for w in weights]
    # Référence nominale unitaire, avec familles indépendantes.
    hours = sum(s * cfg["processingHours"][f][bottleneck] for f, s in zip(families, shares))
    hours += cfg["setupHours"][bottleneck] * (1 - sum(s*s for s in shares))
    result = []
    def arrival_times():
        t, budget = 0., arrivals.expovariate(1)
        for end, level in profile or [(cfg["arrivalEnd"], load)]:
            rate = level / hours
            while budget < (end-t)*rate:
                t += budget/rate
                yield t
                budget = arrivals.expovariate(1)
            budget -= (end-t)*rate
            t = end

    for t in arrival_times():
        family = demand.choices(families, weights)[0]
        due = t + demand.uniform(*cfg["requestedLead"])
        if distribution == "lognormal":
            # Un même quantile normal par opération pour apparier les niveaux de CV.
            durations = [h * exp(s*work.gauss(0,1)-s*s/2)
                         for h,s in zip(cfg["processingHours"][family],sigmas)]
        else:
            durations = [h * work.uniform(1-cfg["variation"], 1+cfg["variation"])
                         for h in cfg["processingHours"][family]]
        result.append((t, due, family, durations))
    return result
