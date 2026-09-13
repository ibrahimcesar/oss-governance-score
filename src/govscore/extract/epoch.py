"""Época por repositório para o catálogo v2 (reparo de D1/D5).

Implementa a política do registro de decisão
``docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md`` (seção "Época"):
a re-medição dos itens binários de D1/D5 é feita sobre a ÁRVORE DO BRANCH
DEFAULT NO COMMIT DE ÉPOCA — o primeiro commit da cadeia *first-parent* com
data de committer ≤ ``cutoff_r``, sendo ``cutoff_r`` o instante da última
sondagem v1 de D1/D5 daquele repositório (máximo de ``fetched_at`` nos
arquivos de cache das sondagens; fallback ``repo_metadata.json``).

Obtenção (só git, nunca REST/GraphQL — exceção única e declarada à regra
"a análise nunca reconsulta a rede": os objetos são IMUTÁVEIS e endereçados
por SHA):

1. ``git clone --bare --single-branch --branch <branch> --filter=tree:0
   --shallow-since=<cutoff-60d>`` (``--no-tags`` adicionado: tags não
   participam da cadeia). Se o servidor responde "no commits selected for
   shallow requests" (nenhum commit nos 60 dias que antecedem o corte —
   branch inativo), recorre-se a ``--depth=1``: a ponta é, por construção,
   anterior ao corte.
2. Escada de aprofundamento enquanto a cadeia não cruza o corte:
   ``git fetch --shallow-since=<cutoff-365d>`` → ``--depth 400`` → ``1600``
   → ``6400``. Usa-se ``--depth=N`` (absoluto a partir da ponta, como no
   registro), NÃO ``--deepen``; degraus com ``N`` ≤ comprimento já obtido da
   cadeia são pulados, porque ``--depth`` menor ENCURTARIA a história.
3. Seleção em Python sobre ``git log --first-parent --format=%H%x09%ct``
   (mais novo primeiro): primeira entrada com ``ts <= cutoff``. Não se usa
   ``rev-list --before`` (falhou em linux, cf. registro).

Verificação: cada blob positivo em v1 (respostas do endpoint ``contents``
em cache) deve existir com o mesmo ``sha`` na árvore de época; divergência
⇒ ``epoch_status = "unverified"`` (o repositório é mantido e D1/D5 vêm do
cache v1, decisão do módulo de re-pontuação). Inacessível ou sem branch/commit
de época ⇒ ``"unreachable"``.

Saídas em ``<cache_root>/<owner>__<repo>/v2/`` (nunca sobrescrevem chaves v1).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

CATALOG_VERSION = "v2"

# Base das URLs de clone; testes trocam por file://<dir>/ (fixtures locais).
REMOTE_BASE = "https://github.com/"

# Variáveis de ambiente extras para todo git (testes isolam config global).
EXTRA_ENV: dict[str, str] = {}

# Tempos-limite por comando (s). Monorepos de Federação passam de 10 min.
TIMEOUT_CLONE = 1800
TIMEOUT_FETCH = 1800
TIMEOUT_LOG = 300
TIMEOUT_LS_TREE = 900

# Escada de aprofundamento (registro: 60d → 365d → 400 → 1600 → 6400).
SINCE_CLONE_DAYS = 60
SINCE_FETCH_DAYS = 365
DEPTH_LADDER = (400, 1600, 6400)

# Sondagens v1 de D1/D5 (chaves de cache de extract/artifacts.py) que
# definem cutoff_r; funding_yml* e security_md* cobrem as variantes de caminho.
CUTOFF_PROBE_GLOBS = (
    "community_profile", "codeowners", "governance", "funding_yml*",
    "security_md*", "workflows", "dependabot",
)
# Sondagens com resposta `contents` de UM arquivo (data = {"sha","path",...}).
VERIFY_FILE_PROBES = (
    "codeowners", "governance", "funding_yml", "funding_yml_github",
    "security_md", "security_md_github", "security_md_docs", "dependabot",
)
# Sondagem de DIRETÓRIO (data = lista de entradas): todos os arquivos batem.
VERIFY_DIR_PROBES = ("workflows",)

BLOB_MODES = ("100644", "100755", "120000")
SYMLINK_MODE = "120000"
TS_FMT = "%Y-%m-%dT%H:%M:%SZ"


# --------------------------------------------------------------------- tipos
@dataclass
class EpochResult:
    """Resultado da resolução do commit de época de um branch.

    status: "ok" | "unreachable" | "no_commit_before_cutoff".
    resolver_step: degrau da escada em que a cadeia cruzou o corte
    (clone_since_60d, clone_depth_1, fetch_since_365d, fetch_depth_400/1600/
    6400) ou, sem cruzar, history_exhausted / ladder_exhausted; "clone" quando
    o clone falhou. Campos com default (branch, error) foram acrescentados ao
    contrato para relato — não alteram a ordem posicional.
    """
    sha: str | None
    committer_ts: int | None
    cutoff: str
    cutoff_source: str
    resolver_step: str
    status: str
    branch: str | None = None
    error: str | None = None


@dataclass
class TreeEntry:
    """Entrada de ``git ls-tree -r`` restrita a blobs (100644/100755/120000)."""
    mode: str
    sha: str
    path: str


class GitError(RuntimeError):
    """Falha de um comando git, classificada para a política de retry.

    kind: "transient" (rede, shallow em mutação, timeout — vale UMA nova
    tentativa), "not_found", "branch_not_found", "no_commits_selected",
    "empty", "other".
    """

    def __init__(self, message: str, kind: str = "other"):
        super().__init__(message)
        self.kind = kind


# Ordem importa: mensagens definitivas primeiro ("Could not read from remote
# repository" acompanha tanto 404 quanto falhas de rede).
_DEFINITIVE = (
    ("no_commits_selected", r"no commits selected for shallow requests"),
    ("branch_not_found", r"remote branch .* not found"),
    ("not_found", r"repository .*not found|does not appear to be a git repository"
                  r"|is not a git repository|authentication failed"
                  r"|could not read username|permission denied|access denied"
                  r"|invalid username or password|terminal prompts disabled"),
    ("empty", r"does not have any commits yet|bad revision|unknown revision"
              r"|needed a single revision|not a valid object name"),
)
_TRANSIENT = re.compile(
    r"shallow file has changed|error processing shallow info"
    r"|could not read from remote|unable to access|early eof|rpc failed"
    r"|connection reset|timed out|connection refused|hung up unexpectedly"
    r"|unexpected disconnect|temporarily unavailable|could not resolve host"
    r"|http/?\s*5\d\d|error: 5\d\d|the remote end hung up|premature end"
    r"|fetch-pack: .*(error|fail)|pack has bad object|index-pack failed",
    re.IGNORECASE)


def _classify(stderr: str) -> str:
    for kind, rx in _DEFINITIVE:
        if re.search(rx, stderr, re.IGNORECASE):
            return kind
    if _TRANSIENT.search(stderr):
        return "transient"
    return "other"


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"   # jamais pedir credenciais (repo removido/privado)
    env["LC_ALL"] = "C"                # mensagens estáveis para a classificação
    env.update(EXTRA_ENV)
    return env


def _run_git(args: list[str], cwd: Path | None = None,
             timeout: float = TIMEOUT_LOG) -> str:
    """Executa ``git -c gc.auto=0 <args>`` com timeout; stdout decodificado.

    Levanta GitError classificado. TimeoutExpired vira kind="transient"
    (o processo filho é morto pelo subprocess).
    """
    cmd = ["git", "-c", "gc.auto=0", *args]
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, env=_git_env(),
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        raise GitError(f"git {' '.join(args[:2])}: timeout após {timeout:.0f}s",
                       "transient")
    except FileNotFoundError:
        raise GitError("git não encontrado no PATH", "other")
    stderr = r.stderr.decode("utf-8", "replace")
    if r.returncode != 0:
        raise GitError(f"git {' '.join(args[:2])}: {stderr.strip()[:400]}",
                       _classify(stderr))
    return r.stdout.decode("utf-8", "replace")


def _run_git_retry(args: list[str], cwd: Path | None = None,
                   timeout: float = TIMEOUT_LOG,
                   reset: Callable[[], None] | None = None) -> str:
    """Uma nova tentativa em falha transitória; ``reset`` limpa estado parcial."""
    try:
        return _run_git(args, cwd=cwd, timeout=timeout)
    except GitError as e:
        if e.kind != "transient":
            raise
        if reset is not None:
            reset()
        return _run_git(args, cwd=cwd, timeout=timeout)


def remote_url(repo: str) -> str:
    return f"{REMOTE_BASE}{repo}.git"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime(TS_FMT)


def _fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(TS_FMT)


def _parse_ts(s: str) -> datetime:
    return datetime.strptime(s, TS_FMT).replace(tzinfo=timezone.utc)


# ------------------------------------------------------------- cache v1 → corte
def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _latest_probe(repo_cache_dir: Path) -> tuple[datetime, str] | None:
    """(fetched_at máximo, nome da sondagem) entre as sondagens v1 de D1/D5."""
    best: tuple[datetime, str] | None = None
    for pattern in CUTOFF_PROBE_GLOBS:
        for f in sorted(repo_cache_dir.glob(f"{pattern}.json")):
            payload = _read_json(f)
            if not payload or not payload.get("fetched_at"):
                continue
            ts = _parse_ts(payload["fetched_at"])
            if best is None or ts > best[0]:
                best = (ts, f.stem)
    return best


def v1_probe_cutoff(repo_cache_dir: Path) -> tuple[datetime, str]:
    """``cutoff_r``: máximo de ``fetched_at`` das sondagens v1 de D1/D5.

    Retorna (cutoff_utc, source) com source "probes" ou "repo_metadata"
    (fallback quando nenhuma sondagem existe). Levanta FileNotFoundError sem
    cache v1 — a época não é definível sem a sondagem original.
    """
    best = _latest_probe(repo_cache_dir)
    if best is not None:
        return best[0], "probes"
    meta = _read_json(repo_cache_dir / "repo_metadata.json")
    if meta and meta.get("fetched_at"):
        return _parse_ts(meta["fetched_at"]), "repo_metadata"
    raise FileNotFoundError(f"sem cache v1 em {repo_cache_dir}")


def _cutoff_probe(repo_cache_dir: Path) -> str | None:
    """Nome da sondagem que definiu o corte (anotação de relato)."""
    best = _latest_probe(repo_cache_dir)
    return best[1] if best else None


def v1_default_branch(repo_cache_dir: Path) -> str:
    """Branch default REGISTRADO em v1 (``repo_metadata.json``), não o atual."""
    meta = _read_json(repo_cache_dir / "repo_metadata.json")
    branch = ((meta or {}).get("data") or {}).get("default_branch")
    if not branch:
        raise FileNotFoundError(f"repo_metadata.json sem default_branch em {repo_cache_dir}")
    return branch


# ------------------------------------------------------------------ resolução
def select_first_parent(chain: list[tuple[str, int]],
                        cutoff_ts: int) -> tuple[str, int] | None:
    """Primeira entrada (mais novo primeiro) com committer_ts ≤ cutoff.

    A ordem é a da cadeia first-parent, não a cronológica: um commit com
    data antiga incorporado depois do corte (rebase) fica atrás dos mais
    novos e não é escolhido — coerente com "estado do branch no instante".
    """
    for sha, ts in chain:
        if ts <= cutoff_ts:
            return sha, ts
    return None


def _first_parent_chain(clone: Path, ref: str) -> list[tuple[str, int]]:
    out = _run_git(["log", "--first-parent", "--format=%H%x09%ct", ref, "--"],
                   cwd=clone, timeout=TIMEOUT_LOG)
    chain = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        sha, ts = line.split("\t", 1)
        chain.append((sha.strip(), int(ts)))
    return chain


def _is_shallow(clone: Path) -> bool:
    return (clone / "shallow").exists()


def _since_arg(dt: datetime) -> str:
    # Inteiro de ≥ 9 dígitos é lido pelo git como segundos desde a época
    # (date.c, match_digit) — sem ambiguidade de fuso.
    return f"--shallow-since={int(dt.timestamp())}"


def _clone(url: str, branch: str | None, dest: Path, *extra: str) -> None:
    args = ["clone", "--quiet", "--bare", "--single-branch", "--no-tags",
            "--filter=tree:0"]
    if branch:
        args += ["--branch", branch]
    args += [*extra, url, str(dest)]

    def reset():
        shutil.rmtree(dest, ignore_errors=True)

    _run_git_retry(args, timeout=TIMEOUT_CLONE, reset=reset)


def _resolve(url: str, branch: str | None, cutoff: datetime, clone: Path,
             cutoff_source: str) -> EpochResult:
    """Clone + escada + seleção. ``branch=None`` usa o HEAD remoto (org)."""
    cutoff_s = _fmt(cutoff)
    cutoff_ts = int(cutoff.timestamp())
    shutil.rmtree(clone, ignore_errors=True)
    clone.parent.mkdir(parents=True, exist_ok=True)

    def result(sha, ts, step, status, error=None):
        return EpochResult(sha=sha, committer_ts=ts, cutoff=cutoff_s,
                           cutoff_source=cutoff_source, resolver_step=step,
                           status=status, branch=branch, error=error)

    # 1. clone raso por data; branch inativo (nenhum commit nos 60 dias
    #    anteriores ao corte) ⇒ --depth=1
    step = "clone_since_60d"
    try:
        _clone(url, branch, clone, _since_arg(cutoff - timedelta(days=SINCE_CLONE_DAYS)))
    except GitError as e:
        if e.kind != "no_commits_selected":
            return result(None, None, "clone", "unreachable", str(e))
        step = "clone_depth_1"
        try:
            _clone(url, branch, clone, "--depth=1")
        except GitError as e2:
            return result(None, None, "clone", "unreachable", str(e2))

    ref = f"refs/heads/{branch}" if branch else "HEAD"
    if branch is None:
        try:
            branch = _run_git(["symbolic-ref", "--short", "HEAD"], cwd=clone).strip() or None
        except GitError:
            branch = None

    def chain_now() -> list[tuple[str, int]]:
        try:
            return _first_parent_chain(clone, ref)
        except GitError as e:
            if e.kind == "empty":
                return []
            raise

    try:
        chain = chain_now()
        if not chain:
            return result(None, None, step, "unreachable", "repositório vazio")
        sel = select_first_parent(chain, cutoff_ts)
        if sel:
            return result(sel[0], sel[1], step, "ok")

        # 2. escada de aprofundamento
        ladder: list[tuple[str, list[str], int | None]] = [
            ("fetch_since_365d",
             [_since_arg(cutoff - timedelta(days=SINCE_FETCH_DAYS))], None)]
        ladder += [(f"fetch_depth_{d}", [f"--depth={d}"], d) for d in DEPTH_LADDER]
        for step, args, depth in ladder:
            if not _is_shallow(clone):
                return result(None, None, "history_exhausted", "no_commit_before_cutoff")
            if depth is not None and len(chain) >= depth:
                continue  # --depth menor encurtaria a história já obtida
            try:
                _run_git_retry(["fetch", "--quiet", *args, "origin"], cwd=clone,
                               timeout=TIMEOUT_FETCH)
            except GitError as e:
                if e.kind == "no_commits_selected":
                    continue
                raise
            chain = chain_now()
            sel = select_first_parent(chain, cutoff_ts)
            if sel:
                return result(sel[0], sel[1], step, "ok")
        last = "history_exhausted" if not _is_shallow(clone) else "ladder_exhausted"
        return result(None, None, last, "no_commit_before_cutoff")
    except GitError as e:
        return result(None, None, step, "unreachable", str(e))


def resolve_epoch(repo: str, branch: str, cutoff: datetime, workdir: Path,
                  cutoff_source: str = "probes") -> EpochResult:
    """Commit de época do branch default v1 de ``repo``; clone em workdir/clone."""
    return _resolve(remote_url(repo), branch, cutoff, workdir / "clone", cutoff_source)


def resolve_org(owner: str, cutoff: datetime, workdir: Path,
                cutoff_source: str = "probes") -> EpochResult | None:
    """Época de ``{owner}/.github`` (branch default atual); clone em workdir/org.

    None quando o repositório especial não existe (404) ou está vazio (409 /
    sem commits) — sem herança. Inacessível por outra razão (rede) ⇒
    EpochResult "unreachable", para distinguir de "ausente" no relato.
    """
    res = _resolve(remote_url(f"{owner}/.github"), None, cutoff, workdir / "org",
                   cutoff_source)
    if res.status == "unreachable":
        err = res.error or ""
        if "repositório vazio" in err or _classify(err) in ("not_found", "empty"):
            return None
    return res


# ------------------------------------------------------------------- árvore
def _parse_ls_tree(output: str) -> list[TreeEntry]:
    """Parser de ``git ls-tree -r -z``: só blobs (arquivos e symlinks).

    Diretórios não aparecem com -r; submódulos (160000 commit) são excluídos.
    """
    entries = []
    for rec in output.split("\0"):
        if not rec or "\t" not in rec:
            continue
        meta, path = rec.split("\t", 1)
        parts = meta.split()
        if len(parts) != 3:
            continue
        mode, typ, sha = parts
        if typ != "blob" or mode not in BLOB_MODES:
            continue
        entries.append(TreeEntry(mode=mode, sha=sha, path=path))
    return entries


def list_tree(clone: Path, sha: str) -> list[TreeEntry]:
    """Blobs da árvore do commit ``sha`` (fetch preguiçoso das trees no tree:0)."""
    out = _run_git_retry(["ls-tree", "-r", "-z", sha], cwd=clone,
                         timeout=TIMEOUT_LS_TREE)
    return _parse_ls_tree(out)


# ---------------------------------------------------------------- verificação
def _probe_data(repo_cache_dir: Path, probe: str):
    payload = _read_json(repo_cache_dir / f"{probe}.json")
    if not payload:
        return None
    return payload.get("data")


def verify_against_v1(repo_cache_dir: Path, tree: list[TreeEntry]) -> dict[str, dict]:
    """Todo blob positivo em v1 deve existir com o mesmo sha na árvore de época.

    Sondagens com data nula (404 em v1) ou arquivo ausente são puladas —
    negativos não têm o que verificar. O sha do endpoint ``contents`` é o
    sha do blob git, comparável diretamente. Retorna
    {probe: {"path", "v1_sha", "epoch_sha", "ok"}}; para diretórios
    (``workflows``) ``ok`` exige que todos os arquivos listados batam e
    ``files`` detalha cada um.
    """
    by_path = {e.path: e.sha for e in tree}
    out: dict[str, dict] = {}

    def check(entry: dict) -> dict:
        path = entry.get("path")
        v1_sha = entry.get("sha")
        epoch_sha = by_path.get(path)
        return {"path": path, "v1_sha": v1_sha, "epoch_sha": epoch_sha,
                "ok": bool(v1_sha) and epoch_sha == v1_sha}

    for probe in VERIFY_FILE_PROBES:
        data = _probe_data(repo_cache_dir, probe)
        if not isinstance(data, dict) or not data.get("sha"):
            continue
        out[probe] = check(data)

    for probe in VERIFY_DIR_PROBES:
        data = _probe_data(repo_cache_dir, probe)
        if not isinstance(data, list):
            continue
        files = [check(e) for e in data
                 if isinstance(e, dict) and e.get("type") in ("file", "symlink")]
        out[probe] = {"path": f".github/{probe}", "v1_sha": None, "epoch_sha": None,
                      "ok": all(f["ok"] for f in files), "n_files": len(files),
                      "files": files}
    return out


# --------------------------------------------------------------------- driver
def _tree_payload(sha: str, tree: list[TreeEntry]) -> dict:
    return {"sha": sha, "entries": [asdict(e) for e in tree],
            "n_blobs": len(tree),
            "n_symlinks": sum(1 for e in tree if e.mode == SYMLINK_MODE),
            "fetched_at": _utcnow(), "catalog_version": CATALOG_VERSION}


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False))
    tmp.replace(path)


def _tree_file(v2_dir: Path, prefix: str, sha: str) -> Path:
    return v2_dir / f"{prefix}tree_paths_{sha[:12]}.json"


def _artifacts_complete(v2_dir: Path) -> dict | None:
    """epoch_commit.json (+ árvore quando ok) e org_epoch_commit.json presentes."""
    epoch = _read_json(v2_dir / "epoch_commit.json")
    if not epoch or not (v2_dir / "org_epoch_commit.json").exists():
        return None
    if epoch.get("status") == "ok" and not _tree_file(v2_dir, "", epoch["sha"]).exists():
        return None
    org = _read_json(v2_dir / "org_epoch_commit.json") or {}
    if org.get("status") == "ok" and not _tree_file(v2_dir, "org_", org["sha"]).exists():
        return None
    return epoch


def ensure_epoch_artifacts(repo: str, cache_root: Path, workdir: Path,
                           force: bool = False, keep: bool = False) -> dict:
    """Idempotente: resolve época + árvore do repo e de ``{owner}/.github``.

    Escreve em ``cache_root/<owner>__<repo>/v2/``: ``epoch_commit.json``,
    ``tree_paths_<sha12>.json``, ``org_epoch_commit.json`` (ou
    ``{"status": "absent"}``), ``org_tree_paths_<sha12>.json``. Com os
    arquivos presentes e ``force=False`` apenas lê (nenhum git). O clone em
    ``workdir/<owner>__<repo>/`` é removido ao final, salvo ``keep=True``.
    Retorna o dicionário de ``epoch_commit.json``.
    """
    owner, name = repo.split("/", 1)
    repo_cache = cache_root / f"{owner}__{name}"
    v2_dir = repo_cache / "v2"
    if not force:
        cached = _artifacts_complete(v2_dir)
        if cached is not None:
            return cached

    cutoff, cutoff_source = v1_probe_cutoff(repo_cache)
    branch = v1_default_branch(repo_cache)
    wd = workdir / f"{owner}__{name}"
    shutil.rmtree(wd, ignore_errors=True)
    wd.mkdir(parents=True, exist_ok=True)
    try:
        # --- repositório -----------------------------------------------------
        res = resolve_epoch(repo, branch, cutoff, wd, cutoff_source)
        verification: dict = {}
        epoch_status = "unreachable"
        if res.status == "ok":
            try:
                tree = list_tree(wd / "clone", res.sha)
            except GitError as e:
                # commit resolvido, árvore inobtenível (fetch preguiçoso das
                # trees falhou após retry): sem árvore não há medição v2
                res.status, res.error = "unreachable", f"ls-tree: {e}"
            else:
                verification = verify_against_v1(repo_cache, tree)
                epoch_status = ("ok" if all(v["ok"] for v in verification.values())
                                else "unverified")
                _write(_tree_file(v2_dir, "", res.sha), _tree_payload(res.sha, tree))

        # --- {owner}/.github (herança) ----------------------------------------
        org_res = resolve_org(owner, cutoff, wd, cutoff_source)
        if org_res is None:
            org_payload = {"repo": f"{owner}/.github", "status": "absent",
                           "cutoff": _fmt(cutoff), "fetched_at": _utcnow(),
                           "catalog_version": CATALOG_VERSION}
        else:
            if org_res.status == "ok":
                try:
                    org_tree = list_tree(wd / "org", org_res.sha)
                except GitError as e:
                    org_res.status, org_res.error = "unreachable", f"ls-tree: {e}"
                else:
                    _write(_tree_file(v2_dir, "org_", org_res.sha),
                           _tree_payload(org_res.sha, org_tree))
            org_payload = {"repo": f"{owner}/.github", **asdict(org_res),
                           "fetched_at": _utcnow(), "catalog_version": CATALOG_VERSION}
        _write(v2_dir / "org_epoch_commit.json", org_payload)

        epoch = {"repo": repo, **asdict(res), "branch": branch,
                 "cutoff_probe": _cutoff_probe(repo_cache),
                 "verification": verification, "epoch_status": epoch_status,
                 "fetched_at": _utcnow(), "catalog_version": CATALOG_VERSION}
        _write(v2_dir / "epoch_commit.json", epoch)  # por último: marca de completude
        return epoch
    finally:
        if not keep:
            shutil.rmtree(wd, ignore_errors=True)
