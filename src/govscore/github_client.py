"""Cliente REST da API do GitHub com cache em disco, rate limit e retry.

Toda resposta é persistida em data/raw/{owner}__{repo}/ antes de qualquer
processamento — a análise nunca reconsulta a API (reprodutibilidade).
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests

API = "https://api.github.com"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


class GitHubClient:
    def __init__(self, token: str | None = None, cache_dir: Path = RAW_DIR):
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/vnd.github+json"
        self.session.headers["X-GitHub-Api-Version"] = "2022-11-28"
        token = token or os.environ.get("GITHUB_TOKEN")
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.cache_dir = cache_dir

    # ------------------------------------------------------------------ cache
    def _cache_path(self, repo: str, key: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", key)
        d = self.cache_dir / repo.replace("/", "__")
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{safe}.json"

    # -------------------------------------------------------------------- get
    def get(self, repo: str, path: str, key: str, params: dict | None = None,
            max_retries: int = 3) -> dict | list | None:
        """GET com cache. Retorna None para 404 (ausência é informação)."""
        cache = self._cache_path(repo, key)
        if cache.exists():
            payload = json.loads(cache.read_text())
            return payload["data"]

        url = f"{API}{path}"
        for attempt in range(max_retries + 1):
            resp = self.session.get(url, params=params, timeout=30)
            remaining = int(resp.headers.get("X-RateLimit-Remaining", "1"))
            if resp.status_code == 403 and remaining == 0:
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(0, reset - time.time()) + 1
                raise RateLimitExceeded(f"Rate limit; reset em {wait:.0f}s")
            if resp.status_code == 202:  # /stats/* assíncrono
                time.sleep(2 * (attempt + 1))
                continue
            if resp.status_code == 404:
                data = None
                break
            resp.raise_for_status()
            data = resp.json()
            break
        else:
            data = None  # 202 persistente — tratar como faltante nesta rodada

        cache.write_text(json.dumps(
            {"path": path, "params": params, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "data": data}, ensure_ascii=False))
        return data

    # ---------------------------------------------------------------- graphql
    def graphql(self, repo: str, query: str, variables: dict, key: str,
                max_retries: int = 3) -> dict | None:
        """POST /graphql com o mesmo cache em disco das respostas REST."""
        cache = self._cache_path(repo, key)
        if cache.exists():
            return json.loads(cache.read_text())["data"]
        if "Authorization" not in self.session.headers:
            raise RuntimeError("GraphQL exige GITHUB_TOKEN")

        data = None
        for attempt in range(max_retries + 1):
            resp = self.session.post(f"{API}/graphql",
                                     json={"query": query, "variables": variables},
                                     timeout=60)
            if resp.status_code in (502, 503):  # instável em queries pesadas
                time.sleep(2 * (attempt + 1))
                continue
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("errors") and not payload.get("data"):
                raise RuntimeError(f"GraphQL: {payload['errors'][0].get('message')}")
            data = payload.get("data")
            break

        cache.write_text(json.dumps(
            {"query_key": key, "variables": variables,
             "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "data": data}, ensure_ascii=False))
        return data

    def remaining(self) -> int:
        resp = self.session.get(f"{API}/rate_limit", timeout=15)
        return resp.json()["resources"]["core"]["remaining"]


class RateLimitExceeded(RuntimeError):
    pass
