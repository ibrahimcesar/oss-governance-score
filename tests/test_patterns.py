"""Regras v2 de detecção de D1/D5 (decisão 2026-09-13) — casos conhecidos.

Cada caso reproduz um repositório da amostra (ou um contraexemplo documentado)
que motivou a regra: nodejs/node (issue forms em `.github/ISSUE_TEMPLATE/*.yml`),
golang/go (`.github/PULL_REQUEST_TEMPLATE` sem extensão), tensorflow
(`CODEOWNERS` na raiz), rails (`.github/security.md` em minúsculas), jekyll
(`.github/SECURITY.markdown`), guzzle (política herdada de
`guzzle/.github/.github/SECURITY.md`), gitlabhq (`.gitlab-ci.yml`), rust
(`.github/renovate.json5`), kubernetes (caminhos vendorizados que NÃO contam).
Nenhum teste toca a rede: `detect` opera sobre listas de caminhos.
"""
import re
from datetime import timezone
from pathlib import Path

import pytest

from govscore.extract.patterns import (
    CI_SYSTEMS,
    D1_ITEMS,
    D1_RULES,
    D5_ITEMS,
    D5_RULES,
    DEP_TOOLS,
    FLAG_RULES,
    INHERITABLE,
    LOC,
    DOC,
    ORG_RULES,
    SNAPSHOT_UTC,
    SYMLINK_MODE,
    detect,
    joined_source,
    matches,
    normalize,
    symlink_hits,
)

# --------------------------------------------- regras congeladas (verbatim)
# Cópia LITERAL do bloco "Regras v2" do registro de decisão de 2026-09-13.
# O teste abaixo garante que nenhuma expressão compilada em `patterns.py`
# diverge do texto congelado — qualquer ajuste de regra exige catálogo v3
# com novo registro, e quebra este teste por construção.
RECORD_PATH = Path(__file__).resolve().parents[1] / "docs" / "decisions" / \
    "2026-09-13-catalogo-v2-reparo-d1-d5.md"
RECORD_RULES_BLOCK = r"""
readme                ^LOC readme DOC$
contributing          ^LOC contributing DOC$
code_of_conduct       ^LOC code[-_]of[-_]conduct DOC$
license (só raiz)     ^((un)?licen[sc]e|copying|copyright)(\.(md|txt|rst|markdown))?$
                    | ^((un)?licen[sc]e|copying|copyright)[-_.](?!.*\.json[5c]?$)[a-z0-9.+_-]+$
                    | ^[a-z0-9]+[-_](un)?licen[sc]e(\.[a-z]+)?$
                    | ^patents$ | ^ofl\.md$
issue_template        ^LOC issue_template DOC$
                    | ^\.github/issue_template/(?!config\.ya?ml$)[^/]+\.(md|yml)$
pull_request_template ^LOC pull_request_template DOC$
                    | ^LOC pull_request_template/[^/]+\.(md|txt)$
codeowners            ^LOC codeowners$
governance            ^LOC governance DOC$
funding (repo)        ^\.github/funding\.yml$
funding (org)         ^(\.github/)?funding\.yml$
security_policy       ^LOC security\.(md|markdown|adoc|rst)$
ci_configured         ^\.github/workflows/[^/]+\.ya?ml$ | ^\.travis\.ya?ml$
                    | ^\.circleci/config\.ya?ml$ | ^jenkinsfile$ | ^\.jenkins/.+
                    | ^azure-pipelines([-.][a-z0-9-]+)?\.ya?ml$ | ^\.azure-pipelines/.+\.ya?ml$
                    | ^\.gitlab-ci\.ya?ml$ | ^\.gitlab/ci/.+ | ^\.drone\.ya?ml$
                    | ^\.buildkite/[^/]+\.ya?ml$ | ^\.?appveyor\.ya?ml$ | ^cloudbuild\.ya?ml$
                    | ^\.cirrus\.ya?ml$ | ^\.semaphore/[^/]+\.ya?ml$ | ^bitbucket-pipelines\.ya?ml$
                    | ^\.woodpecker\.ya?ml$ | ^\.woodpecker/[^/]+\.ya?ml$ | ^\.prow\.ya?ml$ | ^\.prow/.+
                    | ^\.zuul\.ya?ml$ | ^zuul\.d/.+ | ^\.tekton/[^/]+\.ya?ml$
                    | ^\.(forgejo|gitea)/workflows/[^/]+\.ya?ml$
dependency_automation ^\.github/dependabot\.yml$
                    | ^(\.github/|\.gitlab/)?renovate\.json[5c]?$ | ^\.renovaterc(\.json[5c]?)?$
                    | ^(\.github/|\.config/)?\.?scala-steward\.conf$ | ^\.pyup\.ya?ml$
"""


def parse_record_rules(block: str) -> dict[str, str]:
    """`nome  alt | alt` (+ continuações iniciadas por `|`) → união `a|b|c`
    com as abreviaturas LOC/DOC expandidas; `funding (repo)`/`(org)` viram
    `funding:repo`/`funding:org`. As expressões não contêm espaços
    significativos, logo todo espaço em branco é descartado."""
    rules: dict[str, list[str]] = {}
    key = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line.lstrip().startswith("|"):
            body = line.strip()[1:]
        else:
            m = re.match(r"^(\w+)(?:\s+\(([^)]*)\))?\s+(.*)$", line)
            name, qualifier, body = m.group(1), m.group(2), m.group(3)
            key = f"{name}:{qualifier}" if name == "funding" else name
            rules.setdefault(key, [])
        for alt in body.split(" | "):
            alt = re.sub(r"\s+", "", alt).replace("LOC", LOC).replace("DOC", DOC)
            if alt:
                rules[key].append(alt)
    return {k: "|".join(v) for k, v in rules.items()}


def compiled_rules() -> dict[str, str]:
    out = {k: joined_source(v) for k, v in D1_RULES.items()}
    out.update({k: joined_source(v) for k, v in D5_RULES.items()})
    out["funding:repo"] = out.pop("funding")
    out["funding:org"] = joined_source(ORG_RULES["funding"])
    return out


def test_compiled_rules_are_verbatim_from_decision_record():
    expected = parse_record_rules(RECORD_RULES_BLOCK)
    assert set(expected) == set(compiled_rules())
    for item, source in compiled_rules().items():
        assert source == expected[item], item
    # ORG_RULES reutiliza as regras do repositório nos demais itens herdáveis
    for item in INHERITABLE:
        if item not in ("funding", "issue_template"):
            assert ORG_RULES[item] is D1_RULES.get(item, D5_RULES.get(item))
    assert joined_source(ORG_RULES["issue_template"]) == \
        r"^\.github/issue_template/(?!config\.ya?ml$)[^/]+\.(md|yml)$"


@pytest.mark.skipif(not RECORD_PATH.exists(),
                    reason="registro de decisão ainda não está nesta árvore")
def test_embedded_block_equals_decision_record_file():
    """Quando o registro está no repositório, a cópia embutida acima deve ser
    idêntica ao bloco `Regras v2` do arquivo (a menos de espaço em branco)."""
    text = RECORD_PATH.read_text(encoding="utf-8")
    block = text.split("## Regras v2", 1)[1].split("```", 2)[1]
    squash = lambda s: re.sub(r"\s+", " ", s).strip()  # noqa: E731
    assert squash(block) == squash(RECORD_RULES_BLOCK)


def art(paths, org=None):
    return detect(paths, org)[0]


def sec(paths, org=None):
    return detect(paths, org)[1]


def meta(paths, org=None):
    return detect(paths, org)[2]


# ------------------------------------------------------------- catálogo/API
def test_catalogue_shape_matches_decision_record():
    assert D1_ITEMS == ("readme", "contributing", "code_of_conduct", "license",
                        "issue_template", "pull_request_template", "codeowners",
                        "governance", "funding")
    assert D5_ITEMS == ("security_policy", "ci_configured", "dependency_automation")
    assert set(ORG_RULES) == set(INHERITABLE)
    # nunca herdam: readme, license, codeowners, governance, CI, dependências
    assert not {"readme", "license", "codeowners", "governance",
                "ci_configured", "dependency_automation"} & set(INHERITABLE)
    assert set(FLAG_RULES) == {"issue_template_yaml_only", "issue_template_config_only",
                               "funding_yaml", "dependabot_yaml"}
    # ci_configured / dependency_automation são a união das listas fechadas
    assert D5_RULES["ci_configured"] == list(CI_SYSTEMS.values())
    assert D5_RULES["dependency_automation"] == list(DEP_TOOLS.values())


def test_snapshot_constant():
    assert SNAPSHOT_UTC.isoformat() == "2026-07-24T23:59:59+00:00"
    assert SNAPSHOT_UTC.tzinfo is timezone.utc


def test_normalize_lowercases_and_strips_dot_slash():
    assert normalize(["./README.md", ".github/CODEOWNERS", "docs/Security.MD"]) == [
        "readme.md", ".github/codeowners", "docs/security.md"]
    assert normalize([]) == []


def test_detect_empty_tree_is_all_false():
    a, s, m = detect([])
    assert a == {k: False for k in D1_ITEMS}
    assert s == {k: False for k in D5_ITEMS}
    assert m["inherited_from_org"] == [] and m["ci_systems"] == []
    assert all(v is False for v in m["flags"].values())
    assert set(m["matched"]) == set(D1_ITEMS) | set(D5_ITEMS)


# ------------------------------------------------------------ issue_template
def test_issue_template_nodejs_issue_form_yml():
    a = art([".github/ISSUE_TEMPLATE/1-bug-report.yml", "README.md"])
    assert a["issue_template"] is True
    assert "issue_template_inherited" not in a


def test_issue_template_config_only_is_flag_not_score():
    a, _, m = detect([".github/ISSUE_TEMPLATE/config.yml"])
    assert a["issue_template"] is False
    assert m["flags"]["issue_template_config_only"] is True
    assert m["flags"]["issue_template_yaml_only"] is False


def test_issue_template_yaml_only_is_flag_not_score():
    a, _, m = detect([".github/ISSUE_TEMPLATE/bug.yaml"])
    assert a["issue_template"] is False
    assert m["flags"]["issue_template_yaml_only"] is True
    # config.yaml é o seletor, não um formulário .yaml
    assert meta([".github/ISSUE_TEMPLATE/config.yaml"])["flags"]["issue_template_yaml_only"] is False


def test_issue_template_flags_cleared_when_scoring_template_exists():
    _, _, m = detect([".github/ISSUE_TEMPLATE/bug.yaml",
                      ".github/ISSUE_TEMPLATE/config.yml",
                      ".github/ISSUE_TEMPLATE/feature.md"])
    assert m["flags"]["issue_template_yaml_only"] is False
    assert m["flags"]["issue_template_config_only"] is False


def test_issue_template_flags_share_flip_semantics():
    # Semântica uniforme das flags: "trocaria de valor se a variante fosse
    # aceita". Um repositório com bug.yaml + config.yml (e nenhum template que
    # pontue) trocaria sob QUALQUER das duas variantes — aciona as duas flags.
    a, _, m = detect([".github/ISSUE_TEMPLATE/bug.yaml",
                      ".github/ISSUE_TEMPLATE/config.yml"])
    assert a["issue_template"] is False
    assert m["flags"]["issue_template_yaml_only"] is True
    assert m["flags"]["issue_template_config_only"] is True


def test_issue_template_legacy_single_file():
    assert art([".github/ISSUE_TEMPLATE.md"])["issue_template"]
    assert art(["issue_template.md"])["issue_template"]
    assert art(["docs/ISSUE_TEMPLATE"])["issue_template"]
    # fora dos locais documentados ou sem extensão de template/formulário
    assert not art(["src/.github/ISSUE_TEMPLATE/bug.md"])["issue_template"]
    assert not art([".github/ISSUE_TEMPLATE/bug.txt"])["issue_template"]


# ---------------------------------------------------- pull_request_template
def test_pull_request_template_golang_extensionless():
    assert art([".github/PULL_REQUEST_TEMPLATE"])["pull_request_template"]


def test_pull_request_template_directory_file():
    assert art(["PULL_REQUEST_TEMPLATE/ci.md"])["pull_request_template"]
    assert art([".github/PULL_REQUEST_TEMPLATE/feature.txt"])["pull_request_template"]
    assert not art([".github/PULL_REQUEST_TEMPLATE/feature.yml"])["pull_request_template"]


# ---------------------------------------------------------------- codeowners
def test_codeowners_documented_locations_only():
    assert art(["CODEOWNERS"])["codeowners"]           # tensorflow: raiz
    assert art(["docs/CODEOWNERS"])["codeowners"]
    assert art([".github/codeowners"])["codeowners"]   # caminhos em minúsculas
    assert not art(["src/CODEOWNERS"])["codeowners"]
    assert not art(["vendor/x/.github/CODEOWNERS"])["codeowners"]


# ------------------------------------------------------------------- license
@pytest.mark.parametrize("path", [
    "LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYRIGHT", "UNLICENSE",
    "LICENSE-MIT", "LICENSE.APACHE2", "COPYING.GPLv2", "MIT-LICENSE",
    "mit_license.txt", "PATENTS", "OFL.md",
])
def test_license_positive_family(path):
    assert art([path])["license"] is True, path


@pytest.mark.parametrize("path", [
    "license-metadata.json", "licenses/foo", "src/license", "vendor/foo/license",
    "docs/LICENSE", ".github/LICENSE", "LICENSES.md", "license_metadata.json5",
])
def test_license_negative_family(path):
    # só raiz; metadados *.json excluídos (Licensee não lê license-metadata.json)
    assert art([path])["license"] is False, path


# ------------------------------------------------------------------- funding
def test_funding_only_dot_github_yml():
    assert art([".github/funding.yml"])["funding"]
    assert art([".github/FUNDING.yml"])["funding"]
    assert not art(["funding.yml"])["funding"]          # raiz não conta no repo
    assert not art(["packages/x/.github/funding.yml"])["funding"]


def test_funding_yaml_is_flag_not_score():
    a, _, m = detect([".github/FUNDING.yaml"])
    assert a["funding"] is False
    assert m["flags"]["funding_yaml"] is True
    # com o .yml presente, a flag não se aplica
    assert meta([".github/FUNDING.yaml", ".github/FUNDING.yml"])["flags"]["funding_yaml"] is False
    # a variante é procurada no MESMO local da regra que pontua (.github/):
    # FUNDING.yaml na raiz não trocaria o valor nem como .yml — sem flag
    assert meta(["FUNDING.yaml"])["flags"]["funding_yaml"] is False
    assert meta(["FUNDING.yml"])["flags"]["funding_yaml"] is False


# --------------------------------------------------- readme/contrib/coc/gov
def test_readme_contributing_coc_governance_locations_and_doc_extensions():
    a = art(["README.rst", "docs/CONTRIBUTING.md", ".github/CODE_OF_CONDUCT.adoc",
             "GOVERNANCE"])
    assert a["readme"] and a["contributing"] and a["code_of_conduct"] and a["governance"]
    a = art(["README.html", "contributing.py", "code_of_conduct/index.md",
             "community/GOVERNANCE.md"])
    assert not (a["readme"] or a["contributing"] or a["code_of_conduct"] or a["governance"])


# ----------------------------------------------------------- security_policy
def test_security_policy_positive_cases():
    assert sec([".github/security.md"])["security_policy"]        # rails
    assert sec([".github/SECURITY.markdown"])["security_policy"]  # jekyll
    assert sec(["SECURITY.md"])["security_policy"]
    assert sec(["docs/SECURITY.rst"])["security_policy"]
    assert sec(["SECURITY.adoc"])["security_policy"]


def test_security_policy_negative_cases():
    assert not sec(["security.go"])["security_policy"]
    assert not sec(["docs/security/index.md"])["security_policy"]
    assert not sec(["staging/docs/security.md"])["security_policy"]   # kubernetes
    assert not sec(["SECURITY"])["security_policy"]                   # sem extensão
    assert not sec(["SECURITY.txt"])["security_policy"]               # fora da lista


# ------------------------------------------------------------- ci_configured
@pytest.mark.parametrize("path,system", [
    (".github/workflows/ci.yaml", "github_actions"),
    (".gitlab-ci.yml", "gitlab_ci"),               # gitlabhq
    (".circleci/config.yml", "circleci"),          # uniffi
    ("Jenkinsfile", "jenkins"),
    (".travis.yml", "travis"),
    ("azure-pipelines-ci.yml", "azure_pipelines"),
    (".drone.yml", "drone"),
    ("appveyor.yml", "appveyor"),
    (".cirrus.yml", "cirrus"),
    ("zuul.d/jobs.yaml", "zuul"),
    (".gitea/workflows/build.yml", "forgejo_gitea_actions"),
])
def test_ci_recognised_providers(path, system):
    s, m = sec([path]), meta([path])
    assert s["ci_configured"] is True, path
    assert m["ci_systems"] == [system]


def test_ci_negative_cases():
    for p in ["vendor/x/.circleci/config.yml",
              "staging/src/k8s.io/x/.github/workflows/ci.yaml",
              ".github/workflows/README.md", ".github/workflows/sub/ci.yml",
              "ci/build.sh", "Makefile"]:
        assert not sec([p])["ci_configured"], p


# ----------------------------------------------------- dependency_automation
def test_dependency_automation_positive_cases():
    assert sec([".github/dependabot.yml"])["dependency_automation"]
    assert sec([".github/renovate.json5"])["dependency_automation"]   # rust
    assert sec([".renovaterc"])["dependency_automation"]
    assert sec([".renovaterc.json"])["dependency_automation"]
    assert sec([".gitlab/renovate.json"])["dependency_automation"]
    assert sec([".scala-steward.conf"])["dependency_automation"]
    assert sec([".pyup.yml"])["dependency_automation"]
    m = meta([".github/dependabot.yml", "renovate.json"])
    assert m["dependency_tools"] == ["dependabot", "renovate"]


def test_dependabot_yaml_is_flag_not_score():
    s, m = sec([".github/dependabot.yaml"]), meta([".github/dependabot.yaml"])
    assert s["dependency_automation"] is False
    assert m["flags"]["dependabot_yaml"] is True
    assert not sec(["dependabot.yml"])["dependency_automation"]         # raiz
    assert not sec(["packages/renovate.json"])["dependency_automation"]


# ------------------------------------------------------------------- herança
def test_inherit_security_policy_from_org_dot_github_subdir():
    # guzzle/guzzle: política em guzzle/.github/.github/SECURITY.md
    a, s, m = detect(["README.md"], [".github/SECURITY.md"])
    assert s["security_policy"] is True
    assert s["security_policy_inherited"] is True
    assert m["inherited_from_org"] == ["security_policy"]
    assert m["org_matched"]["security_policy"] == [".github/security.md"]
    assert m["matched"]["security_policy"] == []


def test_inherit_security_policy_from_org_root():
    # expressjs/express: política em expressjs/.github/SECURITY.md
    s = sec(["README.md"], ["SECURITY.md"])
    assert s["security_policy"] is True and s["security_policy_inherited"] is True


def test_no_inheritance_when_repo_has_own_file():
    a, s, m = detect(["SECURITY.md", "CONTRIBUTING.md"],
                     [".github/SECURITY.md", "CONTRIBUTING.md"])
    assert s["security_policy"] and "security_policy_inherited" not in s
    assert a["contributing"] and "contributing_inherited" not in a
    assert m["inherited_from_org"] == []


def test_never_inherit_codeowners_license_readme_governance_ci_deps():
    a, s, m = detect([], ["CODEOWNERS", "LICENSE", "README.md", "GOVERNANCE.md",
                          ".github/workflows/ci.yml", ".github/dependabot.yml"])
    assert not any([a["codeowners"], a["license"], a["readme"], a["governance"],
                    s["ci_configured"], s["dependency_automation"]])
    assert m["inherited_from_org"] == []
    assert not any(k.endswith("_inherited") for k in list(a) + list(s))


def test_inherit_issue_template_only_from_org_issue_template_dir():
    a = art([], [".github/issue_template/bug.md"])
    assert a["issue_template"] is True and a["issue_template_inherited"] is True
    a = art([], ["issue_template.md"])          # legado não é default file
    assert a["issue_template"] is False and "issue_template_inherited" not in a
    a = art([], [".github/issue_template/config.yml"])
    assert a["issue_template"] is False


def test_inherit_funding_from_org_root_or_dot_github():
    for org in (["FUNDING.yml"], [".github/FUNDING.yml"]):
        a = art(["README.md"], org)
        assert a["funding"] is True and a["funding_inherited"] is True
    assert not art([], ["FUNDING.yaml"])["funding"]
    assert not art([], ["docs/FUNDING.yml"])["funding"]


def test_inherit_contributing_coc_pr_template():
    a, _, m = detect([], ["CONTRIBUTING.md", "docs/CODE_OF_CONDUCT.md",
                          ".github/PULL_REQUEST_TEMPLATE.md"])
    assert a["contributing"] and a["code_of_conduct"] and a["pull_request_template"]
    assert m["inherited_from_org"] == ["contributing", "code_of_conduct",
                                       "pull_request_template"]


def test_org_none_or_empty_means_no_inheritance():
    for org in (None, []):
        a, s, m = detect(["README.md"], org)
        assert not s["security_policy"] and m["inherited_from_org"] == []


def test_flags_are_computed_before_inheritance():
    # funding.yaml próprio + FUNDING.yml na org: pontua por herança, mas a
    # flag registra que o repositório só tem a variante .yaml
    a, _, m = detect([".github/FUNDING.yaml"], ["FUNDING.yml"])
    assert a["funding"] and a["funding_inherited"]
    assert m["flags"]["funding_yaml"] is True


# ---------------------------------------------------------------------- meta
def test_matched_paths_follow_location_precedence():
    m = meta(["docs/CONTRIBUTING.md", "CONTRIBUTING.md", ".github/CONTRIBUTING.md",
              "src/CONTRIBUTING.md"])
    assert m["matched"]["contributing"] == [
        ".github/contributing.md", "contributing.md", "docs/contributing.md"]
    assert matches(["b", "a"], D1_RULES["license"]) == []


def test_matched_paths_lists_every_ci_file():
    m = meta([".github/workflows/ci.yml", ".github/workflows/release.yml", ".travis.yml"])
    assert m["matched"]["ci_configured"] == [
        ".github/workflows/ci.yml", ".github/workflows/release.yml", ".travis.yml"]
    assert m["ci_systems"] == ["github_actions", "travis"]


def test_symlink_hits_reports_only_symlinks_that_match_a_rule():
    entries = [
        ("100644", "README.md"),                  # blob regular: não é symlink
        (SYMLINK_MODE, ".github/SECURITY.md"),    # symlink que casa D5
        (SYMLINK_MODE, "docs/CONTRIBUTING.md"),   # symlink que casa D1
        (SYMLINK_MODE, "src/link-to-license"),    # symlink fora das regras
        ("160000", "vendor/LICENSE"),             # submódulo (não é blob)
    ]
    assert symlink_hits(entries) == [".github/security.md", "docs/contributing.md"]
    assert symlink_hits([]) == []
    # symlinks continuam CONTANDO na detecção (são blobs); a função só relata
    blobs = [path for mode, path in entries if mode != "160000"]
    assert detect(blobs)[1]["security_policy"] is True


def test_joined_source_is_union_of_alternatives():
    src = joined_source(D1_RULES["funding"])
    assert src == r"^\.github/funding\.yml$"
    assert joined_source(D5_RULES["security_policy"]).startswith("^(\\.github/|docs/)?")
    assert joined_source(D1_RULES["license"]).count("|^") == 4


# ------------------------------------------------------- monorepo (kubernetes)
def test_kubernetes_like_monorepo_counts_only_root_artifacts():
    paths = [
        "README.md", "LICENSE", "CONTRIBUTING.md", "code-of-conduct.md",
        ".github/ISSUE_TEMPLATE/bug-report.yaml", ".github/PULL_REQUEST_TEMPLATE.md",
        "SECURITY.md", ".github/workflows/ci.yml",
        "vendor/github.com/x/y/LICENSE", "vendor/github.com/x/y/.circleci/config.yml",
        "staging/src/k8s.io/api/SECURITY.md", "staging/src/k8s.io/api/CODEOWNERS",
        "staging/src/k8s.io/api/.github/dependabot.yml",
    ]
    a, s, m = detect(paths)
    assert a["readme"] and a["license"] and a["contributing"] and a["code_of_conduct"]
    assert a["pull_request_template"] and s["security_policy"] and s["ci_configured"]
    assert not a["issue_template"] and m["flags"]["issue_template_yaml_only"]
    assert not a["codeowners"] and not s["dependency_automation"]
    assert m["ci_systems"] == ["github_actions"]
