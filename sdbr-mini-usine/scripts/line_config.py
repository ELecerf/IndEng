"""Construction d'une ligne homogène hors goulot, indices commençant à zéro,
et échelles relatives à la somme des temps opératoires (contenu d'usinage W)."""
from math import isfinite
from random import Random


def resolve_line(config):
    cfg = config
    if "line" in config:
        line = config["line"]
        count = line["stationCount"]
        position = line["bottleneckIndex"]
        if (type(count) is not int or count < 1 or type(position) is not int
                or not 0 <= position < count):
            raise ValueError("line exige stationCount >= 1 et bottleneckIndex entre 0 et stationCount-1")
        if "families" in line:
            families = line["families"]
        elif "familyCount" in line:
            # familyCount familles générées dans la même gamme d'heures
            # (regularHours / bottleneckHours : scalaire ou plage [min, max],
            # tirage déterministe). overCapacity calcule regularHours pour
            # viser une surcapacité non-goulot donnée (ex. 1.25 = +25 %).
            n = line["familyCount"]
            if type(n) is not int or n < 1:
                raise ValueError("line.familyCount doit être un entier >= 1")
            setup_r = line.get("regularSetupHours", 0)
            setup_b = line.get("bottleneckSetupHours", setup_r)
            bn = line.get("bottleneckHours")
            if bn is None:
                raise ValueError("line.bottleneckHours requis avec familyCount")
            if "overCapacity" in line:
                oc = line["overCapacity"]
                if not (isfinite(oc) and oc > 1):
                    raise ValueError("line.overCapacity doit être > 1")
                bn_mean = sum(bn)/2 if isinstance(bn, list) else bn
                regular = (bn_mean + setup_b)/oc - setup_r
            else:
                regular = line.get("regularHours")
                if regular is None:
                    raise ValueError("line.regularHours ou line.overCapacity requis avec familyCount")
            rng = Random(line.get("familySeed", 20261120))
            def draw(v):
                if isinstance(v, list):
                    lo, hi = v
                    if not (isfinite(lo) and isfinite(hi) and 0 < lo <= hi):
                        raise ValueError("plage d'heures invalide")
                    return rng.uniform(lo, hi)
                return v
            families = {}
            for i in range(n):
                reg = draw(regular)
                families[f"F{i+1}"] = {"regularHours": reg, "bottleneckHours": max(reg, draw(bn))}
        else:
            raise ValueError("line.families ou line.familyCount requis")
        if not families:
            raise ValueError("line.families doit contenir au moins une famille")
        processing = {}
        for name, times in families.items():
            normal, bottleneck = times["regularHours"], times["bottleneckHours"]
            if not all(isfinite(v) and v > 0 for v in (normal, bottleneck)) or bottleneck < normal:
                raise ValueError("Les durées doivent être positives, avec bottleneckHours >= regularHours")
            processing[name] = [bottleneck if p == position else normal for p in range(count)]
        regular_setup = line.get("regularSetupHours", 0)
        bottleneck_setup = line.get("bottleneckSetupHours", regular_setup)
        if not all(isfinite(v) and v >= 0 for v in (regular_setup, bottleneck_setup)):
            raise ValueError("Les temps de réglage doivent être positifs ou nuls")
        capacity = line.get("bufferCapacity")
        if capacity is not None and (type(capacity) is not int or capacity < 1):
            raise ValueError("bufferCapacity doit être null ou un entier positif")
        cfg = config | dict(stations=[f"poste_{p+1}" for p in range(count)], bottleneck=position,
                            processingHours=processing,
                            setupHours=[bottleneck_setup if p == position else regular_setup for p in range(count)],
                            capacity=[capacity]*(count-1),
                            familyWeights=config["familyWeights"] if "familyWeights" in config else [1]*len(families))
    if any(k in cfg for k in ("requestedLeadWorkMultiple", "windowsWorkMultiple", "windowsLeadFraction")):
        families = list(cfg["processingHours"])
        weights = cfg["familyWeights"]
        shares = [w/sum(weights) for w in weights]
        work = sum(s*sum(cfg["processingHours"][f]) for f, s in zip(families, shares))
        out = dict(cfg)
        if "requestedLeadWorkMultiple" in cfg:
            a, b = cfg["requestedLeadWorkMultiple"]
            if not (0 < a <= b):
                raise ValueError("requestedLeadWorkMultiple exige 0 < a <= b")
            out["requestedLead"] = [a*work, b*work]
            out.pop("requestedLeadWorkMultiple")
        if "windowsLeadFraction" in cfg:
            lead = out.get("requestedLead", cfg.get("requestedLead"))
            if not lead or min(lead) <= 0:
                raise ValueError("windowsLeadFraction exige un requestedLead positif")
            out["windows"] = sorted({round(f*sum(lead)/2, 6) for f in cfg["windowsLeadFraction"]})
            out.pop("windowsLeadFraction")
        elif "windowsWorkMultiple" in cfg:
            out["windows"] = sorted({round(w*work, 6) for w in cfg["windowsWorkMultiple"]})
            out.pop("windowsWorkMultiple")
        out["workContentHours"] = round(work, 6)
        cfg = out
    return cfg
