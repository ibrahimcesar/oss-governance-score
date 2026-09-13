# Registro de decisão — catálogo v2: reparo da medição de D1/D5 na época do snapshot

**Data:** 2026-09-13 · **Status:** aceito (autor: reparo, não errata) · **Fase:**
pós-extração completa e pós-validação (catálogo congelado desde 2026-07-19;
esta decisão altera DETECÇÃO, não itens, limiares nem pesos) · **Commit das
regras:** tag `v2-regras-2026-09-13` (nada abaixo do protocolo roda antes
desse commit existir) · **Estado v1 arquivado:** tag `v1-catalogo-2026-07`.

## Contexto

A extração completa (23–24/07/2026, modo `both`) obteve D1 (artefatos) e D5
(segurança) pelo caminho de API de `extract/artifacts.py`: `community/profile`
para README/CONTRIBUTING/código de conduta/licença/templates, e sondagens
pontuais do endpoint `contents` para CODEOWNERS (só `.github/CODEOWNERS`),
GOVERNANCE (só `GOVERNANCE.md` na raiz), FUNDING, SECURITY (raiz, `.github/`,
`docs/`, com herança de `{owner}/.github` só na raiz do repositório especial),
CI (só listagem de `.github/workflows/`, qualquer conteúdo) e automação de
dependências (só `.github/dependabot.yml`). O backend git
(`extract/git_extractor.py`), com padrões mais amplos e herança
organizacional, não foi usado para D1/D5 no modo `both` (`cli.py`,
`extract_both`).

## Defeito (evidência anterior a qualquer re-pontuação)

- `issue_template` = True em 5/100. O campo `files.issue_template` do
  `community/profile` só reconhece o template legado de arquivo único
  (`.github/ISSUE_TEMPLATE.md`): nos 5 casos positivos é esse o arquivo;
  `nodejs/node` tem `issue_template: null` no perfil embora a árvore do
  snapshot contenha `.github/ISSUE_TEMPLATE/1-bug-report.yml` e outros três
  formulários. A documentação do GitHub fixa esse diretório como o local dos
  templates. 11 repositórios têm `health_percentage = 100` com
  `issue_template: null` — inconsistência interna do próprio perfil. O perfil
  é um cache do lado do GitHub (`updated_at` com idade mediana de 466 dias na
  sondagem; 46/100 com mais de um ano).
- `codeowners` = True em 24/100 e `governance` = True em 2/100, com sondagem
  em um único caminho, embora a documentação admita CODEOWNERS em `.github/`,
  raiz ou `docs/` (6 repositórios com CODEOWNERS na raiz não detectados).
- `security_policy`: verificação cruzada com o check *Security-Policy* do
  OpenSSF Scorecard (53 repositórios com varredura pública, mesma época)
  revela 3 falsos negativos em v1 — `rails/rails` (`.github/security.md`,
  minúsculas: o endpoint `contents` é sensível a caixa), `jekyll/jekyll`
  (`.github/SECURITY.markdown`) e `guzzle/guzzle` (herdado de
  `guzzle/.github/.github/SECURITY.md`, subpasta não sondada) — contra 0
  falsos positivos; concordância 48/53 (2 omissões do Scorecard:
  `statamic/cms`, `mavlink/qgroundcontrol`). `firefly-iii/firefly-iii`
  (`.github/security.md` e `.github/funding.yml`, minúsculas) é o 4º caso.
- `ci_configured` e `dependency_automation`: v1 ignora Travis, CircleCI,
  GitLab CI e demais provedores, e Renovate/Scala Steward — padrões que o
  próprio backend git v1 já cobria em parte.

O defeito é de MEDIÇÃO (detector mais estreito que a convenção documentada),
não de construto: itens, limiares (binários) e pesos permanecem os de
2026-07-19.

## Decisão

Re-medir os 9 itens binários de D1 e os 3 de D5 dos 100 repositórios sobre a
ÁRVORE DE ARQUIVOS DO BRANCH DEFAULT NO COMMIT DE ÉPOCA (instante da sondagem
v1), com as regras fixadas neste registro ANTES da re-pontuação, e re-executar
pontuação, sensibilidade, validação, robustez e figuras como **catálogo v2**.
As saídas v1 são arquivadas e comparadas item a item; nenhuma é sobrescrita em
silêncio. Escopo: **apenas D1/D5**. A janela fixa de D3 (limitação iii da
monografia) fica para um catálogo v3 com registro próprio, porque issues e
comentários são objetos mutáveis cuja época de julho não pode ser garantida.

## Proveniência (honesta)

Regras redigidas em 13/09/2026 a partir das documentações do GitHub, do
Licensee, do Renovate e do código do Scorecard, após a detecção do defeito em
`nodejs/node`. Três passagens de protótipo sobre a amostra, em cache separado
fora de `data/raw/`, com as regras fixadas às 10:57 (UTC−3) antes da
execução. Clarificações feitas entre passagens, cada uma com base documental:
(1) apenas blobs (semântica de `git ls-tree -r` do backend git v1; o
diretório `security/` da raiz de `torvalds/linux` não é uma política); (2)
formulários `.yaml` de issue NÃO pontuam (docs: `.yml`), registrados como
flag; (3) `config.yml` excluído (é configuração do seletor de templates); (4)
`FUNDING.yml` na raiz de `{owner}/.github` aceito por continuidade com
`FUNDING_PATHS` v1 e comportamento observado da plataforma (seção *Sponsor
this project* em godot/hugo/advanced-java em 13/09/2026), embora a
documentação cite só `.github/`. Os deltas de score e de ρ externos foram
vistos durante o protótipo (ρ v1×v2 ≈ 0,997; +2,4 pontos em média); nenhuma
regra foi escolhida por eles e nenhuma será alterada após este commit.
Ajuste posterior = catálogo v3 com novo registro.

## Época (por repositório)

- `cutoff_r` = instante da última sondagem v1 de D1/D5 do repositório: máximo
  de `fetched_at` entre os arquivos de cache `community_profile`,
  `codeowners`, `governance`, `funding_yml*`, `security_md*`, `workflows` e
  `dependabot` (fallback: `fetched_at` de `repo_metadata.json`). Todos
  ≤ 2026-07-24T23:59:59Z. O corte global foi rejeitado: devolve commits até
  25 h DEPOIS da sondagem (`nodejs/node`, `torvalds/linux`); 48/100 commits
  first-parent sob o corte global são posteriores à sondagem v1.
- Commit de época = primeiro commit da cadeia **first-parent** do branch
  default registrado em `repo_metadata.json` (v1; 5 branches fora de
  main/master: `4.x`, `13.x`, `6.x`, `dev`, `8.0`) com data de committer
  ≤ `cutoff_r`, obtido por clone parcial:
  `git clone --bare --single-branch --branch <branch> --filter=tree:0
  --shallow-since=<cutoff−60d>`; escada de aprofundamento se a cadeia não
  cruza o corte: `fetch --shallow-since=<cutoff−365d>` → `--depth 400` →
  `1600` → `6400`; seleção em Python sobre `git log --first-parent
  --format=%H%x09%ct` (não `rev-list --before`, que falhou em linux). REST
  `commits?until=` rejeitado como resolvedor (percorre o grafo completo:
  13/100 candidatos fora da cadeia first-parent; em `ydb-platform/ydb`
  devolve um commit de importação com 15 entradas na raiz) — mantido só como
  coluna de verificação cruzada.
- Verificação: todo blob positivo em v1 (respostas do `contents` para
  `codeowners`, `security_md*`, `governance`, `funding_yml*`, `workflows`,
  `dependabot`) deve existir com o mesmo `sha` na árvore de época; divergência
  ⇒ `epoch_status = "unverified"`, repositório mantido, D1/D5 de v1 com
  `v2_source = "v1_cache"`, contado no relatório. Repositório inacessível em
  setembro ou branch de época inexistente ⇒ idem (`"unreachable"`).
- Aproximação declarada: data de committer ≠ instante de push (limitada por
  `pushed_at`); defasagem `cutoff_r − committer` mediana de 13 h, 12
  repositórios > 7 dias por inatividade do branch (não é erro de época).
- `{owner}/.github` resolvido com o mesmo `cutoff_r` (branch default atual;
  35 existem, 4 vazios, 61 inexistentes); inexistente (404), vazio (409) ou
  sem commit ≤ corte ⇒ sem herança.
- Exceção única à regra "a análise nunca reconsulta a API/rede": os objetos
  v2 são obtidos em 09/2026, mas são IMUTÁVEIS e endereçados por SHA
  (commit e árvore do snapshot de julho). Chaves v1 não são reconsultadas nem
  sobrescritas; os objetos v2 vivem em `data/raw/<owner>__<repo>/v2/`
  (`epoch_commit.json`, `tree_paths_<sha12>.json`, `org_epoch_commit.json`,
  `org_tree_paths_<sha12>.json`), cada um com `fetched_at` e
  `catalog_version`. Nenhuma chamada REST/GraphQL é necessária para o passo
  central (só git); as opcionais usam prefixo `v2_`.

## Fonte de detecção

Lista de BLOBS (`git ls-tree -r`: arquivos, inclusive symlinks — contados e
relatados; diretórios e submódulos não) da árvore do commit de época;
caminhos comparados em minúsculas; padrões ANCORADOS à raiz (regra do piloto
contra caminhos vendorizados — mantida). Fonte única: o perfil comunitário
deixa de pontuar (a união com o perfil contribuiria 0 decisões e é uma
catraca unidirecional por construção); `health_percentage` é copiado de v1
como anotação.

Abreviaturas: `LOC = (\.github/|docs/)?` · `DOC = (\.(md|markdown|mdown|rst|txt|adoc|asciidoc))?`

## Regras v2 (verbatim; expressões sobre caminhos em minúsculas)

```
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
```

Herança de `{owner}/.github` (organizações E contas pessoais), só quando o
repositório não tem arquivo próprio do tipo, com `<item>_inherited = true`:
`contributing`, `code_of_conduct`, `issue_template` (só
`.github/issue_template/…` do repositório especial), `pull_request_template`,
`funding`, `security_policy`; arquivos do repositório especial em raiz,
`.github/` ou `docs/` (precedência `.github` > raiz > `docs`). **Nunca
herdam:** `readme`, `license`, `codeowners`, `governance` (não consta da
lista *Supported file types* consultada em 13/09/2026), `ci_configured`,
`dependency_automation`.

Registrados como flags, sem pontuar: `issue_template_yaml_only` (formulários
`.yaml`; 5 repositórios no protótipo), `issue_template_config_only`,
`funding_yaml`, `dependabot_yaml` (2 repositórios: `openai/codex`,
`openinterpreter/openinterpreter`), `symlink_hits`, `profile_updated_at`.

Fontes: GitHub Docs — *Creating a default community health file*; *About
READMEs*; *Setting guidelines for repository contributors*; *Adding a code of
conduct*; *About code owners*; *Configuring issue templates* e *Syntax for
issue forms*; *Creating a pull request template*; *About community profiles*;
*Displaying a sponsor button*; *Dependabot options reference*.
`licensee/lib/licensee/project_files/license_file.rb`.
`docs.renovatebot.com/configuration-options`. Scorecard
`checks/raw/{security_policy,dependency_update_tool}.go`. Páginas dos
provedores de CI (lista fechada).

Semânticas declaradas: `ci_configured` passa de "diretório
`.github/workflows` não vazio" para "≥ 1 arquivo de pipeline reconhecido";
templates contam sem validação de *frontmatter*; espelhos recebem crédito por
CI de outra forja (`.gitlab-ci.yml`). Invisíveis (declarados, sem regra *ad
hoc*): `renovate` em `package.json`, Renovate/Dependabot só por aplicativo ou
configuração do repositório, CI externa (KernelCI, LUCI, FATE, Prow central),
`OWNERS`, *private vulnerability reporting* (observável, mas sem época).

## O que NÃO muda

- `config/metrics.yaml`: itens, limiares e pesos — intactos.
- Amostra e arquétipos (classificados em 2026-07-20; 5 cruzamentos de
  faixa de stars entre amostragem e extração declarados; `penecho`
  renomeado) — intactos; nenhum repositório entra ou sai por artefatos.
- D2, D3, D4, stars, forks, `releases_12m`, `release_notes_share`,
  `health_percentage`: copiados de v1 sem re-extração. Correção de código
  sem efeito em v1: o corte da janela de releases passa a ser a constante do
  snapshot (`2026-07-24T23:59:59Z − 365 d`) em vez de `datetime.now()` —
  reproduz v1 em 100/100 e impede a deriva silenciosa de 26 repositórios em
  qualquer re-execução futura.
- Indicadores externos (Scorecard-53, deps.dev, stars/forks): cache de julho;
  `external_fetched_at` do relatório v2 é o de v1.

## Protocolo (sequência ex ante)

1. Commit deste registro (`v2-regras-2026-09-13`) com `make test` verde; tag
   `v1-catalogo-2026-07` no último commit com as saídas v1.
2. Arquivar v1 por cópia: `data/processed/v1/`, `results/v1/`, `figures/v1/`
   + `SHA256SUMS`.
3. `govscore epoch` → commit e árvore de época por repositório e por
   `{owner}/.github` (git apenas).
4. `govscore rescore --catalogue v2` → substitui APENAS os 12 binários (e
   `*_inherited`); tudo o mais verbatim de v1; campos `catalog_version`,
   `epoch_sha`, `epoch_cutoff`, `epoch_status`, `remeasured_at`,
   `v1_artifacts`, `v1_security`; pontuação com o catálogo congelado.
5. `govscore compare` → `results/reparo_v1_v2.md`: ρ de Spearman v1×v2
   (score, D1, D5); trocas por item × arquétipo nas DUAS direções; herdados;
   médias/medianas/DP/quartis por arquétipo; maiores deslocamentos; tabela
   de época (status, divergências first-parent × `until`, não verificados);
   cross-checks descritivos (Scorecard *Security-Policy* 48/53 → v2; *License*
   53/53; asserção `health = 100 ⇒ issue_template`); sensibilidades das flags
   não pontuadas. Toda troca True→False é listada nominalmente.
6. Re-executar `validate` (cache; variantes discriminantes *sem D5* e *sem
   D1+D5*, com a sobreposição parcial das regras de D5 com os checks
   *Security-Policy*/*Dependency-Update-Tool* declarada), `sensitivity`,
   `robustness` (cenários adicionais abaixo), `figures`.
7. Texto: monografia (cap. 3 e 4), README, `CLAUDE.md`, kit de defesa,
   `ESTADO_DO_ESTUDO.md`; `docs/rascunho_secoes_4.2_4.3.md` marcado como
   superado.

## Instrumentos complementares (pré-registrados como DESCRITIVOS; nunca árbitros de regra)

- Declarações de QA: censura de releases (`per_page = 30`: 25 repositórios
  saturados; `releases_12m` ≥ 30 é piso; `release_notes_share` sobre as 30
  mais recentes; 14,3 % de *prereleases* na janela); `retention_reason ∈
  {young_repo, first_half_empty, observed}` (9 repositórios criados após
  2026-01-24); `ci_configured = False` significa "sem configuração de CI no
  repositório" (14 repositórios listados); par quase-duplicado
  `openinterpreter/openinterpreter ⊃ openai/codex` (histórico) — mantidos, com
  cenário `sem_openinterpreter` na robustez.
- Locus de coordenação: `govscore locus-evidence` a partir das mensagens de
  commit em cache (Gerrit `Reviewed-on`, Phabricator `Differential Revision`,
  Piper `PiperOrigin-RevId`, `has_issues = false`, espelho declarado) →
  tabela de evidência e cenário `sem_locus_externo` na robustez (`git`,
  `gitlabhq`, `golang/go`, `react-native`, `tensorflow` + espelhos v1).
  **Não** altera scores: uma regra de D3 estrutural para espelhos reverteria
  a decisão "mantido" de 12/09/2026 sobre a mesma evidência e teria escopo
  desenhado a partir de merges observados.
- OpenSSF Scorecard CLI (v5.5.0, `brew`) nos 100 repositórios em HEAD de
  09/2026, 18 checks: família de validação SECUNDÁRIA com época declarada
  (~7 semanas após o snapshot; *Maintained*, *Vulnerabilities*,
  *Signed-Releases* e *Branch-Protection* não são retrodatáveis); a API-53 de
  julho permanece o critério primário. Relatar concordância CLI×API nos 53
  restrita aos 13 checks comuns e o ganho de poder intra-arquétipo (Brinquedo
  n = 5 → 25). Verificação de consistência `compare/{scorecard_commit}...
  {epoch_sha}` nos 56 resultados em cache.
- Catálogo v3 (D3 em janela fixa, exclusão de bots em D2/D4, `.mailmap`):
  registros próprios, depois deste.
