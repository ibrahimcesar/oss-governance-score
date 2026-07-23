"""Testes de resiliência do GitHubClient (sessão mockada, sem rede).

Contrato central: só respostas DEFINITIVAS (dados ou 404) entram no cache —
uma falha transitória cacheada envenenaria todas as rodadas futuras, porque
a análise nunca reconsulta a API.
"""
import time

import pytest
import requests

from govscore.github_client import GitHubClient, RateLimitExceeded


class _Resp:
    def __init__(self, status, data=None, headers=None):
        self.status_code = status
        self._data = data
        self.headers = headers or {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


class _Session:
    """Devolve as respostas na ordem; exceções na lista são levantadas."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.headers = {"Authorization": "Bearer t"}

    def _next(self):
        self.calls += 1
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def get(self, *a, **kw):
        return self._next()

    def post(self, *a, **kw):
        return self._next()


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)


def _client(tmp_path, responses):
    gh = GitHubClient(token="t", cache_dir=tmp_path)
    gh.session = _Session(responses)
    return gh


def _cached(tmp_path, repo="o/r"):
    return list((tmp_path / repo.replace("/", "__")).glob("*.json"))


# ------------------------------------------------------------------------ get
def test_get_404_cacheia_none(tmp_path):
    gh = _client(tmp_path, [_Resp(404)])
    assert gh.get("o/r", "/x", "k") is None
    assert len(_cached(tmp_path)) == 1  # ausência é informação — cacheada


def test_get_202_persistente_nao_cacheia(tmp_path):
    gh = _client(tmp_path, [_Resp(202)] * 4)
    assert gh.get("o/r", "/x", "k") is None
    assert _cached(tmp_path) == []  # faltante NESTA rodada, não para sempre


def test_get_sucesso_apos_falha_de_rede(tmp_path):
    gh = _client(tmp_path, [requests.ConnectionError(), _Resp(200, {"a": 1})])
    assert gh.get("o/r", "/x", "k") == {"a": 1}
    assert len(_cached(tmp_path)) == 1
    # segunda chamada vem do cache, sem HTTP
    assert gh.get("o/r", "/x", "k") == {"a": 1}
    assert gh.session.calls == 2


def test_get_rate_limit_persistente_levanta(tmp_path):
    limited = _Resp(403, headers={"X-RateLimit-Remaining": "0",
                                  "X-RateLimit-Reset": "0"})
    gh = _client(tmp_path, [limited] * 4)
    with pytest.raises(RateLimitExceeded):
        gh.get("o/r", "/x", "k")
    assert _cached(tmp_path) == []


# -------------------------------------------------------------------- graphql
def test_graphql_502_persistente_levanta_e_nao_cacheia(tmp_path):
    gh = _client(tmp_path, [_Resp(502)] * 5)
    with pytest.raises(requests.HTTPError):
        gh.graphql("o/r", "query {}", {}, "gql_k")
    assert _cached(tmp_path) == []  # cache jamais envenenado por transitório


def test_graphql_rate_limit_persistente_levanta(tmp_path):
    limited = _Resp(403, headers={"X-RateLimit-Remaining": "0",
                                  "X-RateLimit-Reset": "0"})
    gh = _client(tmp_path, [limited] * 4)
    with pytest.raises(RateLimitExceeded):
        gh.graphql("o/r", "query {}", {}, "gql_k")
    assert _cached(tmp_path) == []


def test_graphql_sucesso_apos_502_cacheia(tmp_path):
    gh = _client(tmp_path, [_Resp(502),
                            _Resp(200, {"data": {"repository": {}}})])
    assert gh.graphql("o/r", "query {}", {}, "gql_k") == {"repository": {}}
    assert len(_cached(tmp_path)) == 1
    assert gh.graphql("o/r", "query {}", {}, "gql_k") == {"repository": {}}
    assert gh.session.calls == 2  # segunda veio do cache
