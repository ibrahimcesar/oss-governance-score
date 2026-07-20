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
