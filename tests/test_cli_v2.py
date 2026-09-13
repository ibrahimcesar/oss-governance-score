"""Integração dos subcomandos do catálogo v2 (epoch/rescore/compare/locus)
sobre fixtures sintéticas — sem rede, sem tocar em data/."""
import json
from pathlib import Path

import yaml

from govscore import cli


def test_parser_aceita_subcomandos_v2(tmp_path):
    ap = cli.build_parser()
    a = ap.parse_args(["epoch", "--only", "o/r", "--workdir", str(tmp_path)])
    assert a.cmd == "epoch" and a.only == ["o/r"] and a.workdir == tmp_path
    a = ap.parse_args(["rescore", "--v1", "x.json", "--data-dir", "d",
                       "--results-dir", "r", "--remeasured-at", "2026-09-13"])
    assert a.cmd == "rescore" and a.remeasured_at == "2026-09-13"
    a = ap.parse_args(["compare", "--v1-dir", "a", "--v2-dir", "b"])
    assert a.cmd == "compare"
    a = ap.parse_args(["locus-evidence"])
    assert a.cmd == "locus-evidence"


def _v1_record(repo, arch, issue_template=False):
    return {
        "repo": repo, "archetype": arch, "language": "python", "stars": 10,
        "forks": 2, "backend": "api+git", "extracted_at": "2026-07-24",
        "artifacts": {"readme": True, "contributing": True,
                      "code_of_conduct": False, "license": True,
                      "issue_template": issue_template,
                      "pull_request_template": False, "codeowners": False,
                      "governance": False, "funding": False,
                      "health_percentage": 100},
        "security": {"security_policy": False, "ci_configured": True,
                     "dependency_automation": False, "releases_12m": 3,
                     "release_notes_share": 1.0},
        "distribution": {"top1_share": 0.5, "hhi": 0.3, "truck_factor": 2,
                         "contributors_5plus": 4, "commit_entropy": 0.5,
                         "elephant_factor": 1, "contributor_retention": 0.3},
        "responsiveness": {"median_first_response_hours": 10.0,
                           "median_pr_merge_hours": 100.0,
                           "pr_merge_ratio": 0.5, "pr_review_coverage": 0.5,
                           "n_issues_sampled": 10, "n_prs_sampled": 10,
                           "n_first_responses": 5},
        "subscores": {}, "score": None,
    }


def _write_v2_cache(cache_root: Path, repo: str, paths: list[str],
                    epoch_status="ok"):
    d = cache_root / repo.replace("/", "__") / "v2"
    d.mkdir(parents=True)
    sha = "a" * 40
    (d / "epoch_commit.json").write_text(json.dumps({
        "repo": repo, "sha": sha, "committer_ts": 1, "cutoff": "2026-07-24T00:00:00Z",
        "cutoff_source": "probes", "resolver_step": "since60", "status": "ok",
        "epoch_status": epoch_status, "verification": {},
        "fetched_at": "2026-09-13T00:00:00Z", "catalog_version": "v2"}))
    (d / f"tree_paths_{sha[:12]}.json").write_text(json.dumps({
        "sha": sha, "entries": [{"mode": "100644", "sha": "b" * 40, "path": p}
                                for p in paths]}))
    (d / "org_epoch_commit.json").write_text(json.dumps({"status": "absent"}))


def test_rescore_e_compare_ponta_a_ponta(tmp_path, monkeypatch):
    cache = tmp_path / "raw"
    v1 = [_v1_record("o/a", "toy"), _v1_record("o/b", "toy", issue_template=True)]
    # o/a: template em diretório (defeito v1) → passa a True; o/b: inalterado
    _write_v2_cache(cache, "o/a", ["README.md", "CONTRIBUTING.md", "LICENSE",
                                   ".github/ISSUE_TEMPLATE/bug.yml",
                                   ".github/workflows/ci.yml"])
    _write_v2_cache(cache, "o/b", ["README.md", "CONTRIBUTING.md", "LICENSE",
                                   ".github/ISSUE_TEMPLATE.md",
                                   ".github/workflows/ci.yml"])
    cfg = cli.load_config()
    from govscore.score.scoring import compute_score, compute_subscores
    for r in v1:
        r["subscores"] = compute_subscores(r, cfg)
        r["score"] = compute_score(r["subscores"], cfg["weights"])
    v1_dir = tmp_path / "v1"
    v1_dir.mkdir()
    (v1_dir / "full_metrics.json").write_text(json.dumps({"results": v1, "errors": []}))
    sample = tmp_path / "sample.yaml"
    sample.write_text(yaml.safe_dump({"full": [{"repo": "o/a", "archetype": "toy"},
                                               {"repo": "o/b", "archetype": "toy"}]}))
    monkeypatch.setattr(cli, "_code_version", lambda: "test")

    out = cli.cmd_rescore(v1_dir / "full_metrics.json", tmp_path / "v2",
                          tmp_path / "res", remeasured_at="2026-09-13",
                          cache_root=cache)
    assert out["n"] == 2 and out["epoch_status"] == {"ok": 2}
    v2 = json.loads((tmp_path / "v2" / "full_metrics.json").read_text())["results"]
    a = next(r for r in v2 if r["repo"] == "o/a")
    assert a["artifacts"]["issue_template"] is True
    assert a["v1_artifacts"]["issue_template"] is False
    assert a["catalog_version"] == "v2" and a["score"] > v1[0]["score"]
    assert a["distribution"] == v1[0]["distribution"]  # verbatim
    assert "Declarações de QA (v2)" in (tmp_path / "res" / "qa_extracao.md").read_text()

    res = cli.cmd_compare(v1_dir, tmp_path / "v2", tmp_path / "res", sample,
                          cache_root=cache)
    md = (tmp_path / "res" / "reparo_v1_v2.md").read_text()
    assert "Reparo v1→v2" in md and "issue_template" in md
    assert res["n_common"] == 2
