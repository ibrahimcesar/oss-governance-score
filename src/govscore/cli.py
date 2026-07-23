"""CLI: python -m govscore.cli pilot | extract --repo owner/name"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from govscore.extract.artifacts import extract_artifacts, extract_security
from govscore.extract.contributions import extract_contributions
from govscore.extract.responsiveness import extract_responsiveness
from govscore.github_client import GitHubClient
from govscore.score.scoring import compute_score, compute_subscores

ROOT = Path(__file__).resolve().parents[2]


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config" / "metrics.yaml").read_text())


def extract_repo(gh: GitHubClient, repo: str) -> dict:
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
        "security": extract_security(gh, repo),
        "distribution": extract_contributions(gh, repo),
        "responsiveness": extract_responsiveness(gh, repo),
        "backend": "api",
    }


def extract_both(gh: GitHubClient, repo: str) -> dict:
    """Modo canônico da fase completa: API (D1/D3/D5, releases, stars) +
    git (D2/D4 na janela de 12 meses — método §3.2.2)."""
    from govscore.extract.git_extractor import extract_via_git
    m = extract_repo(gh, repo)
    g = extract_via_git(repo)
    m["distribution"] = g["distribution"]
    m["backend"] = "api+git"
    return m


def run(repos: list[dict], backend: str = "api") -> list[dict]:
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
            m = extract_both(gh, repo)
        else:
            m = extract_repo(gh, repo)
        subs = compute_subscores(m, cfg)
        m["subscores"] = subs
        m["score"] = compute_score(subs, cfg["weights"])
        if isinstance(entry, dict):
            m["archetype"] = entry.get("archetype")
        out.append(m)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(prog="govscore")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pilot")
    p.add_argument("--backend", choices=["api", "git", "both"], default="api")
    ex = sub.add_parser("extract")
    ex.add_argument("--repo", required=True)
    ex.add_argument("--backend", choices=["api", "git", "both"], default="api")
    sp = sub.add_parser("sample", help="amostragem estratificada (plano §3.1–3.2)")
    sp.add_argument("--quota", type=int, default=None,
                    help="repositórios por arquétipo (default: sampling.yaml)")
    rn = sub.add_parser("run", help="extração completa da amostra (item 5)")
    rn.add_argument("--backend", choices=["api", "git", "both"], default="both")
    rn.add_argument("--sample-file",
                    default=str(ROOT / "config" / "sample_full.yaml"))
    rn.add_argument("--fresh", action="store_true",
                    help="ignora o progresso salvo e reextrai tudo")
    args = ap.parse_args()

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
        if args.backend == "both":
            fn = lambda repo: extract_both(gh, repo)  # noqa: E731
        elif args.backend == "git":
            from govscore.extract.git_extractor import extract_via_git
            fn = extract_via_git
        else:
            fn = lambda repo: extract_repo(gh, repo)  # noqa: E731
        progress = ROOT / "data" / "processed" / "full_metrics_progress.jsonl"
        progress.parent.mkdir(parents=True, exist_ok=True)
        if args.fresh and progress.exists():
            progress.unlink()
        expected = {"both": "api+git", "git": "git", "api": "api"}[args.backend]
        results, errors = run_sample(entries, fn, cfg,
                                     progress_path=progress,
                                     resume=not args.fresh,
                                     expected_backend=expected)
        paths = write_outputs(results, errors, ROOT / "data" / "processed")
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True,
                             cwd=ROOT).stdout.strip()
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                          text=True, cwd=ROOT).stdout.strip():
            rev += "-dirty"  # proveniência honesta: código não commitado
        report = qa_report(results, errors, code_version=rev)
        qa_path = ROOT / "results" / "qa_extracao.md"
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
        results = run(sample["pilot"], backend=args.backend)
    else:
        results = run([{"repo": args.repo}], backend=args.backend)

    out_path = ROOT / "data" / "processed" / "pilot_scores.json"
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
