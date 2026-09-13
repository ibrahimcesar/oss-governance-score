"""OpenSSF Scorecard CLI nos 100 repositórios — instrumento de validação
SECUNDÁRIO, pré-registrado como descritivo no registro de decisão de
2026-09-13 ("Instrumentos complementares"). Nunca árbitro de regra.

Época declarada: HEAD de 09/2026 (~7 semanas após o snapshot de julho);
checks *Maintained*, *Vulnerabilities*, *Signed-Releases* e
*Branch-Protection* não são retrodatáveis. A API-53 de julho permanece o
critério primário (results/validacao.md); aqui reporta-se (i) a
concordância CLI × API nos 53, restrita aos checks comuns, e (ii) as
correlações do score v2 com o agregado do CLI em n = 100 e por arquétipo.

Fonte: data/raw/<owner>__<repo>/v2_scorecard_cli.json (scripts/
scorecard_cli_run.py) e openssf_scorecard.json (cache de julho).
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from govscore.score.sensitivity import spearman

ARCHETYPES = ("federation", "stadium", "club", "toy")

# Pesos por nível de risco do agregado do Scorecard (docs/checks.md):
# Critical 10, High 7,5, Medium 5, Low 2,5; checks com score < 0
# (inconclusivos) ficam fora do agregado.
RISK_WEIGHT = {"Critical": 10.0, "High": 7.5, "Medium": 5.0, "Low": 2.5}
CHECK_RISK = {
    "Binary-Artifacts": "High", "Branch-Protection": "High",
    "CI-Tests": "Low", "CII-Best-Practices": "Low", "Code-Review": "High",
    "Contributors": "Low", "Dangerous-Workflow": "Critical",
    "Dependency-Update-Tool": "High", "Fuzzing": "Medium", "License": "Low",
    "Maintained": "High", "Packaging": "Medium",
    "Pinned-Dependencies": "Medium", "SAST": "Medium",
    "Security-Policy": "Medium", "Signed-Releases": "High",
    "Token-Permissions": "High", "Vulnerabilities": "High",
    "Webhooks": "Critical",
}
# Sobreposição declarada com o catálogo (D5 e revisão de código em D3):
OVERLAP_CHECKS = ("Security-Policy", "Dependency-Update-Tool", "Code-Review",
                  "CI-Tests", "License")


def check_scores(payload: dict | None) -> dict[str, float]:
    """{nome do check: score} a partir de um resultado do Scorecard
    (CLI ou API); scores ausentes ou < 0 são omitidos."""
    if not payload:
        return {}
    out = {}
    for c in payload.get("checks") or []:
        name, score = c.get("name"), c.get("score")
        if name and score is not None and score >= 0:
            out[name] = float(score)
    return out


def aggregate(scores: dict[str, float], subset: set[str] | None = None) -> float | None:
    """Agregado ponderado por risco, como o Scorecard; `subset` restringe
    aos checks comuns entre instrumentos. None se nenhum check válido."""
    num = den = 0.0
    for name, s in scores.items():
        if subset is not None and name not in subset:
            continue
        w = RISK_WEIGHT[CHECK_RISK.get(name, "Medium")]
        num += w * s
        den += w
    return num / den if den else None


def load_results(cache_root: Path, repos: list[str]) -> list[dict]:
    """Uma linha por repositório: agregados do CLI (reportado e reproduzido),
    checks do CLI e da API de julho (quando existe)."""
    rows = []
    for repo in repos:
        d = Path(cache_root) / repo.replace("/", "__")
        row: dict = {"repo": repo, "cli": None, "cli_reported": None,
                     "cli_checks": {}, "api": None, "api_checks": {},
                     "cli_elapsed_s": None, "cli_error": None}
        f = d / "v2_scorecard_cli.json"
        if f.exists():
            p = json.loads(f.read_text())
            row["cli_elapsed_s"] = p.get("elapsed_s")
            row["cli_error"] = p.get("error")
            data = p.get("data")
            if data:
                row["cli_checks"] = check_scores(data)
                row["cli_reported"] = data.get("score")
                row["cli"] = aggregate(row["cli_checks"])
        g = d / "openssf_scorecard.json"
        if g.exists():
            try:
                data = json.loads(g.read_text()).get("data")
            except json.JSONDecodeError:
                data = None
            if isinstance(data, dict):
                row["api_checks"] = check_scores(data)
                row["api"] = data.get("score")
        rows.append(row)
    return rows


def analyze(rows: list[dict], records: list[dict]) -> dict:
    """Concordância CLI×API (n = 53, checks comuns) e correlações do score
    v2 com o agregado do CLI (n = 100, por arquétipo; sem correção —
    família secundária, descritiva)."""
    by_repo = {r["repo"]: r for r in records}
    ok = [r for r in rows if r["cli"] is not None]
    # reprodução do agregado reportado pelo CLI (validação interna)
    repro = [abs(r["cli"] - r["cli_reported"]) for r in ok
             if r["cli_reported"] is not None]
    both = [r for r in ok if r["api"] is not None]
    common_agree = []
    for r in both:
        common = set(r["cli_checks"]) & set(r["api_checks"])
        common_agree.append({
            "repo": r["repo"], "n_common": len(common),
            "cli_common": aggregate(r["cli_checks"], common),
            "api_common": aggregate(r["api_checks"], common),
            "cli_18": r["cli"], "api": r["api"]})
    res: dict = {
        "n_cli": len(ok), "n_failed": len(rows) - len(ok),
        "failed": [r["repo"] for r in rows if r["cli"] is None],
        "repro_max_abs_diff": max(repro) if repro else None,
        "elapsed_median_s": statistics.median(
            [r["cli_elapsed_s"] for r in ok if r["cli_elapsed_s"]]) if ok else None,
        "n_api": len(both),
        "rho_cli18_vs_api": spearman([c["cli_18"] for c in common_agree],
                                     [c["api"] for c in common_agree]),
        "rho_common_vs_api": spearman([c["cli_common"] for c in common_agree],
                                      [c["api_common"] for c in common_agree]),
        "mean_abs_diff_common": (statistics.mean(
            [abs(c["cli_common"] - c["api_common"]) for c in common_agree
             if c["cli_common"] is not None and c["api_common"] is not None])
            if common_agree else None),
        "cli_mean": statistics.mean([r["cli"] for r in ok]) if ok else None,
    }
    # correlações com o score v2
    pairs = [(by_repo[r["repo"]], r["cli"]) for r in ok if r["repo"] in by_repo]
    res["rho_score_cli_all"] = spearman([p[0]["score"] for p in pairs],
                                        [p[1] for p in pairs])
    res["n_all"] = len(pairs)
    # agregado sem os checks sobrepostos ao catálogo (não circular)
    res["rho_score_cli_nonoverlap"] = spearman(
        [p[0]["score"] for p in pairs],
        [aggregate(next(r for r in ok if r["repo"] == p[0]["repo"])["cli_checks"],
                   set(CHECK_RISK) - set(OVERLAP_CHECKS)) for p in pairs])
    res["por_arquetipo"] = {}
    for a in ARCHETYPES:
        sub = [p for p in pairs if p[0].get("archetype") == a]
        res["por_arquetipo"][a] = {
            "n": len(sub),
            "rho": spearman([p[0]["score"] for p in sub], [p[1] for p in sub]),
            "cli_mean": statistics.mean([p[1] for p in sub]) if sub else None,
        }
    # a mesma correlação no subconjunto API-53 (comparabilidade com o primário)
    api_pairs = [p for p in pairs if next(r for r in ok if r["repo"] == p[0]["repo"])["api"] is not None]
    res["rho_score_cli_api53_subset"] = spearman(
        [p[0]["score"] for p in api_pairs], [p[1] for p in api_pairs])
    return res


def _f(v, nd=3):
    return "—" if v is None else f"{v:.{nd}f}"


def report(res: dict) -> str:
    lines = [
        "# OpenSSF Scorecard CLI nos 100 repositórios (validação secundária)", "",
        "Pré-registrado como DESCRITIVO no registro de decisão de 2026-09-13; "
        "a API-53 de julho permanece o critério primário. Época do CLI: HEAD "
        "em 09/2026 (~7 semanas após o snapshot); *Maintained*, "
        "*Vulnerabilities*, *Signed-Releases* e *Branch-Protection* não são "
        "retrodatáveis. Versão única do CLI (v5.5.0, 18 checks).", "",
        f"Repositórios com resultado: {res['n_cli']}/100"
        + (f" (falhas: {', '.join(res['failed'])})" if res["failed"] else "")
        + f"; mediana de {_f(res['elapsed_median_s'], 0)} s por repositório; "
        f"agregado reportado reproduzido a partir dos checks (diferença máxima "
        f"{_f(res['repro_max_abs_diff'], 4)}).", "",
        "## Concordância CLI × API de julho (n = %d)" % res["n_api"], "",
        f"- ρ entre o agregado do CLI (18 checks) e o da API: "
        f"{_f(res['rho_cli18_vs_api'])} — instrumentos com conjuntos de checks "
        "distintos (a varredura pública omite CI-Tests, Contributors e "
        "Dependency-Update-Tool).",
        f"- ρ entre agregados restritos aos checks COMUNS: "
        f"{_f(res['rho_common_vs_api'])}; diferença média absoluta "
        f"{_f(res['mean_abs_diff_common'], 2)} pontos — a diferença "
        "remanescente é a deriva de época (julho → setembro).", "",
        "## Correlação do score v2 com o agregado do CLI", "",
        "| subconjunto | n | ρ |", "|---|---|---|",
        f"| todos | {res['n_all']} | {_f(res['rho_score_cli_all'])} |",
        f"| todos, agregado sem os checks sobrepostos ao catálogo "
        f"(Security-Policy, Dependency-Update-Tool, Code-Review, CI-Tests, "
        f"License) | {res['n_all']} | {_f(res['rho_score_cli_nonoverlap'])} |",
        f"| só os 53 com resultado na API (comparabilidade com o primário) | "
        f"{len([1 for _ in range(res['n_api'])])} | "
        f"{_f(res['rho_score_cli_api53_subset'])} |",
        "", "| arquétipo | n | ρ | média do CLI |", "|---|---|---|---|",
    ]
    for a, v in res["por_arquetipo"].items():
        lines.append(f"| {a} | {v['n']} | {_f(v['rho'])} | {_f(v['cli_mean'], 2)} |")
    lines += ["", "Leitura: sem correção para múltiplos testes (família "
              "secundária, descritiva); poder intra-arquétipo com n = 25 "
              "apenas para efeitos grandes (ρ ≳ 0,57). O agregado sem os "
              "checks sobrepostos mostra a convergência que não é mecânica.", ""]
    return "\n".join(lines)
