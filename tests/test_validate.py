"""Testes da validação externa (item 7): Holm–Bonferroni, Spearman com
exclusão par a par, parsing do deps.dev e relatório tolerante a None."""
import math

from govscore.validate.correlation import (
    holm_bonferroni,
    report,
    spearman_with_p,
    validate_correlations,
)
from govscore.validate.external import (
    default_version,
    package_candidates,
    version_matches_repo,
)


def test_holm_bonferroni_caso_classico():
    # m=4: p ordenados 0.01, 0.02, 0.03, 0.04
    adj = holm_bonferroni({"a": 0.01, "b": 0.02, "c": 0.03, "d": 0.04})
    assert math.isclose(adj["a"], 0.04)   # 4 × 0.01
    assert math.isclose(adj["b"], 0.06)   # 3 × 0.02
    assert math.isclose(adj["c"], 0.06)   # 2×0.03=0.06 (monotônico)
    assert math.isclose(adj["d"], 0.06)   # 1×0.04=0.04 → sobe para 0.06


def test_holm_bonferroni_trunca_em_um():
    adj = holm_bonferroni({"a": 0.9, "b": 0.95})
    assert adj["a"] == 1.0 and adj["b"] == 1.0


def test_spearman_with_p_exclusao_par_a_par():
    rho, p, n = spearman_with_p([1, 2, None, 3, 4], [2, 4, 9, 6, 8])
    assert math.isclose(rho, 1.0) and n == 4
    # n < 4: teste não realizado, mas o nº de pares É reportado
    assert spearman_with_p([1, 2, 3], [3, 2, 1]) == (None, None, 3)


def test_spearman_constante_nao_vira_significativo():
    # entrada constante → NaN do scipy → teste não realizado (jamais p_adj=0)
    rho, p, n = spearman_with_p([1, 2, 3, 4, 5], [7, 7, 7, 7, 7])
    assert rho is None and p is None and n == 5
    rows = [{"repo": f"r{i}", "archetype": "toy", "score": float(i),
             "constante": 7.0} for i in range(10)]
    res = validate_correlations(rows, ["constante"])
    assert res["global"]["constante"]["rho"] is None
    assert "significant" not in res["global"]["constante"]


def test_holm_rejeita_nan():
    import pytest
    with pytest.raises(ValueError):
        holm_bonferroni({"a": 0.01, "b": float("nan")})


def test_versions_to_probe_uma_por_major():
    from govscore.validate.external import versions_to_probe
    pkg = {"versions": [
        {"versionKey": {"version": "18.3.1"}},
        {"versionKey": {"version": "18.2.0"}},
        {"versionKey": {"version": "19.2.8"}, "isDefault": True},
        {"versionKey": {"version": "19.1.0"}},
        {"versionKey": {"version": "17.0.2"}},
        {"versionKey": {"version": "20.0.0-rc1"}},  # major só com pré-release
    ]}
    probe = versions_to_probe(pkg)
    # caso react: o major anterior (18.x) TEM que ser sondado
    assert "18.3.1" in probe and "19.2.8" in probe and "17.0.2" in probe
    assert "20.0.0-rc1" in probe   # pré-release entra só sem estável no major
    assert "18.2.0" not in probe   # uma versão por major
    assert versions_to_probe(None) == []


def test_package_candidates_por_linguagem():
    assert package_candidates("expressjs/express", "JavaScript") == [
        ("NPM", "express"), ("NPM", "@expressjs/express")]
    assert package_candidates("astropy/astropy", "Python") == [
        ("PYPI", "astropy")]
    assert package_candidates("FFmpeg/FFmpeg", "C") == []   # sem ecossistema
    assert package_candidates("uber-go/zap", "Go") == []    # sem :dependents


def test_default_version_prefere_is_default():
    pkg = {"versions": [
        {"versionKey": {"version": "1.0.0"}},
        {"versionKey": {"version": "2.0.0"}, "isDefault": True},
        {"versionKey": {"version": "3.0.0-rc1"}},
    ]}
    assert default_version(pkg) == "2.0.0"
    assert default_version({"versions": [{"versionKey": {"version": "9"}}]}) == "9"
    assert default_version(None) is None


def test_version_matches_repo_exige_projeto_relacionado():
    detail = {"relatedProjects": [
        {"projectKey": {"id": "github.com/OutroDono/rename"}}]}
    # pacote homônimo de OUTRO projeto não conta (falso positivo evitado)
    assert not version_matches_repo(detail, "morshedalam/rename")
    assert version_matches_repo(detail, "outrodono/rename".replace(
        "outrodono", "OutroDono"))
    assert not version_matches_repo(None, "a/b")


def test_validate_correlations_e_report_toleram_none():
    rows = [{"repo": f"r{i}", "archetype": "toy", "score": float(i),
             "stars": float(i * 2), "dependents": None} for i in range(10)]
    res = validate_correlations(rows, ["stars", "dependents"])
    assert math.isclose(res["global"]["stars"]["rho"], 1.0)
    assert res["global"]["stars"]["significant"] is True
    assert res["global"]["dependents"]["rho"] is None  # tudo None → sem teste
    texto = report(res)
    assert "stars" in texto and "—" in texto


def test_familia_corrigida_so_com_testes_realizados():
    # dependents sem dados não entra na família (m=1, não m=2)
    rows = [{"repo": f"r{i}", "archetype": "club", "score": float(i),
             "stars": float(i), "dependents": None} for i in range(20)]
    res = validate_correlations(rows, ["stars", "dependents"])
    assert "p_adj" in res["global"]["stars"]
    assert "p_adj" not in res["global"]["dependents"]


def test_familia_exclui_teste_com_n_menor_que_10():
    # n=5 → p da aproximação t não confiável: fora da família de Holm
    rows = [{"repo": f"r{i}", "archetype": "club", "score": float(i),
             "stars": float(i),
             "dependents": float(i * 3) if i < 5 else None}
            for i in range(20)]
    res = validate_correlations(rows, ["stars", "dependents"])
    dep = res["global"]["dependents"]
    assert dep["n"] == 5 and dep["rho"] is not None
    assert dep["in_family"] is False and "p_adj" not in dep
    assert res["global"]["stars"]["in_family"] is True
