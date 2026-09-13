"""D1 (artefatos de governança) e D5 (práticas de segurança)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from govscore.github_client import GitHubClient

# Instante do snapshot da extração completa (23–24/07/2026): âncora de toda
# janela temporal derivada de "agora". Fonte única após o catálogo v2 é
# `extract/patterns.py` (M1); enquanto esse módulo não existe no merge, o
# valor é definido aqui com o mesmo conteúdo. Decisão:
# docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md ("O que NÃO muda").
try:  # fonte única após o merge do catálogo v2
    from govscore.extract.patterns import SNAPSHOT_UTC
except ImportError:  # patterns.py ainda não integrado
    SNAPSHOT_UTC = datetime(2026, 7, 24, 23, 59, 59, tzinfo=timezone.utc)

RELEASE_WINDOW_DAYS = 365


def release_cutoff(snapshot: datetime = SNAPSHOT_UTC) -> datetime:
    """Início da janela de releases (12 meses) ancorado no snapshot.

    Antes do reparo v2 o corte era `datetime.now() − 365 d`: reproduzia v1
    apenas enquanto executado em julho de 2026 e deslocaria silenciosamente
    `releases_12m` de 26 repositórios em qualquer re-execução posterior.
    Com a constante, o corte é 2025-07-24T23:59:59Z em toda re-execução.
    """
    if snapshot.tzinfo is None:
        snapshot = snapshot.replace(tzinfo=timezone.utc)
    return snapshot - timedelta(days=RELEASE_WINDOW_DAYS)


# FUNDING.yml: no repo (.github/ ou raiz) ou herdado de {owner}/.github
FUNDING_PATHS = [
    ("funding_yml_github", ".github/FUNDING.yml"),
    ("funding_yml", "FUNDING.yml"),
]


def has_funding(gh: GitHubClient, repo: str) -> tuple[bool, bool]:
    """Retorna (presente, herdado de {owner}/.github)."""
    for key, path in FUNDING_PATHS:
        if gh.get(repo, f"/repos/{repo}/contents/{path}", key) is not None:
            return True, False
    org = f"{repo.split('/')[0]}/.github"
    for key, path in FUNDING_PATHS:
        if gh.get(org, f"/repos/{org}/contents/{path}", key) is not None:
            return True, True
    return False, False


def extract_artifacts(gh: GitHubClient, repo: str) -> dict:
    """D1 — presença de artefatos via community profile + contents API."""
    profile = gh.get(repo, f"/repos/{repo}/community/profile", "community_profile") or {}
    files = profile.get("files") or {}

    codeowners = gh.get(repo, f"/repos/{repo}/contents/.github/CODEOWNERS", "codeowners")
    governance = gh.get(repo, f"/repos/{repo}/contents/GOVERNANCE.md", "governance")
    funding, funding_inherited = has_funding(gh, repo)

    out = {
        "readme": files.get("readme") is not None,
        "contributing": files.get("contributing") is not None,
        "code_of_conduct": (files.get("code_of_conduct") is not None
                            or files.get("code_of_conduct_file") is not None),
        "license": files.get("license") is not None,
        "issue_template": files.get("issue_template") is not None,
        "pull_request_template": files.get("pull_request_template") is not None,
        "codeowners": codeowners is not None,
        "governance": governance is not None,
        "funding": funding,
        "health_percentage": profile.get("health_percentage"),  # verificação cruzada
    }
    if funding_inherited:
        out["funding_inherited"] = True
    return out


# community/profile NÃO expõe a security policy (só readme, contributing,
# code_of_conduct, license e templates) — verificar convenções de caminho.
SECURITY_POLICY_PATHS = [
    ("security_md", "SECURITY.md"),
    ("security_md_github", ".github/SECURITY.md"),
    ("security_md_docs", "docs/SECURITY.md"),
]


def has_security_policy(gh: GitHubClient, repo: str) -> tuple[bool, bool]:
    """Retorna (presente, herdada). Herança: {owner}/.github, como no backend git."""
    for key, path in SECURITY_POLICY_PATHS:
        if gh.get(repo, f"/repos/{repo}/contents/{path}", key) is not None:
            return True, False
    org = f"{repo.split('/')[0]}/.github"
    if gh.get(org, f"/repos/{org}/contents/SECURITY.md", "security_md") is not None:
        return True, True
    return False, False


def release_metrics(releases: list[dict], cutoff) -> tuple[int, float | None]:
    """(nº de releases nos 12m, share delas com notas não vazias).

    Share é None quando não há release na janela — prática não observável,
    omitida da média (nunca imputada como zero).
    """
    recent = [
        r for r in releases
        if r.get("published_at")
        and datetime.fromisoformat(r["published_at"].replace("Z", "+00:00")) >= cutoff
    ]
    if not recent:
        return 0, None
    with_notes = sum(1 for r in recent if (r.get("body") or "").strip())
    return len(recent), with_notes / len(recent)


def extract_security(gh: GitHubClient, repo: str,
                     snapshot: datetime = SNAPSHOT_UTC) -> dict:
    """D5 — política de segurança, CI e automação de dependências, releases.

    `snapshot` ancora a janela de 12 meses das releases (nunca `now()`):
    o mesmo cache de julho produz o mesmo `releases_12m` em qualquer data.
    """
    policy, inherited = has_security_policy(gh, repo)

    workflows = gh.get(repo, f"/repos/{repo}/contents/.github/workflows", "workflows")
    dependabot = gh.get(repo, f"/repos/{repo}/contents/.github/dependabot.yml", "dependabot")
    releases = gh.get(repo, f"/repos/{repo}/releases", "releases",
                      params={"per_page": 30}) or []

    releases_12m, notes_share = release_metrics(releases, release_cutoff(snapshot))

    out = {
        "security_policy": policy,
        "ci_configured": bool(workflows),
        "dependency_automation": dependabot is not None,
        "releases_12m": releases_12m,
        "release_notes_share": notes_share,
    }
    if inherited:
        out["security_policy_inherited"] = True
    return out
