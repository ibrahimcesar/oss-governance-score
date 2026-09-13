"""Testes da comparação v1×v2 (protocolo, passo 5) com fixture de 4
registros: uma troca False→True por detecção, uma herança de
`{owner}/.github`, um repositório inacessível (itens v1 mantidos) e uma
troca True→False (deve ser listada nominalmente); ρ e deslocamentos de
ranking com caso conhecido; relatório PT-BR.
"""
import json
import math

from govscore import rescore
from govscore.compare import (
    compare_records,
    describe,
    report,
    scorecard_check_rows,
)
from govscore.rescore import rescore_record
from tests.test_rescore import CFG, EPOCH_OK, _stub_detect, _v1

TREE = ["README.md", "LICENSE", ".github/workflows/ci.yml"]
SAMPLE = [{"repo": "f/alpha", "archetype": "federation"},
          {"repo": "s/beta", "archetype": "stadium"},
          {"repo": "c/gamma", "archetype": "club"},
          {"repo": "t/delta", "archetype": "toy"}]


def _fixture(monkeypatch, with_t2f=True):
    monkeypatch.setattr(rescore, "_detect", _stub_detect)
    v1 = [
        _v1("f/alpha", "federation"),                       # health 100, sem tpl
        _v1("s/beta", "stadium", artifacts={"health_percentage": 80}),
        _v1("c/gamma", "club", artifacts={"funding": True,
                                          "funding_inherited": True,
                                          "health_percentage": 60}),
        _v1("t/delta", "toy", artifacts={"codeowners": with_t2f}),
    ]
    v2 = [
        rescore_record(v1[0], EPOCH_OK, TREE + [".github/ISSUE_TEMPLATE/bug.yml"],
                       None, CFG, "2026-09-13"),                     # F→T
        rescore_record(v1[1], EPOCH_OK, TREE, ["SECURITY.md"], CFG,
                       "2026-09-13"),                                # herdado
        rescore_record(v1[2], {"epoch_status": "unreachable", "sha": None,
                               "resolver_step": "clone_failed",
                               "note": "404"}, None, None, CFG,
                       "2026-09-13"),                                # mantido
        rescore_record(v1[3], dict(EPOCH_OK, resolver_step="depth_400",
                                   until_candidate_sha="e" * 40),
                       TREE + [".github/ISSUE_TEMPLATE/form.yaml"], None,
                       CFG, "2026-09-13"),                           # T→F
    ]
    return v1, v2


def test_trocas_por_item_e_arquetipo_nas_duas_direcoes(monkeypatch):
    v1, v2 = _fixture(monkeypatch)
    res = compare_records(v1, v2, SAMPLE, None)
    assert res["n_common"] == 4 and not res["missing_in_v2"]

    it = res["items"]["issue_template"]
    assert it["false_to_true"] == ["f/alpha"] and it["true_to_false"] == []
    assert it["by_archetype"]["federation"]["false_to_true"] == ["f/alpha"]
    assert it["by_archetype"]["toy"]["false_to_true"] == []
    assert (it["v1_true"], it["v2_true"]) == (0, 1)

    co = res["items"]["codeowners"]
    assert co["true_to_false"] == ["t/delta"]
    assert co["by_archetype"]["toy"]["true_to_false"] == ["t/delta"]
    assert res["n_true_to_false"] == 1
    assert res["true_to_false_all"] == [{"repo": "t/delta", "archetype": "toy",
                                         "item": "codeowners"}]
    assert res["n_false_to_true"] == 2          # issue_template + security_policy
    assert res["items"]["security_policy"]["false_to_true"] == ["s/beta"]

    # inacessível: nada muda, mantém a anotação herdada de v1
    assert res["items"]["funding"]["false_to_true"] == []
    assert res["inherited"]["funding"] == {
        "v1": 1, "v2": 1, "v1_repos": ["c/gamma"], "v2_repos": ["c/gamma"],
        "by_archetype": {"federation": {"v1": 0, "v2": 0},
                         "stadium": {"v1": 0, "v2": 0},
                         "club": {"v1": 1, "v2": 1},
                         "toy": {"v1": 0, "v2": 0}}}
    assert res["inherited"]["security_policy"]["v2_repos"] == ["s/beta"]
    assert res["inherited"]["security_policy"]["v1"] == 0

    repos = {f["repo"]: f for f in res["repo_flips"]}
    assert set(repos) == {"f/alpha", "s/beta", "t/delta"}
    assert repos["s/beta"]["changes"] == {
        "security_policy": {"v1": False, "v2": True, "inherited_v2": True}}
    assert repos["t/delta"]["delta_score"] < 0 < repos["f/alpha"]["delta_score"]
    assert res["n_repos_changed"] == 3
    assert res["inconsistent_v1_copy"] == []
    json.dumps(res)                              # serializável para o .json


def test_epoca_flags_e_assercao(monkeypatch):
    v1, v2 = _fixture(monkeypatch)
    res = compare_records(v1, v2, SAMPLE, None)
    ep = res["epoch"]
    assert ep["status"] == {"ok": 3, "unreachable": 1}
    assert ep["resolver_step"] == {"shallow_since_60d": 2, "depth_400": 1,
                                   "clone_failed": 1}
    assert ep["v2_source"] == {"tree": 3, "v1_cache": 1}
    assert ep["unreachable"] == [{"repo": "c/gamma", "archetype": "club",
                                  "note": "404"}]
    assert ep["unverified"] == []
    assert ep["n_until_available"] == 1 and ep["until_divergent"] == ["t/delta"]
    assert ep["cutoff_min"] == ep["cutoff_max"] == "2026-07-23T20:15:00Z"
    assert res["min_rank_move"] == 5                     # padrão do protocolo

    # "no_commit_before_cutoff" (status do resolvedor M2) conta como
    # inacessível na tabela de época, com itens v1 mantidos
    v1b = v1 + [_v1("z/omega", "toy")]
    v2b = v2 + [rescore_record(v1b[4], {"status": "no_commit_before_cutoff",
                                        "sha": None, "resolver_step":
                                        "depth_6400"}, None, None, CFG,
                               "2026-09-13")]
    epb = compare_records(v1b, v2b, SAMPLE, None)["epoch"]
    assert epb["status"] == {"ok": 3, "unreachable": 1,
                             "no_commit_before_cutoff": 1}
    assert epb["v2_source"] == {"tree": 3, "v1_cache": 2}
    assert [u["repo"] for u in epb["unreachable"]] == ["c/gamma", "z/omega"]

    fl = res["flags"]
    assert fl["flags"]["issue_template_yaml_only"] == {"n": 1,
                                                       "repos": ["t/delta"]}
    assert fl["ci_systems"] == {"github_actions": 3}
    assert fl["inherited_from_org"] == {"security_policy": 1}

    # perfil 100 % ⇒ issue_template: alpha corrigido em v2, delta permanece
    assert res["assertions"]["health100_no_issue_template"] == {
        "v1": ["f/alpha", "t/delta"], "v2": ["t/delta"]}


def test_estatisticas_por_arquetipo_e_describe(monkeypatch):
    d = describe([4, 1, 3, 2])
    assert (d["n"], d["mean"], d["median"], d["min"], d["max"]) == (4, 2.5, 2.5, 1, 4)
    assert math.isclose(d["sd"], 1.2909944487)
    assert (d["q1"], d["q3"]) == (1.25, 3.75)      # método exclusivo (padrão)
    assert describe([5])["sd"] == 0.0 and describe([5])["q1"] == 5
    assert describe([None, None])["n"] == 0 and describe([])["mean"] is None

    v1, v2 = _fixture(monkeypatch)
    res = compare_records(v1, v2, SAMPLE, None)
    st = res["stats"]["subscore_artifacts"]
    assert st["federation"]["v1"]["mean"] == 2 / 9
    assert st["federation"]["v2"]["mean"] == 3 / 9
    assert st["all"]["v1"]["n"] == 4
    assert res["stats"]["score"]["club"]["v1"] == res["stats"]["score"]["club"]["v2"]
    assert res["delta_score"]["club"]["mean"] == 0.0
    assert res["delta_score"]["all"]["n"] == 4


def _rec(repo, score, arch="toy"):
    return {"repo": repo, "archetype": arch, "score": score,
            "subscores": {"artifacts": score / 100, "security": score / 100},
            "artifacts": {}, "security": {}}


def test_spearman_e_deslocamento_de_ranking_caso_conhecido():
    v1 = [_rec(f"r/{i}", s) for i, s in enumerate([90, 80, 70, 60, 50])]
    v2 = [_rec(f"r/{i}", s) for i, s in enumerate([80, 90, 70, 60, 50])]
    res = compare_records(v1, v2, [], None, min_rank_move=1)
    # troca dos dois primeiros: Σd² = 2 → ρ = 1 − 12/120 = 0,9
    assert math.isclose(res["spearman"]["score"]["rho"], 0.9)
    assert res["spearman"]["score"]["n"] == 5
    assert math.isclose(res["spearman"]["subscore_artifacts"]["rho"], 0.9)
    assert res["ranks"]["max_abs_delta"] == 1
    moved = {m["repo"]: m for m in res["ranks"]["moved"]}
    assert moved["r/0"]["rank_v1"] == 1 and moved["r/0"]["rank_v2"] == 2
    assert moved["r/1"]["delta_rank"] == -1          # subiu uma posição
    assert set(moved) == {"r/0", "r/1"}

    same = compare_records(v1, v1, [], None)          # limiar padrão (5)
    assert math.isclose(same["spearman"]["score"]["rho"], 1.0)
    assert same["ranks"]["moved"] == [] and same["ranks"]["max_abs_delta"] == 0


def test_cross_check_scorecard(monkeypatch, tmp_path):
    v1, v2 = _fixture(monkeypatch)
    ext = [{"repo": "s/beta", "scorecard_security_policy": True},
           {"repo": "t/delta", "scorecard_security_policy": False},
           {"repo": "f/alpha", "scorecard_security_policy": None}]
    res = compare_records(v1, v2, SAMPLE, ext)
    e = res["external"]["scorecard_security_policy"]
    assert e["check"] == "Security-Policy" and e["n"] == 2
    assert e["v1"] == {"agree": 1, "ours_true_ext_false": [],
                       "ours_false_ext_true": ["s/beta"]}   # falso negativo v1
    assert e["v2"] == {"agree": 2, "ours_true_ext_false": [],
                       "ours_false_ext_true": []}
    assert "scorecard_license" not in res["external"]        # sem dados
    assert compare_records(v1, v2, SAMPLE, None)["external"] is None

    # linhas a partir do cache v1 do Scorecard (score do check > 0 = presente)
    d = tmp_path / "x__one"
    d.mkdir()
    (d / "openssf_scorecard.json").write_text(json.dumps({"data": {
        "checks": [{"name": "Security-Policy", "score": 10},
                   {"name": "License", "score": 0},
                   {"name": "Dependency-Update-Tool", "score": -1}]}}))
    rows = scorecard_check_rows(tmp_path, ["x/one", "x/none"])
    assert rows[0] == {"repo": "x/one", "scorecard_security_policy": True,
                       "scorecard_license": False,
                       "scorecard_dependency_update_tool": None}
    assert rows[1] == {"repo": "x/none", "scorecard_security_policy": None,
                       "scorecard_license": None,
                       "scorecard_dependency_update_tool": None}


def _section(text, heading):
    """Primeira linha não vazia após o cabeçalho."""
    lines = text.splitlines()
    i = lines.index(heading)
    return next(l for l in lines[i + 1:] if l.strip())


def test_report_pt_br_lista_trocas_true_false(monkeypatch):
    v1, v2 = _fixture(monkeypatch)
    ext = [{"repo": "s/beta", "scorecard_security_policy": True}]
    texto = report(compare_records(v1, v2, SAMPLE, ext))
    assert texto.startswith("# Reparo v1→v2 (catálogo v2)")
    assert "## 3. Trocas True→False" in texto
    assert "| `t/delta` | toy | codeowners |" in texto
    assert "| issue_template | D1 | 0 | 1 | 1 | 0 | 0 |" in texto
    assert "| security_policy | 0 | 1 | `s/beta` |" in texto     # herdados
    assert "`c/gamma` — 404" in texto                             # inacessível
    assert "issue_template_yaml_only | 1 | `t/delta`" in texto
    assert "Security-Policy | security_policy | 1 |" in texto
    assert "violada em v1 por 2 repositórios" in texto
    assert "em v2 por 1 (`t/delta`)" in texto

    # sem troca True→False: a seção declara "nenhuma"
    v1b, v2b = _fixture(monkeypatch, with_t2f=False)
    texto_b = report(compare_records(v1b, v2b, SAMPLE, None))
    assert _section(texto_b, "## 3. Trocas True→False") == "nenhuma"
    assert "não fornecidos" in texto_b
