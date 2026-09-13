"""Análises de robustez pós-revisão adversarial (Fase 1 do plano de melhoria).

Todas operam sobre artefatos já extraídos (data/processed/, config/) — nada
reconsulta APIs. Sete análises:

1. Sensibilidade dos LIMIARES de normalização (±25%, ±50%) — a verificação
   prometida no plano §3.1 e não coberta pela sensibilidade de pesos.
2. Reclassificação dos arquétipos com limiares de classificação ±50%.
3. Validade discriminante vs OpenSSF Scorecard (composto social + Steiger).
4. Robustez à exclusão de repositórios suspeitos de não-software.
5. Taxonomia de faltantes (estrutural × informativo) + sensibilidade
   omissão vs imputação de pior caso em D3.
6. Composição da cobertura do Scorecard (ausência estrutural).
7. Triagem de sinais de inflação de stars + valores de referência por
   arquétipo (quartis).
"""
from __future__ import annotations

import json
import math
import re
import statistics
from pathlib import Path

from govscore.score.scoring import compute_score, compute_subscores
from govscore.score.sensitivity import spearman

ROOT = Path(__file__).resolve().parents[2]
ARCHETYPES = ("federation", "stadium", "club", "toy")

# métricas contínuas com limiares best/worst no catálogo:
# (seção do cfg, métrica, seção do dict de métricas cruas)
THRESHOLDED = [
    ("distribution", "top1_share", "distribution"),
    ("distribution", "hhi", "distribution"),
    ("distribution", "truck_factor", "distribution"),
    ("responsiveness", "median_first_response_hours", "responsiveness"),
    ("responsiveness", "median_pr_merge_hours", "responsiveness"),
    ("responsiveness", "pr_merge_ratio", "responsiveness"),
    ("responsiveness", "pr_review_coverage", "responsiveness"),
    ("diversity", "contributors_5plus", "distribution"),
    ("diversity", "commit_entropy", "distribution"),
    ("diversity", "elephant_factor", "distribution"),
    ("diversity", "contributor_retention", "distribution"),
    ("security", "releases_12m", "security"),
    ("security", "release_notes_share", "security"),
]

SUSPECT_NAME = re.compile(
    r"leetcode|interview|awesome|explore|roadmap|tutorial|study|notes|book|"
    r"course|cheat|free[-_]?vpn|subscription", re.IGNORECASE)

# Categorias da inspeção manual (notebook 01; decisão em
# docs/decisions/2026-09-12-inspecao-manual-amostra.md). Todos MANTIDOS na
# amostra; as categorias existem para reportar os resultados com e sem eles.
# Conteúdo inclui 4 casos que as heurísticas de nome/silêncio não capturam.
CONTENT_REPOS = (
    "MisterBooo/LeetCodeAnimation", "EFanZh/LeetCode", "github/explore",
    "krahets/hello-algo", "doocs/advanced-java", "danielmiessler/SecLists",
    "SwiftOldDriver/iOS-Weekly", "Au1rxx/free-vpn-subscriptions",
)
# desenvolvimento fora do GitHub (issues desativadas; patches por lista/GitLab)
MIRROR_REPOS = ("torvalds/linux", "FFmpeg/FFmpeg", "git/git",
                "gitlabhq/gitlabhq")

# Conjuntos PRÉ-REGISTRADOS no catálogo v2
# (docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md, "Instrumentos
# complementares"). Descritivos: todos MANTIDOS na amostra e nos scores.
# Locus de coordenação fora do GitHub (Gerrit/Phabricator/Piper/lista de
# e-mail; evidência em results/locus_evidence.md, `govscore locus-evidence`):
# cenário `sem_locus_externo` = LOCUS_EXTERNAL_REPOS ∪ MIRROR_REPOS.
LOCUS_EXTERNAL_REPOS = ("git/git", "gitlabhq/gitlabhq", "golang/go",
                        "react/react-native", "tensorflow/tensorflow")
# Par quase-duplicado por histórico (openinterpreter/openinterpreter ⊃
# openai/codex): cenário `sem_openinterpreter` retira só o superconjunto.
NEAR_DUPLICATE_REPOS = ("openinterpreter/openinterpreter",)


def _scores_with_cfg(results: list[dict], cfg: dict) -> list[float | None]:
    return [compute_score(compute_subscores(r, cfg), cfg["weights"])
            for r in results]


def _perturb_cfg(cfg: dict, targets: list[tuple[str, str]],
                 factor: float) -> dict:
    """Copia o catálogo escalando best/worst das métricas alvo por `factor`
    (pesos e demais limiares intocados)."""
    out = json.loads(json.dumps(cfg))
    for section, metric in targets:
        th = out[section][metric]
        th["best"] = th["best"] * factor
        th["worst"] = th["worst"] * factor
    return out


def threshold_sensitivity(results: list[dict], cfg: dict,
                          deltas=(0.25, 0.50)) -> dict:
    """ρ do ranking sob perturbação dos limiares de normalização.

    Por métrica (individual) e conjunta (todas simultaneamente), em
    ±25% e ±50%. Métricas binárias não têm limiar — ficam fora por definição.
    """
    base = _scores_with_cfg(results, cfg)
    out: dict = {"per_metric": {}, "joint": {}}
    for delta in deltas:
        rhos: dict[str, float | None] = {}
        for section, metric, _ in THRESHOLDED:
            for factor, tag in ((1 + delta, "+"), (1 - delta, "-")):
                v = _scores_with_cfg(
                    results, _perturb_cfg(cfg, [(section, metric)], factor))
                rhos[f"{metric} {tag}{delta:.0%}"] = spearman(base, v)
        valid = [r for r in rhos.values() if r is not None]
        out["per_metric"][f"±{delta:.0%}"] = {
            "min": min(valid) if valid else None,
            "mean": statistics.mean(valid) if valid else None,
            "pior_variante": (min((k for k in rhos if rhos[k] is not None),
                                  key=lambda k: rhos[k]) if valid else None),
            "variantes": rhos,
        }
        joint: dict[str, float | None] = {}
        for factor, tag in ((1 + delta, "+"), (1 - delta, "-")):
            all_targets = [(s, m) for s, m, _ in THRESHOLDED]
            v = _scores_with_cfg(results,
                                 _perturb_cfg(cfg, all_targets, factor))
            joint[f"todas {tag}{delta:.0%}"] = spearman(base, v)
        out["joint"][f"±{delta:.0%}"] = joint
    return out


def reclassification_sensitivity(sample_entries: list[dict],
                                 thresholds: dict) -> dict:
    """Reclassifica a amostra com limiares de classificação ±50%.

    CAVEAT declarado: contagens de Federações são pisos (early stop ao
    confirmar ≥100), então federation_min +50% é intestável — Federações com
    contagem truncada ficam indeterminadas, não 'reclassificadas'.
    """
    from govscore.sampling import classify

    keys = ["federation_min_contributors", "stadium_max_contributors",
            "club_min_contributors", "toy_max_contributors",
            "stars_high_min", "club_stars_max", "toy_stars_max"]
    variants: dict[str, dict] = {}
    for name, factor_map in (
            [("conjunto +50%", {k: 1.5 for k in keys}),
             ("conjunto −50%", {k: 0.5 for k in keys})]
            + [(f"{k} {tag}50%", {k: f})
               for k in keys for f, tag in ((1.5, "+"), (0.5, "−"))]):
        t = dict(thresholds)
        for k, f in factor_map.items():
            t[k] = thresholds[k] * f
        same = changed = unclass = fed_indet = 0
        for e in sample_entries:
            new = classify(e["active_contributors_2plus"], e["stars"], t)
            orig = e["archetype"]
            if (orig == "federation"
                    and t["federation_min_contributors"]
                    > thresholds["federation_min_contributors"]):
                # contagem é piso: subir o limiar torna o caso indeterminado
                fed_indet += 1
                continue
            if new == orig:
                same += 1
            elif new is None:
                unclass += 1
            else:
                changed += 1
        n_eval = same + changed + unclass
        variants[name] = {
            "preservados": same, "mudam_de_arquetipo": changed,
            "ficam_fora_das_faixas": unclass,
            "federacoes_indeterminadas": fed_indet,
            "pct_preservados": round(100 * same / n_eval, 1) if n_eval else None,
        }
    return variants


# ------------------------------------------------------------ discriminante
def steiger_z(r13: float, r23: float, r12: float, n: int) -> tuple[float, float]:
    """Teste de Steiger (1980) para correlações dependentes que compartilham
    uma variável (aqui: Scorecard). Aplicado sobre ρ de Spearman —
    aproximação declarada. Retorna (z, p bicaudal)."""
    z13, z23 = math.atanh(r13), math.atanh(r23)
    rm2 = (r13 ** 2 + r23 ** 2) / 2
    f = min((1 - r12) / (2 * (1 - rm2)), 1.0)
    h = (1 - f * rm2) / (1 - rm2)
    z = (z13 - z23) * math.sqrt((n - 3) / (2 * (1 - r12) * h))
    from scipy.stats import norm
    return z, float(2 * (1 - norm.cdf(abs(z))))


def social_composite(results: list[dict], weights: dict) -> list[float | None]:
    """Score restrito às dimensões sociais/organizacionais (D2, D3, D4),
    com pesos renormalizados — as dimensões que o Scorecard NÃO mede."""
    social = {d: w for d, w in weights.items()
              if d in ("distribution", "responsiveness", "diversity")}
    return [compute_score({d: r["subscores"].get(d) for d in social}, social)
            for r in results]


def discriminant_validity(results: list[dict], scorecard: dict[str, float],
                          weights: dict) -> dict:
    sc = [scorecard.get(r["repo"]) for r in results]
    full = [r["score"] for r in results]
    social = social_composite(results, weights)

    out: dict = {"por_dimensao": {}}
    for dim in ("artifacts", "distribution", "responsiveness",
                "diversity", "security"):
        out["por_dimensao"][dim] = spearman(
            [r["subscores"].get(dim) for r in results], sc)
    rho_full = spearman(full, sc)
    rho_social = spearman(social, sc)
    pairs = [(f, s, c) for f, s, c in zip(full, social, sc)
             if None not in (f, s, c)]
    r12 = spearman([p[0] for p in pairs], [p[1] for p in pairs])
    z, p = steiger_z(rho_full, rho_social, r12, len(pairs))
    out.update({"rho_score_cheio": rho_full, "rho_composto_social": rho_social,
                "rho_entre_compostos": r12, "n": len(pairs),
                "steiger_z": z, "steiger_p": p})
    return out


# ----------------------------------------------------------------- suspeitos
def find_suspects(results: list[dict]) -> dict[str, list[str]]:
    nome = [r["repo"] for r in results if SUSPECT_NAME.search(r["repo"])]
    sem_resposta = [r["repo"] for r in results
                    if r.get("responsiveness", {}).get("n_first_responses") == 0]
    return {"nome": nome, "sem_resposta_humana": sem_resposta,
            "uniao": sorted(set(nome) | set(sem_resposta))}


def _rows(results, ext):
    return [{**{"repo": r["repo"], "archetype": r["archetype"],
                "score": r["score"], "stars": r.get("stars"),
                "forks": r.get("forks")},
             **ext.get(r["repo"], {})} for r in results]


def suspect_robustness(results: list[dict], ext: dict[str, dict]) -> dict:
    suspects = find_suspects(results)
    excl = set(suspects["uniao"])
    kept = [r for r in results if r["repo"] not in excl]
    rows_all, rows_kept = _rows(results, ext), _rows(kept, ext)

    def stadium_forks(rows):
        sub = [r for r in rows if r["archetype"] == "stadium"]
        return spearman([r["score"] for r in sub],
                        [r.get("forks") for r in sub]), len(sub)

    def global_rho(rows, ind):
        return spearman([r["score"] for r in rows],
                        [r.get(ind) for r in rows])

    rho_all, n_all = stadium_forks(rows_all)
    rho_kept, n_kept = stadium_forks(rows_kept)
    medias = {a: {
        "com": statistics.mean([r["score"] for r in results
                                if r["archetype"] == a]),
        "sem": statistics.mean([r["score"] for r in kept
                                if r["archetype"] == a]),
        "n_excluidos": sum(1 for s in excl for r in results
                           if r["repo"] == s and r["archetype"] == a),
    } for a in ARCHETYPES}
    return {"suspeitos": suspects, "n_excluidos": len(excl),
            "estadio_forks": {"com": {"rho": rho_all, "n": n_all},
                              "sem": {"rho": rho_kept, "n": n_kept}},
            "global_sem_suspeitos": {
                ind: global_rho(rows_kept, ind)
                for ind in ("scorecard", "stars", "forks")},
            "medias_por_arquetipo": medias,
            "cenarios": exclusion_scenarios(results, ext, suspects["uniao"])}


def stratum_rho(rows: list[dict], archetype: str, indicator: str) -> dict:
    """ρ de Spearman score × indicador dentro de um arquétipo, com exclusão
    par a par de faltantes; p nominal (sem correção — análise exploratória)."""
    pairs = [(r["score"], r.get(indicator)) for r in rows
             if r["archetype"] == archetype and r["score"] is not None
             and r.get(indicator) is not None]
    if len(pairs) < 3:
        return {"rho": None, "p": None, "n": len(pairs)}
    from scipy.stats import spearmanr
    res = spearmanr([p[0] for p in pairs], [p[1] for p in pairs])
    return {"rho": float(res.statistic), "p": float(res.pvalue),
            "n": len(pairs)}


# achados intra-arquétipo citados na seção 4.3.4 do rascunho
STRATUM_FINDINGS = (("stadium", "forks"), ("federation", "scorecard"))


def exclusion_scenarios(results: list[dict], ext: dict[str, dict],
                        heuristic: list[str]) -> dict:
    """Resultados globais e intra-arquétipo sob cada conjunto de exclusão
    da inspeção manual (heurística, conteúdo, espelhos e a união) e dos
    cenários pré-registrados do catálogo v2 (locus externo, quase-duplicado).
    `sem_todos` permanece a união da inspeção manual (2026-09-12)."""
    sets = {
        "completa": set(),
        "sem_heuristica": set(heuristic),
        "sem_conteudo": set(CONTENT_REPOS),
        "sem_espelhos": set(MIRROR_REPOS),
        "sem_todos": set(heuristic) | set(CONTENT_REPOS) | set(MIRROR_REPOS),
        "sem_locus_externo": set(LOCUS_EXTERNAL_REPOS) | set(MIRROR_REPOS),
        "sem_openinterpreter": set(NEAR_DUPLICATE_REPOS),
    }
    out = {}
    for name, excl in sets.items():
        rows = _rows([r for r in results if r["repo"] not in excl], ext)
        out[name] = {
            "n": len(rows),
            "global": {ind: spearman([r["score"] for r in rows],
                                     [r.get(ind) for r in rows])
                       for ind in ("scorecard", "stars", "forks")},
            "estratos": {f"{a}×{ind}": stratum_rho(rows, a, ind)
                         for a, ind in STRATUM_FINDINGS},
        }
    return out


# ---------------------------------------------------------------- faltantes
def missingness_taxonomy(results: list[dict]) -> dict:
    """Estrutural ('não se aplica' / não observável) × informativo
    (silêncio observado — issues existem, nenhuma resposta humana)."""
    info, estrut = [], []
    for r in results:
        resp = r.get("responsiveness", {})
        if resp.get("median_first_response_hours") is None:
            if (resp.get("n_issues_sampled") or 0) > 0:
                info.append(r["repo"])       # silêncio observado
            else:
                estrut.append(r["repo"])     # sem issues na plataforma
    sem_release = [r["repo"] for r in results
                   if r.get("security", {}).get("release_notes_share") is None]
    return {"d3_informativo": info, "d3_estrutural": estrut,
            "release_notes_estrutural_sem_release": sem_release}


def imputation_sensitivity(results: list[dict], cfg: dict) -> dict:
    """Omissão (regra do método) vs imputação de pior caso (worst → 0) para
    a 1ª resposta nos casos INFORMATIVOS. Reporta ρ e deslocamentos."""
    tax = missingness_taxonomy(results)
    info = set(tax["d3_informativo"])
    base = _scores_with_cfg(results, cfg)
    worst = cfg["responsiveness"]["median_first_response_hours"]["worst"]
    imputed = []
    for r in results:
        r2 = json.loads(json.dumps(r))
        if r2["repo"] in info:
            r2["responsiveness"]["median_first_response_hours"] = worst
        imputed.append(r2)
    imp = _scores_with_cfg(imputed, cfg)

    def ranks(xs):
        order = sorted(range(len(xs)), key=lambda i: -(xs[i] or 0))
        pos = [0] * len(xs)
        for k, i in enumerate(order):
            pos[i] = k + 1
        return pos
    rb, ri = ranks(base), ranks(imp)
    shifts = {results[i]["repo"]: ri[i] - rb[i]
              for i in range(len(results)) if results[i]["repo"] in info}
    presentes = [a for a in ARCHETYPES
                 if any(r["archetype"] == a for r in results)]
    medias = {a: {
        "omissao": statistics.mean([b for b, r in zip(base, results)
                                    if r["archetype"] == a]),
        "imputacao": statistics.mean([v for v, r in zip(imp, results)
                                      if r["archetype"] == a]),
    } for a in presentes}
    return {"n_informativos": len(info), "rho": spearman(base, imp),
            "deslocamento_max_rank": max(shifts.values(), default=0),
            "deslocamentos": shifts, "medias_por_arquetipo": medias,
            "taxonomia": tax}


# ------------------------------------------------------- cobertura scorecard
def scorecard_coverage(results: list[dict], ext: dict[str, dict]) -> dict:
    cov = [r for r in results if ext.get(r["repo"], {}).get("scorecard")
           is not None]
    not_cov = [r for r in results if r not in cov]

    def perfil(sub):
        langs: dict[str, int] = {}
        for r in sub:
            lg = (r.get("language") or "?").lower()
            langs[lg] = langs.get(lg, 0) + 1
        return {"n": len(sub),
                "por_arquetipo": {a: sum(1 for r in sub
                                         if r["archetype"] == a)
                                  for a in ARCHETYPES},
                "linguagens": dict(sorted(langs.items())),
                "score_medio": round(statistics.mean(
                    [r["score"] for r in sub]), 1) if sub else None}
    from scipy.stats import mannwhitneyu
    mw = mannwhitneyu([r["score"] for r in cov],
                      [r["score"] for r in not_cov])
    return {"cobertos": perfil(cov), "nao_cobertos": perfil(not_cov),
            "mannwhitney_p_score": float(mw.pvalue)}


# ------------------------------------------------- stars + valores de refer.
def star_inflation_screens(results: list[dict],
                           active: dict[str, int]) -> list[dict]:
    """Sinais baratos de plausibilidade: razão stars/forks e stars por
    contribuidor ativo, sinalizando os destoantes do próprio estrato."""
    flags = []
    for a in ARCHETYPES:
        sub = [r for r in results if r["archetype"] == a
               and r.get("stars") and r.get("forks")]
        ratios = sorted((r["stars"] / max(r["forks"], 1)) for r in sub)
        med = statistics.median(ratios)
        for r in sub:
            ratio = r["stars"] / max(r["forks"], 1)
            per_active = (r["stars"] / max(active.get(r["repo"], 1), 1))
            if ratio > 5 * med:
                flags.append({"repo": r["repo"], "archetype": a,
                              "stars": r["stars"], "forks": r["forks"],
                              "stars_por_fork": round(ratio, 1),
                              "mediana_do_estrato": round(med, 1),
                              "stars_por_contribuidor_ativo":
                                  round(per_active)})
    return sorted(flags, key=lambda f: -f["stars_por_fork"])


def reference_values(results: list[dict]) -> dict:
    """Valores de referência por arquétipo (quartis) — a leitura correta é
    SEMPRE dentro do arquétipo."""
    out = {}
    for a in ARCHETYPES:
        xs = sorted(r["score"] for r in results if r["archetype"] == a
                    and r["score"] is not None)
        q = statistics.quantiles(xs, n=4)
        out[a] = {"q1": round(q[0], 1), "mediana": round(q[1], 1),
                  "q3": round(q[2], 1), "n": len(xs)}
    return out


# -------------------------------------------------------------- orquestração
def run_all() -> dict:
    import pandas as pd
    import yaml
    cfg = yaml.safe_load((ROOT / "config" / "metrics.yaml").read_text())
    results = json.loads((ROOT / "data" / "processed" /
                          "full_metrics.json").read_text())["results"]
    sample = yaml.safe_load((ROOT / "config" / "sample_full.yaml").read_text())
    thresholds = yaml.safe_load(
        (ROOT / "config" / "sampling.yaml").read_text())["thresholds"]
    ext_df = pd.read_csv(ROOT / "data" / "processed" /
                         "external_indicators.csv")
    ext = {r["repo"]: {"scorecard": (None if pd.isna(r["scorecard"])
                                     else float(r["scorecard"])),
                       "dependents": (None if pd.isna(r["dependents"])
                                      else float(r["dependents"]))}
           for r in ext_df.to_dict("records")}
    scorecard = {k: v["scorecard"] for k, v in ext.items()}
    active = {e["repo"]: e["active_contributors_2plus"]
              for e in sample["full"]}

    return {
        "limiar_normalizacao": threshold_sensitivity(results, cfg),
        "reclassificacao": reclassification_sensitivity(
            sample["full"], thresholds),
        "discriminante": discriminant_validity(
            results, scorecard, cfg["weights"]),
        "suspeitos": suspect_robustness(results, ext),
        "imputacao": imputation_sensitivity(results, cfg),
        "cobertura_scorecard": scorecard_coverage(results, ext),
        "stars_flags": star_inflation_screens(results, active),
        "valores_referencia": reference_values(results),
    }


def _f(v, nd=3):
    return f"{v:.{nd}f}" if v is not None else "—"


def scenario_section(cen: dict) -> list[str]:
    """Linhas da seção 4.1 (cenários de exclusão): definição dos conjuntos,
    tabela com uma linha por cenário — inclusive os pré-registrados do
    catálogo v2 — e leitura da robustez de cada achado intra-arquétipo."""
    finds = list(next(iter(cen.values()))["estratos"])
    lines = ["### 4.1 Cenários da inspeção manual (todos mantidos na amostra)",
             "",
             "Categorias definidas na inspeção manual (notebook 01; "
             "`docs/decisions/2026-09-12-inspecao-manual-amostra.md`). "
             "**Conteúdo**: " + ", ".join(f"`{x}`" for x in CONTENT_REPOS)
             + ". **Espelhos**: " + ", ".join(f"`{x}`" for x in MIRROR_REPOS)
             + ". Cenários pré-registrados do catálogo v2 "
             "(`docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md`): "
             "**sem_locus_externo** = locus de coordenação fora do GitHub "
             "(" + ", ".join(f"`{x}`" for x in LOCUS_EXTERNAL_REPOS)
             + ") ∪ espelhos — evidência em `results/locus_evidence.md`; "
             "**sem_openinterpreter** = par quase-duplicado "
             "(" + ", ".join(f"`{x}`" for x in NEAR_DUPLICATE_REPOS)
             + " ⊃ `openai/codex`). `sem_todos` permanece a união da "
             "inspeção manual de 2026-09-12 (heurística ∪ conteúdo ∪ "
             "espelhos) e NÃO incorpora os cenários v2, que são lidos "
             "isoladamente. Intra-arquétipo: ρ (p nominal, n).", "",
             "| cenário | n | scorecard | stars | forks | "
             + " | ".join(finds) + " |",
             "|---|---|---|---|---|" + "---|" * len(finds)]
    for name, v in cen.items():
        g = v["global"]
        cells = [f"{_f(e['rho'])} (p={_f(e['p'])}, n={e['n']})"
                 for e in v["estratos"].values()]
        lines.append(f"| {name} | {v['n']} | {_f(g['scorecard'])} | "
                     f"{_f(g['stars'])} | {_f(g['forks'])} | "
                     + " | ".join(cells) + " |")
    lines.append("")
    for f in finds:
        caem = [name for name, v in cen.items()
                if (v["estratos"][f]["p"] or 1) >= 0.05]
        lines.append(f"- **{f}**: " + (
            "p nominal < 0,05 em todos os cenários." if not caem else
            "perde significância nominal em: "
            + ", ".join(f"`{c}`" for c in caem)
            + " — achado NÃO robusto à composição da amostra."))
    lines.append("")
    return lines


def report(res: dict) -> str:
    lines = ["# Robustez e validade adicional (pós-revisão adversarial)", ""]

    t = res["limiar_normalizacao"]
    lines += ["## 1. Sensibilidade dos limiares de normalização", "",
              "Perturbação de best/worst por métrica (individual) e conjunta; "
              "ρ do ranking vs base. Pesos intocados.", "",
              "| perturbação | ρ mín (por métrica) | ρ médio | pior variante "
              "| conjunta + | conjunta − |", "|---|---|---|---|---|---|"]
    for delta in t["per_metric"]:
        pm, j = t["per_metric"][delta], t["joint"][delta]
        jvals = list(j.values())
        lines.append(f"| {delta} | {_f(pm['min'])} | {_f(pm['mean'])} | "
                     f"{pm['pior_variante']} | {_f(jvals[0])} | "
                     f"{_f(jvals[1])} |")
    lines.append("")

    r = res["reclassificacao"]
    lines += ["## 2. Reclassificação dos arquétipos (limiares ±50%)", "",
              "Contagens de Federações são pisos (early stop) — elevar "
              "`federation_min` torna esses casos indeterminados, não "
              "reclassificados (coluna própria).", "",
              "| variante | preservados | mudam | fora das faixas | "
              "federações indet. | % preservados |", "|---|---|---|---|---|---|"]
    for name, v in r.items():
        lines.append(f"| {name} | {v['preservados']} | "
                     f"{v['mudam_de_arquetipo']} | "
                     f"{v['ficam_fora_das_faixas']} | "
                     f"{v['federacoes_indeterminadas']} | "
                     f"{v['pct_preservados']}% |")
    lines.append("")

    d = res["discriminante"]
    lines += ["## 3. Validade discriminante vs OpenSSF Scorecard", "",
              f"ρ do score cheio = {_f(d['rho_score_cheio'])}; ρ do composto "
              f"social D2/D3/D4 = {_f(d['rho_composto_social'])} "
              f"(n = {d['n']}). Teste de Steiger para correlações "
              f"dependentes (aproximação sobre Spearman): z = "
              f"{d['steiger_z']:.2f}, p = {d['steiger_p']:.4f} — as "
              "dimensões sociais medem construto distinto do Scorecard.", "",
              "| dimensão | ρ vs Scorecard |", "|---|---|"]
    for dim, rho in d["por_dimensao"].items():
        lines.append(f"| {dim} | {_f(rho)} |")
    lines.append("")

    s = res["suspeitos"]
    ef = s["estadio_forks"]
    lines += ["## 4. Robustez à exclusão de suspeitos de não-software", "",
              f"{s['n_excluidos']} repositórios sinalizados (nome típico de "
              "não-software ou nenhuma resposta humana): "
              + ", ".join(f"`{x}`" for x in s["suspeitos"]["uniao"]) + ".", "",
              f"- **Estádio × forks**: com suspeitos ρ = "
              f"{_f(ef['com']['rho'])} (n={ef['com']['n']}); sem suspeitos "
              f"ρ = {_f(ef['sem']['rho'])} (n={ef['sem']['n']}). O achado "
              "exploratório deve ser reportado com esta análise ao lado.",
              "- Globais sem suspeitos: "
              + ", ".join(f"{k} ρ={_f(v)}"
                          for k, v in s["global_sem_suspeitos"].items())
              + ".", ""]

    lines += scenario_section(s["cenarios"])

    imp = res["imputacao"]
    lines += ["## 5. Faltantes: taxonomia e sensibilidade de imputação", "",
              f"D3 informativo (silêncio observado): "
              f"{imp['n_informativos']} repos; omissão vs imputação de pior "
              f"caso na 1ª resposta: ρ = {_f(imp['rho'])}, deslocamento "
              f"máximo de {imp['deslocamento_max_rank']} posições.", "",
              "| arquétipo | média (omissão) | média (imputação) |",
              "|---|---|---|"]
    for a, v in imp["medias_por_arquetipo"].items():
        lines.append(f"| {a} | {v['omissao']:.1f} | {v['imputacao']:.1f} |")
    lines.append("")

    c = res["cobertura_scorecard"]
    lines += ["## 6. Cobertura do Scorecard (ausência estrutural)", "",
              f"Cobertos n={c['cobertos']['n']} (score médio "
              f"{c['cobertos']['score_medio']}), não cobertos "
              f"n={c['nao_cobertos']['n']} (score médio "
              f"{c['nao_cobertos']['score_medio']}); Mann–Whitney sobre o "
              f"score: p = {c['mannwhitney_p_score']:.2f} (sem evidência de "
              "que a subamostra coberta seja melhor no score).", "",
              "Cobertos por arquétipo: "
              + ", ".join(f"{a} {n}" for a, n
                          in c["cobertos"]["por_arquetipo"].items()) + ".", ""]

    lines += ["## 7. Triagem de inflação de stars", ""]
    if res["stars_flags"]:
        lines += ["| repo | arquétipo | stars | forks | stars/fork | "
                  "mediana do estrato | stars/contrib. ativo |",
                  "|---|---|---|---|---|---|---|"]
        for fl in res["stars_flags"]:
            lines.append(f"| {fl['repo']} | {fl['archetype']} | "
                         f"{fl['stars']} | {fl['forks']} | "
                         f"{fl['stars_por_fork']} | "
                         f"{fl['mediana_do_estrato']} | "
                         f"{fl['stars_por_contribuidor_ativo']} |")
        lines.append("\nSinal de plausibilidade (razão >5× a mediana do "
                     "estrato) — inspecionar manualmente; não é prova de "
                     "manipulação.")
    else:
        lines.append("Nenhum repositório destoante (>5× a mediana do estrato).")
    lines.append("")

    lines += ["## 8. Valores de referência por arquétipo (quartis)", "",
              "Leitura correta: comparar um repositório com os quartis do "
              "SEU arquétipo — nunca o número absoluto isolado.", "",
              "| arquétipo | Q1 | mediana | Q3 |", "|---|---|---|---|"]
    for a, q in res["valores_referencia"].items():
        lines.append(f"| {a} | {q['q1']} | {q['mediana']} | {q['q3']} |")
    lines.append("")
    return "\n".join(lines)
