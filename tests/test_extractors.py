"""Testes das correções de extração descobertas no piloto (2026-07-19).

Casos conhecidos: kubernetes/kubernetes (monorepo com vendor/ e staging/;
security policy em .github/SECURITY.md) e expressjs/express (security policy
herdada de expressjs/.github).
"""
from govscore.extract.artifacts import has_security_policy
from govscore.extract.git_extractor import (
    ARTIFACT_PATTERNS,
    SECURITY_PATTERNS,
    _present,
)


# ---------------------------------------------------------------- backend git
def test_ci_pattern_ignores_vendored_paths():
    assert _present([".circleci/config.yml"], SECURITY_PATTERNS["ci_configured"])
    assert _present([".github/workflows/ci.yaml"], SECURITY_PATTERNS["ci_configured"])
    # caso kubernetes: vendor/ e staging/ não são CI do próprio repo
    assert not _present(["vendor/foo/.circleci/config.yml"],
                        SECURITY_PATTERNS["ci_configured"])
    assert not _present(["staging/src/k8s.io/x/.github/workflows/ci.yaml"],
                        SECURITY_PATTERNS["ci_configured"])


def test_security_policy_pattern_only_conventional_paths():
    assert _present(["security.md"], SECURITY_PATTERNS["security_policy"])
    assert _present([".github/security.md"], SECURITY_PATTERNS["security_policy"])
    assert not _present(["staging/src/k8s.io/docs/security.md"],
                        SECURITY_PATTERNS["security_policy"])


def test_license_pattern_ignores_vendored_licenses():
    assert _present(["license"], ARTIFACT_PATTERNS["license"])
    assert _present(["license.txt"], ARTIFACT_PATTERNS["license"])
    assert not _present(["vendor/foo/license"], ARTIFACT_PATTERNS["license"])


# ---------------------------------------------------------------- backend api
class _StubClient:
    """GitHubClient falso: responde de um dicionário {(repo, key): data}."""

    def __init__(self, responses: dict):
        self.responses = responses

    def get(self, repo, path, key, **kw):
        return self.responses.get((repo, key))


def test_security_policy_in_repo_root():
    gh = _StubClient({("astropy/astropy", "security_md"): {"name": "SECURITY.md"}})
    assert has_security_policy(gh, "astropy/astropy") == (True, False)


def test_security_policy_in_dot_github_dir():
    gh = _StubClient({("kubernetes/kubernetes", "security_md_github"):
                      {"name": "SECURITY.md"}})
    assert has_security_policy(gh, "kubernetes/kubernetes") == (True, False)


def test_security_policy_inherited_from_org():
    gh = _StubClient({("expressjs/.github", "security_md"): {"name": "SECURITY.md"}})
    assert has_security_policy(gh, "expressjs/express") == (True, True)


def test_security_policy_absent():
    gh = _StubClient({})
    assert has_security_policy(gh, "ibrahimcesar/react-lite-youtube-embed") == (False, False)


# ------------------------------------------------- D3 GraphQL (decisão 2026-07-19)
from govscore.extract.responsiveness import (  # noqa: E402
    first_response_hours,
    is_bot,
    review_coverage,
)


def test_is_bot_heuristic():
    assert is_bot({"login": "dependabot", "__typename": "Bot"})
    assert is_bot({"login": "k8s-ci-robot", "__typename": "User"})  # caso kubernetes
    assert not is_bot({"login": "alice", "__typename": "User"})
    assert not is_bot(None)  # autor removido (ghost)


def test_first_response_ignores_author_and_bots():
    issue = {
        "createdAt": "2026-01-01T00:00:00Z",
        "author": {"login": "alice"},
        "comments": {"nodes": [
            {"createdAt": "2026-01-01T01:00:00Z", "author": {"login": "alice"}},
            {"createdAt": "2026-01-01T02:00:00Z",
             "author": {"login": "helper-bot", "__typename": "Bot"}},
            {"createdAt": "2026-01-01T05:00:00Z", "author": {"login": "bob"}},
        ]},
    }
    assert first_response_hours(issue) == 5.0


def test_first_response_none_without_human_reply():
    issue = {"createdAt": "2026-01-01T00:00:00Z", "author": {"login": "alice"},
             "comments": {"nodes": [
                 {"createdAt": "2026-01-01T01:00:00Z",
                  "author": {"login": "stale-bot", "__typename": "Bot"}}]}}
    assert first_response_hours(issue) is None


def test_review_coverage_known_case():
    prs = [{"reviews": {"totalCount": 1}}, {"reviews": {"totalCount": 0}},
           {"reviews": {"totalCount": 2}}, {"reviews": {"totalCount": 1}}]
    assert review_coverage(prs) == 0.75
    assert review_coverage([]) is None


# ------------------------------------------------- D4 (elephant factor, retenção)
from collections import Counter  # noqa: E402

from govscore.extract.git_extractor import (  # noqa: E402
    contributor_retention,
    elephant_factor,
)


def test_elephant_factor_one_org_dominates():
    counts = Counter({"a@corp.com": 4, "b@corp.com": 2,
                      "alice@gmail.com": 3, "bob@gmail.com": 1})
    # corp.com = 6 de 10 commits ≥ 50% → 1 organização basta
    assert elephant_factor(counts) == 1


def test_elephant_factor_generic_domains_count_per_person():
    counts = Counter({"alice@gmail.com": 4, "bob@gmail.com": 3, "c@corp.com": 3})
    # unidades: alice(4), bob(3), corp(3); 4 < 5, 4+3 = 7 ≥ 5 → 2
    assert elephant_factor(counts) == 2
    assert elephant_factor(Counter()) is None


def test_contributor_retention_known_case():
    day = 86400
    now = 1_000_000_000
    times = {
        "a@x.com": [now - 8 * day, now - 2 * day],   # ativa nas duas metades
        "b@x.com": [now - 9 * day],                  # só na 1ª metade
        "c@x.com": [now - 1 * day],                  # só na 2ª metade
    }
    assert contributor_retention(times, now_ts=now, window_days=10) == 0.5
    assert contributor_retention({}, now_ts=now, window_days=10) is None


# ------------------------------------------------- D1 funding / D5 release notes
from datetime import datetime, timezone  # noqa: E402

from govscore.extract.artifacts import has_funding, release_metrics  # noqa: E402
from govscore.extract.git_extractor import ARTIFACT_PATTERNS as _AP  # noqa: E402


def test_funding_pattern_git_backend():
    assert _present([".github/funding.yml"], _AP["funding"])
    assert _present(["funding.yml"], _AP["funding"])
    assert not _present(["packages/x/funding.yml"], _AP["funding"])


def test_has_funding_repo_and_org_fallback():
    gh = _StubClient({("expressjs/express", "funding_yml_github"): {"name": "FUNDING.yml"}})
    assert has_funding(gh, "expressjs/express") == (True, False)
    gh = _StubClient({("astropy/.github", "funding_yml"): {"name": "FUNDING.yml"}})
    assert has_funding(gh, "astropy/astropy") == (True, True)
    assert has_funding(_StubClient({}), "a/b") == (False, False)


def test_release_metrics_notes_share():
    cutoff = datetime(2026, 1, 1, tzinfo=timezone.utc)
    releases = [
        {"published_at": "2026-03-01T00:00:00Z", "body": "## Changelog\n- fix"},
        {"published_at": "2026-02-01T00:00:00Z", "body": "  "},
        {"published_at": "2025-06-01T00:00:00Z", "body": "antiga, fora da janela"},
        {"published_at": None, "body": "draft — ignorada"},
    ]
    assert release_metrics(releases, cutoff) == (2, 0.5)
    assert release_metrics([], cutoff) == (0, None)  # sem release → None, não 0
