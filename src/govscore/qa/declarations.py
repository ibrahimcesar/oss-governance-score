"""Declarações de QA do catálogo v2 (instrumentos DESCRITIVOS, pré-registrados).

Registro: docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md, seção
"Instrumentos complementares". Três declarações sobre limites de medição já
presentes em v1 e copiados verbatim para v2 — nada aqui altera scores:

1. Censura de releases: a extração pediu `per_page = 30`; quando as 30
   releases devolvidas caem todas na janela de 12 meses, `releases_12m` é um
   PISO e `release_notes_share` foi calculado sobre as 30 mais recentes.
   Contam-se também as *prereleases* na janela (o catálogo não as distingue)
   e verifica-se se a ordem devolvida (por `created_at`) é monotônica em
   `published_at`.
2. Motivo de `contributor_retention = None`: repositório jovem (criado na 2ª
   metade da janela — 1ª metade vazia POR CONSTRUÇÃO) versus 1ª metade vazia
   em repositório antigo (dormência do branch) versus observado.
3. `ci_configured = False` significa "sem configuração de CI reconhecida no
   repositório" (regras v2), não "sem CI" (CI externa: KernelCI, LUCI, FATE,
   Prow central — invisíveis declarados no registro); a lista nominal
   acompanha o relatório.

Fontes: registros processados (`full_metrics.json`) e cache bruto
(`repo_metadata.json`, `releases.json`) — nunca a API.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:  # constante única do snapshot (M1); fallback idêntico se ausente
    from govscore.extract.patterns import SNAPSHOT_UTC
except ImportError:  # pragma: no cover — só até a integração do M1
    SNAPSHOT_UTC = datetime(2026, 7, 24, 23, 59, 59, tzinfo=timezone.utc)

RELEASES_PER_PAGE = 30   # params={"per_page": 30} em extract_security (v1)
WINDOW_DAYS = 365

RETENTION_REASONS = ("observed", "young_repo", "first_half_empty", "unknown")


def _parse_iso(value) -> datetime | None:
    """ISO-8601 (`Z` ou offset; só data → 00:00 UTC) → datetime tz-aware."""
    if not value:
        return None
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _unwrap(payload):
    """Aceita o arquivo de cache inteiro ({"data": ...}) ou só o `data`."""
    if isinstance(payload, dict) and "data" in payload and (
            "fetched_at" in payload or "path" in payload):
        return payload["data"]
    return payload


def retention_reason(record: dict, repo_metadata: dict | None,
                     window_days: int = WINDOW_DAYS) -> str:
    """Motivo da retenção observada/ausente.

    - "observed": `distribution.contributor_retention` não é None;
    - "young_repo": `created_at` ≥ `extracted_at` − window/2 — a 1ª metade
      da janela (Constantinou & Mens, 2017) é vazia por construção;
    - "first_half_empty": repositório anterior à janela, mas sem autores na
      1ª metade (dormência) — silêncio informativo, não estrutural;
    - "unknown": sem `created_at`/`extracted_at` para decidir (cache ausente).

    `extracted_at` é só a data (00:00 UTC): a fronteira real da metade da
    janela é até 24 h posterior — aproximação declarada, conservadora para
    "young_repo".
    """
    retention = (record.get("distribution") or {}).get("contributor_retention")
    if retention is not None:
        return "observed"
    meta = _unwrap(repo_metadata) or {}
    created = _parse_iso(meta.get("created_at"))
    extracted = _parse_iso(record.get("extracted_at"))
    if created is None or extracted is None:
        return "unknown"
    half = extracted - timedelta(days=window_days / 2)
    return "young_repo" if created >= half else "first_half_empty"


def releases_censoring(record: dict, releases_json,
                       snapshot: datetime = SNAPSHOT_UTC,
                       per_page: int = RELEASES_PER_PAGE,
                       window_days: int = WINDOW_DAYS) -> dict:
    """Censura à direita da lista de releases (`per_page` = 30).

    Retorna: releases_fetched (n devolvidas), in_window (com `published_at`
    ≥ snapshot − window), saturated (n ≥ per_page E todas na janela ⇒
    `releases_12m` é piso), prereleases_12m (`prerelease: true` na janela),
    nonmonotone (`published_at` não decrescente na ordem devolvida — a API
    ordena por `created_at`, logo uma release publicada tardiamente pode
    ficar fora das 30) e releases_12m_record (valor do registro, para
    conferência). Releases sem `published_at` (rascunhos) não contam na
    janela, como em `release_metrics` v1.
    """
    releases = _unwrap(releases_json) or []
    cutoff = snapshot - timedelta(days=window_days)
    dated = [(_parse_iso(r.get("published_at")), r) for r in releases]
    dated = [(t, r) for t, r in dated if t is not None]
    in_window = [r for t, r in dated if t >= cutoff]
    n = len(releases)
    times = [t for t, _ in dated]
    return {
        "releases_fetched": n,
        "in_window": len(in_window),
        "saturated": n >= per_page and len(in_window) == n,
        "prereleases_12m": sum(1 for r in in_window if r.get("prerelease")),
        "nonmonotone": any(b > a for a, b in zip(times, times[1:])),
        "releases_12m_record": (record.get("security") or {}).get("releases_12m"),
    }


def ci_false_list(records: list[dict]) -> list[str]:
    """Repositórios com `security.ci_configured` exatamente False (None —
    não observado — fica de fora), em ordem alfabética."""
    return sorted(r["repo"] for r in records
                  if (r.get("security") or {}).get("ci_configured") is False)


def _repo_dir(cache_root: Path | str, repo: str) -> Path:
    return Path(cache_root) / repo.replace("/", "__")


def _read_cache(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def _names(repos: list[str]) -> str:
    return ", ".join(f"`{r}`" for r in repos) if repos else "nenhum"


def qa_section(records: list[dict], cache_root: Path | str,
               snapshot: datetime = SNAPSHOT_UTC) -> str:
    """Seção "## Declarações de QA (v2)" (PT-BR) para anexar ao relatório de
    QA via `run_full.qa_report(..., extra_sections=[...])`. Lê só o cache."""
    saturated, nonmono, no_cache = [], [], []
    pre_total = win_total = 0
    reasons: dict[str, list[str]] = {k: [] for k in RETENTION_REASONS}
    for r in records:
        d = _repo_dir(cache_root, r["repo"])
        meta = _read_cache(d / "repo_metadata.json")
        rel = _read_cache(d / "releases.json")
        reasons[retention_reason(r, meta)].append(r["repo"])
        if rel is None:
            no_cache.append(r["repo"])
            continue
        c = releases_censoring(r, rel, snapshot=snapshot)
        pre_total += c["prereleases_12m"]
        win_total += c["in_window"]
        if c["saturated"]:
            saturated.append(r["repo"])
        if c["nonmonotone"]:
            nonmono.append(r["repo"])
    ci_false = ci_false_list(records)
    pct = f"{100 * pre_total / win_total:.1f}%" if win_total else "—"

    lines = [
        "## Declarações de QA (v2)", "",
        "Instrumentos descritivos pré-registrados "
        "(`docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md`); nenhum "
        "altera scores.", "",
        f"### Censura de releases (`per_page = {RELEASES_PER_PAGE}`)", "",
        f"- **Saturados** ({len(saturated)}): {RELEASES_PER_PAGE} releases "
        "devolvidas, todas na janela de 12 meses — `releases_12m` é PISO e "
        f"`release_notes_share` foi calculado sobre as {RELEASES_PER_PAGE} "
        f"mais recentes: {_names(sorted(saturated))}.",
        f"- **Prereleases na janela**: {pre_total} de {win_total} releases "
        f"({pct}) — o catálogo não distingue prereleases de releases.",
        f"- **`published_at` não monotônico na ordem devolvida** "
        f"({len(nonmono)}; a API ordena por `created_at`): "
        f"{_names(sorted(nonmono))}.",
    ]
    if no_cache:
        lines.append(f"- Sem `releases.json` em cache ({len(no_cache)}): "
                     f"{_names(sorted(no_cache))}.")
    lines += [
        "", "### Retenção de contribuidores (`contributor_retention`)", "",
        "| motivo | n | repositórios |", "|---|---|---|",
        f"| observed | {len(reasons['observed'])} | — |",
        f"| young_repo (criado na 2ª metade da janela — 1ª metade vazia por "
        f"construção) | {len(reasons['young_repo'])} | "
        f"{_names(sorted(reasons['young_repo']))} |",
        f"| first_half_empty (repositório antigo sem autores na 1ª metade — "
        f"dormência) | {len(reasons['first_half_empty'])} | "
        f"{_names(sorted(reasons['first_half_empty']))} |",
    ]
    if reasons["unknown"]:
        lines.append(f"| unknown (sem `created_at` em cache) | "
                     f"{len(reasons['unknown'])} | "
                     f"{_names(sorted(reasons['unknown']))} |")
    lines += [
        "", "### CI não detectada (`ci_configured = False`)", "",
        f"Significa \"sem configuração de CI reconhecida no repositório\" "
        f"(lista fechada de provedores do registro), NÃO \"sem CI\" — CI "
        f"externa (KernelCI, LUCI, FATE, Prow central) é invisível declarada. "
        f"{len(ci_false)} repositórios: {_names(ci_false)}.", "",
    ]
    return "\n".join(lines)
