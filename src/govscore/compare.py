"""Comparação v1 → v2 do catálogo (reparo de D1/D5; protocolo, passo 5).

Produz `results/reparo_v1_v2.md` (+ `.json`): ρ de Spearman v1×v2 (score,
D1, D5); trocas por item × arquétipo NAS DUAS DIREÇÕES, com listas nominais
(toda troca True→False é listada); herdados de `{owner}/.github` em v1 e v2;
médias/medianas/DP/quartis por arquétipo; maiores deslocamentos de score e de
ranking; tabela de época (status, passo do resolvedor, fonte do corte,
divergências first-parent × `until`, não verificados e inacessíveis); flags
não pontuadas (`issue_template_yaml_only` etc.); asserção
`health_percentage = 100 ⇒ issue_template`; cross-checks descritivos com os
checks do OpenSSF Scorecard (cache de julho) quando fornecidos.

Tudo aqui é DESCRITIVO: nenhum número deste relatório altera regra, limiar ou
peso (registro de decisão de 2026-09-13).
"""
from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

from govscore.rescore import D1_ITEMS, D5_ITEMS
from govscore.score.sensitivity import _ranks, spearman

ARCHETYPES = ("federation", "stadium", "club", "toy")
ITEM_SECTION = {**{i: "artifacts" for i in D1_ITEMS},
                **{i: "security" for i in D5_ITEMS}}
ITEMS = tuple(ITEM_SECTION)
INHERITABLE = ("contributing", "code_of_conduct", "issue_template",
               "pull_request_template", "funding", "security_policy")
METRICS = ("score", "subscore_artifacts", "subscore_security")
MIN_RANK_MOVE = 5

# Checks do Scorecard cruzados com itens nossos: chave em ext_rows →
# (seção, item, nome do check). Presença = score do check > 0; check ausente
# ou score < 0 (inconclusivo) = None (fora do cruzamento).
SCORECARD_CHECKS = {
    "scorecard_security_policy": ("security", "security_policy",
                                  "Security-Policy"),
    "scorecard_license": ("artifacts", "license", "License"),
    "scorecard_dependency_update_tool": ("security", "dependency_automation",
                                         "Dependency-Update-Tool"),
}


# ------------------------------------------------------------------ helpers
def describe(xs: list[float | None]) -> dict:
    """Estatística descritiva com exclusão de None. Quartis pelo método
    padrão de `statistics.quantiles` (exclusivo), o mesmo dos valores de
    referência em `robustness.reference_values`."""
    vals = sorted(x for x in xs if x is not None)
    n = len(vals)
    if n == 0:
        return {"n": 0, "mean": None, "median": None, "sd": None,
                "q1": None, "q3": None, "min": None, "max": None}
    q = statistics.quantiles(vals, n=4) if n >= 2 else [vals[0]] * 3
    return {"n": n, "mean": statistics.fmean(vals),
            "median": statistics.median(vals),
            "sd": statistics.stdev(vals) if n > 1 else 0.0,
            "q1": q[0], "q3": q[2], "min": vals[0], "max": vals[-1]}


def _metric(rec: dict, metric: str) -> float | None:
    if metric == "score":
        return rec.get("score")
    dim = metric.replace("subscore_", "", 1)
    return (rec.get("subscores") or {}).get(dim)


def _item(rec: dict, item: str) -> bool:
    return bool((rec.get(ITEM_SECTION[item]) or {}).get(item))


def _inherited(rec: dict, item: str) -> bool:
    return bool((rec.get(ITEM_SECTION[item]) or {}).get(f"{item}_inherited"))


def _rho(xs: list[float | None], ys: list[float | None]) -> float | None:
    """ρ de Spearman (exclusão par a par); None quando indefinido — n < 3 ou
    entrada constante (NaN do scipy jamais chega ao JSON/relatório)."""
    import math
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # ConstantInputWarning tratado abaixo
        rho = spearman(xs, ys)
    return None if rho is None or math.isnan(rho) else rho


def _rank_desc(values: list[float]) -> list[float]:
    """Posição 1 = maior score; empates recebem a média das posições."""
    n = len(values)
    return [n + 1 - r for r in _ranks(values)]


def scorecard_check_rows(cache_root: Path, repos: list[str]) -> list[dict]:
    """`ext_rows` a partir do cache v1 `openssf_scorecard.json` (julho):
    presença por check (score > 0), None se sem varredura, check ausente ou
    score < 0 (inconclusivo). Leitura de cache apenas — nunca reconsulta."""
    rows = []
    for repo in repos:
        f = Path(cache_root) / repo.replace("/", "__") / "openssf_scorecard.json"
        row: dict = {"repo": repo}
        checks: dict[str, float] = {}
        if f.exists():
            try:
                data = json.loads(f.read_text()).get("data") or {}
            except json.JSONDecodeError:
                data = {}
            for c in (data.get("checks") or []) if isinstance(data, dict) else []:
                if c.get("name") and c.get("score") is not None:
                    checks[c["name"]] = float(c["score"])
        for key, (_, _, name) in SCORECARD_CHECKS.items():
            s = checks.get(name)
            row[key] = None if s is None or s < 0 else s > 0
        rows.append(row)
    return rows


# ------------------------------------------------------------- comparação
def compare_records(v1: list[dict], v2: list[dict], sample_entries: list[dict],
                    ext_rows: list[dict] | None = None,
                    min_rank_move: int = MIN_RANK_MOVE) -> dict:
    """Comparação completa v1×v2 sobre a interseção de repositórios (ordem
    de v1). Arquétipo: da amostra (`sample_entries`), com fallback ao próprio
    registro. Resultado serializável em JSON."""
    v1_by = {r["repo"]: r for r in v1}
    v2_by = {r["repo"]: r for r in v2}
    arch_of = {e["repo"]: e.get("archetype") for e in (sample_entries or [])}
    for r in list(v2) + list(v1):
        arch_of.setdefault(r["repo"], r.get("archetype"))
    repos = [r["repo"] for r in v1 if r["repo"] in v2_by]
    arch = {repo: arch_of.get(repo) or "?" for repo in repos}

    res: dict = {
        "n_v1": len(v1), "n_v2": len(v2), "n_common": len(repos),
        "missing_in_v2": [r["repo"] for r in v1 if r["repo"] not in v2_by],
        "missing_in_v1": [r["repo"] for r in v2 if r["repo"] not in v1_by],
        "remeasured_at": sorted({v2_by[r].get("remeasured_at") for r in repos
                                 if v2_by[r].get("remeasured_at")}),
        "catalog_version": dict(Counter(
            v2_by[r].get("catalog_version") for r in repos)),
        "min_rank_move": min_rank_move,
    }

    # --- trocas por item × arquétipo (duas direções) ----------------------
    items: dict = {}
    t2f_all: list[dict] = []
    n_f2t = n_t2f = 0
    for item in ITEMS:
        entry: dict = {"section": ITEM_SECTION[item], "v1_true": 0,
                       "v2_true": 0, "false_to_true": [], "true_to_false": [],
                       "by_archetype": {a: {"n": 0, "v1_true": 0, "v2_true": 0,
                                            "false_to_true": [],
                                            "true_to_false": []}
                                        for a in ARCHETYPES}}
        for repo in repos:
            a = arch[repo]
            by = entry["by_archetype"].setdefault(
                a, {"n": 0, "v1_true": 0, "v2_true": 0,
                    "false_to_true": [], "true_to_false": []})
            by["n"] += 1
            b1, b2 = _item(v1_by[repo], item), _item(v2_by[repo], item)
            entry["v1_true"] += b1
            entry["v2_true"] += b2
            by["v1_true"] += b1
            by["v2_true"] += b2
            if b1 != b2:
                key = "false_to_true" if b2 else "true_to_false"
                entry[key].append(repo)
                by[key].append(repo)
                if b2:
                    n_f2t += 1
                else:
                    n_t2f += 1
                    t2f_all.append({"repo": repo, "archetype": a,
                                    "item": item})
        items[item] = entry
    res["items"] = items
    res["n_false_to_true"] = n_f2t
    res["n_true_to_false"] = n_t2f
    res["true_to_false_all"] = t2f_all

    # --- herdados -----------------------------------------------------------
    inherited: dict = {}
    for item in INHERITABLE:
        v1_repos = [r for r in repos if _inherited(v1_by[r], item)]
        v2_repos = [r for r in repos if _inherited(v2_by[r], item)]
        inherited[item] = {
            "v1": len(v1_repos), "v2": len(v2_repos),
            "v1_repos": v1_repos, "v2_repos": v2_repos,
            "by_archetype": {a: {"v1": sum(1 for r in v1_repos if arch[r] == a),
                                 "v2": sum(1 for r in v2_repos if arch[r] == a)}
                             for a in ARCHETYPES}}
    res["inherited"] = inherited

    # --- trocas por repositório ----------------------------------------------
    flips: list[dict] = []
    inconsistent: list[str] = []
    for repo in repos:
        r1, r2 = v1_by[repo], v2_by[repo]
        changes = {}
        for item in ITEMS:
            b1, b2 = _item(r1, item), _item(r2, item)
            if b1 != b2:
                changes[item] = {"v1": b1, "v2": b2,
                                 "inherited_v2": _inherited(r2, item)}
        for section, its in (("artifacts", D1_ITEMS), ("security", D5_ITEMS)):
            saved = r2.get(f"v1_{section}")
            if saved is not None and any(
                    bool(saved.get(i)) != bool((r1.get(section) or {}).get(i))
                    for i in its):
                inconsistent.append(repo)
                break
        if not changes:
            continue
        s1, s2 = r1.get("score"), r2.get("score")
        flips.append({
            "repo": repo, "archetype": arch[repo], "changes": changes,
            "n_changes": len(changes),
            "score_v1": s1, "score_v2": s2,
            "delta_score": (s2 - s1) if s1 is not None and s2 is not None
            else None,
            "d1_v1": _metric(r1, "subscore_artifacts"),
            "d1_v2": _metric(r2, "subscore_artifacts"),
            "d5_v1": _metric(r1, "subscore_security"),
            "d5_v2": _metric(r2, "subscore_security"),
            "v2_source": r2.get("v2_source"),
            "epoch_status": r2.get("epoch_status"),
        })
    flips.sort(key=lambda f: -abs(f["delta_score"] or 0))
    res["repo_flips"] = flips
    res["n_repos_changed"] = len(flips)
    res["inconsistent_v1_copy"] = inconsistent

    deltas = {repo: (v2_by[repo]["score"] - v1_by[repo]["score"])
              for repo in repos
              if v1_by[repo].get("score") is not None
              and v2_by[repo].get("score") is not None}
    res["delta_score"] = {"all": describe(list(deltas.values()))}
    for a in ARCHETYPES:
        res["delta_score"][a] = describe(
            [d for r, d in deltas.items() if arch[r] == a])

    # --- estatísticas por arquétipo -----------------------------------------
    stats: dict = {}
    for metric in METRICS:
        stats[metric] = {"all": {
            "v1": describe([_metric(v1_by[r], metric) for r in repos]),
            "v2": describe([_metric(v2_by[r], metric) for r in repos])}}
        for a in ARCHETYPES:
            sub = [r for r in repos if arch[r] == a]
            stats[metric][a] = {
                "v1": describe([_metric(v1_by[r], metric) for r in sub]),
                "v2": describe([_metric(v2_by[r], metric) for r in sub])}
    res["stats"] = stats

    # --- ρ de Spearman v1×v2 e deslocamentos de ranking ---------------------
    sp: dict = {}
    for metric in METRICS:
        xs = [_metric(v1_by[r], metric) for r in repos]
        ys = [_metric(v2_by[r], metric) for r in repos]
        sp[metric] = {"rho": _rho(xs, ys),
                      "n": sum(1 for x, y in zip(xs, ys)
                               if x is not None and y is not None)}
    res["spearman"] = sp

    ranked = [r for r in repos if r in deltas]
    rk1 = _rank_desc([v1_by[r]["score"] for r in ranked])
    rk2 = _rank_desc([v2_by[r]["score"] for r in ranked])
    moves = [{"repo": r, "archetype": arch[r], "rank_v1": a1, "rank_v2": a2,
              "delta_rank": a2 - a1, "score_v1": v1_by[r]["score"],
              "score_v2": v2_by[r]["score"]}
             for r, a1, a2 in zip(ranked, rk1, rk2)]
    res["ranks"] = {
        "n": len(ranked),
        "max_abs_delta": max((abs(m["delta_rank"]) for m in moves), default=0),
        "moved": sorted([m for m in moves
                         if abs(m["delta_rank"]) >= min_rank_move],
                        key=lambda m: -abs(m["delta_rank"])),
    }

    # --- época ---------------------------------------------------------------
    cutoffs = sorted(v2_by[r].get("epoch_cutoff") for r in repos
                     if v2_by[r].get("epoch_cutoff"))
    until = [r for r in repos if v2_by[r].get("epoch_until_sha")]
    res["epoch"] = {
        "status": dict(Counter(v2_by[r].get("epoch_status") for r in repos)),
        "resolver_step": dict(Counter(
            v2_by[r].get("epoch_resolver_step") for r in repos)),
        "cutoff_source": dict(Counter(
            v2_by[r].get("epoch_cutoff_source") for r in repos)),
        "v2_source": dict(Counter(v2_by[r].get("v2_source") for r in repos)),
        "cutoff_min": cutoffs[0] if cutoffs else None,
        "cutoff_max": cutoffs[-1] if cutoffs else None,
        "unverified": [{"repo": r, "archetype": arch[r],
                        "probes": v2_by[r].get("epoch_unverified_probes") or []}
                       for r in repos
                       if v2_by[r].get("epoch_status") == "unverified"],
        "unreachable": [{"repo": r, "archetype": arch[r],
                         "note": v2_by[r].get("epoch_note")}
                        for r in repos
                        if v2_by[r].get("epoch_status")
                        not in ("ok", "unverified")],
        "n_until_available": len(until),
        "until_divergent": [r for r in until
                            if v2_by[r]["epoch_until_sha"]
                            != v2_by[r].get("epoch_sha")],
    }

    # --- flags não pontuadas -------------------------------------------------
    flag_repos: dict[str, list[str]] = {}
    ci: Counter = Counter()
    tools: Counter = Counter()
    org_items: Counter = Counter()
    symlinks = []
    for r in repos:
        meta = v2_by[r].get("v2_meta") or {}
        for flag, on in (meta.get("flags") or {}).items():
            if on:
                flag_repos.setdefault(flag, []).append(r)
        ci.update(meta.get("ci_systems") or [])
        tools.update(meta.get("dependency_tools") or [])
        org_items.update(meta.get("inherited_from_org") or [])
        if meta.get("symlink_hits"):
            symlinks.append({"repo": r, "paths": list(meta["symlink_hits"])})
    res["flags"] = {
        "flags": {f: {"n": len(rs), "repos": rs}
                  for f, rs in sorted(flag_repos.items())},
        "ci_systems": dict(sorted(ci.items())),
        "dependency_tools": dict(sorted(tools.items())),
        "inherited_from_org": dict(sorted(org_items.items())),
        "symlink_hits": symlinks,
    }

    # --- asserção: perfil 100 % ⇒ issue_template -----------------------------
    def _h100_no_tpl(by: dict) -> list[str]:
        return [r for r in repos
                if (by[r].get("artifacts") or {}).get("health_percentage") == 100
                and not _item(by[r], "issue_template")]
    res["assertions"] = {"health100_no_issue_template": {
        "v1": _h100_no_tpl(v1_by), "v2": _h100_no_tpl(v2_by)}}

    # --- cross-checks externos (opcionais, descritivos) ----------------------
    res["external"] = _external_crosscheck(ext_rows, repos, v1_by, v2_by) \
        if ext_rows else None
    return res


def _external_crosscheck(ext_rows: list[dict], repos: list[str],
                         v1_by: dict, v2_by: dict) -> dict:
    ext_by = {e["repo"]: e for e in ext_rows}
    out: dict = {}
    for key, (section, item, name) in SCORECARD_CHECKS.items():
        avail = [r for r in repos
                 if r in ext_by and ext_by[r].get(key) is not None]
        if not avail:
            continue
        entry: dict = {"check": name, "item": item, "n": len(avail)}
        for tag, by in (("v1", v1_by), ("v2", v2_by)):
            ours_t_ext_f, ours_f_ext_t = [], []
            for r in avail:
                ours, ext = bool((by[r].get(section) or {}).get(item)), \
                    bool(ext_by[r][key])
                if ours and not ext:
                    ours_t_ext_f.append(r)
                elif ext and not ours:
                    ours_f_ext_t.append(r)
            entry[tag] = {"agree": len(avail) - len(ours_t_ext_f)
                          - len(ours_f_ext_t),
                          "ours_true_ext_false": ours_t_ext_f,
                          "ours_false_ext_true": ours_f_ext_t}
        out[key] = entry
    return out


# ---------------------------------------------------------------- relatório
def _f(v, nd: int = 3) -> str:
    return f"{v:.{nd}f}" if v is not None else "—"


def _lst(repos: list[str], empty: str = "nenhum") -> str:
    return ", ".join(f"`{r}`" for r in repos) if repos else empty


def _desc_cells(d: dict, nd: int = 1) -> str:
    """Células `n | média | mediana | dp | Q1 | Q3 | mín | máx`."""
    return (f"{d['n']} | {_f(d['mean'], nd)} | {_f(d['median'], nd)} | "
            f"{_f(d['sd'], nd)} | {_f(d['q1'], nd)} | {_f(d['q3'], nd)} | "
            f"{_f(d['min'], nd)} | {_f(d['max'], nd)}")


def _desc_row(label: str, tag: str, d: dict, nd: int = 1) -> str:
    return f"| {label} | {tag} | {_desc_cells(d, nd)} |"


def report(res: dict) -> str:
    """Relatório PT-BR para results/reparo_v1_v2.md (protocolo, passo 5)."""
    lines = ["# Reparo v1→v2 (catálogo v2)", ""]
    ep = res["epoch"]
    lines += [
        f"Registros comparados: **{res['n_common']}** (v1 = {res['n_v1']}, "
        f"v2 = {res['n_v2']}); re-medição em "
        f"{', '.join(res['remeasured_at']) or 'n/d'}; cortes de época entre "
        f"{ep.get('cutoff_min') or 'n/d'} e {ep.get('cutoff_max') or 'n/d'}. "
        "Escopo: apenas os 12 itens binários de D1/D5 (regras no registro "
        "de decisão de 2026-09-13); D2, D3, D4, stars, forks, releases e "
        "`health_percentage` copiados de v1; catálogo (itens, limiares, "
        "pesos) intacto.", ""]
    if res["missing_in_v2"] or res["missing_in_v1"]:
        lines += [f"Fora da interseção — só em v1: "
                  f"{_lst(res['missing_in_v2'], 'nenhum')}; "
                  f"só em v2: {_lst(res['missing_in_v1'], 'nenhum')}.", ""]
    if res.get("inconsistent_v1_copy"):
        lines += ["⚠️ `v1_artifacts`/`v1_security` do registro v2 divergem do "
                  f"arquivo v1 em: {_lst(res['inconsistent_v1_copy'])}.", ""]

    # 1. ρ
    sp, rk = res["spearman"], res["ranks"]
    lines += ["## 1. Correlação v1×v2 (ρ de Spearman)", "",
              "| métrica | n | ρ |", "|---|---|---|"]
    for m in METRICS:
        lines.append(f"| {m} | {sp[m]['n']} | {_f(sp[m]['rho'])} |")
    lines += ["",
              f"Deslocamento máximo de ranking (score): "
              f"**{_f(rk['max_abs_delta'], 1)}** posições (n = {rk['n']}); "
              f"repositórios que se movem ≥ {res['min_rank_move']} posições: "
              f"{len(rk['moved'])}.", ""]
    if rk["moved"]:
        lines += ["| repo | arquétipo | posição v1 | posição v2 | Δ | "
                  "score v1 | score v2 |", "|---|---|---|---|---|---|---|"]
        for m in rk["moved"]:
            lines.append(f"| `{m['repo']}` | {m['archetype']} | "
                         f"{_f(m['rank_v1'], 1)} | {_f(m['rank_v2'], 1)} | "
                         f"{m['delta_rank']:+.1f} | {_f(m['score_v1'], 1)} | "
                         f"{_f(m['score_v2'], 1)} |")
        lines.append("")

    # 2. trocas por item × arquétipo
    items = res["items"]
    lines += ["## 2. Trocas por item × arquétipo (duas direções)", "",
              f"Repositórios com ≥ 1 troca: **{res['n_repos_changed']}**; "
              f"trocas False→True: **{res['n_false_to_true']}**; "
              f"True→False: **{res['n_true_to_false']}**.", "",
              "| item | dimensão | v1 True | v2 True | F→T | T→F | herdados v2 |",
              "|---|---|---|---|---|---|---|"]
    for item, e in items.items():
        inh = res["inherited"].get(item, {}).get("v2", 0)
        dim = "D1" if e["section"] == "artifacts" else "D5"
        lines.append(f"| {item} | {dim} | {e['v1_true']} | {e['v2_true']} | "
                     f"{len(e['false_to_true'])} | {len(e['true_to_false'])} | "
                     f"{inh} |")
    lines += ["", "| item | arquétipo | n | v1 True | v2 True | F→T | T→F |",
              "|---|---|---|---|---|---|---|"]
    for item, e in items.items():
        for a in ARCHETYPES:
            by = e["by_archetype"].get(a)
            if not by:
                continue
            lines.append(f"| {item} | {a} | {by['n']} | {by['v1_true']} | "
                         f"{by['v2_true']} | {len(by['false_to_true'])} | "
                         f"{len(by['true_to_false'])} |")
    lines += ["", "### Trocas False→True (nominais, por item)", ""]
    any_f2t = False
    for item, e in items.items():
        if not e["false_to_true"]:
            continue
        any_f2t = True
        lines.append(f"- **{item}** ({len(e['false_to_true'])}): "
                     + "; ".join(
                         f"{a}: " + _lst(e["by_archetype"][a]["false_to_true"])
                         for a in ARCHETYPES
                         if e["by_archetype"].get(a, {}).get("false_to_true")))
    if not any_f2t:
        lines.append("nenhuma")
    lines.append("")

    # 3. T→F
    lines += ["## 3. Trocas True→False", ""]
    if res["true_to_false_all"]:
        lines += ["Toda troca neste sentido é listada nominalmente e exige "
                  "inspeção (esperado: nenhuma — as regras v2 são "
                  "extensões documentadas das v1).", "",
                  "| repo | arquétipo | item |", "|---|---|---|"]
        lines += [f"| `{t['repo']}` | {t['archetype']} | {t['item']} |"
                  for t in res["true_to_false_all"]]
    else:
        lines.append("nenhuma")
    lines.append("")

    # 4. herdados
    lines += ["## 4. Herdados de `{owner}/.github`", "",
              "| item | v1 | v2 | repositórios (v2) |", "|---|---|---|---|"]
    for item, h in res["inherited"].items():
        lines.append(f"| {item} | {h['v1']} | {h['v2']} | "
                     f"{_lst(h['v2_repos'])} |")
    lines.append("")

    # 5. estatísticas por arquétipo
    lines += ["## 5. Estatísticas por arquétipo (v1 vs v2)", ""]
    for metric in METRICS:
        nd = 1 if metric == "score" else 3
        lines += [f"### {metric}", "",
                  "| arquétipo | versão | n | média | mediana | dp | Q1 | Q3 | "
                  "mín | máx |", "|---|---|---|---|---|---|---|---|---|---|"]
        for a in ("all",) + ARCHETYPES:
            st = res["stats"][metric].get(a)
            if not st:
                continue
            label = "todos" if a == "all" else a
            lines.append(_desc_row(label, "v1", st["v1"], nd))
            lines.append(_desc_row(label, "v2", st["v2"], nd))
        lines.append("")
    ds = res["delta_score"]
    lines += ["### Δ score (v2 − v1)", "",
              "| arquétipo | n | média | mediana | dp | Q1 | Q3 | mín | máx |",
              "|---|---|---|---|---|---|---|---|---|"]
    for a in ("all",) + ARCHETYPES:
        d = ds.get(a)
        if d:
            lines.append(f"| {'todos' if a == 'all' else a} | "
                         f"{_desc_cells(d, 2)} |")
    lines.append("")

    # 6. maiores deslocamentos
    lines += ["## 6. Maiores deslocamentos de score", ""]
    top = res["repo_flips"][:10]
    if top:
        lines += ["| repo | arquétipo | itens alterados | score v1 | score v2 "
                  "| Δ | D1 v1→v2 | D5 v1→v2 |", "|---|---|---|---|---|---|---|---|"]
        for fl in top:
            its = ", ".join(f"{i} {'F→T' if c['v2'] else 'T→F'}"
                            + (" (herdado)" if c["inherited_v2"] else "")
                            for i, c in fl["changes"].items())
            lines.append(f"| `{fl['repo']}` | {fl['archetype']} | {its} | "
                         f"{_f(fl['score_v1'], 1)} | {_f(fl['score_v2'], 1)} | "
                         f"{_f(fl['delta_score'], 2)} | "
                         f"{_f(fl['d1_v1'], 2)}→{_f(fl['d1_v2'], 2)} | "
                         f"{_f(fl['d5_v1'], 2)}→{_f(fl['d5_v2'], 2)} |")
    else:
        lines.append("nenhum repositório teve troca de item.")
    lines.append("")

    # 7. época
    lines += ["## 7. Época", "",
              "| estatística | contagens |", "|---|---|"]
    for key, label in (("status", "epoch_status"),
                       ("resolver_step", "passo do resolvedor"),
                       ("cutoff_source", "fonte do corte"),
                       ("v2_source", "fonte dos itens (v2_source)")):
        cnt = ", ".join(f"{k if k is not None else 'n/d'}: {n}"
                        for k, n in sorted(ep[key].items(),
                                           key=lambda kv: (-kv[1], str(kv[0]))))
        lines.append(f"| {label} | {cnt or '—'} |")
    lines += ["",
              f"Divergências first-parent × `until` (cross-check REST, quando "
              f"disponível): {len(ep['until_divergent'])} de "
              f"{ep['n_until_available']}"
              + (" — " + _lst(ep["until_divergent"])
                 if ep["until_divergent"] else "") + ".", "",
              "Não verificados (blob v1 divergente na árvore de época; itens "
              "v1 mantidos): "
              + (", ".join(f"`{u['repo']}` ({', '.join(u['probes']) or 'n/d'})"
                           for u in ep["unverified"]) or "nenhum") + ".", "",
              "Inacessíveis (itens v1 mantidos): "
              + (", ".join(f"`{u['repo']}`" + (f" — {u['note']}" if u["note"]
                                                else "")
                           for u in ep["unreachable"]) or "nenhum") + ".", ""]

    # 8. cross-checks
    lines += ["## 8. Cross-checks descritivos", ""]
    a = res["assertions"]["health100_no_issue_template"]
    lines += [f"Asserção `health_percentage = 100 ⇒ issue_template`: violada "
              f"em v1 por {len(a['v1'])} repositórios ({_lst(a['v1'])}); em v2 "
              f"por {len(a['v2'])} ({_lst(a['v2'])}).", ""]
    ext = res.get("external")
    if ext:
        lines += ["Concordância com checks do OpenSSF Scorecard (cache de "
                  "julho; presença = score do check > 0; descritivo — "
                  "sobreposição parcial das regras de D5 com os checks "
                  "declarada):", "",
                  "| check | item | n | concordância v1 | concordância v2 | "
                  "nosso True / Scorecard False (v2) | nosso False / "
                  "Scorecard True (v2) |", "|---|---|---|---|---|---|---|"]
        for e in ext.values():
            lines.append(
                f"| {e['check']} | {e['item']} | {e['n']} | "
                f"{e['v1']['agree']}/{e['n']} | {e['v2']['agree']}/{e['n']} | "
                f"{_lst(e['v2']['ours_true_ext_false'])} | "
                f"{_lst(e['v2']['ours_false_ext_true'])} |")
    else:
        lines.append("Checks do Scorecard não fornecidos (cross-check omitido).")
    lines.append("")

    # 9. flags
    fl = res["flags"]
    lines += ["## 9. Flags não pontuadas (sensibilidades declaradas)", ""]
    if fl["flags"]:
        lines += ["| flag | n | repositórios |", "|---|---|---|"]
        lines += [f"| {f} | {v['n']} | {_lst(v['repos'])} |"
                  for f, v in fl["flags"].items()]
    else:
        lines.append("nenhuma flag ativa.")
    lines += ["",
              "Sistemas de CI reconhecidos: "
              + (", ".join(f"{k} {n}" for k, n in fl["ci_systems"].items())
                 or "—") + ".",
              "Ferramentas de automação de dependências: "
              + (", ".join(f"{k} {n}" for k, n in fl["dependency_tools"].items())
                 or "—") + ".",
              "Itens herdados por origem (`inherited_from_org`): "
              + (", ".join(f"{k} {n}" for k, n
                           in fl["inherited_from_org"].items()) or "—") + ".",
              "Symlinks entre os arquivos casados: "
              + (", ".join(f"`{s['repo']}` ({', '.join(s['paths'])})"
                           for s in fl["symlink_hits"]) or "nenhum") + ".", ""]

    # 10. por repositório
    lines += ["## 10. Trocas por repositório (auditoria completa)", ""]
    if res["repo_flips"]:
        lines += ["| repo | arquétipo | fonte | itens alterados | Δ score |",
                  "|---|---|---|---|---|"]
        for fl_ in sorted(res["repo_flips"], key=lambda f: f["repo"].lower()):
            its = ", ".join(f"{i} {'F→T' if c['v2'] else 'T→F'}"
                            + (" (herdado)" if c["inherited_v2"] else "")
                            for i, c in fl_["changes"].items())
            lines.append(f"| `{fl_['repo']}` | {fl_['archetype']} | "
                         f"{fl_['v2_source']} | {its} | "
                         f"{_f(fl_['delta_score'], 2)} |")
    else:
        lines.append("nenhuma.")
    lines.append("")
    return "\n".join(lines)
