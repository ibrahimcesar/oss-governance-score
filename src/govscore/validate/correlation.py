"""Correlações de validação (item 7; plano §6.2).

ρ de Spearman (ordinal, robusto a caudas pesadas do GitHub) entre o score e
cada indicador externo; α = 0,05 com correção de Holm–Bonferroni na família
de testes global. Pares com None são excluídos par a par (n reportado por
indicador). Análise por arquétipo (n=25) é EXPLORATÓRIA — poder apenas para
efeitos grandes — e não entra na família corrigida (declarar na 4.3).

Nota amostral: stars foi proxy de classificação na amostragem (§3.1), então
a correlação global score×stars é parcialmente estruturada pela
estratificação; a leitura por arquétipo é a mais limpa para esse indicador.
"""
from __future__ import annotations

from typing import Iterable

ARCHETYPES = ("federation", "stadium", "club", "toy")


def spearman_with_p(xs: Iterable[float | None],
                    ys: Iterable[float | None]) -> tuple[float | None, float | None, int]:
    """(ρ, p, nº de pares válidos), com exclusão par a par.

    ρ/p são None quando o teste não é realizável: n < 4 ou entrada constante
    (spearmanr devolve NaN — que jamais pode chegar à correção de Holm, onde
    max(running, nan) silenciosamente viraria p_adj = 0). O n de pares é
    sempre reportado, mesmo sem teste."""
    import math

    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None]
    n = len(pairs)
    if n < 4:
        return None, None, n
    from scipy.stats import spearmanr
    r = spearmanr([p[0] for p in pairs], [p[1] for p in pairs])
    if math.isnan(r.statistic) or math.isnan(r.pvalue):
        return None, None, n  # entrada constante — teste não realizável
    return float(r.statistic), float(r.pvalue), n


def holm_bonferroni(pvals: dict[str, float]) -> dict[str, float]:
    """p-valores ajustados (step-down de Holm), monotônicos e ≤ 1.
    NaN é rejeitado na entrada (defensivo — quebraria o max monotônico)."""
    import math
    if any(math.isnan(p) for p in pvals.values()):
        raise ValueError("p-valor NaN na família de testes")
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, (m - i) * p)
        adjusted[k] = min(1.0, running)
    return adjusted


def validate_correlations(rows: list[dict], indicators: list[str],
                          alpha: float = 0.05,
                          meta: dict | None = None) -> dict:
    """rows: [{score, archetype, <indicadores>...}] — família global corrigida
    por Holm–Bonferroni (apenas testes realizados) + tabelas exploratórias
    por arquétipo. `meta` (datas de snapshot etc.) é anexado ao resultado."""
    scores = [r.get("score") for r in rows]

    global_res: dict[str, dict] = {}
    pvals: dict[str, float] = {}
    MIN_N_FAMILY = 10  # p da aproximação t não é confiável abaixo disto
    for ind in indicators:
        rho, p, n = spearman_with_p(scores, [r.get(ind) for r in rows])
        in_family = p is not None and n >= MIN_N_FAMILY
        global_res[ind] = {"rho": rho, "p": p, "n": n, "in_family": in_family}
        if in_family:
            pvals[ind] = p
    adjusted = holm_bonferroni(pvals) if pvals else {}
    for ind, adj in adjusted.items():
        global_res[ind]["p_adj"] = adj
        global_res[ind]["significant"] = adj < alpha

    by_arch: dict[str, dict] = {}
    for arch in ARCHETYPES:
        sub = [r for r in rows if r.get("archetype") == arch]
        arch_res: dict[str, dict] = {}
        for ind in indicators:
            rho, p, n = spearman_with_p([r.get("score") for r in sub],
                                        [r.get(ind) for r in sub])
            arch_res[ind] = {"rho": rho, "p": p, "n": n}
        by_arch[arch] = arch_res

    # composição do subamostra de dependentes (ausência é ESTRUTURAL:
    # cobertura de ecossistema — declarar na 4.3)
    coverage: dict[str, dict] = {}
    for ind in indicators:
        with_data = [r for r in rows if r.get(ind) is not None]
        cov: dict = {"n": len(with_data)}
        if any("language" in r for r in rows):
            langs: dict[str, int] = {}
            for r in with_data:
                lg = (r.get("language") or "?").lower()
                langs[lg] = langs.get(lg, 0) + 1
            cov["languages"] = dict(sorted(langs.items()))
        coverage[ind] = cov

    return {"n_total": len(rows), "alpha": alpha, "indicators": indicators,
            "global": global_res, "by_archetype": by_arch,
            "coverage": coverage, "meta": meta or {}}


def _f(v: float | None, nd: int = 3) -> str:
    return f"{v:.{nd}f}" if v is not None else "—"


def report(res: dict) -> str:
    """Relatório PT-BR para results/validacao.md (seção 4.3 do TCC)."""
    m = len([i for i in res["global"].values() if i.get("in_family")])
    meta = res.get("meta") or {}
    lines = [
        "# Validação externa (item 7; plano §6)", "",
        f"n = {res['n_total']}; α = {res['alpha']} com correção de "
        f"Holm–Bonferroni na família global (m = {m} testes realizados).",
        "",
        "Cautelas de leitura (declarar na 4.3):",
        "- frequência de releases foi excluída do conjunto (insumo de D5 — "
        "circularidade); stars/forks são proxies de popularidade e stars "
        "estruturou a amostragem (§3.1) — a leitura por arquétipo é a mais "
        "limpa para esses indicadores;",
        "- a ausência em dependentes/scorecard é ESTRUTURAL, não aleatória "
        "(cobertura de ecossistema do deps.dev; lista de varredura do "
        "OpenSSF) — cada ρ refere-se a uma subpopulação distinta e os "
        "coeficientes não são diretamente comparáveis entre indicadores;",
    ]
    if meta.get("stars_snapshot") or meta.get("external_fetched_at"):
        lines.append(
            f"- épocas: stars/forks do snapshot de extração "
            f"({meta.get('stars_snapshot', 'n/d')}); dependentes/scorecard "
            f"consultados em {meta.get('external_fetched_at', 'n/d')}.")
    lines += ["", "## Família global (corrigida)", "",
              "| indicador | n | ρ | p | p ajustado | significativo |",
              "|---|---|---|---|---|---|"]
    for ind, g in res["global"].items():
        if not g.get("in_family"):
            sig = "fora da família (n<10)" if g.get("p") is not None else "n/d"
            p_show = "—"
        else:
            sig = "✅" if g.get("significant") else "—"
            p_show = _f(g["p"], 4)
        lines.append(f"| {ind} | {g['n']} | {_f(g['rho'])} | {p_show} | "
                     f"{_f(g.get('p_adj'), 4)} | {sig} |")
    cov = res.get("coverage") or {}
    dep_langs = (cov.get("dependents") or {}).get("languages")
    if dep_langs:
        lines += ["", "Composição do subamostra de dependentes (linguagens "
                  "com pacote verificado): "
                  + ", ".join(f"{k} {v}" for k, v in dep_langs.items())
                  + ". Cobertura efetiva de `:dependents` no deps.dev: "
                  "NPM/CARGO/PYPI (RubyGems e Packagist retornam 404 — "
                  "verificado empiricamente); Java/MAVEN fora por "
                  "mapeamento nome→coordenada inviável; Go sem "
                  "`:dependents`; C/C++ sem ecossistema (§8 do plano). "
                  "Com n insuficiente, o indicador é reportado apenas "
                  "descritivamente."]
    lines += ["", "## Por arquétipo (exploratório, n≈25; sem correção; "
              "p pela aproximação t do scipy, SUPRIMIDO quando n < 10 — "
              "não confiável em amostras pequenas)", ""]
    for arch, arch_res in res["by_archetype"].items():
        lines += [f"### {arch}", "", "| indicador | n | ρ | p |", "|---|---|---|---|"]
        for ind, g in arch_res.items():
            p_show = _f(g["p"], 4) if g["n"] >= 10 else "—"
            lines.append(f"| {ind} | {g['n']} | {_f(g['rho'])} | {p_show} |")
        lines.append("")
    lines += ["Poder estatístico (Spearman bicaudal, α = 0,05, ~80%): "
              "ρ ≈ 0,28 para indicadores com n = 100 (stars/forks); a "
              "exclusão par a par reduz o poder (ex.: n ≈ 55 → ρ ≈ 0,38) e "
              "o passo mais rigoroso de Holm testa a α/m (n = 100 → "
              "ρ ≈ 0,34) — declarar ao interpretar não-significâncias "
              "(§6.2).", ""]
    return "\n".join(lines)
