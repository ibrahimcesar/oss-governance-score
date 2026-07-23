"""Testes da extração completa (item 5): flatten, tolerância a falhas,
retomada (ponto de recuperação) e relatório de QA."""
import json

import yaml

from govscore.run_full import flatten_record, load_progress, qa_report, run_sample

CFG = yaml.safe_load(open("config/metrics.yaml"))


def _fake_metrics(repo: str) -> dict:
    return {
        "repo": repo, "stars": 100, "forks": 5, "backend": "api+git",
        "artifacts": {"readme": True, "contributing": False, "license": True,
                      "code_of_conduct": False, "issue_template": False,
                      "pull_request_template": False, "codeowners": False,
                      "governance": False, "funding": False,
                      "health_percentage": 50},
        "security": {"security_policy": True, "ci_configured": True,
                     "dependency_automation": False, "releases_12m": 4,
                     "release_notes_share": 1.0},
        "distribution": {"top1_share": 0.4, "hhi": 0.2, "truck_factor": 2,
                         "contributors_5plus": 5, "commit_entropy": 0.6,
                         "elephant_factor": 2, "contributor_retention": 0.5,
                         "n_contributors_listed": 10, "n_commits_window": 200},
        "responsiveness": {"median_first_response_hours": 24.0,
                           "median_pr_merge_hours": 48.0,
                           "pr_merge_ratio": 0.7, "pr_review_coverage": 0.8,
                           "median_issue_close_hours": 100.0,
                           "n_first_responses": 10},
    }


def test_flatten_record_achata_secoes_e_subscores():
    m = _fake_metrics("a/b")
    m["subscores"] = {"artifacts": 0.5, "security": None}
    flat = flatten_record(m)
    assert flat["repo"] == "a/b"
    assert flat["artifacts_readme"] is True
    assert flat["security_releases_12m"] == 4
    assert flat["distribution_elephant_factor"] == 2
    assert flat["subscore_artifacts"] == 0.5
    assert flat["subscore_security"] is None
    assert not any(isinstance(v, (dict, list)) for v in flat.values())


def test_run_sample_continua_apos_falha():
    def extract(repo):
        if repo == "x/quebrado":
            raise RuntimeError("boom")
        return _fake_metrics(repo)

    entries = [{"repo": "a/ok", "archetype": "toy"},
               {"repo": "x/quebrado", "archetype": "club"},
               {"repo": "b/ok", "archetype": "toy"}]
    results, errors = run_sample(entries, extract, CFG)
    assert [r["repo"] for r in results] == ["a/ok", "b/ok"]
    assert results[0]["score"] is not None
    assert errors == [{"repo": "x/quebrado", "archetype": "club",
                       "error": "RuntimeError: boom"}]


def test_run_sample_retoma_do_progresso(tmp_path):
    progress = tmp_path / "p.jsonl"
    calls = []

    def extract(repo):
        calls.append(repo)
        return _fake_metrics(repo)

    entries = [{"repo": "a/um", "archetype": "toy"},
               {"repo": "b/dois", "archetype": "toy"}]
    # 1ª rodada: extrai os dois e grava progresso linha a linha
    r1, _ = run_sample(entries, extract, CFG, progress_path=progress)
    assert calls == ["a/um", "b/dois"]
    assert len(progress.read_text().splitlines()) == 2
    # 2ª rodada: nada é reextraído (ponto de recuperação)
    r2, _ = run_sample(entries, extract, CFG, progress_path=progress)
    assert calls == ["a/um", "b/dois"]
    assert [r["repo"] for r in r2] == ["a/um", "b/dois"]
    assert r2[0]["score"] == r1[0]["score"]


def test_load_progress_ignora_linha_corrompida(tmp_path):
    progress = tmp_path / "p.jsonl"
    ok = json.dumps({"repo": "a/b", "score": 50})
    progress.write_text(ok + '\n{"repo": "c/d", "sc')  # escrita interrompida
    done = load_progress(progress)
    assert list(done) == ["a/b"]


def test_qa_report_estatisticas_e_falhas():
    m = _fake_metrics("a/b")
    m["subscores"] = {"artifacts": 0.5}
    m["score"] = 50.0
    m["archetype"] = "toy"
    m["extracted_at"] = "2026-07-21"
    rep = qa_report([m], [{"repo": "x/y", "archetype": "club",
                           "error": "RuntimeError: boom"}], "abc1234")
    assert "| toy | 1 | 50.0 |" in rep
    assert "`x/y`" in rep and "boom" in rep
    assert "abc1234" in rep
