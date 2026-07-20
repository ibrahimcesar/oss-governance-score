"""Agregação: métricas normalizadas → sub-scores por dimensão → score 0–100.

Sub-score de dimensão = média simples das métricas disponíveis (métricas
faltantes são omitidas da média, nunca imputadas como zero).
Score = 100 × Σ w_d × sub-score_d, com pesos renormalizados sobre as
dimensões disponíveis.
"""
from __future__ import annotations

from govscore.score.normalize import binary, linear


def _mean(values: list[float | None]) -> float | None:
    xs = [v for v in values if v is not None]
    return sum(xs) / len(xs) if xs else None


def compute_subscores(metrics: dict, cfg: dict) -> dict:
    d1 = _mean([binary(metrics["artifacts"].get(item))
                for item in cfg["artifacts"]["items"]])

    dist_cfg = cfg["distribution"]
    d2 = _mean([
        linear(metrics["distribution"].get("top1_share"),
               dist_cfg["top1_share"]["best"], dist_cfg["top1_share"]["worst"]),
        linear(metrics["distribution"].get("hhi"),
               dist_cfg["hhi"]["best"], dist_cfg["hhi"]["worst"]),
        linear(metrics["distribution"].get("truck_factor"),
               dist_cfg["truck_factor"]["best"], dist_cfg["truck_factor"]["worst"]),
    ])

    resp_cfg = cfg["responsiveness"]
    d3 = _mean([
        linear(metrics["responsiveness"].get("median_first_response_hours"),
               resp_cfg["median_first_response_hours"]["best"],
               resp_cfg["median_first_response_hours"]["worst"]),
        linear(metrics["responsiveness"].get("median_pr_merge_hours"),
               resp_cfg["median_pr_merge_hours"]["best"],
               resp_cfg["median_pr_merge_hours"]["worst"]),
        linear(metrics["responsiveness"].get("pr_merge_ratio"),
               resp_cfg["pr_merge_ratio"]["best"], resp_cfg["pr_merge_ratio"]["worst"]),
        linear(metrics["responsiveness"].get("pr_review_coverage"),
               resp_cfg["pr_review_coverage"]["best"],
               resp_cfg["pr_review_coverage"]["worst"]),
    ])

    div_cfg = cfg["diversity"]
    d4 = _mean([
        linear(metrics["distribution"].get("contributors_5plus"),
               div_cfg["contributors_5plus"]["best"], div_cfg["contributors_5plus"]["worst"]),
        linear(metrics["distribution"].get("commit_entropy"),
               div_cfg["commit_entropy"]["best"], div_cfg["commit_entropy"]["worst"]),
        linear(metrics["distribution"].get("elephant_factor"),
               div_cfg["elephant_factor"]["best"], div_cfg["elephant_factor"]["worst"]),
        linear(metrics["distribution"].get("contributor_retention"),
               div_cfg["contributor_retention"]["best"],
               div_cfg["contributor_retention"]["worst"]),
    ])

    sec_cfg = cfg["security"]
    d5 = _mean(
        [binary(metrics["security"].get(item)) for item in sec_cfg["items"]]
        + [linear(metrics["security"].get("releases_12m"),
                  sec_cfg["releases_12m"]["best"], sec_cfg["releases_12m"]["worst"]),
           linear(metrics["security"].get("release_notes_share"),
                  sec_cfg["release_notes_share"]["best"],
                  sec_cfg["release_notes_share"]["worst"])]
    )

    return {"artifacts": d1, "distribution": d2, "responsiveness": d3,
            "diversity": d4, "security": d5}


def compute_score(subscores: dict, weights: dict) -> float | None:
    available = {d: s for d, s in subscores.items() if s is not None}
    if not available:
        return None
    total_w = sum(weights[d] for d in available)
    return 100.0 * sum(weights[d] * s for d, s in available.items()) / total_w
