"""Testes da re-pontuação v2 (reparo de D1/D5 na época do snapshot):
substituição APENAS dos 12 binários, preservação verbatim do resto do
registro v1, herança recalculada, inacessíveis/não verificados e leitura do
cache v2. A detecção (`extract.patterns.detect`, módulo de padrões) é
substituída por um stub — estes testes não dependem das regras v2.
"""
import copy
import json

import yaml

from govscore import rescore
from govscore.rescore import (
    D1_ITEMS,
    D5_ITEMS,
    load_v2_cache,
    rescore_all,
    rescore_record,
)
from govscore.score.scoring import compute_score, compute_subscores

CFG = yaml.safe_load(open("config/metrics.yaml"))
SHA = "a" * 40
ORG_SHA = "b" * 40

EPOCH_OK = {
    "repo": "a/b", "branch": "main", "sha": SHA, "committer_ts": 1_753_300_000,
    "cutoff": "2026-07-23T20:15:00Z", "cutoff_source": "probe_max_fetched_at",
    "resolver_step": "shallow_since_60d", "status": "ok",
    "verification": {"codeowners": {"path": ".github/CODEOWNERS",
                                    "v1_sha": "c" * 40, "epoch_sha": "c" * 40,
                                    "ok": True}},
    "epoch_status": "ok", "fetched_at": "2026-09-13T12:00:00Z",
    "catalog_version": "v2",
}

# Caminho canônico (minúsculas) que o stub reconhece para cada item.
CANON = {
    "readme": "readme.md", "contributing": "contributing.md",
    "code_of_conduct": "code_of_conduct.md", "license": "license",
    "issue_template": ".github/issue_template/bug.yml",
    "pull_request_template": ".github/pull_request_template.md",
    "codeowners": "codeowners", "governance": "governance.md",
    "funding": ".github/funding.yml", "security_policy": "security.md",
    "ci_configured": ".github/workflows/ci.yml",
    "dependency_automation": ".github/dependabot.yml",
}
INHERITABLE = ("contributing", "code_of_conduct", "issue_template",
               "pull_request_template", "funding", "security_policy")


def _stub_detect(paths, org_paths=None):
    """Stub de `patterns.detect` com a MESMA interface do contrato:
    (artifacts, security, meta); herança só quando o repo não tem o arquivo."""
    paths = {p.lower() for p in paths}
    org = {p.lower() for p in (org_paths or [])}
    art, sec, matched, inherited = {}, {}, {}, []
    for item, canon in CANON.items():
        target = art if item in D1_ITEMS else sec
        if canon in paths:
            target[item] = True
            matched[item] = [canon]
        elif item in INHERITABLE and canon in org:
            target[item] = True
            target[f"{item}_inherited"] = True
            matched[item] = [f"{{owner}}/.github:{canon}"]
            inherited.append(item)
        else:
            target[item] = False
    yaml_only = (any(p.startswith(".github/issue_template/")
                     and p.endswith(".yaml") for p in paths)
                 and not art["issue_template"])
    meta = {"matched": matched,
            "flags": {"issue_template_yaml_only": yaml_only,
                      "issue_template_config_only": False,
                      "funding_yaml": False, "dependabot_yaml": False},
            "ci_systems": ["github_actions"] if sec["ci_configured"] else [],
            "dependency_tools": (["dependabot"]
                                 if sec["dependency_automation"] else []),
            "inherited_from_org": inherited}
    return art, sec, meta


def _v1(repo="a/b", arch="club", artifacts=None, security=None, **top):
    """Registro v1 completo (formato de data/processed/full_metrics.json)."""
    m = {
        "repo": repo, "stars": 100, "forks": 5,
        "artifacts": {"readme": True, "contributing": False,
                      "code_of_conduct": False, "license": True,
                      "issue_template": False, "pull_request_template": False,
                      "codeowners": False, "governance": False,
                      "funding": False, "health_percentage": 100},
        "security": {"security_policy": False, "ci_configured": True,
                     "dependency_automation": False, "releases_12m": 4,
                     "release_notes_share": 0.75},
        "distribution": {"top1_share": 0.4, "top2_share": 0.6, "hhi": 0.2,
                         "truck_factor": 2, "contributors_5plus": 5,
                         "commit_entropy": 0.6, "n_contributors_listed": 10,
                         "n_commits_window": 200, "elephant_factor": 2,
                         "contributor_retention": 0.5},
        "responsiveness": {"median_first_response_hours": 24.0,
                           "pr_review_coverage": 0.8,
                           "median_issue_close_hours": 100.0,
                           "median_pr_merge_hours": 48.0,
                           "pr_merge_ratio": 0.7, "n_issues_sampled": 30,
                           "n_prs_sampled": 30, "n_first_responses": 10},
        "backend": "api+git", "window": "12 months ago",
        "archetype": arch, "language": "python", "extracted_at": "2026-07-24",
    }
    m["artifacts"].update(artifacts or {})
    m["security"].update(security or {})
    m.update(top)
    m["subscores"] = compute_subscores(m, CFG)
    m["score"] = compute_score(m["subscores"], CFG["weights"])
    return m


BASE_TREE = ["README.md", "LICENSE", ".github/workflows/ci.yml"]


# ------------------------------------------------------------ rescore_record
def test_troca_issue_template_recalcula_d1_e_score(monkeypatch):
    monkeypatch.setattr(rescore, "_detect", _stub_detect)
    v1 = _v1()
    # caso nodejs/node: formulário em .github/ISSUE_TEMPLATE/ invisível ao
    # perfil comunitário v1, presente na árvore de época
    tree = BASE_TREE + [".github/ISSUE_TEMPLATE/bug.yml"]   # caixa original
    v2 = rescore_record(v1, EPOCH_OK, tree, None, CFG, "2026-09-13")

    assert v1["artifacts"]["issue_template"] is False
    assert v2["artifacts"]["issue_template"] is True
    assert v2["v1_artifacts"]["issue_template"] is False
    assert v2["subscores"]["artifacts"] == 3 / 9          # readme, license, tpl
    assert v1["subscores"]["artifacts"] == 2 / 9
    assert v2["score"] == compute_score(v2["subscores"], CFG["weights"])
    assert v2["score"] > v1["score"]
    # D5: só ci_configured True (como em v1) → sub-score idêntico
    assert v2["subscores"]["security"] == v1["subscores"]["security"]

    assert v2["catalog_version"] == "v2"
    assert v2["epoch_sha"] == SHA
    assert v2["epoch_cutoff"] == "2026-07-23T20:15:00Z"
    assert v2["epoch_cutoff_source"] == "probe_max_fetched_at"
    assert v2["epoch_resolver_step"] == "shallow_since_60d"
    assert v2["epoch_status"] == "ok"
    assert v2["epoch_unverified_probes"] == []
    assert v2["remeasured_at"] == "2026-09-13"
    assert v2["v2_source"] == "tree"
    assert v2["v2_meta"]["matched"]["issue_template"] == [
        ".github/issue_template/bug.yml"]
    assert v2["v2_meta"]["ci_systems"] == ["github_actions"]


def test_preserva_verbatim_d2_d3_d4_releases_e_nao_muta_v1(monkeypatch):
    monkeypatch.setattr(rescore, "_detect", _stub_detect)
    v1 = _v1()
    snapshot = copy.deepcopy(v1)
    v2 = rescore_record(v1, EPOCH_OK, BASE_TREE + [".github/dependabot.yml"],
                        None, CFG, "2026-09-13")

    assert v1 == snapshot                       # entrada intacta (deep copy)
    for k in ("distribution", "responsiveness", "stars", "forks", "backend",
              "window", "extracted_at", "archetype", "language", "repo"):
        assert v2[k] == snapshot[k], k
    assert v2["artifacts"]["health_percentage"] == 100
    assert v2["security"]["releases_12m"] == 4
    assert v2["security"]["release_notes_share"] == 0.75
    assert set(v2["artifacts"]) == set(D1_ITEMS) | {"health_percentage"}
    assert set(v2["security"]) == set(D5_ITEMS) | {"releases_12m",
                                                   "release_notes_share"}
    assert v2["v1_artifacts"] == snapshot["artifacts"]
    assert v2["v1_security"] == snapshot["security"]
    # cópias independentes: mutar v2 não alcança v1
    v2["distribution"]["hhi"] = 0.99
    v2["v1_artifacts"]["readme"] = False
    assert v1 == snapshot


def test_heranca_recalculada_descarta_anotacao_v1(monkeypatch):
    monkeypatch.setattr(rescore, "_detect", _stub_detect)
    # v1 marcou funding e security_policy como herdados; na árvore de época o
    # repo tem FUNDING.yml PRÓPRIO, e a org fornece SECURITY.md e CONTRIBUTING
    v1 = _v1(artifacts={"funding": True, "funding_inherited": True},
             security={"security_policy": True,
                       "security_policy_inherited": True})
    tree = BASE_TREE + [".github/FUNDING.yml"]
    org = ["SECURITY.md", "CONTRIBUTING.md", "CODEOWNERS"]
    v2 = rescore_record(v1, EPOCH_OK, tree, org, CFG, "2026-09-13")

    assert v2["artifacts"]["funding"] is True
    assert "funding_inherited" not in v2["artifacts"]     # agora é próprio
    assert v2["artifacts"]["contributing"] is True
    assert v2["artifacts"]["contributing_inherited"] is True
    assert v2["artifacts"]["codeowners"] is False          # nunca herda
    assert v2["security"]["security_policy"] is True
    assert v2["security"]["security_policy_inherited"] is True
    assert v2["v2_meta"]["inherited_from_org"] == ["contributing",
                                                   "security_policy"]
    assert v2["v1_artifacts"]["funding_inherited"] is True  # histórico mantido
    assert v2["subscores"]["artifacts"] == 4 / 9


def test_inacessivel_ou_nao_verificado_mantem_v1(monkeypatch):
    monkeypatch.setattr(rescore, "_detect", _stub_detect)
    v1 = _v1(artifacts={"funding": True, "funding_inherited": True})
    tree = BASE_TREE + [".github/ISSUE_TEMPLATE/bug.yml", "SECURITY.md"]

    for epoch in ({"epoch_status": "unreachable", "sha": None,
                   "cutoff": None, "resolver_step": "clone_failed"}, None):
        v2 = rescore_record(v1, epoch, tree, None, CFG, "2026-09-13")
        assert v2["artifacts"] == v1["artifacts"]   # inclusive *_inherited v1
        assert v2["security"] == v1["security"]
        assert v2["v2_source"] == "v1_cache"
        assert v2["epoch_status"] == "unreachable"
        assert v2["epoch_sha"] is None
        assert v2["score"] == v1["score"]
        assert v2["subscores"] == v1["subscores"]
        assert v2["catalog_version"] == "v2"
        assert v2["v2_meta"]["matched"] == {}

    unverified = dict(EPOCH_OK, epoch_status="unverified",
                      verification={"security_md": {"ok": False},
                                    "codeowners": {"ok": True}})
    v2 = rescore_record(v1, unverified, tree, None, CFG, "2026-09-13")
    assert v2["artifacts"]["issue_template"] is False   # v1 mantido
    assert v2["v2_source"] == "v1_cache"
    assert v2["epoch_status"] == "unverified"
    assert v2["epoch_sha"] == SHA
    assert v2["epoch_unverified_probes"] == ["security_md"]

    # época ok mas árvore ausente no cache ⇒ inacessível, com nota
    v2 = rescore_record(v1, EPOCH_OK, None, None, CFG, "2026-09-13")
    assert v2["epoch_status"] == "unreachable"
    assert v2["v2_source"] == "v1_cache"
    assert "tree_paths" in v2["epoch_note"]


# ------------------------------------------------------------- cache v2
def _entries(paths, symlinks=()):
    return [{"mode": "120000" if p in symlinks else "100644",
             "sha": "d" * 40, "path": p} for p in paths]


def _write_cache(root, repo, tree, org=None, org_absent=False, epoch=None,
                 profile_updated_at=None):
    d = root / repo.replace("/", "__") / "v2"
    d.mkdir(parents=True)
    ep = dict(epoch or EPOCH_OK, repo=repo)
    (d / "epoch_commit.json").write_text(json.dumps(ep))
    if tree is not None:
        (d / f"tree_paths_{SHA[:12]}.json").write_text(json.dumps(
            {"sha": SHA, "entries": tree, "n_blobs": len(tree),
             "n_symlinks": sum(e["mode"] == "120000" for e in tree),
             "fetched_at": "2026-09-13T12:00:00Z"}))
    if org_absent:
        (d / "org_epoch_commit.json").write_text(json.dumps({"status": "absent"}))
    elif org is not None:
        (d / "org_epoch_commit.json").write_text(json.dumps(
            {"sha": ORG_SHA, "status": "ok", "epoch_status": "ok"}))
        (d / f"org_tree_paths_{ORG_SHA[:12]}.json").write_text(json.dumps(
            {"sha": ORG_SHA, "entries": org}))
    if profile_updated_at:
        (d.parent / "community_profile.json").write_text(json.dumps(
            {"path": "/x", "fetched_at": "2026-07-23T20:15:00Z",
             "data": {"health_percentage": 100,
                      "updated_at": profile_updated_at}}))


def test_load_v2_cache_formatos(tmp_path):
    _write_cache(tmp_path, "x/one", _entries(["README.md", "LICENSE"],
                                             symlinks={"LICENSE"}),
                 org=_entries(["CONTRIBUTING.md"]))
    c = load_v2_cache(tmp_path, "x/one")
    assert c["epoch"]["sha"] == SHA
    assert c["tree_paths"] == ["README.md", "LICENSE"]   # caixa original
    assert c["symlink_paths"] == {"license"}
    assert c["org_paths"] == ["CONTRIBUTING.md"]

    _write_cache(tmp_path, "x/two", None, org_absent=True)  # árvore ausente
    c = load_v2_cache(tmp_path, "x/two")
    assert c["epoch"] is not None and c["tree_paths"] is None
    assert c["org_paths"] is None

    c = load_v2_cache(tmp_path, "x/none")                  # sem cache v2
    assert c == {"epoch": None, "tree_paths": None, "org_paths": None,
                 "symlink_paths": set()}


def test_rescore_all_le_cache_e_trata_ausencias(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rescore, "_detect", _stub_detect)
    _write_cache(tmp_path, "x/one",
                 _entries(["README.md", "LICENSE", ".github/workflows/ci.yml",
                           ".github/ISSUE_TEMPLATE/bug.yml"],
                          symlinks={"README.md"}),
                 org_absent=True, profile_updated_at="2025-01-01T00:00:00Z")
    _write_cache(tmp_path, "x/two", _entries(["README.md"]),
                 org=_entries(["CONTRIBUTING.md", "docs/SECURITY.md"]))
    _write_cache(tmp_path, "x/four", None)      # época ok, árvore ausente
    v1 = [_v1("x/one", "toy"), _v1("x/two", "club"),
          _v1("x/three", "stadium"), _v1("x/four", "federation")]

    out = rescore_all(v1, tmp_path, CFG, "2026-09-13")
    assert [r["repo"] for r in out] == ["x/one", "x/two", "x/three", "x/four"]
    one, two, three, four = out

    assert one["v2_source"] == "tree"
    assert one["artifacts"]["issue_template"] is True
    assert one["v2_meta"]["symlink_hits"] == ["readme.md"]
    assert one["v2_meta"]["profile_updated_at"] == "2025-01-01T00:00:00Z"
    assert "contributing_inherited" not in one["artifacts"]   # org ausente

    assert two["artifacts"]["contributing_inherited"] is True
    assert two["artifacts"]["license"] is False                # não está na árvore
    assert two["security"]["ci_configured"] is False
    assert two["v2_meta"]["symlink_hits"] == []
    assert two["v2_meta"]["profile_updated_at"] is None

    assert three["v2_source"] == "v1_cache"
    assert three["epoch_status"] == "unreachable"
    assert three["epoch_resolver_step"] == "cache_missing"
    assert three["artifacts"] == v1[2]["artifacts"]
    assert three["score"] == v1[2]["score"]
    assert "x/three" in capsys.readouterr().err

    assert four["epoch_status"] == "unreachable"
    assert four["epoch_sha"] == SHA
    assert four["v2_source"] == "v1_cache"
    assert all(r["catalog_version"] == "v2" for r in out)
    assert all(r["remeasured_at"] == "2026-09-13" for r in out)
