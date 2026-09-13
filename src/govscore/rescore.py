"""Re-pontuação com o catálogo v2 — reparo da medição de D1/D5 na época do
snapshot (docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md, protocolo,
passo 4).

Princípio: o registro v1 é a base e permanece VERBATIM — D2, D3, D4, stars,
forks, releases (`releases_12m`, `release_notes_share`), `health_percentage`,
`extracted_at`, `backend`, `window`, arquétipo e linguagem não são
reextraídos. Só os 12 itens binários (9 de D1, 3 de D5) e as anotações
`*_inherited` são substituídos pela detecção v2 (`extract.patterns.detect`)
sobre a lista de blobs da árvore do commit de época (e da árvore de
`{owner}/.github` para a herança). Os valores v1 ficam preservados em
`v1_artifacts`/`v1_security` para a comparação item a item (`compare.py`).

Quando a época não pôde ser verificada contra os blobs de julho ou o
repositório está inacessível (`epoch_status != "ok"`), os 12 itens de v1 são
MANTIDOS (`v2_source = "v1_cache"`) — nunca imputados — e o caso é contado no
relatório de reparo.

A pontuação usa o catálogo congelado (`config/metrics.yaml`, intacto):
`compute_subscores` + `compute_score`, com pesos renormalizados sobre as
dimensões disponíveis, exatamente como em v1.

Campos acrescentados ao registro v2 (todos escalares no nível raiz chegam ao
parquet via `run_full.flatten_record`; dicionários ficam só no JSON):
`catalog_version`, `epoch_sha`, `epoch_cutoff`, `epoch_cutoff_source`,
`epoch_resolver_step`, `epoch_status`, `epoch_until_sha`, `epoch_note`,
`epoch_unverified_probes`, `remeasured_at`, `v2_source`, `v1_artifacts`,
`v1_security`, `v2_meta`.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Iterable

from govscore.score.scoring import compute_score, compute_subscores

CATALOG_VERSION = "v2"

# Itens binários re-medidos (idênticos a config/metrics.yaml — a lista é
# lida do catálogo em tempo de execução; estas constantes documentam o escopo
# e servem ao módulo de comparação).
D1_ITEMS = ("readme", "contributing", "code_of_conduct", "license",
            "issue_template", "pull_request_template", "codeowners",
            "governance", "funding")
D5_ITEMS = ("security_policy", "ci_configured", "dependency_automation")

EPOCH_OK = "ok"
SYMLINK_MODE = "120000"


# ------------------------------------------------------------------ detecção
def _detect(paths: Iterable[str], org_paths: Iterable[str] | None):
    """Indireção para `govscore.extract.patterns.detect` (regras v2, fonte
    única). Importada tardiamente para que os testes substituam a detecção
    por um stub sem depender do módulo de padrões. Os caminhos passam por
    `normalize` (minúsculas, sem `./` inicial) — idempotente se `detect`
    normalizar de novo."""
    from govscore.extract.patterns import detect, normalize
    return detect(normalize(paths),
                  None if org_paths is None else normalize(org_paths))


def _splice(v1_section: dict, v2_section: dict, items: Iterable[str]) -> dict:
    """Substitui só `items` (+ `*_inherited` recalculados) em uma seção v1.

    Tudo o mais (`health_percentage`, `releases_12m`, `release_notes_share`)
    é copiado verbatim; anotações `*_inherited` de v1 são descartadas — a
    herança é redeterminada pela detecção v2 (herdado só quando o repositório
    não tem arquivo próprio)."""
    items = tuple(items)
    out: dict = {}
    for k, v in v1_section.items():
        if k in items:
            out[k] = bool(v2_section[k])
        elif k.endswith("_inherited"):
            continue  # anotação v1 obsoleta
        else:
            out[k] = copy.deepcopy(v)
    for k in items:  # item ausente em v1 (defensivo): entra mesmo assim
        if k not in out:
            out[k] = bool(v2_section[k])
    for k, v in v2_section.items():
        if k.endswith("_inherited") and v:
            out[k] = True
    return out


def _empty_meta() -> dict:
    return {"matched": {}, "flags": {}, "ci_systems": [],
            "dependency_tools": [], "inherited_from_org": []}


# ------------------------------------------------------------- re-pontuação
def rescore_record(v1_record: dict, epoch: dict | None, tree_paths: list[str] | None,
                   org_paths: list[str] | None, cfg: dict,
                   remeasured_at: str) -> dict:
    """Registro v2 a partir do registro v1 (cópia profunda; v1 não é mutado).

    `epoch` é o dicionário de `epoch_commit.json` (M2) — `None` equivale a
    inacessível. O status lido é `epoch_status` ("ok" | "unverified" |
    "unreachable"); na sua ausência vale `status` do resolvedor ("ok" |
    "unreachable" | "no_commit_before_cutoff"), e qualquer valor ≠ "ok"
    mantém os itens v1. `until_candidate_sha` e `note` são opcionais
    (cross-check REST `commits?until=` e motivo da inacessibilidade).
    `tree_paths`/`org_paths` são as listas de blobs (caminhos) da árvore de
    época do repositório e de `{owner}/.github` (`None` em `org_paths` = sem
    repositório especial ⇒ sem herança; `None` em `tree_paths` com época
    "ok" ⇒ tratado como inacessível, com nota).
    """
    rec = copy.deepcopy(v1_record)
    epoch = epoch or {}
    v1_artifacts = copy.deepcopy(v1_record.get("artifacts") or {})
    v1_security = copy.deepcopy(v1_record.get("security") or {})

    status = epoch.get("epoch_status") or epoch.get("status") or "unreachable"
    note = epoch.get("note")
    if status == EPOCH_OK and tree_paths is None:
        status, note = "unreachable", "tree_paths ausente no cache v2"

    d1_items = cfg["artifacts"]["items"]
    d5_items = cfg["security"]["items"]

    if status == EPOCH_OK:
        art_v2, sec_v2, meta = _detect(tree_paths, org_paths)
        rec["artifacts"] = _splice(v1_artifacts, art_v2, d1_items)
        rec["security"] = _splice(v1_security, sec_v2, d5_items)
        rec["v2_source"] = "tree"
        rec["v2_meta"] = copy.deepcopy(meta) if meta else _empty_meta()
    else:
        # itens v1 mantidos (inclusive anotações *_inherited de v1)
        rec["artifacts"] = copy.deepcopy(v1_artifacts)
        rec["security"] = copy.deepcopy(v1_security)
        rec["v2_source"] = "v1_cache"
        rec["v2_meta"] = _empty_meta()

    verification = epoch.get("verification") or {}
    rec["catalog_version"] = CATALOG_VERSION
    rec["epoch_sha"] = epoch.get("sha")
    rec["epoch_cutoff"] = epoch.get("cutoff")
    rec["epoch_cutoff_source"] = epoch.get("cutoff_source")
    rec["epoch_resolver_step"] = epoch.get("resolver_step")
    rec["epoch_status"] = status
    rec["epoch_until_sha"] = epoch.get("until_candidate_sha")
    rec["epoch_note"] = note
    rec["epoch_unverified_probes"] = sorted(
        p for p, v in verification.items()
        if isinstance(v, dict) and v.get("ok") is False)
    rec["remeasured_at"] = remeasured_at
    rec["v1_artifacts"] = v1_artifacts
    rec["v1_security"] = v1_security

    rec["subscores"] = compute_subscores(rec, cfg)
    rec["score"] = compute_score(rec["subscores"], cfg["weights"])
    return rec


# --------------------------------------------------------------- cache v2
def _entries(payload: dict) -> list[dict]:
    return list(payload.get("entries") or [])


def load_v2_cache(cache_root: Path, repo: str) -> dict:
    """Lê os objetos v2 de `cache_root/<owner>__<repo>/v2/` (escritos por
    `extract.epoch.ensure_epoch_artifacts`).

    Retorna {"epoch", "tree_paths", "org_paths", "symlink_paths"}; `epoch` é
    None quando `epoch_commit.json` não existe; `tree_paths` é None quando a
    árvore do sha de época não está em cache; `org_paths` é None quando o
    repositório `{owner}/.github` está ausente/vazio/sem commit ≤ corte.
    """
    d = cache_root / repo.replace("/", "__") / "v2"
    out: dict = {"epoch": None, "tree_paths": None, "org_paths": None,
                 "symlink_paths": set()}
    ep_file = d / "epoch_commit.json"
    if not ep_file.exists():
        return out
    epoch = json.loads(ep_file.read_text())
    out["epoch"] = epoch
    sha = epoch.get("sha")
    if sha:
        tf = d / f"tree_paths_{sha[:12]}.json"
        if tf.exists():
            entries = _entries(json.loads(tf.read_text()))
            out["tree_paths"] = [e["path"] for e in entries]
            out["symlink_paths"] = {e["path"].lower() for e in entries
                                    if e.get("mode") == SYMLINK_MODE}
    of = d / "org_epoch_commit.json"
    if of.exists():
        org = json.loads(of.read_text())
        osha = org.get("sha")
        if org.get("status") != "absent" and osha:
            otf = d / f"org_tree_paths_{osha[:12]}.json"
            if otf.exists():
                out["org_paths"] = [e["path"] for e in
                                    _entries(json.loads(otf.read_text()))]
    return out


def _profile_updated_at(cache_root: Path, repo: str) -> str | None:
    """`updated_at` do perfil comunitário v1 (cache de julho) — flag
    descritiva do registro de decisão; nunca reconsultado."""
    f = cache_root / repo.replace("/", "__") / "community_profile.json"
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text()).get("data") or {}
    except (json.JSONDecodeError, AttributeError):
        return None
    return data.get("updated_at") if isinstance(data, dict) else None


def rescore_all(v1_results: list[dict], cache_root: Path, cfg: dict,
                remeasured_at: str) -> list[dict]:
    """Re-pontua todos os registros v1 (mesma ordem) com o cache v2.

    Cache v2 ausente para um repositório ⇒ tratado como inacessível
    (`epoch_status = "unreachable"`, `epoch_resolver_step = "cache_missing"`,
    itens v1 mantidos) e avisado em stderr — nunca aborta a rodada.
    """
    cache_root = Path(cache_root)
    out: list[dict] = []
    for r in v1_results:
        repo = r["repo"]
        c = load_v2_cache(cache_root, repo)
        epoch = c["epoch"]
        if epoch is None:
            print(f"  ! {repo}: cache v2 ausente — itens v1 mantidos",
                  file=sys.stderr, flush=True)
            epoch = {"sha": None, "cutoff": None, "cutoff_source": None,
                     "resolver_step": "cache_missing",
                     "epoch_status": "unreachable",
                     "note": "cache v2 ausente (epoch_commit.json)"}
        rec = rescore_record(r, epoch, c["tree_paths"], c["org_paths"],
                             cfg, remeasured_at)
        meta = rec["v2_meta"]
        matched = {p.lower() for ps in (meta.get("matched") or {}).values()
                   for p in ps}
        meta["symlink_hits"] = sorted(matched & c["symlink_paths"])
        meta["profile_updated_at"] = _profile_updated_at(cache_root, repo)
        out.append(rec)
    return out
