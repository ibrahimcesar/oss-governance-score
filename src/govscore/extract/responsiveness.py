"""D3 — responsividade da manutenção.

Versão piloto (REST, econômica em chamadas): tempo até fechamento das últimas
issues fechadas e tempo de merge dos últimos PRs fechados.
Fase completa: migrar para GraphQL e medir tempo até a PRIMEIRA RESPOSTA
(métrica CHAOSS), que captura melhor a atenção do mantenedor.
"""
from __future__ import annotations

import statistics
from datetime import datetime

from govscore.github_client import GitHubClient


def _hours(a: str, b: str) -> float:
    ta = datetime.fromisoformat(a.replace("Z", "+00:00"))
    tb = datetime.fromisoformat(b.replace("Z", "+00:00"))
    return (tb - ta).total_seconds() / 3600.0


def extract_responsiveness(gh: GitHubClient, repo: str, sample: int = 50) -> dict:
    issues = gh.get(repo, f"/repos/{repo}/issues", "issues_closed",
                    params={"state": "closed", "per_page": sample,
                            "sort": "updated", "direction": "desc"}) or []
    # o endpoint /issues inclui PRs — separá-los
    pure_issues = [i for i in issues if "pull_request" not in i]

    prs = gh.get(repo, f"/repos/{repo}/pulls", "pulls_closed",
                 params={"state": "closed", "per_page": sample,
                         "sort": "updated", "direction": "desc"}) or []

    issue_close = [_hours(i["created_at"], i["closed_at"])
                   for i in pure_issues if i.get("closed_at")]
    merged = [p for p in prs if p.get("merged_at")]
    pr_merge = [_hours(p["created_at"], p["merged_at"]) for p in merged]

    return {
        "median_issue_close_hours": statistics.median(issue_close) if issue_close else None,
        "median_pr_merge_hours": statistics.median(pr_merge) if pr_merge else None,
        "pr_merge_ratio": len(merged) / len(prs) if prs else None,
        "n_issues_sampled": len(pure_issues),
        "n_prs_sampled": len(prs),
    }
