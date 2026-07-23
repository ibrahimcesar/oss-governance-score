"""Extração completa da amostra (item 5) + QA do dataset.

Orquestração tolerante a falhas: um repositório com erro não derruba a
rodada — o erro é registrado e a extração continua; re-execuções retomam
do cache em data/raw/. Saídas em data/processed/ (full_metrics.json,
metrics.parquet, scores.csv) e relatório de QA em results/qa_extracao.md.

Nenhum identificador de contribuidor (login/e-mail) chega aos artefatos
processados — só agregados; a regra de anonimização (SHA-256 + salt) se
aplicaria apenas se identificadores fossem publicados. O cache bruto em
data/raw/ permanece fora do versionamento.
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
ARCHETYPES = ("federation", "stadium", "club", "toy")

# Seções aninhadas achatadas para colunas (prefixo_metrica)
FLAT_SECTIONS = ("artifacts", "security", "distribution", "responsiveness")


def flatten_record(m: dict) -> dict:
    """Métricas aninhadas → colunas planas para o parquet/csv."""
    flat: dict = {}
    for k, v in m.items():
        if k in FLAT_SECTIONS and isinstance(v, dict):
            for mk, mv in v.items():
                if not isinstance(mv, (dict, list)):
                    flat[f"{k}_{mk}"] = mv
        elif k == "subscores" and isinstance(v, dict):
            for dim, s in v.items():
                flat[f"subscore_{dim}"] = s
        elif not isinstance(v, (dict, list)):
            flat[k] = v
    return flat


def load_progress(progress_path: Path | None,
                  expected_backend: str | None = None) -> dict[str, dict]:
    """Registros já extraídos (JSONL, um por linha; linhas corrompidas por
    interrupção no meio da escrita são ignoradas). Proveniência: registros de
    outro backend não são retomados — serão reextraídos."""
    done: dict[str, dict] = {}
    if progress_path and progress_path.exists():
        for line in progress_path.read_text().splitlines():
            try:
                r = json.loads(line)
                if expected_backend and r.get("backend") != expected_backend:
                    continue
                done[r["repo"]] = r
            except (json.JSONDecodeError, KeyError):
                continue
    return done


def run_sample(entries: list[dict], extract_fn: Callable[[str], dict],
               cfg: dict, progress_path: Path | None = None,
               resume: bool = True,
               expected_backend: str | None = None) -> tuple[list[dict], list[dict]]:
    """Extrai e pontua cada repositório da amostra; falhas não interrompem.

    Ponto de recuperação contínuo: cada sucesso é gravado imediatamente em
    progress_path (JSONL). Re-execuções puladas os já concluídos (resume) e
    retentam apenas os que falharam; o cache de data/raw/ garante que nenhuma
    chamada de API é repetida.
    """
    from govscore.score.scoring import compute_score, compute_subscores

    done = load_progress(progress_path, expected_backend) if resume else {}
    results: list[dict] = []
    errors: list[dict] = []
    for i, entry in enumerate(entries, 1):
        repo = entry["repo"]
        if repo in done:
            print(f"[{i}/{len(entries)}] {repo} (retomado)",
                  file=sys.stderr, flush=True)
            results.append(done[repo])
            continue
        print(f"[{i}/{len(entries)}] {repo}", file=sys.stderr, flush=True)
        try:
            m = extract_fn(repo)
            m["subscores"] = compute_subscores(m, cfg)
            m["score"] = compute_score(m["subscores"], cfg["weights"])
            m["archetype"] = entry.get("archetype")
            m["language"] = entry.get("language")
            m["extracted_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            results.append(m)
            if progress_path:
                with progress_path.open("a") as fh:
                    fh.write(json.dumps(m, ensure_ascii=False) + "\n")
                    fh.flush()
        except KeyboardInterrupt:
            raise
        except Exception as ex:  # noqa: BLE001 — rodada não pode morrer
            print(f"  ✗ {repo}: {type(ex).__name__}: {ex}",
                  file=sys.stderr, flush=True)
            errors.append({"repo": repo, "archetype": entry.get("archetype"),
                           "error": f"{type(ex).__name__}: {ex}"})
    return results, errors


def write_outputs(results: list[dict], errors: list[dict],
                  out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "full_metrics.json").write_text(
        json.dumps({"results": results, "errors": errors},
                   indent=2, ensure_ascii=False))

    import pandas as pd
    df = pd.DataFrame([flatten_record(r) for r in results])
    df.to_parquet(out_dir / "metrics.parquet", index=False)

    score_cols = ["repo", "archetype", "language", "stars", "score",
                  "subscore_artifacts", "subscore_distribution",
                  "subscore_responsiveness", "subscore_diversity",
                  "subscore_security", "extracted_at"]
    df[[c for c in score_cols if c in df.columns]].to_csv(
        out_dir / "scores.csv", index=False)
    return {"json": out_dir / "full_metrics.json",
            "parquet": out_dir / "metrics.parquet",
            "csv": out_dir / "scores.csv"}


def _fmt(x: float | None, nd: int = 1) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def qa_report(results: list[dict], errors: list[dict],
              code_version: str = "") -> str:
    """Relatório de QA (PT-BR) para results/qa_extracao.md."""
    lines = ["# QA da extração completa (item 5)", ""]
    dates = sorted({r["extracted_at"] for r in results}) or ["—"]
    lines += [f"**Extração:** {dates[0]} → {dates[-1]} · "
              f"**código:** `{code_version or 'n/d'}` · "
              f"**ok:** {len(results)} · **falhas:** {len(errors)}", ""]

    lines += ["## Scores por arquétipo", "",
              "| Arquétipo | n | média | mediana | dp | mín | máx |",
              "|---|---|---|---|---|---|---|"]
    for arch in ARCHETYPES:
        xs = [r["score"] for r in results
              if r.get("archetype") == arch and r.get("score") is not None]
        if not xs:
            lines.append(f"| {arch} | 0 | — | — | — | — | — |")
            continue
        dp = statistics.stdev(xs) if len(xs) > 1 else 0.0
        lines.append(
            f"| {arch} | {len(xs)} | {_fmt(statistics.mean(xs))} | "
            f"{_fmt(statistics.median(xs))} | {_fmt(dp)} | "
            f"{_fmt(min(xs))} | {_fmt(max(xs))} |")
    lines.append("")

    lines += ["## Métricas faltantes (None — omitidas do score, nunca zero)",
              "", "| métrica | faltantes | % |", "|---|---|---|"]
    n = len(results) or 1
    flats = [flatten_record(r) for r in results]
    keys = sorted({k for f in flats for k in f
                   if k.split("_", 1)[0] in
                   ("artifacts", "security", "distribution",
                    "responsiveness", "subscore")})
    miss_rows = 0
    for k in keys:
        if k.endswith("_inherited"):  # anotação opcional, não é métrica
            continue
        miss = sum(1 for f in flats if f.get(k) is None)
        if miss:
            lines.append(f"| {k} | {miss} | {100 * miss / n:.0f}% |")
            miss_rows += 1
    if miss_rows == 0:
        lines.append("| (nenhuma) | 0 | 0% |")
    lines.append("")

    if errors:
        lines += ["## Falhas de extração", ""]
        lines += [f"- `{e['repo']}` ({e.get('archetype')}): {e['error']}"
                  for e in errors]
        lines.append("")

    caps = [r["repo"] for r in results
            if r.get("responsiveness", {}).get("n_first_responses") == 0]
    if caps:
        lines += ["## Avisos", "",
                  "Sem resposta humana observada nas issues amostradas "
                  "(D3 parcial): " + ", ".join(f"`{r}`" for r in caps), ""]
    return "\n".join(lines)
