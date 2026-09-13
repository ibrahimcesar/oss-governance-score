"""CLI: python -m govscore.cli pilot | extract --repo owner/name | sample | run
| sensitivity | validate | robustness | figures

Diretórios de entrada/saída das análises (`--data-dir`, `--results-dir`,
`--fig-dir`) são parametrizáveis para que o catálogo v2 rode em diretórios
próprios sem sobrescrever as saídas v1 arquivadas (decisão 2026-09-13).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from govscore.extract.artifacts import (
    SNAPSHOT_UTC,
    extract_artifacts,
    extract_security,
)
from govscore.extract.contributions import extract_contributions
from govscore.extract.responsiveness import extract_responsiveness
from govscore.github_client import GitHubClient
from govscore.score.scoring import compute_score, compute_subscores

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT / "data" / "processed"
DEFAULT_RESULTS_DIR = ROOT / "results"


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config" / "metrics.yaml").read_text())


def parse_snapshot(value: str | datetime) -> datetime:
    """Instante do snapshot (UTC) a partir da linha de comando.

    `YYYY-MM-DD` → fim do dia (23:59:59Z), a mesma convenção de SNAPSHOT_UTC;
    ISO 8601 completo com `Z` ou offset → convertido a UTC; sem fuso → UTC.
    """
    if isinstance(value, datetime):
        dt = value
    else:
        s = value.strip()
        if len(s) == 10:  # só a data
            dt = datetime.fromisoformat(s).replace(hour=23, minute=59, second=59)
        else:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------- extração
def extract_repo(gh: GitHubClient, repo: str,
                 include_contributions: bool = True,
                 snapshot: datetime = SNAPSHOT_UTC) -> dict:
    """`snapshot` ancora a janela de releases de D5 (nunca `now()`)."""
    meta = gh.get(repo, f"/repos/{repo}", "repo_metadata") or {}
    if not meta:
        # 404 (removido/privado desde a amostragem): erro explícito — nunca
        # pontuar ausência de acesso como ausência de artefatos
        raise RuntimeError(f"{repo}: metadata inacessível (404)")
    return {
        "repo": repo,
        "stars": meta.get("stargazers_count"),
        "forks": meta.get("forks_count"),
        "artifacts": extract_artifacts(gh, repo),
        "security": extract_security(gh, repo, snapshot=snapshot),
        "distribution": (extract_contributions(gh, repo)
                         if include_contributions else {}),
        "responsiveness": extract_responsiveness(gh, repo),
        "backend": "api",
    }


def extract_both(gh: GitHubClient, repo: str,
                 snapshot: datetime = SNAPSHOT_UTC) -> dict:
    """Modo canônico da fase completa: API (D1/D3/D5, releases, stars) +
    git (D2/D4 na janela de 12 meses — método §3.2.2).

    /contributors da API é dispensável aqui (D2/D4 vêm do git) e retorna
    403 permanente em repositórios gigantes ("list is too large", ex.:
    torvalds/linux) — por isso não é consultado neste modo."""
    from govscore.extract.git_extractor import extract_via_git
    m = extract_repo(gh, repo, include_contributions=False, snapshot=snapshot)
    g = extract_via_git(repo)
    m["distribution"] = g["distribution"]
    m["backend"] = "api+git"
    return m


def run(repos: list[dict], backend: str = "api",
        snapshot: datetime = SNAPSHOT_UTC) -> list[dict]:
    cfg = load_config()
    gh = GitHubClient() if backend in ("api", "both") else None
    out = []
    for entry in repos:
        repo = entry["repo"] if isinstance(entry, dict) else entry
        print(f"→ {repo}", file=sys.stderr)
        if backend == "git":
            from govscore.extract.git_extractor import extract_via_git
            m = extract_via_git(repo)
            m["repo"] = repo
        elif backend == "both":
            m = extract_both(gh, repo, snapshot=snapshot)
        else:
            m = extract_repo(gh, repo, snapshot=snapshot)
        subs = compute_subscores(m, cfg)
        m["subscores"] = subs
        m["score"] = compute_score(subs, cfg["weights"])
        if isinstance(entry, dict):
            m["archetype"] = entry.get("archetype")
        out.append(m)
    return out


# ---------------------------------------------------------------- análises
def cmd_robustness(data_dir: Path, results_dir: Path) -> dict:
    """`govscore robustness`: análises sobre data_dir; relatórios em
    results_dir (robustez.md, robustness.json)."""
    from govscore.robustness import report as rreport
    from govscore.robustness import run_all
    res = run_all(data_dir=Path(data_dir), results_dir=Path(results_dir))
    print(rreport(res))
    return res


def cmd_sensitivity(data_dir: Path, results_dir: Path) -> dict:
    """`govscore sensitivity`: sensibilidade dos pesos sobre os sub-scores de
    data_dir/full_metrics.json; relatórios em results_dir."""
    from govscore.score.sensitivity import analyze, report
    data_dir, results_dir = Path(data_dir), Path(results_dir)
    cfg = load_config()
    data = json.loads((data_dir / "full_metrics.json").read_text())
    subs = [r["subscores"] for r in data["results"]]
    res = analyze(subs, cfg["weights"])
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "sensibilidade.md").write_text(report(res))
    (results_dir / "sensitivity.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False))
    print(report(res))
    return res


VALIDATION_INDICATORS = ["stars", "forks", "dependents", "scorecard"]


def cmd_validate(data_dir: Path, results_dir: Path,
                 external_fetched_at: str | None = None,
                 offline: bool = False) -> dict:
    """`govscore validate`: correlações com indicadores externos.

    `external_fetched_at` fixa a época declarada dos indicadores externos
    (ex.: a data v1 ao re-validar o catálogo v2 sobre o cache de julho);
    sem ela, a época é derivada do `fetched_at` dos arquivos de cache e, só
    na ausência de cache, da data de hoje. `offline=True` proíbe qualquer
    consulta à rede: indicador fora do cache é erro (CacheMissError).
    """
    import time as _time

    from govscore.validate.correlation import report as vreport
    from govscore.validate.correlation import validate_correlations
    from govscore.validate.external import (
        external_fetched_range,
        fetch_external,
    )
    data_dir, results_dir = Path(data_dir), Path(results_dir)
    data = json.loads((data_dir / "full_metrics.json").read_text())
    rows = []
    for i, r in enumerate(data["results"], 1):
        print(f"[{i}/{len(data['results'])}] {r['repo']}", file=sys.stderr)
        ext = fetch_external(r["repo"], r.get("language"), offline=offline)
        rows.append({"repo": r["repo"], "archetype": r.get("archetype"),
                     "language": r.get("language"),
                     "score": r.get("score"), "stars": r.get("stars"),
                     "forks": r.get("forks"),
                     "extracted_at": r.get("extracted_at"),
                     "dependents": ext["dependents"],
                     "scorecard": ext["scorecard"]})
        if not offline:
            _time.sleep(0.1)  # cortesia com APIs públicas sem auth
    snap = sorted({r["extracted_at"] for r in rows if r.get("extracted_at")})
    # Época dos indicadores externos: override explícito > intervalo do
    # `fetched_at` em cache (sobre o cache de julho o valor derivado é
    # "2026-07-24", idêntico ao relatório v1) > hoje, só sem cache algum —
    # avisado em stderr, nunca silencioso.
    fetched = (external_fetched_at
               or external_fetched_range([r["repo"] for r in rows]))
    if not fetched:
        fetched = date.today().isoformat()
        print(f"aviso: nenhum indicador externo em cache — "
              f"external_fetched_at = {fetched} (hoje)", file=sys.stderr)
    meta = {"stars_snapshot": "→".join([snap[0], snap[-1]] if snap else []),
            "external_fetched_at": fetched}
    res = validate_correlations(rows, VALIDATION_INDICATORS, meta=meta)
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "validacao.md").write_text(vreport(res))
    (results_dir / "validation.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False))
    import pandas as pd
    pd.DataFrame(rows).to_csv(data_dir / "external_indicators.csv",
                              index=False)
    print(vreport(res))
    return res


def cmd_figures(data_dir: Path, results_dir: Path,
                fig_dir: Path | None = None) -> Path:
    """`govscore figures`: mesmas figuras de `make figures`, com diretórios
    parametrizáveis (figures.main)."""
    from govscore.figures import main as figures_main
    return figures_main(data_dir=Path(data_dir), results_dir=Path(results_dir),
                        fig_dir=Path(fig_dir) if fig_dir else None)


# ------------------------------------------------------ catálogo v2 (reparo)
RAW_DIR = ROOT / "data" / "raw"
DEFAULT_EPOCH_WORKDIR = RAW_DIR / "_epoch_work"   # ignorado pelo git (data/raw/*)


def _sample_entries(sample_file: Path | str) -> list[dict]:
    return yaml.safe_load(Path(sample_file).read_text())["full"]


def _code_version() -> str:
    import subprocess
    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True, cwd=ROOT).stdout.strip()
    if subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                      text=True, cwd=ROOT).stdout.strip():
        rev += "-dirty"  # proveniência honesta: código não commitado
    return rev


def cmd_epoch(sample_file: Path | str, only: list[str] | None = None,
              workdir: Path = DEFAULT_EPOCH_WORKDIR, force: bool = False,
              keep: bool = False, cache_root: Path = RAW_DIR) -> dict:
    """`govscore epoch`: commit e árvore de época (passo 3 do protocolo da
    decisão 2026-09-13) por repositório e por `{owner}/.github` — só git,
    nenhuma chamada à API. Idempotente e retomável (cache em
    data/raw/<owner>__<repo>/v2/)."""
    from govscore.extract.epoch import ensure_epoch_artifacts
    entries = _sample_entries(sample_file)
    repos = [e["repo"] for e in entries]
    if only:
        repos = [r for r in repos if r in set(only)]
    summary: dict = {"ok": 0, "unverified": 0, "unreachable": 0, "errors": []}
    for i, repo in enumerate(repos, 1):
        print(f"[{i}/{len(repos)}] {repo}", file=sys.stderr, flush=True)
        try:
            ep = ensure_epoch_artifacts(repo, Path(cache_root), Path(workdir),
                                        force=force, keep=keep)
            status = ep.get("epoch_status", "unreachable")
            summary[status] = summary.get(status, 0) + 1
            print(f"    {status} sha={str(ep.get('sha'))[:12]} "
                  f"step={ep.get('resolver_step')}", file=sys.stderr, flush=True)
        except KeyboardInterrupt:
            raise
        except Exception as ex:  # noqa: BLE001 — a rodada não pode morrer
            print(f"    ✗ {type(ex).__name__}: {ex}", file=sys.stderr, flush=True)
            summary["errors"].append({"repo": repo, "error": f"{type(ex).__name__}: {ex}"})
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def cmd_rescore(v1_json: Path | str, data_dir: Path, results_dir: Path,
                remeasured_at: str | None = None,
                cache_root: Path = RAW_DIR) -> dict:
    """`govscore rescore`: passo 4 do protocolo — re-pontua os registros v1
    com os 12 binários de D1/D5 medidos na árvore de época (regras v2);
    tudo o mais verbatim. Saídas em data_dir (full_metrics.json,
    metrics.parquet, scores.csv) e QA em results_dir/qa_extracao.md."""
    from govscore.qa.declarations import qa_section
    from govscore.rescore import rescore_all
    from govscore.run_full import qa_report, write_outputs
    data_dir, results_dir = Path(data_dir), Path(results_dir)
    cfg = load_config()
    v1 = json.loads(Path(v1_json).read_text())["results"]
    remeasured_at = remeasured_at or date.today().isoformat()
    v2 = rescore_all(v1, Path(cache_root), cfg, remeasured_at)
    paths = write_outputs(v2, [], data_dir)
    report = qa_report(v2, [], code_version=_code_version(),
                       extra_sections=[qa_section(v2, Path(cache_root))])
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "qa_extracao.md").write_text(report)
    counts = {}
    for r in v2:
        counts[r.get("epoch_status")] = counts.get(r.get("epoch_status"), 0) + 1
    out = {"n": len(v2), "epoch_status": counts,
           "saidas": {k: str(v) for k, v in paths.items()},
           "qa": str(results_dir / "qa_extracao.md")}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return out


def cmd_compare(v1_dir: Path, v2_dir: Path, results_dir: Path,
                sample_file: Path | str, cache_root: Path = RAW_DIR) -> dict:
    """`govscore compare`: passo 5 do protocolo — results/reparo_v1_v2.md e
    .json (ρ v1×v2, trocas por item × arquétipo nas duas direções,
    época, cross-checks descritivos com o Scorecard de julho)."""
    from govscore.compare import compare_records, report, scorecard_check_rows
    v1 = json.loads((Path(v1_dir) / "full_metrics.json").read_text())["results"]
    v2 = json.loads((Path(v2_dir) / "full_metrics.json").read_text())["results"]
    entries = _sample_entries(sample_file)
    ext_rows = scorecard_check_rows(Path(cache_root), [r["repo"] for r in v1])
    res = compare_records(v1, v2, entries, ext_rows=ext_rows)
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "reparo_v1_v2.md").write_text(report(res))
    (results_dir / "reparo_v1_v2.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False, default=str))
    print(report(res))
    return res


def cmd_locus(results_dir: Path, sample_file: Path | str,
              cache_root: Path = RAW_DIR) -> list[dict]:
    """`govscore locus-evidence`: tabela de evidência do locus de coordenação
    (descritiva; nunca altera scores) → results/locus_evidence.md."""
    from govscore.qa.locus import locus_table, report
    rows = locus_table(Path(cache_root), _sample_entries(sample_file))
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "locus_evidence.md").write_text(report(rows))
    print(report(rows))
    return rows


# --------------------------------------------------------------- argparse
def _add_dir_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                   help="dataset processado (default: data/processed)")
    p.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR,
                   help="relatórios (default: results)")


def _add_snapshot_option(p: argparse.ArgumentParser) -> None:
    p.add_argument("--snapshot", type=parse_snapshot, default=SNAPSHOT_UTC,
                   help="instante UTC que ancora a janela de releases "
                        "(default: snapshot da extração completa, "
                        f"{SNAPSHOT_UTC.strftime('%Y-%m-%dT%H:%M:%SZ')}); "
                        "aceita YYYY-MM-DD (fim do dia) ou ISO 8601")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="govscore")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pilot")
    p.add_argument("--backend", choices=["api", "git", "both"], default="api")
    _add_snapshot_option(p)
    ex = sub.add_parser("extract")
    ex.add_argument("--repo", required=True)
    ex.add_argument("--backend", choices=["api", "git", "both"], default="api")
    _add_snapshot_option(ex)
    sp = sub.add_parser("sample", help="amostragem estratificada (plano §3.1–3.2)")
    sp.add_argument("--quota", type=int, default=None,
                    help="repositórios por arquétipo (default: sampling.yaml)")
    rn = sub.add_parser("run", help="extração completa da amostra (item 5)")
    rn.add_argument("--backend", choices=["api", "git", "both"], default="both")
    rn.add_argument("--sample-file",
                    default=str(ROOT / "config" / "sample_full.yaml"))
    rn.add_argument("--fresh", action="store_true",
                    help="ignora o progresso salvo e reextrai tudo")
    _add_snapshot_option(rn)
    se = sub.add_parser("sensitivity",
                        help="análise de sensibilidade dos pesos (item 6)")
    _add_dir_options(se)
    va = sub.add_parser("validate", help="validação externa (item 7; plano §6)")
    _add_dir_options(va)
    va.add_argument("--external-fetched-at", default=None, metavar="YYYY-MM-DD",
                    help="época declarada dos indicadores externos (ex.: a "
                         "data v1 ao re-validar sobre o cache); default: "
                         "derivada do fetched_at do cache")
    va.add_argument("--offline", action="store_true",
                    help="proíbe consultas à rede: indicador fora do cache "
                         "é erro (a análise v2 usa o cache de julho)")
    ro = sub.add_parser("robustness",
                        help="robustez pós-revisão adversarial (limiares, "
                             "reclassificação, discriminante, suspeitos)")
    _add_dir_options(ro)
    # `figures` como subcomando: necessário para os flags --data-dir/
    # --results-dir/--fig-dir (contrato M4); `make figures` continua em
    # `python -m govscore.figures`. Integrador: os subcomandos v2 (epoch,
    # rescore, compare, locus-evidence) entram aqui, ao lado deste.
    fg = sub.add_parser("figures", help="figuras e tabelas das seções 4.2/4.3")
    _add_dir_options(fg)
    fg.add_argument("--fig-dir", type=Path, default=None,
                    help="saída das figuras (default: figures)")

    # --- catálogo v2 (decisão 2026-09-13) ---------------------------------
    default_sample = str(ROOT / "config" / "sample_full.yaml")
    ep = sub.add_parser("epoch", help="commit/árvore de época por repositório "
                                      "(git apenas; passo 3 do reparo v2)")
    ep.add_argument("--sample-file", default=default_sample)
    ep.add_argument("--only", nargs="*", metavar="owner/name")
    ep.add_argument("--workdir", type=Path, default=DEFAULT_EPOCH_WORKDIR)
    ep.add_argument("--force", action="store_true", help="refaz mesmo com cache v2")
    ep.add_argument("--keep", action="store_true", help="mantém os clones")
    rs = sub.add_parser("rescore", help="re-pontuação D1/D5 sobre a árvore de "
                                        "época (passo 4 do reparo v2)")
    rs.add_argument("--v1", type=Path,
                    default=DEFAULT_DATA_DIR / "v1" / "full_metrics.json",
                    help="registros v1 arquivados")
    _add_dir_options(rs)
    rs.add_argument("--remeasured-at", default=None, metavar="YYYY-MM-DD")
    cp = sub.add_parser("compare", help="relatório v1→v2 (passo 5 do reparo v2)")
    cp.add_argument("--v1-dir", type=Path, default=DEFAULT_DATA_DIR / "v1")
    cp.add_argument("--v2-dir", type=Path, default=DEFAULT_DATA_DIR)
    cp.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    cp.add_argument("--sample-file", default=default_sample)
    lc = sub.add_parser("locus-evidence",
                        help="evidência do locus de coordenação (descritiva)")
    lc.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    lc.add_argument("--sample-file", default=default_sample)
    return ap


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.cmd == "robustness":
        cmd_robustness(args.data_dir, args.results_dir)
        return

    if args.cmd == "validate":
        cmd_validate(args.data_dir, args.results_dir,
                     external_fetched_at=args.external_fetched_at,
                     offline=args.offline)
        return

    if args.cmd == "sensitivity":
        cmd_sensitivity(args.data_dir, args.results_dir)
        return

    if args.cmd == "figures":
        cmd_figures(args.data_dir, args.results_dir, args.fig_dir)
        return

    if args.cmd == "epoch":
        cmd_epoch(args.sample_file, only=args.only, workdir=args.workdir,
                  force=args.force, keep=args.keep)
        return

    if args.cmd == "rescore":
        cmd_rescore(args.v1, args.data_dir, args.results_dir,
                    remeasured_at=args.remeasured_at)
        return

    if args.cmd == "compare":
        cmd_compare(args.v1_dir, args.v2_dir, args.results_dir, args.sample_file)
        return

    if args.cmd == "locus-evidence":
        cmd_locus(args.results_dir, args.sample_file)
        return

    if args.cmd == "run":
        import os
        import subprocess

        from govscore.run_full import qa_report, run_sample, write_outputs
        if args.backend in ("api", "both") and not os.environ.get("GITHUB_TOKEN"):
            sys.exit("GITHUB_TOKEN ausente — backends api/both exigem token "
                     "(sem autenticação o limite é 60 req/h e a rodada trava)")
        cfg = load_config()
        entries = yaml.safe_load(Path(args.sample_file).read_text())["full"]
        gh = GitHubClient()
        snapshot = args.snapshot
        if args.backend == "both":
            fn = lambda repo: extract_both(gh, repo, snapshot=snapshot)  # noqa: E731
        elif args.backend == "git":
            from govscore.extract.git_extractor import extract_via_git
            fn = extract_via_git
        else:
            fn = lambda repo: extract_repo(gh, repo, snapshot=snapshot)  # noqa: E731
        # Saídas de `run` fixas em data/processed e results/: a extração
        # completa não é re-executada no reparo v2 (D2–D4 copiados de v1);
        # só as análises recebem --data-dir/--results-dir.
        progress = DEFAULT_DATA_DIR / "full_metrics_progress.jsonl"
        progress.parent.mkdir(parents=True, exist_ok=True)
        if args.fresh and progress.exists():
            progress.unlink()
        expected = {"both": "api+git", "git": "git", "api": "api"}[args.backend]
        results, errors = run_sample(entries, fn, cfg,
                                     progress_path=progress,
                                     resume=not args.fresh,
                                     expected_backend=expected)
        paths = write_outputs(results, errors, DEFAULT_DATA_DIR)
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True,
                             cwd=ROOT).stdout.strip()
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip():
            rev += "-dirty"  # proveniência honesta: código não commitado
        report = qa_report(results, errors, code_version=rev)
        qa_path = DEFAULT_RESULTS_DIR / "qa_extracao.md"
        qa_path.parent.mkdir(exist_ok=True)
        qa_path.write_text(report)
        print(json.dumps({"ok": len(results), "falhas": len(errors),
                          "saidas": {k: str(v) for k, v in paths.items()},
                          "qa": str(qa_path)}, indent=2, ensure_ascii=False))
        return

    if args.cmd == "sample":
        from govscore.sampling import build_sample, load_sampling_config, write_sample
        cfg = load_sampling_config()
        quota = args.quota or cfg["quota_per_archetype"]
        result = build_sample(GitHubClient(), cfg, quota)
        out = ROOT / "config" / "sample_full.yaml"
        write_sample(result, out)
        print(json.dumps({"counts": result["counts"],
                          "ambiguous": len(result["ambiguous"]),
                          "written_to": str(out)}, indent=2, ensure_ascii=False))
        return

    if args.cmd == "pilot":
        sample = yaml.safe_load((ROOT / "config" / "sample.yaml").read_text())
        results = run(sample["pilot"], backend=args.backend,
                      snapshot=args.snapshot)
    else:
        results = run([{"repo": args.repo}], backend=args.backend,
                      snapshot=args.snapshot)

    out_path = DEFAULT_DATA_DIR / "pilot_scores.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(json.dumps(
        [{"repo": r["repo"], "archetype": r.get("archetype"),
          "score": round(r["score"], 1) if r["score"] is not None else None,
          "subscores": {k: round(v, 3) if v is not None else None
                        for k, v in r["subscores"].items()}}
         for r in results], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
