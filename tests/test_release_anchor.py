"""Ancoragem da janela de releases no snapshot (catálogo v2, M4).

Antes do reparo, `extract_security` cortava a janela de 12 meses em
`datetime.now() − 365 d`: reproduzia a extração de julho de 2026 apenas se
executada em julho de 2026. A decisão 2026-09-13 fixa o corte na constante
do snapshot (2026-07-24T23:59:59Z − 365 d), o que reproduz v1 e impede a
deriva silenciosa em qualquer re-execução futura.
"""
from datetime import datetime, timedelta, timezone

from govscore import cli
from govscore.extract import artifacts
from govscore.extract.artifacts import (
    SNAPSHOT_UTC,
    extract_security,
    release_cutoff,
    release_metrics,
)


class _StubClient:
    """GitHubClient falso: responde de um dicionário {(repo, key): data};
    GraphQL sempre vazio (D3 não é objeto destes testes)."""

    def __init__(self, responses: dict):
        self.responses = responses

    def get(self, repo, path, key, **kw):
        return self.responses.get((repo, key))

    def graphql(self, repo, query, variables, key, **kw):
        return None


# Releases em torno do corte v2 (2025-07-24T23:59:59Z). A sondagem v1 deste
# repositório ocorreu em 24/07/2026 à noite: o corte `now − 365 d` de v1 cai
# no mesmo dia — os dois lados concordam.
RELEASES = [
    {"published_at": "2026-07-20T00:00:00Z", "body": "notas"},       # dentro
    {"published_at": "2026-01-15T00:00:00Z", "body": ""},            # dentro
    {"published_at": "2025-07-25T01:00:00Z", "body": "notas"},       # dentro
    {"published_at": "2025-07-24T22:00:00Z", "body": "notas"},       # fora (1h59 antes)
    {"published_at": "2025-06-01T00:00:00Z", "body": "notas"},       # fora
]
V1_PROBE_INSTANT = datetime(2026, 7, 24, 23, 30, tzinfo=timezone.utc)


def test_snapshot_constant_e_corte_de_releases():
    assert SNAPSHOT_UTC == datetime(2026, 7, 24, 23, 59, 59, tzinfo=timezone.utc)
    assert release_cutoff() == datetime(2025, 7, 24, 23, 59, 59,
                                        tzinfo=timezone.utc)
    # snapshot ingênuo (sem fuso) é tratado como UTC
    assert release_cutoff(datetime(2026, 7, 24, 23, 59, 59)) == release_cutoff()


def test_extract_security_ancorado_reproduz_v1():
    gh = _StubClient({("a/b", "releases"): RELEASES})
    # semântica v1: corte = instante da sondagem − 365 d
    v1 = release_metrics(RELEASES, V1_PROBE_INSTANT - timedelta(days=365))
    assert v1 == (3, 2 / 3)

    sec = extract_security(gh, "a/b")  # default = SNAPSHOT_UTC
    assert (sec["releases_12m"], sec["release_notes_share"]) == v1

    # a mesma chamada ancorada em "agora" um ano depois divergiria: toda a
    # janela de julho/2025→julho/2026 sai e a prática vira não observável
    fake_now = SNAPSHOT_UTC + timedelta(days=365)
    drift = extract_security(gh, "a/b", snapshot=fake_now)
    assert drift["releases_12m"] == 0 and drift["release_notes_share"] is None
    assert drift["releases_12m"] != sec["releases_12m"]


def test_extract_security_sem_datetime_now():
    """Guarda de regressão: nenhuma chamada a `now()`/`utcnow()`/`today()`
    no módulo — a janela de D5 só pode depender do parâmetro `snapshot`."""
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(artifacts))
    calls = [n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    assert not {"now", "utcnow", "today"} & set(calls)


def test_extract_repo_propaga_snapshot():
    gh = _StubClient({("a/b", "repo_metadata"): {"stargazers_count": 1,
                                                 "forks_count": 1},
                      ("a/b", "releases"): RELEASES})
    m = cli.extract_repo(gh, "a/b", include_contributions=False)
    assert m["security"]["releases_12m"] == 3
    m2 = cli.extract_repo(gh, "a/b", include_contributions=False,
                          snapshot=SNAPSHOT_UTC + timedelta(days=365))
    assert m2["security"]["releases_12m"] == 0


def test_parse_snapshot_formatos():
    assert cli.parse_snapshot("2026-07-24") == SNAPSHOT_UTC        # fim do dia
    assert cli.parse_snapshot("2026-07-24T23:59:59Z") == SNAPSHOT_UTC
    assert cli.parse_snapshot("2026-07-24T20:59:59-03:00") == SNAPSHOT_UTC
    assert cli.parse_snapshot("2026-07-24T23:59:59") == SNAPSHOT_UTC  # ingênuo = UTC
    assert cli.parse_snapshot(SNAPSHOT_UTC) == SNAPSHOT_UTC


def test_cli_snapshot_default_e_override():
    ap = cli.build_parser()
    for argv in (["pilot"], ["extract", "--repo", "a/b"], ["run"]):
        assert ap.parse_args(argv).snapshot == SNAPSHOT_UTC
    args = ap.parse_args(["run", "--snapshot", "2027-01-01"])
    assert args.snapshot == datetime(2027, 1, 1, 23, 59, 59, tzinfo=timezone.utc)
