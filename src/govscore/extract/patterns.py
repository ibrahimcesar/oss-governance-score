"""Regras v2 de detecção de D1 (artefatos de governança) e D5 (práticas de
segurança) sobre a lista de caminhos de uma árvore git.

Fonte ÚNICA de verdade para os dois usos — backend git (`git_extractor.py`) e
re-pontuação sobre a árvore do commit de época (`rescore.py`) — fixada pela
decisão de 2026-09-13 (`docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md`).
As expressões abaixo são a transcrição VERBATIM da seção "Regras v2" desse
registro, redigidas ANTES da re-pontuação; nenhuma pode ser ajustada sem novo
registro de decisão (catálogo v3).

Semântica comum a todas as regras:

- entrada = caminhos de BLOBS (`git ls-tree -r`: arquivos e symlinks; nunca
  diretórios nem submódulos), comparados em MINÚSCULAS (ver `normalize`);
- padrões ANCORADOS à raiz do repositório — regra do piloto contra caminhos
  vendorizados (`vendor/**`, `staging/**` em kubernetes/kubernetes), mantida;
- ``LOC = (\\.github/|docs/)?`` — os três locais documentados pelo GitHub para
  arquivos de comunidade (`.github/`, raiz, `docs/`);
- ``DOC = (\\.(md|markdown|mdown|rst|txt|adoc|asciidoc))?`` — extensões de
  documentação aceitas, opcionais (arquivo sem extensão também conta).

Herança de `{owner}/.github` (*default community health files*, válida para
organizações E contas pessoais): apenas os itens em `INHERITABLE`, apenas
quando o repositório não tem arquivo próprio do tipo, sinalizada por
`<item>_inherited = True`. README, LICENSE, CODEOWNERS, GOVERNANCE, CI e
automação de dependências NUNCA herdam (GOVERNANCE não consta da lista
*Supported file types* do GitHub consultada em 13/09/2026).

Variantes NÃO pontuadas (registradas como flags em `meta["flags"]`, para as
análises de sensibilidade do relatório de reparo): formulários de issue em
`.yaml` (a documentação fixa `.yml`), diretório de templates contendo apenas
`config.yml` (configuração do seletor, não é template), `FUNDING.yaml` e
`dependabot.yaml`.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterable

__all__ = [
    "SNAPSHOT_UTC", "LOC", "DOC", "D1_RULES", "D5_RULES", "ORG_RULES",
    "INHERITABLE", "FLAG_RULES", "CI_SYSTEMS", "DEP_TOOLS", "D1_ITEMS",
    "D5_ITEMS", "normalize", "matches", "joined_source", "detect",
]

# Instante do snapshot da extração completa (fim do último dia da janela
# 2026-07-23→24, UTC). Ancora a janela de releases (D5) e o corte máximo de
# época por repositório; substitui `datetime.now()` para impedir deriva
# silenciosa em re-execuções.
SNAPSHOT_UTC = datetime(2026, 7, 24, 23, 59, 59, tzinfo=timezone.utc)

# Abreviaturas do registro de decisão (expandidas textualmente nas regras).
LOC = r"(\.github/|docs/)?"
DOC = r"(\.(md|markdown|mdown|rst|txt|adoc|asciidoc))?"


def _rx(*sources: str) -> list[re.Pattern]:
    """Compila cada alternativa separadamente (as fontes ficam legíveis e
    reexportáveis como texto; os caminhos já chegam em minúsculas, portanto
    sem IGNORECASE — a comparação é literalmente a do registro)."""
    return [re.compile(s) for s in sources]


# ----------------------------------------------------------------- D5: CI
# Lista FECHADA de provedores (páginas dos provedores, 13/09/2026). A união
# destas expressões é a regra `ci_configured`; os nomes alimentam
# `meta["ci_systems"]` para descrição (nunca para pontuar).
CI_SYSTEMS: dict[str, re.Pattern] = {
    "github_actions": re.compile(r"^\.github/workflows/[^/]+\.ya?ml$"),
    "travis": re.compile(r"^\.travis\.ya?ml$"),
    "circleci": re.compile(r"^\.circleci/config\.ya?ml$"),
    "jenkins": re.compile(r"^jenkinsfile$|^\.jenkins/.+"),
    "azure_pipelines": re.compile(
        r"^azure-pipelines([-.][a-z0-9-]+)?\.ya?ml$|^\.azure-pipelines/.+\.ya?ml$"),
    "gitlab_ci": re.compile(r"^\.gitlab-ci\.ya?ml$|^\.gitlab/ci/.+"),
    "drone": re.compile(r"^\.drone\.ya?ml$"),
    "buildkite": re.compile(r"^\.buildkite/[^/]+\.ya?ml$"),
    "appveyor": re.compile(r"^\.?appveyor\.ya?ml$"),
    "cloudbuild": re.compile(r"^cloudbuild\.ya?ml$"),
    "cirrus": re.compile(r"^\.cirrus\.ya?ml$"),
    "semaphore": re.compile(r"^\.semaphore/[^/]+\.ya?ml$"),
    "bitbucket_pipelines": re.compile(r"^bitbucket-pipelines\.ya?ml$"),
    "woodpecker": re.compile(r"^\.woodpecker\.ya?ml$|^\.woodpecker/[^/]+\.ya?ml$"),
    "prow": re.compile(r"^\.prow\.ya?ml$|^\.prow/.+"),
    "zuul": re.compile(r"^\.zuul\.ya?ml$|^zuul\.d/.+"),
    "tekton": re.compile(r"^\.tekton/[^/]+\.ya?ml$"),
    "forgejo_gitea_actions": re.compile(r"^\.(forgejo|gitea)/workflows/[^/]+\.ya?ml$"),
}

# ------------------------------------------- D5: automação de dependências
# Scorecard `checks/raw/dependency_update_tool.go`; docs do Renovate.
# Dependabot só em `.github/dependabot.yml` (docs: extensão `.yml`); a variante
# `.yaml` é registrada como flag `dependabot_yaml`, sem pontuar.
DEP_TOOLS: dict[str, re.Pattern] = {
    "dependabot": re.compile(r"^\.github/dependabot\.yml$"),
    "renovate": re.compile(
        r"^(\.github/|\.gitlab/)?renovate\.json[5c]?$|^\.renovaterc(\.json[5c]?)?$"),
    "scala_steward": re.compile(r"^(\.github/|\.config/)?\.?scala-steward\.conf$"),
    "pyup": re.compile(r"^\.pyup\.ya?ml$"),
}

# ------------------------------------------------------------ D1: artefatos
D1_RULES: dict[str, list[re.Pattern]] = {
    "readme": _rx(rf"^{LOC}readme{DOC}$"),
    "contributing": _rx(rf"^{LOC}contributing{DOC}$"),
    "code_of_conduct": _rx(rf"^{LOC}code[-_]of[-_]conduct{DOC}$"),
    # Licença: SÓ RAIZ, família de nomes do Licensee
    # (`lib/licensee/project_files/license_file.rb`), excluindo metadados
    # `*.json` (ex.: license-metadata.json).
    "license": _rx(
        r"^((un)?licen[sc]e|copying|copyright)(\.(md|txt|rst|markdown))?$",
        r"^((un)?licen[sc]e|copying|copyright)[-_.](?!.*\.json[5c]?$)[a-z0-9.+_-]+$",
        r"^[a-z0-9]+[-_](un)?licen[sc]e(\.[a-z]+)?$",
        r"^patents$",
        r"^ofl\.md$",
    ),
    # Template legado de arquivo único OU diretório documentado
    # `.github/ISSUE_TEMPLATE/` com `*.md` (template) / `*.yml` (issue form);
    # `config.yml` é o seletor, não um template.
    "issue_template": _rx(
        rf"^{LOC}issue_template{DOC}$",
        r"^\.github/issue_template/(?!config\.ya?ml$)[^/]+\.(md|yml)$",
    ),
    # Arquivo único (com ou sem extensão — golang/go usa
    # `.github/PULL_REQUEST_TEMPLATE`) OU múltiplos em `PULL_REQUEST_TEMPLATE/`.
    "pull_request_template": _rx(
        rf"^{LOC}pull_request_template{DOC}$",
        rf"^{LOC}pull_request_template/[^/]+\.(md|txt)$",
    ),
    "codeowners": _rx(rf"^{LOC}codeowners$"),
    "governance": _rx(rf"^{LOC}governance{DOC}$"),
    # Repositório: só `.github/FUNDING.yml` (docs: *Displaying a sponsor
    # button*). `FUNDING.yaml` → flag `funding_yaml`.
    "funding": _rx(r"^\.github/funding\.yml$"),
}

# ------------------------------------------------------------ D5: segurança
D5_RULES: dict[str, list[re.Pattern]] = {
    "security_policy": _rx(rf"^{LOC}security\.(md|markdown|adoc|rst)$"),
    "ci_configured": list(CI_SYSTEMS.values()),
    "dependency_automation": list(DEP_TOOLS.values()),
}

D1_ITEMS: tuple[str, ...] = tuple(D1_RULES)
D5_ITEMS: tuple[str, ...] = tuple(D5_RULES)

# ------------------------------------------------- herança de {owner}/.github
INHERITABLE: tuple[str, ...] = (
    "contributing", "code_of_conduct", "issue_template",
    "pull_request_template", "funding", "security_policy",
)

# Regras aplicadas à árvore do repositório especial `{owner}/.github`. Iguais
# às do repositório, exceto: templates de issue só no diretório documentado
# (`.github/ISSUE_TEMPLATE/` do repositório especial — o arquivo legado
# `issue_template.md` não é um default community health file) e FUNDING.yml
# aceito também na RAIZ do repositório especial (continuidade com
# `FUNDING_PATHS` v1 e comportamento observado da plataforma em 13/09/2026).
ORG_RULES: dict[str, list[re.Pattern]] = {
    "contributing": D1_RULES["contributing"],
    "code_of_conduct": D1_RULES["code_of_conduct"],
    "issue_template": _rx(
        r"^\.github/issue_template/(?!config\.ya?ml$)[^/]+\.(md|yml)$"),
    "pull_request_template": D1_RULES["pull_request_template"],
    "funding": _rx(r"^(\.github/)?funding\.yml$"),
    "security_policy": D5_RULES["security_policy"],
}

# --------------------------------------------------- flags (não pontuadas)
# Cada flag é True apenas quando o item correspondente NÃO tem arquivo próprio
# que pontue e a variante existe — mede "quantos repositórios trocariam de
# valor se a variante fosse aceita" (sensibilidade descritiva do relatório).
FLAG_RULES: dict[str, list[re.Pattern]] = {
    "issue_template_yaml_only": _rx(
        r"^\.github/issue_template/(?!config\.ya?ml$)[^/]+\.yaml$"),
    "issue_template_config_only": _rx(r"^\.github/issue_template/config\.ya?ml$"),
    "funding_yaml": _rx(r"^\.github/funding\.yaml$"),
    "dependabot_yaml": _rx(r"^\.github/dependabot\.yaml$"),
}
_FLAG_ITEM = {
    "issue_template_yaml_only": "issue_template",
    "issue_template_config_only": "issue_template",
    "funding_yaml": "funding",
    "dependabot_yaml": "dependency_automation",
}


# ------------------------------------------------------------------ helpers
def normalize(paths: Iterable[str]) -> list[str]:
    """Caminhos em minúsculas, sem o prefixo `./`; nada mais é alterado.

    As regras são escritas sobre caminhos minúsculos (o endpoint `contents`
    da API v1 era sensível a caixa — `rails/rails` tem `.github/security.md`);
    a árvore git preserva a caixa, por isso a normalização é feita aqui.
    """
    out: list[str] = []
    for p in paths:
        p = p.lower()
        while p.startswith("./"):
            p = p[2:]
        out.append(p)
    return out


def _loc_rank(path: str) -> int:
    """Precedência documentada dos locais: `.github/` > raiz > `docs/`."""
    if path.startswith(".github/"):
        return 0
    if "/" not in path:
        return 1
    if path.startswith("docs/"):
        return 2
    return 3


def matches(paths: Iterable[str], rules: Iterable[re.Pattern]) -> list[str]:
    """Caminhos (já normalizados) casados por qualquer das regras, ordenados
    pela precedência de local e depois alfabeticamente — o primeiro elemento
    é o arquivo que a plataforma usaria."""
    rules = list(rules)
    hits = {p for p in paths if any(rx.search(p) for rx in rules)}
    return sorted(hits, key=lambda p: (_loc_rank(p), p))


def joined_source(rules: Iterable[re.Pattern]) -> str:
    """União textual das alternativas (`a|b|c`) — compatibilidade com a
    representação v1 `dict[str, str]` de `git_extractor.ARTIFACT_PATTERNS`."""
    return "|".join(rx.pattern for rx in rules)


def detect(paths: Iterable[str],
           org_paths: Iterable[str] | None = None) -> tuple[dict, dict, dict]:
    """Aplica as regras v2 a uma árvore (e, opcionalmente, à do `{owner}/.github`).

    Retorna `(artifacts, security, meta)`:

    - `artifacts`: os 9 itens de D1 como bool + `<item>_inherited = True`
      apenas quando o valor veio do repositório especial (chave ausente nos
      demais casos);
    - `security`: os 3 itens binários de D5 (`security_policy`,
      `ci_configured`, `dependency_automation`) + `security_policy_inherited`;
    - `meta`: `matched` (caminhos PRÓPRIOS casados por item, sempre com as 12
      chaves), `org_matched` (caminhos do repositório especial, só para os
      itens herdados), `flags` (variantes não pontuadas, calculadas sobre os
      arquivos próprios, antes da herança), `ci_systems` e `dependency_tools`
      (nomes reconhecidos, para descrição) e `inherited_from_org`.

    Herança: só itens em `INHERITABLE`, só quando o repositório não tem
    arquivo próprio do tipo; `org_paths=None` ou vazio (repositório especial
    inexistente, vazio ou sem commit ≤ corte) ⇒ sem herança.
    """
    own = normalize(paths)
    matched = {item: matches(own, rules) for item, rules in D1_RULES.items()}
    matched.update({item: matches(own, rules) for item, rules in D5_RULES.items()})

    artifacts: dict = {item: bool(matched[item]) for item in D1_ITEMS}
    security: dict = {item: bool(matched[item]) for item in D5_ITEMS}

    flags = {
        flag: (not matched[_FLAG_ITEM[flag]]) and bool(matches(own, rules))
        for flag, rules in FLAG_RULES.items()
    }
    ci_systems = [name for name, rx in CI_SYSTEMS.items()
                  if any(rx.search(p) for p in own)]
    dependency_tools = [name for name, rx in DEP_TOOLS.items()
                        if any(rx.search(p) for p in own)]

    inherited: list[str] = []
    org_matched: dict[str, list[str]] = {}
    org = normalize(org_paths) if org_paths is not None else []
    if org:
        for item in INHERITABLE:
            if matched[item]:
                continue  # arquivo próprio tem precedência sobre o default
            hits = matches(org, ORG_RULES[item])
            if not hits:
                continue
            target = artifacts if item in artifacts else security
            target[item] = True
            target[f"{item}_inherited"] = True
            inherited.append(item)
            org_matched[item] = hits

    meta = {
        "matched": matched,
        "org_matched": org_matched,
        "flags": flags,
        "ci_systems": ci_systems,
        "dependency_tools": dependency_tools,
        "inherited_from_org": inherited,
    }
    return artifacts, security, meta
