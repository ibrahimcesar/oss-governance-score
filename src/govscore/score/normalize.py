"""Normalização por limiares absolutos definidos em config/metrics.yaml."""
from __future__ import annotations


def linear(value: float | None, best: float, worst: float) -> float | None:
    """Interpola value para [0,1]. Funciona nas duas direções (best<worst ou >)."""
    if value is None:
        return None
    if best == worst:
        return 1.0 if value == best else 0.0
    t = (value - worst) / (best - worst)
    return max(0.0, min(1.0, t))


def binary(value: bool | None) -> float | None:
    if value is None:
        return None
    return 1.0 if value else 0.0
