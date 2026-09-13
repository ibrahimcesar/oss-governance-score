#!/usr/bin/env python3
"""OpenSSF Scorecard CLI nos 100 repositórios da amostra (instrumento de
validação SECUNDÁRIO, pré-registrado como descritivo no registro de decisão
de 2026-09-13: época = HEAD de 09/2026, 18 checks, versão única do CLI).

Saída por repositório: data/raw/<owner>__<repo>/v2_scorecard_cli.json
({fetched_at, cli_version, repo, elapsed_s, returncode, data|error}).
Retomável: repositórios já com arquivo são pulados. Nunca toca chaves v1.

Uso: GITHUB_AUTH_TOKEN=$(gh auth token) uv run python scripts/scorecard_cli_run.py \
        [--workers 3] [--timeout 2700] [--only owner/name ...]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
KEY = "v2_scorecard_cli.json"


def cli_version() -> str:
    out = subprocess.run(["scorecard", "version"], capture_output=True, text=True)
    for line in (out.stdout + out.stderr).splitlines():
        if "GitVersion" in line or "version" in line.lower():
            return line.strip()
    return (out.stdout + out.stderr).strip()[:200]


def run_one(repo: str, timeout: int, version: str) -> tuple[str, str]:
    dest = RAW / repo.replace("/", "__") / KEY
    if dest.exists():
        return repo, "cached"
    dest.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cmd = ["scorecard", f"--repo=github.com/{repo}", "--format=json", "--show-details"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        elapsed = time.time() - t0
        payload = {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "cli_version": version, "repo": repo, "elapsed_s": round(elapsed, 1),
                   "returncode": proc.returncode, "catalog_version": "v2"}
        try:
            payload["data"] = json.loads(proc.stdout)
            status = f"ok {elapsed:.0f}s score={payload['data'].get('score')}"
        except json.JSONDecodeError:
            payload["data"] = None
            payload["error"] = (proc.stderr or proc.stdout)[-2000:]
            status = f"error rc={proc.returncode} {elapsed:.0f}s"
    except subprocess.TimeoutExpired:
        payload = {"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "cli_version": version, "repo": repo, "elapsed_s": timeout,
                   "returncode": None, "catalog_version": "v2", "data": None,
                   "error": f"timeout after {timeout}s"}
        status = f"timeout {timeout}s"
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    return repo, status


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=2700)
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    if not (os.environ.get("GITHUB_AUTH_TOKEN") or os.environ.get("GITHUB_TOKEN")):
        print("defina GITHUB_AUTH_TOKEN", file=sys.stderr)
        return 2
    sample = yaml.safe_load((ROOT / "config" / "sample_full.yaml").read_text())["full"]
    repos = [e["repo"] for e in sample]
    if args.only:
        repos = [r for r in repos if r in set(args.only)]
    version = cli_version()
    print(f"scorecard {version} — {len(repos)} repos, {args.workers} workers", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, r, args.timeout, version): r for r in repos}
        for fut in as_completed(futs):
            repo, status = fut.result()
            done += 1
            print(f"[{done}/{len(repos)}] {repo}: {status}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
