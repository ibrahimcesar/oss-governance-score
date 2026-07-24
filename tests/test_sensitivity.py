"""Testes da análise de sensibilidade (item 6) com casos conhecidos."""
import math

from govscore.score.sensitivity import (
    _ranks,
    analyze,
    equal_weights,
    kendalls_w,
    lodo_weights,
    perturbed_weights,
    scores_for,
    spearman,
)

BASE = {"artifacts": 0.25, "distribution": 0.25, "responsiveness": 0.20,
        "diversity": 0.15, "security": 0.15}


def test_variantes_de_pesos_somam_um():
    assert math.isclose(sum(equal_weights().values()), 1.0)
    for dim in BASE:
        assert math.isclose(sum(perturbed_weights(BASE, dim, 1.25).values()), 1.0)
        assert math.isclose(sum(perturbed_weights(BASE, dim, 0.75).values()), 1.0)
        w = lodo_weights(BASE, dim)
        assert dim not in w and math.isclose(sum(w.values()), 1.0)


def test_perturbacao_preserva_proporcao_dos_demais():
    w = perturbed_weights(BASE, "artifacts", 1.25)
    # razão entre os pesos não perturbados é preservada
    assert math.isclose(w["distribution"] / w["security"],
                        BASE["distribution"] / BASE["security"])
    assert w["artifacts"] > BASE["artifacts"]


def test_spearman_casos_conhecidos():
    assert math.isclose(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
    assert math.isclose(spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1.0)
    # exclusão par a par de None
    assert math.isclose(spearman([1, None, 2, 3, 4], [5, 9, 6, 7, 8]), 1.0)
    assert spearman([1, 2], [2, 1]) is None  # n < 3


def test_ranks_com_empates():
    assert _ranks([10.0, 20.0, 20.0, 30.0]) == [1.0, 2.5, 2.5, 4.0]


def test_kendalls_w_extremos():
    identicos = [[1.0, 2.0, 3.0, 4.0]] * 3
    assert math.isclose(kendalls_w(identicos), 1.0)
    # rankings que se cancelam (soma de ranks igual para todos) → W = 0
    opostos = [[1.0, 2.0, 3.0], [3.0, 2.0, 1.0]]
    assert math.isclose(kendalls_w(opostos), 0.0)
    assert kendalls_w([[1.0, 2.0]]) is None  # m < 2
    assert kendalls_w([[5.0], [5.0]]) is None  # n < 2 (denominador zero)
    assert kendalls_w([]) is None


def test_scores_for_renormaliza_faltantes_como_o_score_oficial():
    subs = [{"artifacts": 1.0, "distribution": None, "responsiveness": None,
             "diversity": None, "security": None}]
    assert scores_for(subs, BASE) == [100.0]


def test_report_tolera_none_nas_estatisticas():
    from govscore.score.sensitivity import report
    subs = [{d: 0.5 for d in BASE}, {d: 0.6 for d in BASE}]  # n=2 → ρ None
    res = analyze(subs, BASE)
    texto = report(res)  # não pode lançar TypeError
    assert "—" in texto


def test_analyze_dataset_sintetico_estavel():
    # 10 repos com sub-scores correlacionados: ranking robusto a variações
    subs = [{d: (i + 1) / 10 for d in BASE} for i in range(10)]
    res = analyze(subs, BASE)
    assert math.isclose(res["equal_vs_base"], 1.0)
    assert math.isclose(res["perturbation_min"], 1.0)
    assert math.isclose(res["kendalls_w"], 1.0)
    assert all(math.isclose(v, 1.0) for v in res["lodo"].values())
