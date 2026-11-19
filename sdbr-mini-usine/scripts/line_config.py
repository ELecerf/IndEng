"""Construction d'une ligne homogène hors goulot, indices commençant à zéro."""
from math import isfinite


def resolve_line(config):
    if "line" not in config:
        return config
    line = config["line"]
    count = line["stationCount"]
    position = line["bottleneckIndex"]
    if (type(count) is not int or count < 1 or type(position) is not int
            or not 0 <= position < count):
        raise ValueError("line exige stationCount >= 1 et bottleneckIndex entre 0 et stationCount-1")
    families = line["families"]
    if not families:
        raise ValueError("line.families doit contenir au moins une famille")
    processing = {}
    for name, times in families.items():
        normal, bottleneck = times["regularHours"], times["bottleneckHours"]
        if not all(isfinite(v) and v > 0 for v in (normal,bottleneck)) or bottleneck < normal:
            raise ValueError("Les durées doivent être positives, avec bottleneckHours >= regularHours")
        processing[name] = [bottleneck if p == position else normal for p in range(count)]
    regular_setup = line.get("regularSetupHours",0)
    bottleneck_setup = line.get("bottleneckSetupHours",regular_setup)
    if not all(isfinite(v) and v >= 0 for v in (regular_setup,bottleneck_setup)):
        raise ValueError("Les temps de réglage doivent être positifs ou nuls")
    capacity = line.get("bufferCapacity")
    if capacity is not None and (type(capacity) is not int or capacity < 1):
        raise ValueError("bufferCapacity doit être null ou un entier positif")
    return config | dict(stations=[f"poste_{p+1}" for p in range(count)],bottleneck=position,
                         processingHours=processing,
                         setupHours=[bottleneck_setup if p==position else regular_setup for p in range(count)],
                         capacity=[capacity]*(count-1))
