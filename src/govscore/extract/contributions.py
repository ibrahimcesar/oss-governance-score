"""D2 (concentração de contribuições) e D4 (diversidade) via /contributors.

Limitações do endpoint (declarar no TCC): cobre até 500 contribuidores com
conta GitHub e conta commits do branch default em todo o histórico. Na fase
completa, D4 (janela de 12 meses) migra para GraphQL history(since:).
"""
from __future__ import annotations

import math

from govscore.github_client import GitHubClient


def extract_contributions(gh: GitHubClient, repo: str) -> dict:
    contributors = gh.get(repo, f"/repos/{repo}/contributors", "contributors",
                          params={"per_page": 100, "anon": "false"}) or []
    counts = sorted((c["contributions"] for c in contributors), reverse=True)
    total = sum(counts)
    if not counts or total == 0:
        return {"top1_share": 1.0, "top2_share": 1.0, "hhi": 1.0,
                "truck_factor": 1, "contributors_5plus": 0,
                "commit_entropy": 0.0, "n_contributors_listed": 0}

    shares = [c / total for c in counts]
    hhi = sum(s * s for s in shares)

    # truck factor aproximado: menor k cujo acumulado atinge 50% dos commits
    acc, tf = 0.0, 0
    for s in shares:
        acc += s
        tf += 1
        if acc >= 0.5:
            break

    # entropia de Shannon normalizada (H / H_max)
    h = -sum(s * math.log(s) for s in shares if s > 0)
    h_max = math.log(len(shares)) if len(shares) > 1 else 1.0
    entropy = h / h_max if h_max > 0 else 0.0

    return {
        "top1_share": shares[0],
        "top2_share": sum(shares[:2]),
        "hhi": hhi,
        "truck_factor": tf,
        "contributors_5plus": sum(1 for c in counts if c >= 5),
        "commit_entropy": entropy,
        "n_contributors_listed": len(counts),
    }
