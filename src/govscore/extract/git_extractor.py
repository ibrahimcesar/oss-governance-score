"""Backend de extração via git (sem API) — D1, D2, D4 e parte de D5.

Motivação metodológica: métricas de artefatos e de distribuição de commits
podem ser computadas diretamente do repositório git, sem depender da API do
GitHub — o que reduz o acoplamento à plataforma e reforça a reprodutibilidade.
D3 (responsividade em issues/PRs) e releases existem apenas na plataforma e
continuam no backend de API (requer GITHUB_TOKEN).

Janela temporal: clone raso com --shallow-since=12 meses, alinhado ao critério
de atividade recente do método (seção 3.2.2 do TCC).
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

WINDOW = "12 months ago"

ARTIFACT_PATTERNS = {
    "readme": r"(^|/)readme(\.[a-z]+)?$",
    "contributing": r"(^|\.github/|docs/)contributing(\.[a-z]+)?$",
    "code_of_conduct": r"(^|\.github/|docs/)code[-_]of[-_]conduct(\.[a-z]+)?$",
    "license": r"(^|/)(licen[sc]e|copying)(\.[a-z]+)?$",
    "issue_template": r"\.github/issue_template|\.github/ISSUE_TEMPLATE",
    "pull_request_template": r"(^|\.github/|docs/)pull_request_template(\.[a-z]+)?$",
    "codeowners": r"(^|\.github/|docs/)codeowners$",
    "governance": r"(^|\.github/|docs/)governance(\.[a-z]+)?$",
}

SECURITY_PATTERNS = {
    "security_policy": r"(^|\.github/|docs/)security(\.[a-z]+)?$",
    "ci_configured": r"\.github/workflows/.+\.ya?ml$|\.travis\.yml$|\.circleci/",
    "dependency_automation": r"\.github/dependabot\.ya?ml$|renovate\.json5?$|\.github/renovate\.json5?$",
}


def _git(*args: str, cwd: Path | None = None) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                       timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])}: {r.stderr.strip()[:200]}")
    return r.stdout


def _tree_paths(url: str, dest: Path, *clone_args: str) -> list[str]:
    _git("clone", "--quiet", "--no-checkout", "--single-branch",
         *clone_args, url, str(dest))
    tree = _git("ls-tree", "-r", "HEAD", "--name-only", cwd=dest)
    return [p.lower() for p in tree.splitlines()]


def _present(paths: list[str], pattern: str) -> bool:
    rx = re.compile(pattern, re.IGNORECASE)
    return any(rx.search(p) for p in paths)


def extract_via_git(repo: str, window: str = WINDOW) -> dict:
    owner = repo.split("/")[0]
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "clone"
        paths = _tree_paths(f"https://github.com/{repo}.git", dest,
                            f"--shallow-since={window}")

        # --- D1/D5: presença de arquivos na árvore do HEAD -------------------
        artifacts = {k: _present(paths, v) for k, v in ARTIFACT_PATTERNS.items()}
        security = {k: _present(paths, v) for k, v in SECURITY_PATTERNS.items()}

        # Fallback: default community health files herdados do repo {owner}/.github
        # (invisíveis no clone do repositório individual; a API community/profile
        #  os contabiliza — sem isto o backend git subestimaria D1/D5).
        inheritable = ["contributing", "code_of_conduct", "issue_template",
                       "pull_request_template", "governance"]
        needs_org = ([k for k in inheritable if not artifacts[k]]
                     + (["security_policy"] if not security["security_policy"] else []))
        if needs_org:
            try:
                org_paths = _tree_paths(
                    f"https://github.com/{owner}/.github.git",
                    Path(tmp) / "org", "--depth", "1")
                for k in needs_org:
                    src = ARTIFACT_PATTERNS.get(k) or SECURITY_PATTERNS.get(k)
                    if _present(org_paths, src):
                        if k in artifacts:
                            artifacts[k] = True
                            artifacts[f"{k}_inherited"] = True
                        else:
                            security[k] = True
                            security[f"{k}_inherited"] = True
            except RuntimeError:
                pass  # organização sem repo .github

        security["releases_12m"] = None  # só via API (backend api)

        # --- D2/D4: distribuição de commits na janela ------------------------
        log = _git("log", "--no-merges", f"--since={window}",
                   "--format=%ae", cwd=dest)
        counts = Counter(e.strip().lower() for e in log.splitlines() if e.strip())
        dist = _distribution_metrics(counts)

    return {"artifacts": artifacts, "security": security, "distribution": dist,
            "responsiveness": {"median_issue_close_hours": None,
                               "median_pr_merge_hours": None,
                               "pr_merge_ratio": None},
            "window": window, "backend": "git"}


def _distribution_metrics(counts: Counter) -> dict:
    import math
    values = sorted(counts.values(), reverse=True)
    total = sum(values)
    if not values or total == 0:
        return {"top1_share": 1.0, "top2_share": 1.0, "hhi": 1.0,
                "truck_factor": 1, "contributors_5plus": 0,
                "commit_entropy": 0.0, "n_contributors_listed": 0,
                "n_commits_window": 0}
    shares = [v / total for v in values]
    acc, tf = 0.0, 0
    for s in shares:
        acc += s
        tf += 1
        if acc >= 0.5:
            break
    h = -sum(s * math.log(s) for s in shares if s > 0)
    h_max = math.log(len(shares)) if len(shares) > 1 else 1.0
    return {
        "top1_share": shares[0],
        "top2_share": sum(shares[:2]),
        "hhi": sum(s * s for s in shares),
        "truck_factor": tf,
        "contributors_5plus": sum(1 for v in values if v >= 5),
        "commit_entropy": h / h_max if h_max > 0 else 0.0,
        "n_contributors_listed": len(values),
        "n_commits_window": total,
    }
