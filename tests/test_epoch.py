"""Testes da resolução de época do catálogo v2 (extract/epoch.py).

Fixtures 100 % locais: repositórios git criados em tmp_path com datas de
committer controladas e clonados via file:// (sem rede). O caso central é a
regra do registro de decisão 2026-09-13: o commit de época é o primeiro da
cadeia FIRST-PARENT com data ≤ corte — um commit de branch lateral, mais
novo e também ≤ corte, NÃO pode ser escolhido.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from govscore.extract import epoch
from govscore.extract.epoch import (
    EpochResult,
    GitError,
    TreeEntry,
    _parse_ls_tree,
    _run_git,
    ensure_epoch_artifacts,
    list_tree,
    resolve_epoch,
    resolve_org,
    select_first_parent,
    v1_default_branch,
    v1_probe_cutoff,
    verify_against_v1,
)

DAY = 86400
T0 = 1_700_000_000  # 2023-11-14T22:13:20Z

# Isola as fixtures da configuração global do usuário (gpgsign, hooks…).
FIXTURE_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@x",
    "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@x",
    "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C",
}


def git(*args: str, cwd: Path, ts: int | None = None) -> str:
    env = dict(os.environ, **FIXTURE_ENV)
    if ts is not None:
        env["GIT_COMMITTER_DATE"] = f"{ts} +0000"
        env["GIT_AUTHOR_DATE"] = f"{ts} +0000"
    r = subprocess.run(["git", "-c", "gc.auto=0", *args], cwd=cwd,
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, f"git {' '.join(args)}: {r.stderr}"
    return r.stdout


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git("init", "-q", "-b", "main", cwd=path)
    # clone parcial (--filter) exige permissão do lado servidor
    git("config", "uploadpack.allowFilter", "true", cwd=path)
    return path


def commit(repo: Path, ts: int, msg: str, files: dict[str, str] | None = None) -> str:
    for rel, content in (files or {f"{msg}.txt": msg}).items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    git("add", "-A", cwd=repo)
    git("commit", "-q", "--allow-empty", "-m", msg, cwd=repo, ts=ts)
    return git("rev-parse", "HEAD", cwd=repo).strip()


def dt(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


@pytest.fixture(scope="module")
def filter_support(tmp_path_factory) -> None:
    """Pula o módulo com mensagem clara se o git local não clona com --filter."""
    base = tmp_path_factory.mktemp("probe")
    src = init_repo(base / "src.git")
    commit(src, T0, "c0")
    env = dict(os.environ, **FIXTURE_ENV)
    r = subprocess.run(["git", "clone", "--quiet", "--bare", "--filter=tree:0",
                        f"--shallow-since={T0 - DAY}", f"file://{src}",
                        str(base / "dst")], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        pytest.skip("git local sem suporte a clone parcial (--filter) ou a "
                    f"file:// com --shallow-since: {r.stderr.strip()[:200]}")


@pytest.fixture
def remotes(tmp_path, monkeypatch, filter_support) -> Path:
    """Diretório-base dos 'remotos' locais; REMOTE_BASE aponta para ele."""
    base = tmp_path / "remotes"
    base.mkdir()
    monkeypatch.setattr(epoch, "REMOTE_BASE", f"file://{base}/")
    monkeypatch.setattr(epoch, "EXTRA_ENV",
                        {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull})
    return base


def make_merged_repo(base: Path) -> dict:
    """main: c0 c1 c2 c3 M c4; M incorpora s1 (lateral, data entre c3 e o corte).

    Corte = c3 + 18 h. first-parent ≤ corte ⇒ c3, embora s1 (c3 + 12 h) seja
    mais novo e também ≤ corte.
    """
    src = init_repo(base / "owner" / "repo.git")
    shas = {}
    shas["c0"] = commit(src, T0, "c0", {"README.md": "x", ".github/CODEOWNERS": "* @a"})
    shas["c1"] = commit(src, T0 + 1 * DAY, "c1")
    shas["c2"] = commit(src, T0 + 2 * DAY, "c2")
    git("checkout", "-q", "-b", "side", cwd=src)
    shas["s1"] = commit(src, T0 + 3 * DAY + 12 * 3600, "s1", {"side.txt": "s"})
    git("checkout", "-q", "main", cwd=src)
    shas["c3"] = commit(src, T0 + 3 * DAY, "c3", {".github/CODEOWNERS": "* @b"})
    env_ts = T0 + 4 * DAY
    env = dict(os.environ, **FIXTURE_ENV, GIT_COMMITTER_DATE=f"{env_ts} +0000",
               GIT_AUTHOR_DATE=f"{env_ts} +0000")
    r = subprocess.run(["git", "merge", "-q", "--no-ff", "-m", "M", "side"], cwd=src,
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    shas["M"] = git("rev-parse", "HEAD", cwd=src).strip()
    shas["c4"] = commit(src, T0 + 5 * DAY, "c4")
    return {"src": src, "shas": shas, "cutoff": dt(T0 + 3 * DAY + 18 * 3600)}


# ------------------------------------------------------------ seleção (pura)
def test_select_first_parent_synthetic_chain():
    chain = [("n3", 130), ("n2", 120), ("n1", 110), ("o2", 90), ("o1", 80)]
    assert select_first_parent(chain, 100) == ("o2", 90)
    assert select_first_parent(chain, 90) == ("o2", 90)      # igualdade conta
    assert select_first_parent(chain, 125) == ("n2", 120)
    assert select_first_parent(chain, 50) is None            # nada antes do corte
    assert select_first_parent([], 100) is None


def test_select_first_parent_is_chain_order_not_chronological():
    # commit rebased com data antiga incorporado DEPOIS do corte: fica à
    # frente na cadeia e não é escolhido; o escolhido é o próximo ≤ corte
    chain = [("tip", 200), ("rebased_old_date", 50), ("before", 90)]
    assert select_first_parent(chain, 100) == ("rebased_old_date", 50)
    chain = [("tip", 200), ("before", 90), ("older", 10)]
    assert select_first_parent(chain, 100) == ("before", 90)


# --------------------------------------------------------- parser ls-tree
def test_parse_ls_tree_keeps_only_blobs():
    out = "\0".join([
        "100644 blob aaaa\tREADME.md",
        "100755 blob bbbb\tbin/run.sh",
        "120000 blob cccc\tlink",
        "160000 commit dddd\tvendor/sub",        # submódulo: fora
        "040000 tree eeee\tdocs",                # árvore (só com -t): fora
        "100644 blob ffff\tdocs/a b.md",         # espaço no caminho preservado
    ]) + "\0"
    entries = _parse_ls_tree(out)
    assert entries == [
        TreeEntry("100644", "aaaa", "README.md"),
        TreeEntry("100755", "bbbb", "bin/run.sh"),
        TreeEntry("120000", "cccc", "link"),
        TreeEntry("100644", "ffff", "docs/a b.md"),
    ]


def test_list_tree_real_repo_with_symlink(remotes):
    src = init_repo(remotes / "o" / "t.git")
    (src / ".github").mkdir()
    (src / ".github" / "CODEOWNERS").write_text("* @a\n")
    (src / "run.sh").write_text("#!/bin/sh\n")
    os.chmod(src / "run.sh", 0o755)
    os.symlink("README.md", src / "LINK")
    sha = commit(src, T0, "c0", {"README.md": "r", "docs/x/y.md": "y"})
    entries = list_tree(src, sha)
    by_path = {e.path: e for e in entries}
    assert set(by_path) == {".github/CODEOWNERS", "run.sh", "LINK", "README.md",
                            "docs/x/y.md"}
    assert by_path["LINK"].mode == "120000"
    assert by_path["run.sh"].mode == "100755"
    assert by_path["README.md"].mode == "100644"
    # sha do blob = sha que a API contents devolve (hash-object do conteúdo)
    assert by_path["README.md"].sha == git("hash-object", "README.md", cwd=src).strip()
    assert all("docs" != e.path for e in entries)  # diretório nunca listado


# ------------------------------------------------------------ cache v1 → corte
def write_probe(cache: Path, name: str, fetched_at: str, data) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    (cache / f"{name}.json").write_text(json.dumps(
        {"path": f"/repos/o/r/contents/{name}", "params": None,
         "fetched_at": fetched_at, "data": data}))


def test_v1_probe_cutoff_is_max_fetched_at(tmp_path):
    cache = tmp_path / "o__r"
    write_probe(cache, "repo_metadata", "2026-07-20T00:00:00Z", {"default_branch": "4.x"})
    write_probe(cache, "community_profile", "2026-07-23T23:15:33Z", {})
    write_probe(cache, "codeowners", "2026-07-23T23:15:34Z", None)
    write_probe(cache, "security_md_github", "2026-07-23T23:15:36Z", None)
    write_probe(cache, "workflows", "2026-07-23T23:15:35Z", [])
    write_probe(cache, "releases", "2026-07-24T10:00:00Z", [])  # não é sondagem D1/D5
    cutoff, source = v1_probe_cutoff(cache)
    assert cutoff == datetime(2026, 7, 23, 23, 15, 36, tzinfo=timezone.utc)
    assert source == "probes"
    assert v1_default_branch(cache) == "4.x"


def test_v1_probe_cutoff_falls_back_to_repo_metadata(tmp_path):
    cache = tmp_path / "o__r"
    write_probe(cache, "repo_metadata", "2026-07-20T00:00:00Z", {"default_branch": "main"})
    cutoff, source = v1_probe_cutoff(cache)
    assert (cutoff, source) == (datetime(2026, 7, 20, tzinfo=timezone.utc), "repo_metadata")
    with pytest.raises(FileNotFoundError):
        v1_probe_cutoff(tmp_path / "missing")


# ------------------------------------------------------------- verificação
def test_verify_against_v1_fake_cache(tmp_path):
    cache = tmp_path / "o__r"
    write_probe(cache, "codeowners", "2026-07-23T00:00:00Z",
                {"path": ".github/CODEOWNERS", "sha": "aaaa", "type": "file"})
    write_probe(cache, "security_md", "2026-07-23T00:00:00Z",
                {"path": "SECURITY.md", "sha": "bbbb", "type": "file"})
    write_probe(cache, "funding_yml", "2026-07-23T00:00:00Z", None)  # negativo v1
    write_probe(cache, "workflows", "2026-07-23T00:00:00Z", [
        {"path": ".github/workflows/ci.yml", "sha": "c1c1", "type": "file"},
        {"path": ".github/workflows/old.yml", "sha": "c2c2", "type": "file"},
        {"path": ".github/workflows/sub", "sha": "tree", "type": "dir"},
    ])
    tree = [TreeEntry("100644", "aaaa", ".github/CODEOWNERS"),
            TreeEntry("100644", "beef", "SECURITY.md"),          # sha divergente
            TreeEntry("100644", "c1c1", ".github/workflows/ci.yml")]
    res = verify_against_v1(cache, tree)
    assert set(res) == {"codeowners", "security_md", "workflows"}  # governance ausente, funding nulo
    assert res["codeowners"] == {"path": ".github/CODEOWNERS", "v1_sha": "aaaa",
                                 "epoch_sha": "aaaa", "ok": True}
    assert res["security_md"]["ok"] is False and res["security_md"]["epoch_sha"] == "beef"
    wf = res["workflows"]
    assert wf["ok"] is False and wf["n_files"] == 2         # old.yml sumiu; dir ignorado
    assert [f["ok"] for f in wf["files"]] == [True, False]
    assert wf["files"][1]["epoch_sha"] is None


def test_verify_against_v1_all_ok_and_empty(tmp_path):
    cache = tmp_path / "o__r"
    write_probe(cache, "governance", "2026-07-23T00:00:00Z",
                {"path": "GOVERNANCE.md", "sha": "g", "type": "file"})
    assert verify_against_v1(cache, [TreeEntry("100644", "g", "GOVERNANCE.md")]) == {
        "governance": {"path": "GOVERNANCE.md", "v1_sha": "g", "epoch_sha": "g", "ok": True}}
    assert verify_against_v1(tmp_path / "nothing", []) == {}


# ------------------------------------------------------ resolução (git local)
def test_resolve_epoch_picks_first_parent_not_side_commit(remotes, tmp_path):
    fx = make_merged_repo(remotes)
    res = resolve_epoch("owner/repo", "main", fx["cutoff"], tmp_path / "wd")
    assert res.status == "ok"
    assert res.sha == fx["shas"]["c3"]           # não s1 (lateral, mais novo, ≤ corte)
    assert res.committer_ts == T0 + 3 * DAY
    assert res.resolver_step == "fetch_since_60d"   # ponta > corte ⇒ 1º degrau
    assert res.branch == "main"
    assert res.cutoff == fx["cutoff"].strftime("%Y-%m-%dT%H:%M:%SZ")
    # árvore de época: CODEOWNERS de c3, não a versão de c0
    tree = list_tree(tmp_path / "wd" / "clone", res.sha)
    by_path = {e.path: e.sha for e in tree}
    assert by_path[".github/CODEOWNERS"] == git(
        "rev-parse", f"{res.sha}:.github/CODEOWNERS", cwd=fx["src"]).strip()
    assert "side.txt" not in by_path


def test_resolve_epoch_cutoff_after_tip_uses_tip(remotes, tmp_path):
    fx = make_merged_repo(remotes)
    res = resolve_epoch("owner/repo", "main", dt(T0 + 6 * DAY), tmp_path / "wd")
    assert (res.status, res.sha, res.resolver_step) == ("ok", fx["shas"]["c4"], "clone_depth_1")


def record_git_calls(monkeypatch) -> list[list[str]]:
    """Registra os argumentos de cada git executado (delegando ao real)."""
    real = epoch._run_git
    calls: list[list[str]] = []

    def spy(args, cwd=None, timeout=epoch.TIMEOUT_LOG):
        calls.append(list(args))
        return real(args, cwd=cwd, timeout=timeout)

    monkeypatch.setattr(epoch, "_run_git", spy)
    return calls


def test_resolve_epoch_inactive_branch_resolved_by_depth1(remotes, tmp_path, monkeypatch):
    # ponta 100 dias antes do corte (branch inativo): --depth=1 basta e
    # NENHUMA requisição --shallow-since é emitida — uma com corte−60d não
    # selecionaria commit algum, falha que o HTTP do GitHub não relata
    src = init_repo(remotes / "owner" / "old.git")
    commit(src, T0, "c0")
    tip = commit(src, T0 + 10 * DAY, "c1")
    calls = record_git_calls(monkeypatch)
    res = resolve_epoch("owner/old", "main", dt(T0 + 110 * DAY), tmp_path / "wd")
    assert (res.status, res.sha, res.resolver_step) == ("ok", tip, "clone_depth_1")
    assert not any(a.startswith("--shallow-since") for c in calls for a in c)
    assert any("--depth=1" in c for c in calls)


def github_like_transport(monkeypatch, tip_ts: int) -> list[list[str]]:
    """Simula o transporte HTTP do GitHub (protocolo v2, git 2.50).

    Um ``--shallow-since`` que não seleciona commit algum (data posterior à
    ponta) termina a resposta sem repassar o die() de upload-pack: o cliente
    vê só "error processing shallow info: 4". Reproduzido pela revisão contra
    guzzle/.github e macrozheng/mall com os cortes reais de v1.
    """
    real = epoch._run_git
    calls: list[list[str]] = []

    def fake(args, cwd=None, timeout=epoch.TIMEOUT_LOG):
        calls.append(list(args))
        for a in args:
            if a.startswith("--shallow-since=") and int(a.split("=", 1)[1]) > tip_ts:
                msg = "fatal: error processing shallow info: 4"
                raise GitError(f"git {' '.join(args[:2])}: {msg}", epoch._classify(msg))
        return real(args, cwd=cwd, timeout=timeout)

    monkeypatch.setattr(epoch, "_run_git", fake)
    return calls


def test_resolve_epoch_github_like_transport_inactive_branch(remotes, tmp_path, monkeypatch):
    # caso-manchete do registro: org guzzle/.github inativa há > 60 d da
    # sondagem — com o clone --shallow-since original virava "unreachable"
    src = init_repo(remotes / "owner" / "old.git")
    commit(src, T0, "c0")
    tip = commit(src, T0 + 10 * DAY, "c1")
    org = init_repo(remotes / "owner" / ".github.git")
    o0 = commit(org, T0, "o0", {".github/SECURITY.md": "s"})
    github_like_transport(monkeypatch, tip_ts=T0 + 10 * DAY)
    res = resolve_epoch("owner/old", "main", dt(T0 + 110 * DAY), tmp_path / "wd")
    assert (res.status, res.sha, res.resolver_step) == ("ok", tip, "clone_depth_1")
    org_res = resolve_org("owner", dt(T0 + 110 * DAY), tmp_path / "wd")
    assert org_res is not None
    assert (org_res.status, org_res.sha, org_res.resolver_step) == ("ok", o0, "clone_depth_1")
    assert {e.path for e in list_tree(tmp_path / "wd" / "org", o0)} == {".github/SECURITY.md"}


def test_resolve_epoch_github_like_transport_active_branch(remotes, tmp_path, monkeypatch):
    # branch ativo: ponta > corte ⇒ o fetch --shallow-since=corte−60d é
    # satisfazível por construção e o transporte nunca é levado ao erro
    fx = make_merged_repo(remotes)
    calls = github_like_transport(monkeypatch, tip_ts=T0 + 5 * DAY)
    res = resolve_epoch("owner/repo", "main", fx["cutoff"], tmp_path / "wd")
    assert (res.status, res.sha, res.resolver_step) == ("ok", fx["shas"]["c3"], "fetch_since_60d")
    since = [a for c in calls for a in c if a.startswith("--shallow-since=")]
    assert len(since) == 1 and int(since[0].split("=")[1]) == int(fx["cutoff"].timestamp()) - 60 * DAY


def test_resolve_epoch_ladder_deepens_v1_branch_not_remote_head(remotes, tmp_path):
    # default v1 = 4.x, HEAD remoto = main (5 casos na amostra). O clone
    # --bare --single-branch não grava remote.origin.fetch: sem refspec
    # explícito, "fetch origin" aprofundaria main e 4.x ficaria na ponta
    src = init_repo(remotes / "owner" / "lts.git")
    commit(src, T0, "m0")
    git("checkout", "-q", "-b", "4.x", cwd=src)
    x1 = commit(src, T0 + 1 * DAY, "x1")
    commit(src, T0 + 100 * DAY, "x2")
    git("checkout", "-q", "main", cwd=src)
    for i in range(1, 4):
        commit(src, T0 + 50 * DAY + i * DAY, f"n{i}")
    assert git("symbolic-ref", "--short", "HEAD", cwd=src).strip() == "main"
    res = resolve_epoch("owner/lts", "4.x", dt(T0 + 30 * DAY), tmp_path / "wd")
    assert (res.status, res.sha, res.resolver_step) == ("ok", x1, "fetch_since_60d")
    assert res.branch == "4.x"


def test_resolve_epoch_ladder_since_365d(remotes, tmp_path):
    # c0, c1 antes do corte; c2, c3 mais de 60 d depois: o clone inicial só
    # traz c2/c3 e a cadeia não cruza ⇒ fetch --shallow-since=corte−365d
    src = init_repo(remotes / "owner" / "ladder.git")
    commit(src, T0, "c0")
    c1 = commit(src, T0 + 10 * DAY, "c1")
    commit(src, T0 + 250 * DAY, "c2")
    commit(src, T0 + 260 * DAY, "c3")
    res = resolve_epoch("owner/ladder", "main", dt(T0 + 100 * DAY), tmp_path / "wd")
    assert (res.status, res.sha, res.resolver_step) == ("ok", c1, "fetch_since_365d")


def test_resolve_epoch_ladder_depth_rung(remotes, tmp_path):
    # único commit ≤ corte é anterior a corte−365d: só o degrau --depth cruza
    src = init_repo(remotes / "owner" / "deep.git")
    c0 = commit(src, T0, "c0")
    for i in range(1, 6):
        commit(src, T0 + 400 * DAY + i * DAY, f"c{i}")
    res = resolve_epoch("owner/deep", "main", dt(T0 + 399 * DAY), tmp_path / "wd")
    assert (res.status, res.sha, res.resolver_step) == ("ok", c0, "fetch_depth_400")


def test_resolve_epoch_no_commit_before_cutoff(remotes, tmp_path):
    src = init_repo(remotes / "owner" / "young.git")
    commit(src, T0 + 100 * DAY, "c0")
    commit(src, T0 + 101 * DAY, "c1")
    res = resolve_epoch("owner/young", "main", dt(T0 + 50 * DAY), tmp_path / "wd")
    assert res.status == "no_commit_before_cutoff"
    assert res.sha is None
    assert res.resolver_step == "history_exhausted"   # história completa, sem commit ≤ corte


def test_resolve_epoch_unreachable_repo_and_branch(remotes, tmp_path):
    make_merged_repo(remotes)
    res = resolve_epoch("owner/nope", "main", dt(T0 + DAY), tmp_path / "wd1")
    assert (res.status, res.sha, res.resolver_step) == ("unreachable", None, "clone")
    assert res.error
    # branch default v1 renomeado/removido ⇒ "branch de época inexistente"
    res = resolve_epoch("owner/repo", "master", dt(T0 + DAY), tmp_path / "wd2")
    assert res.status == "unreachable" and "master" in (res.error or "")


def test_resolve_org_absent_empty_and_present(remotes, tmp_path):
    assert resolve_org("owner", dt(T0 + DAY), tmp_path / "wd0") is None   # 404
    # URL do repositório especial espelha a do GitHub: {owner}/.github.git
    org = init_repo(remotes / "owner" / ".github.git")                      # vazio
    assert resolve_org("owner", dt(T0 + DAY), tmp_path / "wd1") is None
    s0 = commit(org, T0, "c0", {".github/ISSUE_TEMPLATE/bug.md": "b", "SECURITY.md": "s"})
    commit(org, T0 + 5 * DAY, "c1", {"SECURITY.md": "s2"})
    res = resolve_org("owner", dt(T0 + DAY), tmp_path / "wd2")
    assert isinstance(res, EpochResult)
    assert (res.status, res.sha, res.branch) == ("ok", s0, "main")
    paths = {e.path for e in list_tree(tmp_path / "wd2" / "org", res.sha)}
    assert paths == {".github/ISSUE_TEMPLATE/bug.md", "SECURITY.md"}
    # sem commit ≤ corte ⇒ EpochResult (não None): sem herança, mas relatável
    res = resolve_org("owner", dt(T0 - DAY), tmp_path / "wd3")
    assert res is not None and res.status == "no_commit_before_cutoff"


# ------------------------------------------------------------------ _run_git
def test_run_git_timeout_and_classification(tmp_path):
    with pytest.raises(GitError) as ei:
        _run_git(["clone", "file:///nonexistent/x.git", str(tmp_path / "d")])
    assert ei.value.kind == "not_found"
    assert epoch._classify("fatal: no commits selected for shallow requests\n"
                           "fatal: the remote end hung up unexpectedly") == "no_commits_selected"
    assert epoch._classify("fatal: Remote branch dev not found in upstream origin") == "branch_not_found"
    # HTTP do GitHub (protocolo v2): resposta encerrada na seção shallow-info
    # = o mesmo "no commits selected" — definitivo, sem nova tentativa
    assert epoch._classify("fatal: error processing shallow info: 4") == "no_commits_selected"
    assert epoch._classify("fatal: error processing shallow info: 0") == "transient"   # EOF real
    assert epoch._classify("fatal: shallow file has changed since we read it") == "transient"
    assert epoch._classify("error: RPC failed; curl 56 ...") == "transient"
    assert epoch._classify("fatal: something else") == "other"


def test_run_git_retries_once_on_transient(monkeypatch):
    calls = []

    def fake(args, cwd=None, timeout=0):
        calls.append(list(args))
        if len(calls) == 1:
            raise GitError("fatal: shallow file has changed", "transient")
        return "ok"

    monkeypatch.setattr(epoch, "_run_git", fake)
    resets = []
    assert epoch._run_git_retry(["fetch"], reset=lambda: resets.append(1)) == "ok"
    assert len(calls) == 2 and resets == [1]
    def definitive(args, cwd=None, timeout=0):
        raise GitError("x", "not_found")

    monkeypatch.setattr(epoch, "_run_git", definitive)
    with pytest.raises(GitError):          # falha definitiva: sem nova tentativa
        epoch._run_git_retry(["fetch"])


# ------------------------------------------------------------------- driver
def make_v1_cache(cache_root: Path, fx: dict, codeowners_sha: str,
                  cutoff: datetime) -> Path:
    cache = cache_root / "owner__repo"
    fetched = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    write_probe(cache, "repo_metadata", "2026-07-20T00:00:00Z",
                {"default_branch": "main", "full_name": "owner/repo"})
    write_probe(cache, "community_profile", fetched, {"health_percentage": 50})
    write_probe(cache, "codeowners", fetched,
                {"path": ".github/CODEOWNERS", "sha": codeowners_sha, "type": "file"})
    write_probe(cache, "governance", fetched, None)
    write_probe(cache, "workflows", fetched, None)
    return cache


def test_ensure_epoch_artifacts_writes_files_and_is_idempotent(remotes, tmp_path, monkeypatch):
    fx = make_merged_repo(remotes)
    cutoff = fx["cutoff"]
    c3 = fx["shas"]["c3"]
    sha_c3 = git("rev-parse", f"{c3}:.github/CODEOWNERS", cwd=fx["src"]).strip()
    cache_root = tmp_path / "raw"
    make_v1_cache(cache_root, fx, sha_c3, cutoff)
    org = init_repo(remotes / "owner" / ".github.git")
    o0 = commit(org, T0, "o0", {"SECURITY.md": "s"})
    wd = tmp_path / "wd"

    out = ensure_epoch_artifacts("owner/repo", cache_root, wd)
    v2 = cache_root / "owner__repo" / "v2"
    assert out["repo"] == "owner/repo" and out["branch"] == "main"
    assert out["sha"] == c3 and out["status"] == "ok" and out["epoch_status"] == "ok"
    assert out["cutoff"] == cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert out["cutoff_source"] == "probes" and out["catalog_version"] == "v2"
    assert out["verification"]["codeowners"]["ok"] is True
    assert out["fetched_at"].endswith("Z")
    assert json.loads((v2 / "epoch_commit.json").read_text()) == out
    tree = json.loads((v2 / f"tree_paths_{c3[:12]}.json").read_text())
    assert tree["sha"] == c3 and tree["n_blobs"] == len(tree["entries"]) > 0
    assert tree["n_symlinks"] == 0 and tree["catalog_version"] == "v2"
    assert {"mode", "sha", "path"} == set(tree["entries"][0])
    org_json = json.loads((v2 / "org_epoch_commit.json").read_text())
    assert org_json["status"] == "ok" and org_json["sha"] == o0
    assert org_json["repo"] == "owner/.github"
    assert (v2 / f"org_tree_paths_{o0[:12]}.json").exists()
    assert not (wd / "owner__repo").exists()      # clone removido (keep=False)
    # nada escrito fora de v2/ (chaves v1 intocadas)
    assert sorted(p.name for p in (cache_root / "owner__repo").iterdir()
                  if p.is_file()) == ["codeowners.json", "community_profile.json",
                                      "governance.json", "repo_metadata.json",
                                      "workflows.json"]

    # 2ª chamada: só leitura, nenhum git
    def boom(*a, **k):
        raise AssertionError("git não deve ser chamado com artefatos presentes")
    monkeypatch.setattr(epoch, "_run_git", boom)
    assert ensure_epoch_artifacts("owner/repo", cache_root, wd) == out

    # force=True re-executa (git volta a ser chamado)
    monkeypatch.setattr(epoch, "_run_git", _run_git)
    again = ensure_epoch_artifacts("owner/repo", cache_root, wd, force=True, keep=True)
    assert again["sha"] == c3
    assert (wd / "owner__repo" / "clone").exists()


def test_ensure_epoch_artifacts_unverified_and_unreachable(remotes, tmp_path):
    fx = make_merged_repo(remotes)
    cache_root = tmp_path / "raw"
    make_v1_cache(cache_root, fx, "0000000000000000000000000000000000000000", fx["cutoff"])
    out = ensure_epoch_artifacts("owner/repo", cache_root, tmp_path / "wd")
    assert out["status"] == "ok" and out["epoch_status"] == "unverified"
    assert out["verification"]["codeowners"]["ok"] is False
    org = json.loads((cache_root / "owner__repo" / "v2" / "org_epoch_commit.json").read_text())
    assert org["status"] == "absent" and org["catalog_version"] == "v2"

    # repositório removido em setembro ⇒ unreachable, sem árvore
    cache = cache_root / "owner__gone"
    write_probe(cache, "repo_metadata", "2026-07-20T00:00:00Z", {"default_branch": "main"})
    write_probe(cache, "community_profile", "2026-07-23T00:00:00Z", {})
    out = ensure_epoch_artifacts("owner/gone", cache_root, tmp_path / "wd2")
    assert out["epoch_status"] == "unreachable" and out["sha"] is None
    assert out["verification"] == {}
    assert not list((cache / "v2").glob("tree_paths_*.json"))


def test_ensure_epoch_artifacts_tree_fetch_failure_is_unreachable(remotes, tmp_path, monkeypatch):
    # commit resolvido, mas o fetch preguiçoso das trees falha após o retry:
    # registrado como unreachable (sem árvore), não como exceção do lote
    fx = make_merged_repo(remotes)
    cache_root = tmp_path / "raw"
    make_v1_cache(cache_root, fx, "irrelevante", fx["cutoff"])

    def failing(clone, sha):
        raise GitError("fatal: unable to access remote (promisor)", "transient")

    monkeypatch.setattr(epoch, "list_tree", failing)
    out = ensure_epoch_artifacts("owner/repo", cache_root, tmp_path / "wd")
    assert out["status"] == "unreachable" and out["epoch_status"] == "unreachable"
    assert out["sha"] == fx["shas"]["c3"] and "ls-tree" in out["error"]
    assert not list((cache_root / "owner__repo" / "v2").glob("tree_paths_*.json"))
    # marcador consistente: com retry_unreachable=False a 2ª chamada lê o
    # cache, sem git
    monkeypatch.setattr(epoch, "_run_git", lambda *a, **k: pytest.fail("git chamado"))
    assert ensure_epoch_artifacts("owner/repo", cache_root, tmp_path / "wd",
                                  retry_unreachable=False) == out
    # padrão: "unreachable" é resolvido de novo — a falha transitória passou
    monkeypatch.setattr(epoch, "_run_git", _run_git)
    monkeypatch.setattr(epoch, "list_tree", list_tree)
    healed = ensure_epoch_artifacts("owner/repo", cache_root, tmp_path / "wd")
    assert healed["status"] == "ok" and healed["sha"] == fx["shas"]["c3"]
    assert (cache_root / "owner__repo" / "v2" / f"tree_paths_{fx['shas']['c3'][:12]}.json").exists()


def test_ensure_epoch_artifacts_retries_unreachable_org_only(remotes, tmp_path, monkeypatch):
    # repo ok, org "unreachable" por falha de rede: o próximo passe refaz o
    # par; um 404 genuíno ("absent") e "no_commit_before_cutoff" não são refeitos
    fx = make_merged_repo(remotes)
    cache_root = tmp_path / "raw"
    sha_c3 = git("rev-parse", f"{fx['shas']['c3']}:.github/CODEOWNERS", cwd=fx["src"]).strip()
    make_v1_cache(cache_root, fx, sha_c3, fx["cutoff"])
    org = init_repo(remotes / "owner" / ".github.git")
    o0 = commit(org, T0, "o0", {"SECURITY.md": "s"})
    real_resolve_org = epoch.resolve_org

    def org_down(owner, cutoff, workdir, cutoff_source="probes"):
        return EpochResult(None, None, epoch._fmt(cutoff), cutoff_source, "clone",
                           "unreachable", None, "git clone: fatal: unable to access")

    monkeypatch.setattr(epoch, "resolve_org", org_down)
    first = ensure_epoch_artifacts("owner/repo", cache_root, tmp_path / "wd")
    v2 = cache_root / "owner__repo" / "v2"
    assert first["status"] == "ok"
    assert json.loads((v2 / "org_epoch_commit.json").read_text())["status"] == "unreachable"
    monkeypatch.setattr(epoch, "resolve_org", real_resolve_org)
    second = ensure_epoch_artifacts("owner/repo", cache_root, tmp_path / "wd")
    assert second["sha"] == first["sha"]
    org_json = json.loads((v2 / "org_epoch_commit.json").read_text())
    assert (org_json["status"], org_json["sha"]) == ("ok", o0)
    # agora completo: 3ª chamada é só leitura
    monkeypatch.setattr(epoch, "_run_git", lambda *a, **k: pytest.fail("git chamado"))
    assert ensure_epoch_artifacts("owner/repo", cache_root, tmp_path / "wd") == second
