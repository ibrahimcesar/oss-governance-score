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
    # catálogo v2 (decisão 2026-09-13): no repositório só .github/FUNDING.yml
    # pontua; a raiz vale apenas no repositório especial {owner}/.github
    assert not _present(["funding.yml"], _AP["funding"])
    assert not _present(["packages/x/funding.yml"], _AP["funding"])


def test_git_backend_patterns_are_v2_sources():
    """As tabelas v1 (dict[str, str]) são a união textual das regras v2 —
    fonte única em extract/patterns.py."""
    from govscore.extract.patterns import D1_RULES, D5_RULES, joined_source
    assert set(ARTIFACT_PATTERNS) == set(D1_RULES)
    assert set(SECURITY_PATTERNS) == set(D5_RULES)
    assert ARTIFACT_PATTERNS["codeowners"] == joined_source(D1_RULES["codeowners"])
    # _present aceita a fonte textual ou o padrão compilado e normaliza a caixa
    assert _present([".github/CODEOWNERS"], ARTIFACT_PATTERNS["codeowners"])
    assert _present([".github/CODEOWNERS"], D1_RULES["codeowners"][0])


def test_inheritance_needed_only_for_missing_inheritable_items():
    """O clone de `{owner}/.github` só acontece quando falta algum item
    HERDÁVEL; itens que nunca herdam (license, codeowners, CI…) não o disparam."""
    from govscore.extract.git_extractor import _inheritance_needed
    from govscore.extract.patterns import D1_ITEMS, D5_ITEMS, INHERITABLE
    full_a = {k: True for k in D1_ITEMS}
    full_s = {k: True for k in D5_ITEMS}
    assert not _inheritance_needed(full_a, full_s)
    # faltam só itens não herdáveis → não precisa da organização
    a = dict(full_a, license=False, codeowners=False, readme=False, governance=False)
    s = dict(full_s, ci_configured=False, dependency_automation=False)
    assert not _inheritance_needed(a, s)
    # qualquer herdável ausente (em D1 ou em D5) dispara
    for item in INHERITABLE:
        a, s = dict(full_a), dict(full_s)
        (a if item in a else s)[item] = False
        assert _inheritance_needed(a, s), item


def test_parse_ls_tree_keeps_blobs_and_symlinks_only():
    from govscore.extract.git_extractor import _parse_ls_tree
    out = "\0".join([
        "100644 blob 1111111111111111111111111111111111111111\tREADME.md",
        "120000 blob 2222222222222222222222222222222222222222\t.github/SECURITY.md",
        "160000 commit 3333333333333333333333333333333333333333\tvendor/LICENSE",
        "100755 blob 4444444444444444444444444444444444444444\tscripts/run.sh",
        "",
    ])
    assert _parse_ls_tree(out) == ["readme.md", ".github/security.md", "scripts/run.sh"]
    assert _parse_ls_tree("") == []


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
