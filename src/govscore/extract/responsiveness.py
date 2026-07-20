"""D3 — responsividade da manutenção.

REST (piloto): tempo até fechamento de issues, tempo/razão de merge de PRs.
GraphQL (fase completa, decisão 2026-07-19): tempo até a PRIMEIRA RESPOSTA em
issues (métrica CHAOSS Time to First Response) e cobertura de revisão nos PRs
merged (CHAOSS Review Coverage). `median_issue_close_hours` segue extraída
para comparabilidade com o piloto, mas fora do score.
"""
from __future__ import annotations

import statistics
from datetime import datetime

from govscore.github_client import GitHubClient

GQL_RESPONSIVENESS = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    issues(states: CLOSED, first: 50,
           orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        createdAt
        author { login }
        comments(first: 10) {
          nodes { createdAt author { login __typename } }
        }
      }
    }
    pullRequests(states: MERGED, first: 50,
                 orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        reviews(first: 1) { totalCount }
      }
    }
  }
}
"""


def _hours(a: str, b: str) -> float:
    ta = datetime.fromisoformat(a.replace("Z", "+00:00"))
    tb = datetime.fromisoformat(b.replace("Z", "+00:00"))
    return (tb - ta).total_seconds() / 3600.0


def is_bot(author: dict | None) -> bool:
    if not author:
        return False
    login = (author.get("login") or "").lower()
    return (author.get("__typename") == "Bot"
            or login.endswith("bot") or login.endswith("[bot]"))


def first_response_hours(issue: dict) -> float | None:
    """Horas até o 1º comentário que não é do autor da issue nem de bot.

    None se não houver resposta humana entre os comentários amostrados —
    a issue é OMITIDA da mediana (ausência de observação, não zero).
    """
    author = (issue.get("author") or {}).get("login")
    for c in (issue.get("comments") or {}).get("nodes") or []:
        c_author = c.get("author") or {}
        if c_author.get("login") == author or is_bot(c_author):
            continue
        return _hours(issue["createdAt"], c["createdAt"])
    return None


def review_coverage(pr_nodes: list[dict]) -> float | None:
    """Share dos PRs merged amostrados com ≥1 review."""
    if not pr_nodes:
        return None
    reviewed = sum(1 for p in pr_nodes
                   if ((p.get("reviews") or {}).get("totalCount") or 0) >= 1)
    return reviewed / len(pr_nodes)


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

    owner, name = repo.split("/")
    gql = gh.graphql(repo, GQL_RESPONSIVENESS,
                     {"owner": owner, "name": name}, "gql_responsiveness") or {}
    repository = gql.get("repository") or {}
    issue_nodes = (repository.get("issues") or {}).get("nodes") or []
    pr_nodes = (repository.get("pullRequests") or {}).get("nodes") or []

    responses = [h for h in (first_response_hours(i) for i in issue_nodes)
                 if h is not None]

    return {
        "median_first_response_hours": statistics.median(responses) if responses else None,
        "pr_review_coverage": review_coverage(pr_nodes),
        "median_issue_close_hours": statistics.median(issue_close) if issue_close else None,
        "median_pr_merge_hours": statistics.median(pr_merge) if pr_merge else None,
        "pr_merge_ratio": len(merged) / len(prs) if prs else None,
        "n_issues_sampled": len(pure_issues),
        "n_prs_sampled": len(prs),
        "n_first_responses": len(responses),
    }
