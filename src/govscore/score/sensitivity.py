"""Análise de sensibilidade dos pesos (item 6; plano §4.3).

Três verificações sobre os sub-scores já extraídos (os pesos são a única
coisa variada — limiares de normalização NÃO são tocados):

1. Pesos iguais (0,20 em cada dimensão) vs pesos da literatura → ρ de
   Spearman entre os rankings.
2. Perturbação: cada peso ±25%, renormalizando os demais → ρ de cada
   variante vs base; W de Kendall entre todas as variantes.
3. Leave-one-dimension-out: score sem uma dimensão por vez → ρ vs base.

Critério de sucesso (DSR, plano §6.3): ρ ≥ 0,8 entre variantes de pesos.
Repositórios com score None em uma variante são excluídos par a par.
"""
from __future__ import annotations

import statistics
from typing import Iterable

from govscore.score.scoring import compute_score

DIMENSIONS = ("artifacts", "distribution", "responsiveness",
              "diversity", "security")


# ------------------------------------------------------------- variantes
def equal_weights() -> dict:
    return {d: 1.0 / len(DIMENSIONS) for d in DIMENSIONS}


def perturbed_weights(base: dict, dim: str, factor: float) -> dict:
    """Multiplica o peso de `dim` por `factor` e renormaliza para Σ=1."""
    w = dict(base)
    w[dim] = base[dim] * factor
    total = sum(w.values())
    return {d: v / total for d, v in w.items()}


def lodo_weights(base: dict, drop: str) -> dict:
    """Remove uma dimensão; os pesos restantes são renormalizados."""
    w = {d: v for d, v in base.items() if d != drop}
    total = sum(w.values())
    return {d: v / total for d, v in w.items()}


def scores_for(subscores_list: list[dict], weights: dict) -> list[float | None]:
    """compute_score por repositório (renormalização de faltantes idêntica
    à do score oficial)."""
    return [compute_score({d: s.get(d) for d in weights}, weights)
            for s in subscores_list]


# ----------------------------------------------------------- estatística
def spearman(xs: Iterable[float | None], ys: Iterable[float | None]) -> float | None:
    """ρ de Spearman com exclusão par a par de None."""
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    from scipy.stats import spearmanr
    rho = spearmanr([p[0] for p in pairs], [p[1] for p in pairs]).statistic
    return float(rho)


def _ranks(xs: list[float]) -> list[float]:
    """Ranks médios (empates recebem a média das posições)."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        mean_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    return ranks


def kendalls_w(variants: list[list[float]]) -> float | None:
    """W de Kendall entre m rankings dos mesmos n itens (sem correção de
    empates — scores contínuos raramente empatam; declarado no relatório)."""
    m = len(variants)
    n = len(variants[0]) if variants else 0
    if m < 2 or n < 2:  # n=1 zeraria o denominador (n³−n)
        return None
    rank_sums = [0.0] * n
    for v in variants:
        for i, r in enumerate(_ranks(v)):
            rank_sums[i] += r
    mean = sum(rank_sums) / n
    s = sum((r - mean) ** 2 for r in rank_sums)
    return float(12 * s / (m * m * (n ** 3 - n)))


# --------------------------------------------------------------- análise
def analyze(subscores_list: list[dict], base_weights: dict,
            factor: float = 0.25) -> dict:
    base = scores_for(subscores_list, base_weights)

    out: dict = {"n": len(subscores_list), "base_weights": base_weights}
    out["equal_vs_base"] = spearman(base, scores_for(subscores_list,
                                                     equal_weights()))

    out["factor"] = factor
    pert: dict[str, float | None] = {}
    variant_scores: list[list[float]] = []
    for dim in DIMENSIONS:
        for factor_dir, tag in ((1 + factor, "+"), (1 - factor, "-")):
            w = perturbed_weights(base_weights, dim, factor_dir)
            scores = scores_for(subscores_list, w)
            pert[f"{dim} {tag}{factor:.0%}"] = spearman(base, scores)
            variant_scores.append(scores)
    out["perturbation"] = pert
    valid = [v for v in pert.values() if v is not None]
    out["perturbation_min"] = min(valid) if valid else None
    out["perturbation_mean"] = statistics.mean(valid) if valid else None

    # W de Kendall sobre base + variantes, apenas repos sem None em nenhuma
    all_variants = [base] + variant_scores
    keep = [i for i in range(len(base))
            if all(v[i] is not None for v in all_variants)]
    out["kendalls_w"] = kendalls_w([[v[i] for i in keep] for v in all_variants])
    out["kendalls_w_n"] = len(keep)

    lodo: dict[str, float | None] = {}
    for dim in DIMENSIONS:
        lodo[dim] = spearman(base, scores_for(
            subscores_list, lodo_weights(base_weights, dim)))
    out["lodo"] = lodo
    return out


def _f(v: float | None) -> str:
    return f"{v:.3f}" if v is not None else "—"


def report(res: dict) -> str:
    """Relatório PT-BR para results/sensibilidade.md."""
    ok = "✅" if (res["perturbation_min"] or 0) >= 0.8 else "⚠️"
    pct = f"{res.get('factor', 0.25):.0%}"
    n_var = len(res["perturbation"])
    lines = [
        "# Análise de sensibilidade dos pesos (item 6; plano §4.3)", "",
        f"n = {res['n']} repositórios; pesos base da literatura: "
        + ", ".join(f"{d} {w:.2f}" for d, w in res["base_weights"].items()),
        "",
        "## Resultados", "",
        f"- **Pesos iguais vs literatura:** ρ = {_f(res['equal_vs_base'])}",
        f"- **Perturbação ±{pct}:** ρ mínimo = {_f(res['perturbation_min'])}, "
        f"médio = {_f(res['perturbation_mean'])} {ok} (critério DSR: ≥ 0,8)",
        f"- **W de Kendall** (base + {n_var} variantes, n = {res['kendalls_w_n']} "
        f"sem faltantes; sem correção de empates): {_f(res['kendalls_w'])}",
        "",
        f"## Perturbação por dimensão (ρ vs base)", "",
        "| variante | ρ |", "|---|---|",
    ]
    lines += [f"| {k} | {_f(v)} |" for k, v in res["perturbation"].items()]
    lines += ["", "## Leave-one-dimension-out (ρ vs base)", "",
              "| dimensão removida | ρ |", "|---|---|"]
    lines += [f"| {k} | {_f(v)} |" for k, v in res["lodo"].items()]
    valid_lodo = {d: v for d, v in res["lodo"].items() if v is not None}
    if valid_lodo:
        lodo_min = min(valid_lodo, key=valid_lodo.get)
        lines += [
            "",
            f"A dimensão cuja remoção mais altera o ranking é **{lodo_min}** "
            f"(ρ = {_f(valid_lodo[lodo_min])}). Interpretação: é a dimensão "
            "menos redundante em relação às demais neste dataset — sua "
            "contribuição ao ranking é a que menos se recupera a partir das "
            "outras —, efeito parcialmente confundido com o peso da dimensão "
            "no índice. O desenho não permite concluir que seja a \"mais "
            "informativa\" sobre governança: uma dimensão ruidosa também "
            "deslocaria o ranking ao ser removida.", ""]
    return "\n".join(lines)
