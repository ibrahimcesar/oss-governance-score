"""Indicadores externos de validação (item 7; plano §6.1).

Nenhum indicador aqui entra no cálculo do score (independência):
- stars/forks: metadata já extraída (proxy fraco de popularidade — declarar);
- dependentes: API deps.dev (adoção real por terceiros — o indicador
  conceitualmente mais forte);
- OpenSSF Scorecard: api.securityscorecards.dev (validade convergente).

Frequência de releases foi EXCLUÍDA do conjunto de validação: releases_12m
é insumo de D5 desde o catálogo do piloto — usá-la dos dois lados seria
circular (registrar na seção 4.3).

Cache: mesmo padrão do pipeline — toda resposta persiste em
data/raw/{owner}__{repo}/ antes de qualquer análise.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
DEPSDEV = "https://api.deps.dev/v3"
# :dependents só existe na v3alpha (a v3 expõe apenas :dependencies)
DEPSDEV_ALPHA = "https://api.deps.dev/v3alpha"
SCORECARD = "https://api.securityscorecards.dev"
MAX_PACKAGES = 5  # pacotes distintos consultados por repo (declarado)


class CacheMissError(RuntimeError):
    """Indicador externo ausente do cache em modo offline (a análise v2
    nunca reconsulta a rede: os indicadores são os de julho de 2026)."""


def _cache_path(repo: str, key: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", key)
    d = RAW_DIR / repo.replace("/", "__")
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe}.json"


def cached_get_json(repo: str, key: str, url: str,
                    max_retries: int = 3, offline: bool = False) -> dict | None:
    """GET sem autenticação, com cache em disco e retry para transientes.
    404 → None (cacheado: ausência é informação). Transientes esgotados
    levantam erro — nunca são cacheados. Com `offline=True` um cache ausente
    é erro explícito (CacheMissError) — garantia de zero chamadas de rede."""
    cache = _cache_path(repo, key)
    if cache.exists():
        return json.loads(cache.read_text())["data"]
    if offline:
        raise CacheMissError(f"{repo}: '{key}' ausente do cache "
                             f"({cache}) — modo offline")
    attempt = 0
    while True:
        try:
            resp = requests.get(url, timeout=30)
        except (requests.ConnectionError, requests.Timeout):
            if attempt >= max_retries:
                raise
            time.sleep(2 ** attempt)
            attempt += 1
            continue
        if resp.status_code in (429, 500, 502, 503, 504):
            if attempt >= max_retries:
                resp.raise_for_status()
            time.sleep(2 * (attempt + 1))
            attempt += 1
            continue
        if resp.status_code == 404:
            data = None
            break
        resp.raise_for_status()
        data = resp.json()
        break
    cache.write_text(json.dumps(
        {"url": url, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                 time.gmtime()),
         "data": data}, ensure_ascii=False))
    return data


# ---------------------------------------------------------------- deps.dev
# O endpoint projects/:packageversions devolve milhares de republicações e
# "bundled deps" não verificadas (paginado alfabeticamente — o pacote
# canônico pode nem aparecer). Estratégia: resolver o pacote pelo nome do
# repositório no ecossistema da linguagem e EXIGIR que a versão default
# aponte de volta para o repositório (relatedProjects) — sem isso, um repo
# homônimo herdaria dependentes de pacote alheio.
# Cobertura declarada (§8 do plano): Java/MAVEN fica FORA porque a
# coordenada group:artifact não é derivável do nome do repo; Go fica fora
# porque o deps.dev não expõe :dependents para o sistema GO (verificado
# empiricamente — 404 mesmo para módulos populares); C/C++ não têm
# ecossistema de pacotes no deps.dev. O subamostra de dependentes é,
# portanto, restrito a linguagens de scripting + Rust — composição
# reportada no relatório de validação.
LANG_SYSTEM = {"javascript": "NPM", "typescript": "NPM", "python": "PYPI",
               "rust": "CARGO", "ruby": "RUBYGEMS", "php": "PACKAGIST"}


def package_candidates(repo: str, language: str | None) -> list[tuple[str, str]]:
    """Candidatos (system, name) pelo nome do repo no ecossistema da
    linguagem principal."""
    system = LANG_SYSTEM.get((language or "").lower())
    base = repo.split("/")[1].lower()
    owner = repo.split("/")[0].lower()
    if system:
        return [(system, base), (system, f"@{owner}/{base}")
                ] if system == "NPM" else [(system, base)]
    return []


def default_version(pkg_response: dict | None) -> str | None:
    versions = (pkg_response or {}).get("versions") or []
    for v in versions:
        if v.get("isDefault"):
            return (v.get("versionKey") or {}).get("version")
    return (versions[-1].get("versionKey") or {}).get("version") if versions else None


def _numeric_key(version: str) -> tuple:
    parts = re.findall(r"\d+", version)
    return tuple(int(p) for p in parts[:4]) or (0,)


def versions_to_probe(pkg_response: dict | None, cap_majors: int = 5) -> list[str]:
    """Versão mais recente de cada major (+ default), maiores majors primeiro.

    :dependents é POR VERSÃO e não agrega — medir só a default confundiria
    adoção com recência de release (caso react: 19.x ~10² dependentes vs
    18.x ~10⁵). Pré-releases só entram se o major não tiver versão estável.
    """
    versions = [(v.get("versionKey") or {}).get("version")
                for v in (pkg_response or {}).get("versions") or []]
    versions = [v for v in versions if v]
    best: dict[tuple[int, bool], str] = {}
    for v in versions:
        nums = _numeric_key(v)
        stable = "-" not in v
        key = (nums[0], stable)
        if key not in best or _numeric_key(best[key]) < nums:
            best[key] = v
    majors: dict[int, str] = {}
    for (major, stable), v in sorted(best.items()):
        if stable or major not in majors:
            majors[major] = v
    probe = [majors[m] for m in sorted(majors, reverse=True)[:cap_majors]]
    default = default_version(pkg_response)
    if default and default not in probe:
        probe.insert(0, default)
    return probe


def version_matches_repo(version_response: dict | None, repo: str) -> bool:
    """A versão publicada aponta de volta para o repositório?"""
    for rp in (version_response or {}).get("relatedProjects") or []:
        pid = ((rp.get("projectKey") or {}).get("id") or "").lower()
        if pid == f"github.com/{repo}".lower():
            return True
    return False


def fetch_dependents(repo: str, language: str | None = None,
                     offline: bool = False) -> int | None:
    """Máximo de dependentes entre a última versão de cada major do pacote
    canônico verificado do repositório. None = sem pacote verificado no
    deps.dev — limitação de cobertura a declarar (§8 do plano)."""
    counts: list[int] = []
    for system, name in package_candidates(repo, language)[:MAX_PACKAGES]:
        s, n = quote(system, safe=""), quote(name, safe="")
        slug = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{system}_{name}")
        pkg = cached_get_json(repo, f"depsdev_pkg_{slug}",
                              f"{DEPSDEV}/systems/{s}/packages/{n}",
                              offline=offline)
        ver = default_version(pkg)
        if not ver:
            continue
        # verificação pacote↔repo uma vez, na versão default
        v = quote(ver, safe="")
        detail = cached_get_json(repo, f"depsdev_ver_{slug}",
                                 f"{DEPSDEV}/systems/{s}/packages/{n}/versions/{v}",
                                 offline=offline)
        if not version_matches_repo(detail, repo):
            continue
        for probe in versions_to_probe(pkg):
            pv = quote(probe, safe="")
            dep = cached_get_json(
                repo, f"depsdev_dependents_{slug}_{probe}",
                f"{DEPSDEV_ALPHA}/systems/{s}/packages/{n}/versions/{pv}:dependents",
                offline=offline)
            if dep and dep.get("dependentCount") is not None:
                counts.append(int(dep["dependentCount"]))
    return max(counts) if counts else None


# --------------------------------------------------------------- scorecard
def fetch_scorecard(repo: str, offline: bool = False) -> float | None:
    """Score agregado do OpenSSF Scorecard (None se o repo não é varrido)."""
    data = cached_get_json(repo, "openssf_scorecard",
                           f"{SCORECARD}/projects/github.com/{repo}",
                           offline=offline)
    if data and data.get("score") is not None:
        return float(data["score"])
    return None


def fetch_external(repo: str, language: str | None = None,
                   offline: bool = False) -> dict:
    """Indicadores externos do repositório. `offline=True` exige que todos
    estejam em cache (CacheMissError caso contrário) — é o modo da análise
    v2, que reutiliza os indicadores de julho de 2026."""
    return {"repo": repo,
            "dependents": fetch_dependents(repo, language, offline=offline),
            "scorecard": fetch_scorecard(repo, offline=offline)}


# ------------------------------------------------------------ proveniência
# Chaves de cache dos indicadores externos (prefixos dos arquivos JSON)
EXTERNAL_CACHE_GLOBS = ("openssf_scorecard.json", "depsdev_*.json")


def cache_fetched_dates(repo: str) -> list[str]:
    """Datas (YYYY-MM-DD, UTC) em que os indicadores externos do repositório
    foram consultados, lidas do `fetched_at` dos arquivos de cache. Vazio se
    nada está em cache."""
    d = RAW_DIR / repo.replace("/", "__")
    if not d.is_dir():
        return []
    dates: set[str] = set()
    for pattern in EXTERNAL_CACHE_GLOBS:
        for f in d.glob(pattern):
            try:
                fetched = json.loads(f.read_text()).get("fetched_at")
            except (json.JSONDecodeError, OSError):
                continue
            if fetched:
                dates.add(str(fetched)[:10])
    return sorted(dates)


def external_fetched_range(repos: list[str]) -> str | None:
    """Intervalo `min→max` (ou data única) das consultas em cache dos
    indicadores externos — a época honesta para `external_fetched_at` quando
    a validação roda sobre o cache. None se nenhum repositório tem cache."""
    dates = sorted({d for r in repos for d in cache_fetched_dates(r)})
    if not dates:
        return None
    return dates[0] if dates[0] == dates[-1] else f"{dates[0]}→{dates[-1]}"
