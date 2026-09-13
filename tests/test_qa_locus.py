"""Testes do instrumento de locus de coordenação (qa.locus) com cache
sintético em tmp_path — nada lê data/ nem a rede."""
import json
import math

from govscore.qa.locus import (
    CONTEXT_SIGNALS,
    PLATFORM_TRAILERS,
    SHARE_KEYS,
    TRAILER_PATTERNS,
    commit_trailer_shares,
    is_external_locus,
    iter_cached_commits,
    locus_table,
    report,
    scan_commit_messages,
)


def _commit(message, author_email="a@x.org", committer_email=None,
            author_login="a"):
    """Objeto de commit REST mínimo (author/committer de topo podem ser nulos
    quando o e-mail não está vinculado a uma conta)."""
    committer_email = committer_email or author_email
    return {
        "sha": "0" * 40,
        "commit": {"message": message,
                   "author": {"name": "A", "email": author_email,
                              "date": "2026-07-01T00:00:00Z"},
                   "committer": {"name": "C", "email": committer_email,
                                 "date": "2026-07-01T00:00:00Z"}},
        "author": {"login": author_login} if author_login else None,
        "committer": None,
    }


def _write_cache(root, repo, pages, meta=None):
    d = root / repo.replace("/", "__")
    d.mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(pages, 1):
        (d / f"commits_12m_p{i:02d}.json").write_text(json.dumps(
            {"path": f"/repos/{repo}/commits", "params": {"page": i},
             "fetched_at": "2026-07-20T11:38:34Z", "data": page}))
    if meta is not None:
        (d / "repo_metadata.json").write_text(json.dumps(
            {"path": f"/repos/{repo}", "params": None,
             "fetched_at": "2026-07-23T20:15:00Z", "data": meta}))
    return d


GERRIT = ("fix: thing\n\nChange-Id: I0123456789abcdef\n"
          "Reviewed-on: https://go-review.googlesource.com/c/go/+/1\n")
DCO = "doc: typo\n\nSigned-off-by: Someone <s@x.org>\n"


def test_particao_das_shares_discriminativas_e_contexto():
    # discriminativas ∪ contexto = todos os trailers + committer≠autor, sem
    # sobreposição — CONTEXT_SIGNALS é a parte não pontuada pela regra
    assert set(PLATFORM_TRAILERS).isdisjoint(CONTEXT_SIGNALS)
    assert set(SHARE_KEYS) == set(TRAILER_PATTERNS) | {"committer_neq_author"}
    assert SHARE_KEYS == PLATFORM_TRAILERS + CONTEXT_SIGNALS
    assert tuple(commit_trailer_shares([]))[:-1] == SHARE_KEYS   # + n_commits


def test_commit_trailer_shares_caso_conhecido():
    commits = [_commit(GERRIT), _commit(GERRIT),
               _commit(DCO, committer_email="noreply@github.com"),
               _commit("plain message")]
    s = commit_trailer_shares(commits)
    assert s["n_commits"] == 4
    assert math.isclose(s["reviewed_on"], 0.5)
    assert math.isclose(s["change_id"], 0.5)
    assert math.isclose(s["signed_off_by"], 0.25)
    assert math.isclose(s["committer_neq_author"], 0.25)
    assert s["differential_revision"] == 0 and s["piper_origin"] == 0
    assert s["lore_link"] == 0


def test_trailers_ancorados_ao_inicio_de_linha():
    # menção no corpo do texto não conta; trailer na 1ª linha conta
    inline = _commit("see Reviewed-on: elsewhere in prose")
    first = _commit("PiperOrigin-RevId: 123\n")
    lore = _commit("net: fix\n\nLink: https://lore.kernel.org/r/abc\n")
    s = commit_trailer_shares([inline, first, lore])
    assert s["reviewed_on"] == 0
    assert math.isclose(s["piper_origin"], 1 / 3)
    assert math.isclose(s["lore_link"], 1 / 3)


def test_shares_none_sem_commits():
    s = commit_trailer_shares([])
    assert s["n_commits"] == 0 and s["reviewed_on"] is None
    assert s["committer_neq_author"] is None


def test_is_external_locus_regra_pre_registrada():
    assert is_external_locus({"mirror_declared": True, "reviewed_on": 0.0})
    assert is_external_locus({"mirror_declared": False, "reviewed_on": 0.5})
    assert is_external_locus({"differential_revision": 0.9})
    assert not is_external_locus({"piper_origin": 0.49})
    # Signed-off-by e committer≠autor NÃO discriminam (DCO; merges via web)
    assert not is_external_locus({"signed_off_by": 1.0,
                                  "committer_neq_author": 1.0,
                                  "change_id": 1.0, "lore_link": 1.0})
    assert not is_external_locus({"reviewed_on": None, "mirror_declared": None})


def test_scan_concatena_paginas_ignora_404_e_le_metadata(tmp_path):
    repo = "o/gerrit"
    _write_cache(tmp_path, repo,
                 pages=[[_commit(GERRIT), _commit(GERRIT), _commit("x")],
                        [_commit(GERRIT, author_login=None)],
                        None],  # página cacheada com data nulo
                 meta={"description": "Read-only mirror of upstream",
                       "has_issues": False, "mirror_url": None})
    row = scan_commit_messages(tmp_path, repo)
    assert len(iter_cached_commits(tmp_path, repo)) == 4
    assert row["n_commits"] == 4
    assert math.isclose(row["reviewed_on"], 0.75)
    assert row["has_issues"] is False
    assert row["mirror_declared"] is True
    # só as chaves do contrato: a sinalização é is_external_locus(row)
    assert set(row) == {"repo", "n_commits", "has_issues", "mirror_declared",
                        *SHARE_KEYS}
    assert is_external_locus(row) is True


def test_scan_sem_espelho_e_sem_metadata(tmp_path):
    repo = "o/plain"
    _write_cache(tmp_path, repo, pages=[[_commit(DCO), _commit("y")]],
                 meta={"description": "A normal project", "has_issues": True})
    row = scan_commit_messages(tmp_path, repo)
    assert row["mirror_declared"] is False and not is_external_locus(row)
    assert row["has_issues"] is True
    # repositório sem nada em cache: linha vazia, não erro
    empty = scan_commit_messages(tmp_path, "o/missing")
    assert empty["n_commits"] == 0 and empty["has_issues"] is None
    assert not is_external_locus(empty)


def test_locus_table_aceita_nomes_e_entradas_da_amostra(tmp_path):
    _write_cache(tmp_path, "o/a", pages=[[_commit("x")]], meta={})
    _write_cache(tmp_path, "o/b", pages=[[_commit(GERRIT)]],
                 meta={"description": "publish-only"})
    rows = locus_table(tmp_path, ["o/a", {"repo": "o/b",
                                           "archetype": "federation"}])
    assert [r["repo"] for r in rows] == ["o/a", "o/b"]
    assert "archetype" not in rows[0] and rows[1]["archetype"] == "federation"
    assert [is_external_locus(r) for r in rows] == [False, True]


def test_report_lista_sinalizados_e_confere_conjunto_pre_registrado(tmp_path):
    _write_cache(tmp_path, "golang/go", pages=[[_commit(GERRIT)]], meta={})
    _write_cache(tmp_path, "o/plain", pages=[[_commit("x")]], meta={})
    _write_cache(tmp_path, "o/surprise", pages=[[_commit(
        "x\n\nDifferential Revision: D123\n")]], meta={})
    rows = locus_table(tmp_path, ["golang/go", "o/plain", "o/surprise"])
    md = report(rows)
    assert md.startswith("# Evidência de locus de coordenação")
    assert "| `golang/go` |" in md and "**sim**" in md
    # sinalizados antes dos demais; o não sinalizado fecha em "não"
    table = [ln for ln in md.splitlines() if ln.startswith("| `")]
    assert [ln.split("|")[1].strip() for ln in table] == [
        "`golang/go`", "`o/surprise`", "`o/plain`"]
    assert table[-1].endswith("| não |")
    assert "## Repositórios sinalizados (2)" in md
    assert "- `golang/go` — Reviewed-on (Gerrit) em 100% dos commits" in md
    # sinalizado fora do conjunto é reportado, não incorporado ao cenário
    assert "Sinalizados fora do conjunto: `o/surprise`" in md
    assert "Nenhum score é alterado" in md
