"""Testes das declarações de QA v2 (qa.declarations) e do gancho
`qa_report(extra_sections=...)`. Fixtures sintéticas em tmp_path."""
import json
from datetime import datetime, timedelta, timezone

from govscore.qa.declarations import (
    ci_false_list,
    qa_section,
    releases_censoring,
    retention_reason,
)
from govscore.run_full import qa_report

SNAP = datetime(2026, 7, 24, 23, 59, 59, tzinfo=timezone.utc)


def _record(repo, retention=0.5, ci=True, releases_12m=3,
            extracted_at="2026-07-24"):
    return {"repo": repo, "extracted_at": extracted_at,
            "distribution": {"contributor_retention": retention},
            "security": {"ci_configured": ci, "releases_12m": releases_12m}}


def _release(days_before_snapshot, prerelease=False, published=True):
    t = SNAP - timedelta(days=days_before_snapshot)
    return {"tag_name": f"v{days_before_snapshot}", "prerelease": prerelease,
            "draft": not published,
            "published_at": t.strftime("%Y-%m-%dT%H:%M:%SZ") if published
            else None, "body": "notes"}


# ------------------------------------------------------------- retenção
def test_retention_reason_observed():
    assert retention_reason(_record("a/b", retention=0.0), {}) == "observed"


def test_retention_reason_young_vs_first_half_empty():
    young = {"created_at": "2026-05-01T00:00:00Z"}   # < 6 meses
    old = {"created_at": "2019-01-01T00:00:00Z"}
    rec = _record("a/b", retention=None, extracted_at="2026-07-24")
    assert retention_reason(rec, young) == "young_repo"
    assert retention_reason(rec, old) == "first_half_empty"
    # aceita o arquivo de cache inteiro (envelope do GitHubClient)
    wrapped = {"path": "/repos/a/b", "fetched_at": "2026-07-23T00:00:00Z",
               "data": young}
    assert retention_reason(rec, wrapped) == "young_repo"


def test_retention_reason_fronteira_meia_janela():
    rec = _record("a/b", retention=None, extracted_at="2026-07-24")
    half = datetime(2026, 7, 24, tzinfo=timezone.utc) - timedelta(days=182.5)
    on = {"created_at": half.strftime("%Y-%m-%dT%H:%M:%SZ")}
    before = {"created_at": (half - timedelta(seconds=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")}
    assert retention_reason(rec, on) == "young_repo"
    assert retention_reason(rec, before) == "first_half_empty"


def test_retention_reason_unknown_sem_metadata():
    rec = _record("a/b", retention=None)
    assert retention_reason(rec, None) == "unknown"
    assert retention_reason(rec, {}) == "unknown"
    assert retention_reason({"repo": "a/b", "distribution": {}},
                            {"created_at": "2020-01-01T00:00:00Z"}) == "unknown"


# ------------------------------------------------------------- releases
def test_releases_censoring_saturado():
    rels = [_release(d) for d in range(1, 31)]          # 30, todas na janela
    out = releases_censoring(_record("a/b", releases_12m=30), rels,
                             snapshot=SNAP)
    assert out == {"releases_fetched": 30, "in_window": 30, "saturated": True,
                   "prereleases_12m": 0, "nonmonotone": False,
                   "releases_12m_record": 30}


def test_releases_censoring_nao_saturado_quando_uma_fica_fora_da_janela():
    rels = [_release(d) for d in range(1, 30)] + [_release(400)]
    out = releases_censoring(_record("a/b"), rels, snapshot=SNAP)
    assert out["releases_fetched"] == 30 and out["in_window"] == 29
    assert out["saturated"] is False
    # menos de 30 devolvidas nunca satura
    assert releases_censoring(_record("a/b"), [_release(1)] * 5,
                              snapshot=SNAP)["saturated"] is False


def test_releases_censoring_prereleases_rascunhos_e_monotonicidade():
    rels = [_release(10, prerelease=True), _release(5),   # 5 depois de 10 → não monotônico
            _release(20, published=False), _release(400, prerelease=True)]
    out = releases_censoring(_record("a/b"), rels, snapshot=SNAP)
    assert out["in_window"] == 2                 # rascunho e fora da janela não
    assert out["prereleases_12m"] == 1           # só a prerelease na janela
    assert out["nonmonotone"] is True
    # envelope de cache aceito; lista vazia/None → tudo zero
    wrapped = {"path": "/repos/a/b/releases", "fetched_at": "x",
               "data": [_release(1), _release(2)]}
    assert releases_censoring(_record("a/b"), wrapped,
                              snapshot=SNAP)["nonmonotone"] is False
    empty = releases_censoring(_record("a/b"), {"path": "p",
                                                "fetched_at": "x",
                                                "data": None}, snapshot=SNAP)
    assert empty["releases_fetched"] == 0 and empty["saturated"] is False


# -------------------------------------------------------------------- CI
def test_ci_false_list_ordena_e_ignora_none():
    recs = [_record("z/1", ci=False), _record("a/1", ci=True),
            _record("m/1", ci=False), {"repo": "n/1", "security": {}}]
    assert ci_false_list(recs) == ["m/1", "z/1"]


# --------------------------------------------------------------- seção QA
def _cache(root, repo, meta, releases):
    d = root / repo.replace("/", "__")
    d.mkdir(parents=True)
    (d / "repo_metadata.json").write_text(json.dumps(
        {"path": f"/repos/{repo}", "fetched_at": "x", "data": meta}))
    if releases is not None:
        (d / "releases.json").write_text(json.dumps(
            {"path": f"/repos/{repo}/releases", "fetched_at": "x",
             "data": releases}))


def test_qa_section_resume_as_tres_declaracoes(tmp_path):
    _cache(tmp_path, "o/sat", {"created_at": "2015-01-01T00:00:00Z"},
           [_release(d, prerelease=(d == 3)) for d in range(1, 31)])
    _cache(tmp_path, "o/young", {"created_at": "2026-06-01T00:00:00Z"},
           [_release(1)])
    _cache(tmp_path, "o/dormant", {"created_at": "2010-01-01T00:00:00Z"}, [])
    recs = [_record("o/sat", ci=False, releases_12m=30),
            _record("o/young", retention=None),
            _record("o/dormant", retention=None, ci=False),
            _record("o/nocache", retention=None)]
    md = qa_section(recs, tmp_path, snapshot=SNAP)
    assert md.startswith("## Declarações de QA (v2)")
    assert "**Saturados** (1)" in md and "`o/sat`" in md
    assert "1 de 31 releases" in md            # 30 + 1 na janela
    assert "| young_repo" in md and "`o/young`" in md
    assert "| first_half_empty" in md and "`o/dormant`" in md
    assert "| unknown" in md and "`o/nocache`" in md
    assert "Sem `releases.json` em cache (1): `o/nocache`" in md
    assert "2 repositórios: `o/dormant`, `o/sat`" in md
    assert "nenhum altera scores" in md


def test_qa_report_anexa_secoes_extras_ao_final():
    m = {"repo": "a/b", "score": 50.0, "archetype": "toy",
         "extracted_at": "2026-07-21", "subscores": {"artifacts": 0.5},
         "artifacts": {"readme": True}, "security": {"ci_configured": True},
         "distribution": {}, "responsiveness": {"n_first_responses": 3}}
    base = qa_report([m], [], "abc1234")
    extra = qa_report([m], [], "abc1234",
                      extra_sections=["## Declarações de QA (v2)\n\nx\n",
                                      "## Outra"])
    assert base in extra                                  # nada é alterado
    assert extra.rstrip().endswith("## Outra")
    assert extra.index("## Declarações de QA (v2)") > extra.index("| toy |")
    assert qa_report([m], [], "abc1234", extra_sections=None) == base
