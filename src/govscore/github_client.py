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

    # ------------------------------------------------------- resiliência HTTP
    MAX_RATELIMIT_WAIT = 3900  # s; acima disto é melhor falhar explicitamente

    def _sleep_if_limited(self, resp) -> bool:
        """Rate limit primário/secundário: dorme e sinaliza retry (plano §5)."""
        if resp.status_code not in (403, 429):
            return False
        if resp.headers.get("Retry-After"):
            time.sleep(min(int(resp.headers["Retry-After"]) + 1, 120))
            return True
        if int(resp.headers.get("X-RateLimit-Remaining", "1")) == 0:
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(0, reset - time.time()) + 1
            if wait > self.MAX_RATELIMIT_WAIT:
                raise RateLimitExceeded(f"Rate limit; reset em {wait:.0f}s")
            print(f"    rate limit — dormindo {wait:.0f}s", flush=True)
            time.sleep(wait)
            return True
        return False

    # -------------------------------------------------------------------- get
    def get(self, repo: str, path: str, key: str, params: dict | None = None,
            max_retries: int = 3) -> dict | list | None:
        """GET com cache. Retorna None para 404 (ausência é informação).

        Transientes (rede, 5xx, 202, rate limit) são retentados com backoff;
        só erros persistentes propagam.
        """
        cache = self._cache_path(repo, key)
        if cache.exists():
            payload = json.loads(cache.read_text())
            return payload["data"]

        url = f"{API}{path}"
        rate_sleeps = 0
        attempt = 0
        while True:
            try:
                resp = self.session.get(url, params=params, timeout=30)
            except (requests.ConnectionError, requests.Timeout):
                if attempt >= max_retries:
                    raise
                time.sleep(2 ** attempt)
                attempt += 1
                continue
            if self._sleep_if_limited(resp):
                rate_sleeps += 1
                if rate_sleeps > 2:
                    raise RateLimitExceeded(f"{path}: rate limit persistente")
                continue
            if resp.status_code in (500, 502, 503, 504) and attempt < max_retries:
                time.sleep(2 ** attempt)
                attempt += 1
                continue
            if resp.status_code == 202:  # /stats/* assíncrono
                if attempt >= max_retries:
                    # 202 persistente — faltante NESTA rodada: não cachear,
                    # senão o None viraria permanente (cache nunca reconsulta)
                    return None
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

        # Só uma resposta DEFINITIVA pode ser cacheada e retornada; esgotar
        # retries levanta erro — jamais gravar None de falha transitória no
        # cache (envenenaria todas as rodadas futuras: cache nunca reconsulta).
        data = None
        rate_sleeps = 0
        attempt = 0
        while True:
            try:
                resp = self.session.post(f"{API}/graphql",
                                         json={"query": query, "variables": variables},
                                         timeout=60)
            except (requests.ConnectionError, requests.Timeout):
                if attempt >= max_retries:
                    raise
                time.sleep(2 ** attempt)
                attempt += 1
                continue
            if self._sleep_if_limited(resp):
                rate_sleeps += 1
                if rate_sleeps > 2:
                    raise RateLimitExceeded(f"graphql {key}: rate limit persistente")
                continue
            if resp.status_code in (500, 502, 503, 504):  # instável em queries pesadas
                if attempt >= max_retries:
                    resp.raise_for_status()
                time.sleep(2 * (attempt + 1))
                attempt += 1
                continue
            resp.raise_for_status()
            payload = resp.json()
            errors = payload.get("errors") or []
            if any(e.get("type") == "RATE_LIMITED" for e in errors):
                rate_sleeps += 1
                if rate_sleeps > 2:
                    raise RateLimitExceeded(f"graphql {key}: rate limit persistente")
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                time.sleep(max(0, reset - time.time()) + 1)
                continue
            if errors and not payload.get("data"):
                raise RuntimeError(f"GraphQL: {errors[0].get('message')}")
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
