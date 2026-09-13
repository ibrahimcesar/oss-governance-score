# Catalogue-v2 repair pass — implementation plan

## 1. Menu

Epoch legend: **E-repo** = per-repo cutoff (v1 `repo_metadata.json` `fetched_at`, all within 2026-07-23T22:18Z–07-24T12:15Z, hence ≤ the global 2026-07-24T23:59:59Z bound); **July-cache** = no new data; **now** = September state, declared.

### Tier 1 — must (the defect and its siblings)

| id | what changes (as fixed by verdicts) | kind | epoch | affected | API | runtime | prio |
|---|---|---|---|---|---|---|---|
| T1.1 epoch-first-parent | Epoch sha = first commit on the **first-parent** chain of the v1 default branch with `%ct` ≤ cutoff, via `git clone --bare --single-branch --branch <v1 default_branch> --filter=tree:0 --shallow-since=cutoff−60d`; ladder: retry once → `fetch --shallow-since=cutoff−365d` → `--depth 400/1600/6400`. REST `commits?until=` demoted to cross-check column (13/100 divergent, ydb/nccl D1-affecting). Verification: every v1-positive contents probe (codeowners/security_md/governance/funding/workflows/dependabot) must exist at the epoch tree with the same blob sha; else `epoch_unverified` → repo kept, D1/D5 carried from v1, counted. | measurement-fix | E-repo | resolver 100/100; 0 unverified expected | 0 | ~5 min, 280 MB | must |
| T1.2 tree-listing | `git ls-tree -r --name-only <sha>` on the same treeless clone (≤1 s even linux/ydb; no Trees-API truncation). Blobs only (dirs/submodules excluded; symlinks count, declared). Same for `{owner}/.github` at its own epoch sha (404/409/empty → no inheritance). Cached under `data/raw/<owner>__<repo>/v2/`. | measurement-fix | E-repo | 100 + ~35 org | 0 | ~2 min | must |
| T1.3 D1 rules v2 | Regexes over lowercased blob paths (verbatim in §4): documented locations; Licensee licence family (no `*.json`); `ISSUE_TEMPLATE/*.{md,yml,yaml}` excl. `config.y(a)ml`; PR-template dirs; GitHub inheritance list only; single locus (tree) for all 9 items — profile union dropped, reported as "0 decisions". | v2-rule | E-repo | issue_template 5→62–67, codeowners 24→30, PR-tpl +1, funding +1; 0 T→F expected | 0 | s | must |
| T1.4 D5 rules v2 | `security_policy` md/markdown/adoc/rst in root/.github/docs + org inheritance; `ci_configured` closed vendor list; `dependency_automation` Dependabot `.yml` + Renovate documented locations + Scala Steward/PyUp. No `.txt`, no `doc/`, `dependabot.yaml` pending author (§6). Fix git-backend `security(\.[a-z]+)?` bug. | v2-rule | E-repo | security +4, ci +2, dep-auto +7 (+2 if .yaml) | 0 | s | must |
| T1.5 shared patterns | `extract/patterns.py` single source for both backends; `detect(paths, org_paths)`; v1 names re-exported. | measurement-fix | n/a | 0 extra | 0 | 1–2 h dev | must |
| T1.6 release anchor | `SNAPSHOT_UTC=2026-07-24T23:59:59Z` constant replaces `datetime.now()` in `extract_security`; fetched_at consistency assert; v2 copies releases from v1 verbatim. | measurement-fix | July-cache | 0 (prevents 26-repo drift) | 0 | <1 s | must |
| T1.7 rescore + compare | `govscore rescore --catalogue v2` (merge over v1 records: replace 12 binaries only; D2/D3/D4/stars/releases verbatim) and `govscore compare`; `--data-dir/--results-dir` on validate/sensitivity/robustness/figures; validate offline with v1 `external_fetched_at`. | qa | July-cache | all outputs | 0 | ~10 min | must |
| T1.8 archive + drift declarations | Copy `data/processed/*`, `results/*.{md,json}`, `figures/*` to `v1/` + `git tag v1-catalogo-2026-07`; declare stars/archetype drift (labels frozen at 2026-07-20), guzzle branch, has_issues=False ×5, profile `updated_at` as *stability* not staleness; drop unverifiable "git offsets ≤1 day". | qa | July-cache | — | 0 | min | must |
| T1.9 validation battery | Descriptive, no targets: Scorecard Security-Policy cross-tab (baseline **48/53**, ceiling 51/53), License 53/53, health=100 ⇒ issue_template assertion, first-parent vs `until` divergences, circularity caveat (D5 rules overlap Scorecard checks). | validation-instrument | July-cache | 53/100 | 0 (+53 optional compare API) | min | must |
| T1.10 thesis/docs | Last step; written from official `results/` only; v1→v2 subsection, corrected exception sentence (§5). | qa | — | ~45 numeric spots | 0 | 2–3 h | must |

### Tier 2 — recommended in the same pass

| id | what | kind | epoch | affected | API | runtime | prio |
|---|---|---|---|---|---|---|---|
| T2.1 releases censoring/prerelease declaration | `releases_fetched`, `prereleases_12m`, `releases_nonmonotone` annotation fields; QA section; "≥30" in per-repo tables; 29 partial-page repos verified safe | qa | July-cache | 25 censored, 7 prerelease-sensitive | 0 | 1–2 h | rec |
| T2.2 undetectable declarations | ci_configured=False = "no in-repo CI config" (16 v1 / 14 v2 listed); App-only Renovate, Dependabot security updates, private vulnerability reporting (observable but no epoch → excluded by rule) | qa | — | declaration | 0 | 30 min | rec |
| T2.3 retention reason column | `retention_reason ∈ {young_repo, first_half_empty, observed}` from cached `created_at` (9 young = 6 toy/2 club/1 stadium; 3 first-half-empty) | qa | July-cache | 12 | 0 | min | rec |
| T2.4 D3 cache-only robustness | scenarios bots-only / window-only / both on `pulls_closed.json` (min-n flagged); pr_review_coverage stays unfiltered (declared) | validation-instrument | July-cache | 12–20 repos | 0 | min | rec |
| T2.5 locus evidence table | `govscore locus-evidence` from cached commits (8 repos by mechanical rule; mall/rufus = genuine zero, internal); `sem_locus_externo` robustness scenario (uniform: git, gitlabhq, golang, react-native, tensorflow) next to `sem_espelhos_v1` | qa | July-cache | 8 | 0 | 2–3 h | rec |
| T2.6 near-duplicate note | openinterpreter ⊃ codex history: keep both, systematic root-tree-sha check over 100, `sem_openinterpreter` scenario | qa | July-cache | 1 pair | 0 | min | rec |
| T2.7 Scorecard sha consistency | `compare/{scorecard_commit}...{epoch_sha}` for 56 cached; consistency only (expect 0 diverged) | validation-instrument | July-cache | 56 | 56 | 1 min | rec |

### Tier 3 — optional / separately decided

| id | what | kind | epoch | API | runtime |
|---|---|---|---|---|---|
| T3.1 D3 v2 fixed cohort (own record, likely v3) | search-stratified enumeration W=[2025-07-24,2026-07-24], systematic N=300, first-response v1 rule (omit), review coverage human/non-author/≤mergedAt (CHAOSS only), bot lists L_AUTO/L_HUMAN frozen, client partial-payload guard, renamed-repo resolution, search-completeness QA; censoring and close-as-response only as diagnostics | v2-rule | createdAt-cohort, now-index | ~4,800–7,000 GraphQL pts | ~2 h + 1 day dev |
| T3.2 D2/D4 bot exclusion + mailmap (own record) | documented suffix rule only, `%an/%ae`, tolerance-based reproducibility (|Δn| ≤ 1%), mailmap on person metrics only; needs epoch-anchored re-clone | v2-rule | E-repo | 0 | ~30 min + ½ day |
| T3.3 EF generic-share column | only with T3.2 (v1 has no per-email data) | qa | E-repo | 0 | — |
| T3.4 Scorecard CLI (HEAD ×1 + `--commit` 7 checks), non-overlap aggregate, secondary family | validation-instrument | now / E-repo | ~1–3k GraphQL | 1–3 h |
| T3.5 Scorecard-at-epoch Security-Policy (brew v5.5.0, `--commit`) | validation-instrument | E-repo | <500 | ~1 h |
| T3.6 GraphQL platform crosscheck, report-only after freeze | validation-instrument | now | 135 GraphQL | ½ day |
| T3.7 package.json `renovate` key probe — only if fixed ex ante for every repo with root package.json | v2-rule | E-repo (`?ref=`) | ≤100 | 1 h |
| T3.8 releases pagination with v1-union merge (prune-safe) | measurement-fix | E-repo | ~200 | 2–3 h |

### Rejected (decisive refutation)
- **REST `commits?until=` as epoch resolver** — full-DAG committer-date walk; 13/100 off first-parent, ydb tree with 15 entries.
- **Trees API `recursive=1` at root** — truncates 6/100 (linux 71,798 entries, root entries omitted).
- **`.txt`/`doc/` for security_policy** — unsourced widenings made with trees in hand.
- **PROFILE_UNION** — contributes 0 decisions; one-directional ratchet by construction.
- **Excluding openinterpreter** — post-hoc sample filter; scores already known.
- **b1 locus rule in headline D3** — reverses the 2026-09-12 "mantido" decision on identical evidence; scope drawn by observed merges.
- **d3-first-response-censoring as scored rule** — equivalent to a 50 % cliff; 78 % of "unanswered" nodejs issues were closed/triaged.
- **d3-window via `sort:updated` search** — sample composition not reproducible today.
- **GraphQL crosscheck "to settle" .yaml/config.yml** — rule arbiter on named repos.
- **Two-pass Scorecard CLI + per-archetype rescue** — api13 derivable offline; forking paths.
- **"Written before any counting" claim** — contradicted by scratchpad mtimes; replaced by an honest revision log.
- **Bare `endswith('bot')` extension / word-boundary regex** — Zabot-type false positives; gopherbot-type misses.

## 2. Protocol (ex-ante sequence)

**(a)** Write `docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md` (§4) with verbatim rules, revision log and open decisions resolved; `make test`; commit; `git tag v1-catalogo-2026-07`. Nothing below runs before this commit hash exists.

**(b)** Archive by copy (not move; canonical paths keep v2 so `.tex` references resolve): `data/processed/{full_metrics.json,metrics.parquet,scores.csv,external_indicators.csv,full_metrics_progress.jsonl}` → `data/processed/v1/`; `results/{qa_extracao,sensibilidade,validacao,robustez,tabelas_tcc}.md` + `{validation,sensitivity,robustness}.json` → `results/v1/` (robustez marked 2026-09-12); `figures/*` → `figures/v1/`; write `SHA256SUMS`. Add `.gitignore` entry for the archived jsonl.

**(c)** `govscore epoch --catalogue v2`: per repo read `default_branch`, `fetched_at`, `pushed_at` from `data/raw/<r>/repo_metadata.json`; cutoff = `fetched_at` (open decision 1); resolver ladder T1.1; write `data/raw/<r>/v2/epoch_commit.json` `{sha, committer_ts, cutoff, cutoff_source, resolver_step, until_candidate_sha (optional), verification: {probe: {v1_sha, epoch_sha, ok}}, status}`. `GIT_TERMINAL_PROMPT=0 -c gc.auto=0`, timeout 1800 s, clone deleted after (d).

**(d)** Same clone: `ls-tree -r --name-only sha` → `v2/tree_paths_<sha12>.json` (blobs, original case, mode). `{owner}/.github`: clone with same cutoff → `v2/org_epoch_commit.json`, `v2/org_tree_paths_<sha12>.json`; absent/empty/no commit ≤ cutoff → `null`.

**(e)** `govscore rescore --catalogue v2 --in data/processed/v1/full_metrics.json --out data/processed/`: per record, `detect()` over paths + org paths; replace `artifacts.{9 items,+_inherited}` and `security.{security_policy,ci_configured,dependency_automation}` (+`*_path`, `ci_systems`, `dependency_tools`, `security_policy_inherited`); keep everything else verbatim (incl. `extracted_at`); add `catalog_version="v2"`, `epoch_sha`, `epoch_cutoff`, `epoch_status`, `remeasured_at`, `v1_artifacts`, `v1_security`. `epoch_unverified`/unreachable → v1 flags carried, `v2_source="v1_cache"`.

**(f)** `compute_subscores/compute_score` with unchanged `config/metrics.yaml`; `write_outputs`; `qa_report` line "catálogo: v2".

**(g)** `govscore compare --v1 data/processed/v1 --v2 data/processed` → `results/reparo_v1_v2.md/.json`: per item × archetype F→T / T→F (nominal) / inherited; per-repo flips; D1, D5, score means/medians/SD/quartiles by archetype; Spearman v1~v2 (score, D1, D5), max |Δrank|, repos moving ≥5; epoch table (status counts, first-parent vs `until` divergences, unverified list); Scorecard Security-Policy 48/53 baseline vs v2, License 53/53, health=100 assertion; symlink hits; issue_template sensitivities (yml-only, config-only, yaml); dependabot.yaml note; declared-flip attribution (API-path defect / inheritance / rule extension).

**(h)** With `--data-dir data/processed --results-dir results` and a no-network guard: `validate` (external_fetched_at carried from `results/v1/validation.json`; add discriminant variants *sem D5* and *sem D1+D5* with the circularity caveat) → `sensitivity` → `robustness` (adds T2.4–T2.6 scenarios) → `figures`.

**(i)** Thesis/docs (§5 sentences): `cap3_metodo.tex` L131-141, L137-139, L173-179; `cap4_secoes_4.2_4.3.tex` L1, L22-31, L37, L50-65, L57-60, L113-122, L152, L162-177, L196-199, L215-220, L235-244, L256-268, L304-321, L323-336, L365-385, L397-440, L444-449, L472-481, L481, L483-540 (new limitations); `cap5_conclusao.tex` L25-26, L34-35, L76; `main.tex` L105/L108; `README.md` L48-78; `CLAUDE.md`; `docs/kit_defesa.md` L15, L18, L25-26, L36, L66-67, L172, L200; `docs/exploracao_2026-09-13/README.md` L25-27/L38; `docs/rascunho_secoes_4.2_4.3.md` marked superseded. `docs/decisions/2026-09-12-*` untouched except an appended T2.6 note.

**Budget.** Core pass: 0 REST/GraphQL (git only, ~200 clones, 254 s + org ~2 min, 280 MB). Optional: 100 REST (`until` cross-check), 56 REST (compare), 0 for validate (cache). Tier 3 D3 would add ~5–7k GraphQL points. Wall-clock Tier 1+2: ~15 min machine, ~1 day implementation, 2–3 h writing.

## 3. Code plan

**New `src/govscore/extract/epoch.py`**
```python
SNAPSHOT_UTC = datetime(2026, 7, 24, 23, 59, 59, tzinfo=timezone.utc)
def select_first_parent(chain: list[tuple[str, int]], cutoff_ts: int) -> tuple[str, int] | None
def resolve_epoch(repo: str, branch: str, cutoff: datetime, workdir: Path) -> EpochResult  # ladder, retry, timeouts
def list_tree(clone: Path, sha: str) -> list[TreeEntry]  # ls-tree -r, blobs only (mode, sha, path)
def verify_against_v1(gh_cache: Path, tree: list[TreeEntry]) -> dict[str, dict]  # blob sha per v1-positive probe
def resolve_org(owner: str, cutoff: datetime, workdir: Path) -> EpochResult | None
```
**New `src/govscore/extract/patterns.py`**: `D1_RULES`, `D5_RULES` (compiled, verbatim from §4), `INHERITABLE`, `detect(paths: Iterable[str], org_paths: Iterable[str] | None) -> tuple[dict, dict, dict]` (artifacts, security, meta with matched paths). `git_extractor.py` imports and re-exports `ARTIFACT_PATTERNS/SECURITY_PATTERNS/_present`.

**`extract/artifacts.py`**: `extract_security(gh, repo, snapshot=SNAPSHOT_UTC)`; `GitHubClient.fetched_at(repo, key)` helper; `extract_artifacts_from_tree()` / `extract_security_from_tree()`; `extract_repo(..., snapshot)` threads the constant through all call sites (cli.py 36/52/180/185).

**New `src/govscore/rescore.py`**: `rescore_v2(v1_records, cache_root, cfg) -> list[dict]`; **`src/govscore/compare.py`**: `compare_records(v1, v2, sample) -> dict`, `report(res) -> str` (PT-BR). **`src/govscore/qa/locus.py`**, **`qa/epoch_drift.py`** (drift counts by script).

**cli.py**: subcommands `epoch`, `rescore`, `compare`, `locus-evidence`; `--data-dir/--results-dir` (or `GOVSCORE_DATA_DIR`) on `validate/sensitivity/robustness/figures` (robustness.py:429-435, figures.py:786-802); `validate` reads `external_fetched_at` from `results/v1/validation.json`; `run_full.load_progress` filters on `catalog_version`; separate progress file `data/processed/full_metrics_v2_progress.jsonl`; never `run --fresh` on v1. Makefile: `repair`, `compare`.

**Cache scheme** — "never re-query within a catalogue version": v1 keys untouched; v2 objects live in `data/raw/<owner>__<repo>/v2/` (`epoch_commit.json`, `tree_paths_<sha12>.json`, `org_epoch_commit.json`, `org_tree_paths_<sha12>.json`, optional `until_candidate.json`), each carrying `fetched_at`, `catalog_version`; content-addressed by sha so re-runs hit cache; `data/raw/_v2_manifest.json` with sha256. Any REST key added later uses prefix `v2_`. Scratchpad prototype cache is never copied.

**Tests (known cases, required)**: `tests/test_epoch.py` — synthetic chain where a side-branch commit newer than the first-parent tip must be ignored; `git init` fixture with `uploadpack.allowFilter=true` cloned via `file://`; cutoff on `%ct`. `tests/test_patterns.py` — positives: nodejs `.github/ISSUE_TEMPLATE/1-bug-report.yml`, golang extension-less `.github/PULL_REQUEST_TEMPLATE`, tensorflow root `CODEOWNERS`, rails `.github/security.md`, jekyll `.github/SECURITY.markdown`, guzzle org `.github/SECURITY.md` (inherited), gitlabhq `.gitlab-ci.yml`, uniffi `.circleci/config.yml`, rust `.github/renovate.json5`, `LICENSE-MIT`, `COPYING.GPLv2`; negatives: `security.go`, `.github/ISSUE_TEMPLATE/config.yml` alone, `licenses/foo`, `src/license`, `license-metadata.json`, root `funding.yml`, `vendor/x/.circleci/config.yml`, `docs/security/index.md`, org `CODEOWNERS`/workflows never inherited. `tests/test_release_anchor.py` — trimmed fixture straddling 2025-07-24: snapshot-anchored == v1, now()-anchored ≠. `tests/test_rescore.py` — splice preserves D2/D3/D4/releases/extracted_at. `tests/test_compare.py` — flip table and ρ on a 4-record fixture. `test_extractors.py` re-pointed to the compiled-regex interface.

## 4. Registro de decisão (rascunho PT-BR)

```
# Registro de decisão — catálogo v2: reparo da medição de D1/D5 na época do snapshot
Data: 2026-09-13 · Status: aceito · Commit das regras: <hash antes da re-pontuação>
Altera DETECÇÃO; não altera itens, limiares nem pesos (config/metrics.yaml intacto).

## Contexto e defeito
[texto do auditor de época, §Contexto e §Defeito, verbatim] + cross-check Scorecard
Security-Policy: concordância v1 = 48/53 (3 falsos negativos: rails, jekyll, guzzle;
2 omissões do Scorecard: statamic/cms, mavlink/qgroundcontrol).

## Proveniência (honesta)
Regras redigidas em 13/09/2026 a partir de docs GitHub/Licensee/Renovate/Scorecard após
o defeito em nodejs/node; três passagens de protótipo sobre a amostra (cache fora de
data/raw). Revisões entre passagens, cada uma com base documental: (1) apenas blobs
(semântica ls-tree do backend git v1; diretório security/ não é política); (2) formulários
.yaml aceitos (docs: "YAML form definition file"); (3) config.yml excluído (é configuração
do seletor); (4) FUNDING.yml na raiz de {owner}/.github (continuidade com FUNDING_PATHS v1
e comportamento observado da plataforma). Os deltas de score e ρ externos foram vistos
durante o protótipo; nenhuma regra foi escolhida por eles e nenhuma será alterada após
este commit. Ajuste posterior = catálogo v3 com novo registro.

## Época (por repositório)
cutoff_r = fetched_at de data/raw/{r}/repo_metadata.json (instante da sondagem v1 de
D1/D5; todos ≤ 2026-07-24T23:59:59Z). Commit de época = primeiro commit da cadeia
first-parent do branch default v1 com data de committer ≤ cutoff_r, via clone parcial
(--filter=tree:0, --shallow-since 60d → 365d → --depth 400/1600/6400). REST
commits?until= rejeitado (grafo completo; 13/100 divergentes). Verificação: todo blob
positivo em v1 (codeowners, security_md, governance, funding_yml, workflows, dependabot)
deve existir com o mesmo sha na árvore de época; divergência ⇒ epoch_unverified,
repositório mantido, D1/D5 de v1 com v2_source="v1_cache", contado. Aproximação
declarada: data de committer ≠ instante de push (limitada por pushed_at). {owner}/.github
resolvido com o mesmo cutoff; inexistente/vazio/sem commit ⇒ sem herança.

## Fonte
Lista de blobs (git ls-tree -r) da árvore de época; caminhos em minúsculas; padrões
ancorados; symlinks contam (relatados); diretórios e submódulos não.
LOC = (\.github/|docs/)?   DOC = (\.(md|markdown|mdown|rst|txt|adoc|asciidoc))?

## Regras v2 (verbatim)
readme                ^LOC readme DOC$
contributing          ^LOC contributing DOC$
code_of_conduct       ^LOC code[-_]of[-_]conduct DOC$
license (só raiz)     ^((un)?licen[sc]e|copying|copyright)(\.(md|txt|rst|markdown))?$
                    | ^((un)?licen[sc]e|copying|copyright)[-_.](?!.*\.json[5c]?$)[a-z0-9.+_-]+$
                    | ^[a-z0-9]+[-_](un)?licen[sc]e(\.[a-z]+)?$ | ^patents$ | ^ofl\.md$
issue_template        ^LOC issue_template DOC$
                    | ^\.github/issue_template/(?!config\.ya?ml$)[^/]+\.(md|ya?ml)$
pull_request_template ^LOC pull_request_template DOC$
                    | ^LOC pull_request_template/[^/]+\.(md|txt)$
codeowners            ^LOC codeowners$
governance            ^LOC governance DOC$
funding (repo)        ^\.github/funding\.yml$     (org: ^(\.github/)?funding\.yml$)
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
dependency_automation ^\.github/dependabot\.yml$ [decisão 2: (\.ya?ml)]
                    | ^(\.github/|\.gitlab/)?renovate\.json[5c]?$ | ^\.renovaterc(\.json[5c]?)?$
                    | ^(\.github/|\.config/)?\.?scala-steward\.conf$ | ^\.pyup\.ya?ml$
Herança de {owner}/.github (só se ausente no repo; <item>_inherited=true): contributing,
code_of_conduct, issue_template, pull_request_template, funding, security_policy
[+ governance apenas se decisão 3 = sim, com citação datada]. Nunca: readme, license,
codeowners, ci_configured, dependency_automation. Fonte única = árvore (perfil
comunitário não é mais usado para pontuar; união teria contribuído 0 decisões).
Registrados sem pontuar: issue_template_config_only, issue_template_yml_only,
funding_yaml, dependabot_yaml, symlink hits, profile.updated_at.
Fontes: GitHub docs (default community health files; about-readmes; contributing
guidelines; adding a code of conduct; about-code-owners; issue/PR templates; issue forms;
community profiles; sponsor button; dependabot options), Licensee license_file.rb,
docs.renovatebot.com/configuration-options, Scorecard checks/raw/{security_policy,
dependency_update_tool}.go, páginas dos provedores de CI (lista fechada).
Semânticas declaradas: ci_configured = "≥1 arquivo de pipeline reconhecido"; templates
sem validação de frontmatter; espelhos recebem crédito por CI de outra forja; invisíveis:
renovate em package.json, Renovate/Dependabot só por App/configuração, CI externa
(KernelCI, LUCI, FATE, Prow central), OWNERS, private vulnerability reporting (sem época).

## O que não muda
Itens, limiares, pesos; amostra e arquétipos (classificados em 2026-07-20; 5 cruzamentos
de estrelas declarados, penecho renomeado); D2, D3, D4, stars/forks, releases_12m,
release_notes_share, health_percentage (copiados de v1); indicadores externos (cache de
julho, external_fetched_at de v1).

## Protocolo
(a) commit deste registro; (b) arquivar v1 (cópia + SHA256SUMS + tag); (c)–(f) epoch →
ls-tree → rescore → score; (g) compare (ρ, trocas por item × arquétipo nas duas direções,
herdados, médias/quartis, divergências de época, cross-checks Scorecard 48/53 e License,
asserção health=100); (h) validate/sensitivity/robustness/figures com v1 arquivado e
variantes discriminantes sem D5 / sem D1+D5 (sobreposição parcial com checks do
Scorecard declarada); (i) texto. Exceção única à regra "nunca reconsulta": objetos
imutáveis (commit/árvore por SHA) obtidos em 09/2026 em data/raw/<r>/v2/.
```

## 5. What to say in the thesis (PT-BR)

**cap3 (§Extração, junto de L137-139):** "Uma exceção registrada (decisão de 13/09/2026) aplica-se aos 12 itens binários de D1 e D5: durante a inspeção do dataset verificou-se que o caminho de API usado na extração de julho era mais estreito que a convenção documentada pelo GitHub (o campo `issue_template` do perfil comunitário só reconhece o arquivo legado; CODEOWNERS, GOVERNANCE, SECURITY, CI e automação de dependências eram sondados em um único local, com sensibilidade a caixa e sem herança organizacional). Esses itens foram re-medidos em setembro de 2026 sobre a árvore de arquivos do commit *first-parent* do branch default no instante da sondagem original — objetos imutáveis endereçados por SHA — com regras fixadas em registro de decisão antes da re-pontuação e verificadas contra os blobs observados em julho; nenhuma outra métrica foi reextraída, limiares e pesos permaneceram os de 19/07/2026 e as saídas originais (catálogo v1) foram arquivadas."

**cap4 (§4.2, após L113-122, e §4.3 validação):** "A comparação v1→v2 é relatada integralmente em `results/reparo_v1_v2.md`: todas as trocas foram de ausente para presente (nenhuma no sentido inverso), concentradas em `issue_template` e `dependency_automation`; a ordem dos arquétipos e o ranking foram preservados (ρ de Spearman v1×v2 = [valor oficial]). Os resultados de validação, sensibilidade e robustez foram re-executados sobre o catálogo v2 e são apresentados lado a lado com os de v1; como as regras de D5 passaram a coincidir parcialmente com os checks *Security-Policy* e *Dependency-Update-Tool* do Scorecard, qualquer aumento de ρ com esse critério é em parte mecânico, o que é controlado pelas variantes discriminantes sem D5 e sem D1+D5. Limitações novas: templates contados sem validação de *frontmatter*; `ci_configured` passa a significar '≥1 arquivo de pipeline reconhecido'; automação configurada apenas por aplicativo ou em `package.json` permanece invisível."

## 6. Open decisions for the author

1. **Cutoff of the epoch**: per-repo `fetched_at` of v1 `repo_metadata.json` (recommended — exact instant of the v1 probe, satisfies guardrail 3 as an upper bound; 48/100 first-parent commits under the global cutoff post-date the v1 probe) vs global 2026-07-24T23:59:59Z (prototype numbers were computed with it). Pick one before (c); the other becomes a sensitivity row.
2. **`.github/dependabot.yaml`** (2 repos: openai/codex, openinterpreter): score only `.yml` (GitHub docs; recommended) with `.yaml` as a declared non-scored flag, or accept `.ya?ml` (Scorecard operational definition).
3. **GOVERNANCE inheritance**: one verdict reports the current GitHub default-files page lists `GOVERNANCE.md`, the D1 auditor's quote does not. Open the page today, cite it with access date; default no inheritance if absent (0 sample cases either way).
4. **Scope of this pass**: D1/D5 only (recommended: mutable D3 objects keep the July sentence "nenhuma outra métrica foi reextraída" true) vs including the D3 fixed-cohort redesign (T3.1, ~2 h GraphQL, own record, changes D3 for all 96 repos, expected ρ_D3 ≈ 0.85–0.9) — if wanted, as a separately declared v3.
5. **Optional validation instruments**: run T2.7 only, or also T3.4/T3.5 (Scorecard CLI, ~1–3 h) and T3.6 (GraphQL platform crosscheck) as report-only appendices; all must be pre-registered as descriptive, never as rule arbiters.