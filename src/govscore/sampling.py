"""Amostragem estratificada por arquétipo (plano de pesquisa, §3.1–3.2).

Fluxo: Search API (universo por estrato de stars × linguagem) → triagem de
não-software (tópicos/nome) → classificação pelo proxy de contribuidores
ativos (≥2 commits/12m, bots excluídos) × stars → preenchimento de quotas
com diversidade de linguagem e de owner.

CUIDADO METODOLÓGICO: a presença de artefatos de governança NÃO é critério
de inclusão (é variável dependente — viés de seleção). Critérios: atividade
em 12 meses + repositório público, apenas.

Casos ambíguos (fora das faixas da §3.1 ou com contagem truncada) vão para a
lista `ambiguous` do arquivo gerado, para inspeção manual documentada.
"""
from __future__ import annotations

import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

from govscore.github_client import GitHubClient

ROOT = Path(__file__).resolve().parents[2]
ARCHETYPES = ("federation", "stadium", "club", "toy")
SEARCH_REPO = "_sampling"  # pseudo-repo para o cache em data/raw/_sampling/


def load_sampling_config() -> dict:
    return yaml.safe_load((ROOT / "config" / "sampling.yaml").read_text())


# ------------------------------------------------------------- classificação
def is_bot_login(ident: str) -> bool:
    ident = ident.lower()
    return ident.endswith("bot") or ident.endswith("[bot]")


def classify(active_2plus: int, stars: int, t: dict) -> str | None:
    """Matriz de arquétipos da §3.1. None = fora das faixas (ambíguo)."""
    if stars >= t["stars_high_min"]:
        if active_2plus >= t["federation_min_contributors"]:
            return "federation"
        if active_2plus <= t["stadium_max_contributors"]:
            return "stadium"
        return None
    if stars < t["toy_stars_max"] and active_2plus <= t["toy_max_contributors"]:
        return "toy"
    if stars < t["club_stars_max"] and active_2plus >= t["club_min_contributors"]:
        return "club"
    return None


def commit_author_counts(pages: list[list[dict]]) -> Counter:
    """Agrega autores de páginas de /commits (login; fallback e-mail do git).

    Bots são excluídos — CHAOSS recomenda contagem humana; sem isto um
    Brinquedo com Dependabot ativo deixaria de ser ≤3.
    """
    counts: Counter = Counter()
    for page in pages:
        for c in page:
            ident = ((c.get("author") or {}).get("login")
                     or ((c.get("commit") or {}).get("author") or {}).get("email")
                     or "")
            ident = ident.strip().lower()
            if not ident or is_bot_login(ident):
                continue
            counts[ident] += 1
    return counts


def count_active_contributors(gh: GitHubClient, repo: str, since_iso: str,
                              t: dict, max_pages: int = 30) -> tuple[int, bool, int]:
    """(autores com ≥ min_commits na janela, contagem truncada?, nº commits).

    Early stop ao confirmar Federação; teto de páginas para repositórios de
    altíssimo volume (capped=True → decisão vai para inspeção manual, exceto
    se a Federação já estiver confirmada). O nº de commits do branch default
    na janela sustenta o critério de inclusão de atividade (§3.2, item 3).
    """
    min_c = t["min_commits_per_contributor"]
    stop_at = t["federation_min_contributors"]
    pages: list[list[dict]] = []
    n_commits = 0
    for page in range(1, max_pages + 1):
        try:
            batch = gh.get(repo, f"/repos/{repo}/commits",
                           f"commits_12m_p{page:02d}",
                           params={"since": since_iso, "per_page": 100,
                                   "page": page}) or []
        except requests.HTTPError:
            break  # 409 repo vazio etc. — trata como sem commits adicionais
        pages.append(batch)
        n_commits += len(batch)
        qualifying = sum(1 for v in commit_author_counts(pages).values()
                         if v >= min_c)
        if qualifying >= stop_at:
            return qualifying, False, n_commits
        if len(batch) < 100:
            return qualifying, False, n_commits
    return (sum(1 for v in commit_author_counts(pages).values() if v >= min_c),
            True, n_commits)


# ------------------------------------------------------------------- triagem
def screen(item: dict, excl: dict) -> str | None:
    """Retorna o motivo de exclusão, ou None se o candidato passa."""
    name = item.get("full_name") or ""
    if name in set(excl.get("repos") or []):
        return "repo piloto (out-of-sample)"
    if item.get("fork"):
        return "fork"
    if item.get("archived"):
        return "arquivado"
    if item.get("is_template"):
        return "template"
    if item.get("mirror_url"):
        return "mirror"
    if not item.get("language"):
        return "sem linguagem detectada (proxy de não-software)"
    topics = {s.lower() for s in item.get("topics") or []}
    hit = topics & {s.lower() for s in excl.get("topics") or []}
    if hit:
        return f"tópico excluído: {sorted(hit)[0]}"
    short = name.split("/")[-1].lower()
    for pat in excl.get("name_patterns") or []:
        if re.search(pat, short):
            return f"padrão de nome excluído: {pat}"
    return None


# --------------------------------------------------------------------- busca
def _cached_search(gh: GitHubClient, key: str, params: dict) -> list[dict]:
    fresh = not gh._cache_path(SEARCH_REPO, key).exists()
    data = gh.get(SEARCH_REPO, "/search/repositories", key, params=params)
    if fresh:
        time.sleep(2.2)  # Search API: 30 req/min autenticado
    return (data or {}).get("items") or []


def search_stratum(gh: GitHubClient, stratum: str, cfg: dict,
                   pushed_since: str) -> list[dict]:
    s = cfg["search"]
    queries = {
        "high": f"stars:>={cfg['thresholds']['stars_high_min']}",
        "club": f"stars:{s['club_stars_min']}..{cfg['thresholds']['club_stars_max'] - 1}",
        "toy": f"stars:{s['toy_stars_min']}..{cfg['thresholds']['toy_stars_max'] - 1}",
    }
    pages = s[f"pages_{stratum}"]
    sort = "updated" if stratum == "toy" else "stars"
    items: dict[str, dict] = {}
    for lang in s["languages"]:
        for page in range(1, pages + 1):
            q = (f"{queries[stratum]} language:{lang} pushed:>={pushed_since} "
                 f"fork:false archived:false")
            key = f"search_{stratum}_{lang}_p{page}"
            for item in _cached_search(
                    gh, key, {"q": q, "sort": sort, "order": "desc",
                              "per_page": s["per_page"], "page": page}):
                item["_search_language"] = lang
                items.setdefault(item["full_name"], item)
    return list(items.values())


# ----------------------------------------------------------- montagem final
def _interleave_by_language(cands: list[dict]) -> list[dict]:
    """Round-robin entre linguagens (diversidade §3.2); stars desc em cada."""
    by_lang: dict[str, list[dict]] = defaultdict(list)
    for c in cands:
        by_lang[c["_search_language"]].append(c)
    for lst in by_lang.values():
        lst.sort(key=lambda c: -c.get("stargazers_count", 0))
    order = sorted(by_lang)
    out, i = [], 0
    while any(by_lang[lang] for lang in order):
        lang = order[i % len(order)]
        if by_lang[lang]:
            out.append(by_lang[lang].pop(0))
        i += 1
    return out


def build_sample(gh: GitHubClient, cfg: dict, quota: int) -> dict:
    t = cfg["thresholds"]
    now = datetime.now(timezone.utc)
    since_iso = (now - timedelta(days=cfg["window_days"])).strftime("%Y-%m-%dT%H:%M:%SZ")
    pushed_since = since_iso[:10]
    today = now.strftime("%Y-%m-%d")

    selected: dict[str, list[dict]] = {a: [] for a in ARCHETYPES}
    ambiguous: list[dict] = []
    owner_count: Counter = Counter()
    lang_count: dict[str, Counter] = {a: Counter() for a in ARCHETYPES}
    max_lang = cfg["diversity"]["max_per_language"]
    max_owner = cfg["diversity"]["max_per_owner"]
    max_pages = cfg["classification"]["max_commit_pages"]

    strata_targets = {"high": ("federation", "stadium"),
                      "club": ("club",), "toy": ("toy",)}

    for stratum, targets in strata_targets.items():
        candidates = _interleave_by_language(
            search_stratum(gh, stratum, cfg, pushed_since))
        print(f"[{stratum}] {len(candidates)} candidatos após busca",
              file=sys.stderr)
        for item in candidates:
            if all(len(selected[a]) >= quota for a in targets):
                break
            reason = screen(item, cfg["exclusions"])
            if reason:
                continue
            repo = item["full_name"]
            owner = repo.split("/")[0]
            lang = item["_search_language"]
            if owner_count[owner] >= max_owner:
                continue
            active, capped, n_commits = count_active_contributors(
                gh, repo, since_iso, t, max_pages)
            stars = item.get("stargazers_count", 0)
            arch = classify(active, stars, t)
            entry = {
                "repo": repo, "language": lang, "stars": stars,
                "active_contributors_2plus": active,
                "classified_at": today,
            }
            if n_commits == 0:
                # pushed: da busca captura branches secundárias; o critério de
                # inclusão (§3.2, item 3) exige atividade de commits na janela
                entry["reason"] = "sem commits no branch default na janela"
                ambiguous.append(entry)
                continue
            if capped and arch != "federation":
                entry["reason"] = (f"contagem truncada em {max_pages * 100} "
                                   "commits — confirmar manualmente")
                ambiguous.append(entry)
                continue
            if arch is None:
                entry["reason"] = "fora das faixas da §3.1"
                ambiguous.append(entry)
                continue
            if arch not in targets or len(selected[arch]) >= quota:
                continue
            if lang_count[arch][lang] >= max_lang:
                continue
            entry["archetype"] = arch
            entry["classification_notes"] = (
                f"auto: {active} contribuidores ≥2 commits/12m, {stars} stars "
                f"(limiares §3.1)")
            selected[arch].append(entry)
            owner_count[owner] += 1
            lang_count[arch][lang] += 1
            done = sum(len(v) for v in selected.values())
            print(f"  ✓ {repo} → {arch} ({active} ativos, {stars}★) "
                  f"[{done}/{quota * 4}]", file=sys.stderr)

    full = [e for a in ARCHETYPES for e in selected[a]]
    return {
        "generated_at": today,
        "window_days": cfg["window_days"],
        "thresholds": t,
        "counts": {a: len(selected[a]) for a in ARCHETYPES},
        "full": full,
        "ambiguous": ambiguous,
    }


def write_sample(result: dict, path: Path) -> None:
    header = (
        "# GERADO por `govscore sample` — amostra estratificada (plano §3.1–3.2).\n"
        "# Edições manuais permitidas apenas em casos ambíguos, com nota em\n"
        "# classification_notes (decisão de pesquisa auditável).\n")
    path.write_text(header + yaml.safe_dump(
        result, allow_unicode=True, sort_keys=False, width=88))
