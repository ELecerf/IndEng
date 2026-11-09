"""indeng: simulations de flux d'usine et ordonnancement bases sur la TOC (SimPy)."""

from indeng.config.loader import load_scenario, scenario_from_dict
from indeng.engine.sim import RunResult, SimEngine
from indeng.experiments.runner import run_experiment, summarize
from indeng.metrics.kpis import compute_kpis

__version__ = "0.1.0"

__all__ = [
    "RunResult",
    "SimEngine",
    "compute_kpis",
    "load_scenario",
    "run_experiment",
    "scenario_from_dict",
    "summarize",
    "__version__",
]
