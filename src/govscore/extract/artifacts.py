"""D1 (artefatos de governança) e D5 (práticas de segurança)."""
from __future__ import annotations

from govscore.github_client import GitHubClient


def extract_artifacts(gh: GitHubClient, repo: str) -> dict:
    """D1 — presença de artefatos via community profile + contents API."""
    profile = gh.get(repo, f"/repos/{repo}/community/profile", "community_profile") or {}
    files = profile.get("files") or {}

    codeowners = gh.get(repo, f"/repos/{repo}/contents/.github/CODEOWNERS", "codeowners")
    governance = gh.get(repo, f"/repos/{repo}/contents/GOVERNANCE.md", "governance")

    return {
        "readme": files.get("readme") is not None,
        "contributing": files.get("contributing") is not None,
        "code_of_conduct": (files.get("code_of_conduct") is not None
                            or files.get("code_of_conduct_file") is not None),
        "license": files.get("license") is not None,
        "issue_template": files.get("issue_template") is not None,
        "pull_request_template": files.get("pull_request_template") is not None,
        "codeowners": codeowners is not None,
        "governance": governance is not None,
        "health_percentage": profile.get("health_percentage"),  # verificação cruzada
    }


def extract_security(gh: GitHubClient, repo: str) -> dict:
    """D5 — política de segurança, CI e automação de dependências, releases."""
    profile = gh.get(repo, f"/repos/{repo}/community/profile", "community_profile") or {}
    files = profile.get("files") or {}

    workflows = gh.get(repo, f"/repos/{repo}/contents/.github/workflows", "workflows")
    dependabot = gh.get(repo, f"/repos/{repo}/contents/.github/dependabot.yml", "dependabot")
    releases = gh.get(repo, f"/repos/{repo}/releases", "releases",
                      params={"per_page": 30}) or []

    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    releases_12m = sum(
        1 for r in releases
        if r.get("published_at")
        and datetime.fromisoformat(r["published_at"].replace("Z", "+00:00")) >= cutoff
    )

    return {
        "security_policy": files.get("security") is not None
                           or files.get("security_policy") is not None,
        "ci_configured": bool(workflows),
        "dependency_automation": dependabot is not None,
        "releases_12m": releases_12m,
    }
