"""Scorecard CLI (validação secundária): agregado por risco e análise
sobre fixtures sintéticas — sem rede, sem data/."""
import json
import math

from govscore.validate.scorecard_cli import (
    aggregate,
    analyze,
    check_scores,
    load_results,
    report,
)


def test_aggregate_pondera_por_risco_e_ignora_inconclusivos():
    scores = check_scores({"checks": [
        {"name": "Dangerous-Workflow", "score": 10},   # Critical, peso 10
        {"name": "License", "score": 0},               # Low, peso 2.5
        {"name": "Fuzzing", "score": -1},              # inconclusivo: fora
    ]})
    assert "Fuzzing" not in scores
    assert math.isclose(aggregate(scores), (10 * 10 + 2.5 * 0) / 12.5)
    assert math.isclose(aggregate(scores, {"License"}), 0.0)
    assert aggregate({}) is None


def _payload(score, checks):
    return {"score": score, "checks": [{"name": n, "score": s}
                                       for n, s in checks.items()]}


def test_load_e_analyze_em_fixture(tmp_path):
    repos = ["o/a", "o/b", "o/c"]
    cli = {"o/a": {"License": 10, "Maintained": 10, "CI-Tests": 10},
           "o/b": {"License": 10, "Maintained": 5, "CI-Tests": 0},
           "o/c": {"License": 0, "Maintained": 0, "CI-Tests": 0}}
    api = {"o/a": {"License": 10, "Maintained": 10},
           "o/b": {"License": 10, "Maintained": 5}}
    for r in repos:
        d = tmp_path / r.replace("/", "__")
        d.mkdir()
        agg = aggregate(cli[r])
        (d / "v2_scorecard_cli.json").write_text(json.dumps(
            {"repo": r, "elapsed_s": 10, "data": _payload(agg, cli[r])}))
        if r in api:
            (d / "openssf_scorecard.json").write_text(json.dumps(
                {"data": _payload(aggregate(api[r]), api[r])}))
    rows = load_results(tmp_path, repos)
    assert [r["cli"] is not None for r in rows] == [True, True, True]
    assert rows[2]["api"] is None
    records = [{"repo": "o/a", "score": 90, "archetype": "toy"},
               {"repo": "o/b", "score": 60, "archetype": "toy"},
               {"repo": "o/c", "score": 10, "archetype": "toy"}]
    res = analyze(rows, records)
    assert res["n_cli"] == 3 and res["n_api"] == 2 and res["n_failed"] == 0
    assert res["repro_max_abs_diff"] < 1e-9        # agregado reproduzido
    assert math.isclose(res["rho_score_cli_all"], 1.0)
    assert res["por_arquetipo"]["toy"]["n"] == 3
    md = report(res)
    assert "validação secundária" in md and "| toy | 3 |" in md
