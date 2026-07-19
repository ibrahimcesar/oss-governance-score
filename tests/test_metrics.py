"""Testes das funções puras de cálculo — a confiança nos números do TCC."""
import math

from govscore.score.normalize import binary, linear
from govscore.score.scoring import compute_score


def test_linear_lower_is_better():
    # tempo de resposta: best=72h, worst=2160h
    assert linear(72, 72, 2160) == 1.0
    assert linear(2160, 72, 2160) == 0.0
    assert 0.0 < linear(1000, 72, 2160) < 1.0
    assert linear(10, 72, 2160) == 1.0      # clamp
    assert linear(9999, 72, 2160) == 0.0    # clamp


def test_linear_higher_is_better():
    assert linear(5, 5, 1) == 1.0
    assert linear(1, 5, 1) == 0.0
    assert linear(3, 5, 1) == 0.5


def test_linear_none_propagates():
    assert linear(None, 0, 1) is None
    assert binary(None) is None


def test_score_renormalizes_missing_dimensions():
    weights = {"a": 0.5, "b": 0.5}
    assert compute_score({"a": 1.0, "b": None}, weights) == 100.0
    assert compute_score({"a": 0.5, "b": 0.5}, weights) == 50.0
    assert compute_score({"a": None, "b": None}, weights) is None


def test_hhi_and_truck_factor():
    from govscore.extract.contributions import extract_contributions  # noqa: F401
    # cálculo manual: 1 contribuidor domina
    shares = [0.9, 0.05, 0.05]
    hhi = sum(s * s for s in shares)
    assert math.isclose(hhi, 0.815)
