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

# Padrões ANCORADOS ao início do caminho (achado do piloto: re.search sem
# âncora casava caminhos aninhados — vendor/**/.circleci/, staging/**/docs/
# security.md — inflando D1/D5 em monorepos como kubernetes/kubernetes).
ARTIFACT_PATTERNS = {
    "readme": r"^readme(\.[a-z]+)?$",
    "contributing": r"^(\.github/|docs/)?contributing(\.[a-z]+)?$",
    "code_of_conduct": r"^(\.github/|docs/)?code[-_]of[-_]conduct(\.[a-z]+)?$",
    "license": r"^(licen[sc]e|copying)(\.[a-z]+)?$",
    "issue_template": r"^\.github/issue_template",
    "pull_request_template": r"^(\.github/|docs/)?pull_request_template(\.[a-z]+)?$",
    "codeowners": r"^(\.github/|docs/)?codeowners$",
    "governance": r"^(\.github/|docs/)?governance(\.[a-z]+)?$",
    "funding": r"^(\.github/)?funding\.ya?ml$",
}

# Provedores genéricos: e-mail conta por PESSOA, não por "organização"
# (prática GrimoireLab para o Elephant Factor).
GENERIC_DOMAINS = {
    "gmail.com", "googlemail.com", "hotmail.com", "outlook.com", "live.com",
    "msn.com", "yahoo.com", "icloud.com", "me.com", "mac.com",
    "protonmail.com", "proton.me", "gmx.de", "gmx.net", "fastmail.com",
    "qq.com", "163.com", "126.com", "mail.ru", "yandex.ru",
    "users.noreply.github.com", "localhost",
}

SECURITY_PATTERNS = {
    "security_policy": r"^(\.github/|docs/)?security(\.[a-z]+)?$",
    "ci_configured": r"^\.github/workflows/.+\.ya?ml$|^\.travis\.yml$|^\.circleci/",
    "dependency_automation": r"^\.github/dependabot\.ya?ml$|^(\.github/)?renovate\.json5?$",
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
                       "pull_request_template", "governance", "funding"]
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
                   "--format=%ae%x09%at", cwd=dest)
        counts: Counter = Counter()
        email_times: dict[str, list[int]] = {}
        for line in log.splitlines():
            if "\t" not in line:
                continue
            email, ts = line.rsplit("\t", 1)
            email = email.strip().lower()
            if not email:
                continue
            counts[email] += 1
            email_times.setdefault(email, []).append(int(ts))
        dist = _distribution_metrics(counts)
        dist["elephant_factor"] = elephant_factor(counts)
        dist["contributor_retention"] = contributor_retention(email_times)

    return {"artifacts": artifacts, "security": security, "distribution": dist,
            "responsiveness": {"median_issue_close_hours": None,
                               "median_pr_merge_hours": None,
                               "pr_merge_ratio": None},
            "window": window, "backend": "git"}


def elephant_factor(email_counts: Counter) -> int | None:
    """CHAOSS Elephant Factor: mín. de organizações cujos commits somam ≥50%.

    Organização ≈ domínio do e-mail; e-mails de provedores genéricos contam
    individualmente (uma pessoa = uma unidade).
    """
    units: Counter = Counter()
    for email, n in email_counts.items():
        domain = email.rsplit("@", 1)[-1] if "@" in email else ""
        unit = domain if domain and domain not in GENERIC_DOMAINS else email
        units[unit] += n
    total = sum(units.values())
    if total == 0:
        return None
    acc, ef = 0, 0
    for _, n in units.most_common():
        acc += n
        ef += 1
        if acc >= total / 2:
            return ef
    return ef


def contributor_retention(email_times: dict[str, list[int]],
                          now_ts: float | None = None,
                          window_days: int = 365) -> float | None:
    """Share dos autores ativos na 1ª metade da janela que seguem na 2ª.

    Metades ancoradas na data de extração (Constantinou & Mens, 2017).
    None se a 1ª metade não tem autores (janela curta ou repo dormente).
    """
    import time
    now_ts = time.time() if now_ts is None else now_ts
    start = now_ts - window_days * 86400
    half = now_ts - window_days * 86400 / 2
    first = {e for e, ts in email_times.items() if any(start <= t < half for t in ts)}
    if not first:
        return None
    second = {e for e, ts in email_times.items() if any(t >= half for t in ts)}
    return len(first & second) / len(first)


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
