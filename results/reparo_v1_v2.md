# Reparo v1→v2 (catálogo v2)

Registros comparados: **100** (v1 = 100, v2 = 100); re-medição em 2026-09-13; cortes de época entre 2026-07-23T22:18:20Z e 2026-07-24T12:15:46Z. Escopo: apenas os 12 itens binários de D1/D5 (regras no registro de decisão de 2026-09-13); D2, D3, D4, stars, forks, releases e `health_percentage` copiados de v1; catálogo (itens, limiares, pesos) intacto.

## 1. Correlação v1×v2 (ρ de Spearman)

| métrica | n | ρ |
|---|---|---|
| score | 100 | 0.997 |
| subscore_artifacts | 100 | 0.960 |
| subscore_security | 100 | 0.966 |

Deslocamento máximo de ranking (score): **6.0** posições (n = 100); repositórios que se movem ≥ 5 posições: 5.

| repo | arquétipo | posição v1 | posição v2 | Δ | score v1 | score v2 |
|---|---|---|---|---|---|---|
| `firefly-iii/firefly-iii` | stadium | 58.0 | 52.0 | -6.0 | 50.3 | 58.8 |
| `ydb-platform/ydb` | club | 9.0 | 15.0 | +6.0 | 83.8 | 83.8 |
| `ggml-org/llama.cpp` | federation | 19.0 | 14.0 | -5.0 | 78.7 | 84.3 |
| `gitlabhq/gitlabhq` | stadium | 92.0 | 87.0 | -5.0 | 24.0 | 27.7 |
| `Gentleman-Programming/gentle-ai` | club | 71.0 | 66.0 | -5.0 | 39.1 | 44.9 |

## 2. Trocas por item × arquétipo (duas direções)

Repositórios com ≥ 1 troca: **63**; trocas False→True: **78**; True→False: **0**.

| item | dimensão | v1 True | v2 True | F→T | T→F | herdados v2 |
|---|---|---|---|---|---|---|
| readme | D1 | 100 | 100 | 0 | 0 | 0 |
| contributing | D1 | 64 | 64 | 0 | 0 | 3 |
| code_of_conduct | D1 | 43 | 43 | 0 | 0 | 6 |
| license | D1 | 93 | 93 | 0 | 0 | 0 |
| issue_template | D1 | 5 | 61 | 56 | 0 | 4 |
| pull_request_template | D1 | 53 | 54 | 1 | 0 | 0 |
| codeowners | D1 | 24 | 30 | 6 | 0 | 0 |
| governance | D1 | 2 | 2 | 0 | 0 | 0 |
| funding | D1 | 26 | 27 | 1 | 0 | 5 |
| security_policy | D5 | 49 | 53 | 4 | 0 | 12 |
| ci_configured | D5 | 84 | 87 | 3 | 0 | 0 |
| dependency_automation | D5 | 32 | 39 | 7 | 0 | 0 |

| item | arquétipo | n | v1 True | v2 True | F→T | T→F |
|---|---|---|---|---|---|---|
| readme | federation | 25 | 25 | 25 | 0 | 0 |
| readme | stadium | 25 | 25 | 25 | 0 | 0 |
| readme | club | 25 | 25 | 25 | 0 | 0 |
| readme | toy | 25 | 25 | 25 | 0 | 0 |
| contributing | federation | 25 | 22 | 22 | 0 | 0 |
| contributing | stadium | 25 | 14 | 14 | 0 | 0 |
| contributing | club | 25 | 20 | 20 | 0 | 0 |
| contributing | toy | 25 | 8 | 8 | 0 | 0 |
| code_of_conduct | federation | 25 | 16 | 16 | 0 | 0 |
| code_of_conduct | stadium | 25 | 8 | 8 | 0 | 0 |
| code_of_conduct | club | 25 | 16 | 16 | 0 | 0 |
| code_of_conduct | toy | 25 | 3 | 3 | 0 | 0 |
| license | federation | 25 | 25 | 25 | 0 | 0 |
| license | stadium | 25 | 23 | 23 | 0 | 0 |
| license | club | 25 | 25 | 25 | 0 | 0 |
| license | toy | 25 | 20 | 20 | 0 | 0 |
| issue_template | federation | 25 | 1 | 22 | 21 | 0 |
| issue_template | stadium | 25 | 2 | 14 | 12 | 0 |
| issue_template | club | 25 | 2 | 17 | 15 | 0 |
| issue_template | toy | 25 | 0 | 8 | 8 | 0 |
| pull_request_template | federation | 25 | 22 | 22 | 0 | 0 |
| pull_request_template | stadium | 25 | 10 | 11 | 1 | 0 |
| pull_request_template | club | 25 | 16 | 16 | 0 | 0 |
| pull_request_template | toy | 25 | 5 | 5 | 0 | 0 |
| codeowners | federation | 25 | 12 | 14 | 2 | 0 |
| codeowners | stadium | 25 | 4 | 4 | 0 | 0 |
| codeowners | club | 25 | 8 | 12 | 4 | 0 |
| codeowners | toy | 25 | 0 | 0 | 0 | 0 |
| governance | federation | 25 | 1 | 1 | 0 | 0 |
| governance | stadium | 25 | 0 | 0 | 0 | 0 |
| governance | club | 25 | 1 | 1 | 0 | 0 |
| governance | toy | 25 | 0 | 0 | 0 | 0 |
| funding | federation | 25 | 8 | 8 | 0 | 0 |
| funding | stadium | 25 | 12 | 13 | 1 | 0 |
| funding | club | 25 | 4 | 4 | 0 | 0 |
| funding | toy | 25 | 2 | 2 | 0 | 0 |
| security_policy | federation | 25 | 20 | 21 | 1 | 0 |
| security_policy | stadium | 25 | 9 | 12 | 3 | 0 |
| security_policy | club | 25 | 16 | 16 | 0 | 0 |
| security_policy | toy | 25 | 4 | 4 | 0 | 0 |
| ci_configured | federation | 25 | 22 | 23 | 1 | 0 |
| ci_configured | stadium | 25 | 22 | 23 | 1 | 0 |
| ci_configured | club | 25 | 23 | 24 | 1 | 0 |
| ci_configured | toy | 25 | 17 | 17 | 0 | 0 |
| dependency_automation | federation | 25 | 10 | 14 | 4 | 0 |
| dependency_automation | stadium | 25 | 10 | 11 | 1 | 0 |
| dependency_automation | club | 25 | 7 | 9 | 2 | 0 |
| dependency_automation | toy | 25 | 5 | 5 | 0 | 0 |

### Trocas False→True (nominais, por item)

- **issue_template** (56): federation: `tensorflow/tensorflow`, `rails/rails`, `freeCodeCamp/freeCodeCamp`, `affaan-m/ECC`, `golang/go`, `ggml-org/llama.cpp`, `laravel/framework`, `rust-lang/rust`, `godotengine/godot`, `filamentphp/filament`, `elastic/elasticsearch`, `NousResearch/hermes-agent`, `openai/codex`, `nodejs/node`, `langgenius/dify`, `infiniflow/ragflow`, `zed-industries/zed`, `huggingface/transformers`, `openinterpreter/openinterpreter`, `supabase/supabase`, `google-gemini/gemini-cli`; stadium: `danielmiessler/SecLists`, `Genymobile/scrcpy`, `jekyll/jekyll`, `ventoy/Ventoy`, `gohugoio/hugo`, `tmux/tmux`, `tesseract-ocr/tesseract`, `monicahq/monica`, `junegunn/fzf`, `firefly-iii/firefly-iii`, `hashicorp/vagrant`, `pbatard/rufus`; club: `flatpak/flatpak`, `lemonade-sdk/lemonade`, `cilium/tetragon`, `vllm-project/aibrix`, `statamic/cms`, `lobsters/lobsters`, `Expensify/App`, `SolaceLabs/solace-agent-mesh`, `hashicorp/terraform-provider-azurerm`, `Gentleman-Programming/gentle-ai`, `librenms/librenms`, `microsoft/FluidFramework`, `X11Libre/xserver`, `asterinas/asterinas`, `mavlink/qgroundcontrol`; toy: `JungHoonGhae/tossinvest-cli`, `spring-cloud/spring-cloud-circuitbreaker`, `justnullname/QuickView`, `gittower/git-flow-next`, `containers/conmon-rs`, `JChristensen/Timezone`, `tailuge/billiards`, `ImageMagick/ImageMagick6`
- **pull_request_template** (1): stadium: `monicahq/monica`
- **codeowners** (6): federation: `tensorflow/tensorflow`, `ggml-org/llama.cpp`; club: `vllm-project/semantic-router`, `github/explore`, `hashicorp/terraform-provider-azurerm`, `asterinas/asterinas`
- **funding** (1): stadium: `firefly-iii/firefly-iii`
- **security_policy** (4): federation: `rails/rails`; stadium: `jekyll/jekyll`, `firefly-iii/firefly-iii`, `guzzle/guzzle`
- **ci_configured** (3): federation: `FFmpeg/FFmpeg`; stadium: `gitlabhq/gitlabhq`; club: `mozilla/uniffi-rs`
- **dependency_automation** (7): federation: `freeCodeCamp/freeCodeCamp`, `rust-lang/rust`, `elastic/elasticsearch`, `zed-industries/zed`; stadium: `huginn/huginn`; club: `cilium/tetragon`, `Gentleman-Programming/gentle-ai`

## 3. Trocas True→False

nenhuma

## 4. Herdados de `{owner}/.github`

| item | v1 | v2 | repositórios (v2) |
|---|---|---|---|
| contributing | 0 | 3 | `freeCodeCamp/freeCodeCamp`, `doocs/advanced-java`, `guzzle/guzzle` |
| code_of_conduct | 0 | 6 | `freeCodeCamp/freeCodeCamp`, `godotengine/godot`, `supabase/supabase`, `guzzle/guzzle`, `spring-cloud/spring-cloud-gateway`, `spring-cloud/spring-cloud-circuitbreaker` |
| issue_template | 0 | 4 | `supabase/supabase`, `guzzle/guzzle`, `SolaceLabs/solace-agent-mesh`, `JChristensen/Timezone` |
| pull_request_template | 0 | 0 | nenhum |
| funding | 5 | 5 | `godotengine/godot`, `nodejs/node`, `gohugoio/hugo`, `doocs/advanced-java`, `cilium/tetragon` |
| security_policy | 11 | 12 | `freeCodeCamp/freeCodeCamp`, `rust-lang/rust`, `godotengine/godot`, `elastic/elasticsearch`, `supabase/supabase`, `hashicorp/vagrant`, `guzzle/guzzle`, `github/explore`, `hashicorp/terraform-provider-azurerm`, `X11Libre/xserver`, `spring-cloud/spring-cloud-circuitbreaker`, `ImageMagick/ImageMagick6` |

## 5. Estatísticas por arquétipo (v1 vs v2)

### score

| arquétipo | versão | n | média | mediana | dp | Q1 | Q3 | mín | máx |
|---|---|---|---|---|---|---|---|---|---|
| todos | v1 | 100 | 55.2 | 57.0 | 22.2 | 35.5 | 76.7 | 6.5 | 94.6 |
| todos | v2 | 100 | 57.4 | 59.5 | 23.2 | 35.9 | 79.6 | 6.5 | 97.4 |
| federation | v1 | 25 | 76.1 | 77.1 | 9.9 | 71.2 | 81.9 | 56.9 | 94.6 |
| federation | v2 | 25 | 79.4 | 82.1 | 10.7 | 72.7 | 86.7 | 56.9 | 97.4 |
| stadium | v1 | 25 | 42.2 | 41.7 | 13.7 | 32.7 | 51.6 | 15.9 | 66.2 |
| stadium | v2 | 25 | 44.5 | 44.3 | 14.4 | 34.0 | 56.8 | 15.9 | 68.9 |
| club | v1 | 25 | 70.4 | 75.3 | 12.7 | 61.7 | 79.8 | 39.1 | 85.7 |
| club | v2 | 25 | 72.9 | 75.5 | 13.0 | 62.3 | 82.6 | 44.9 | 91.4 |
| toy | v1 | 25 | 32.0 | 32.0 | 12.6 | 24.7 | 40.7 | 6.5 | 59.4 |
| toy | v2 | 25 | 32.9 | 32.0 | 13.4 | 24.7 | 42.1 | 6.5 | 62.1 |

### subscore_artifacts

| arquétipo | versão | n | média | mediana | dp | Q1 | Q3 | mín | máx |
|---|---|---|---|---|---|---|---|---|---|
| todos | v1 | 100 | 0.456 | 0.444 | 0.192 | 0.333 | 0.556 | 0.111 | 0.889 |
| todos | v2 | 100 | 0.527 | 0.556 | 0.228 | 0.333 | 0.667 | 0.111 | 1.000 |
| federation | v1 | 25 | 0.587 | 0.556 | 0.159 | 0.500 | 0.667 | 0.222 | 0.889 |
| federation | v2 | 25 | 0.689 | 0.667 | 0.176 | 0.667 | 0.778 | 0.222 | 1.000 |
| stadium | v1 | 25 | 0.436 | 0.444 | 0.160 | 0.333 | 0.556 | 0.111 | 0.778 |
| stadium | v2 | 25 | 0.498 | 0.444 | 0.193 | 0.333 | 0.667 | 0.111 | 0.889 |
| club | v1 | 25 | 0.520 | 0.556 | 0.149 | 0.444 | 0.667 | 0.222 | 0.778 |
| club | v2 | 25 | 0.604 | 0.556 | 0.164 | 0.500 | 0.722 | 0.222 | 0.889 |
| toy | v1 | 25 | 0.280 | 0.222 | 0.154 | 0.222 | 0.333 | 0.111 | 0.667 |
| toy | v2 | 25 | 0.316 | 0.222 | 0.194 | 0.222 | 0.444 | 0.111 | 0.778 |

### subscore_security

| arquétipo | versão | n | média | mediana | dp | Q1 | Q3 | mín | máx |
|---|---|---|---|---|---|---|---|---|---|
| todos | v1 | 100 | 0.614 | 0.633 | 0.308 | 0.408 | 0.800 | 0.000 | 1.000 |
| todos | v2 | 100 | 0.645 | 0.750 | 0.302 | 0.433 | 0.834 | 0.000 | 1.000 |
| federation | v1 | 25 | 0.738 | 0.800 | 0.305 | 0.600 | 1.000 | 0.000 | 1.000 |
| federation | v2 | 25 | 0.790 | 0.800 | 0.281 | 0.675 | 1.000 | 0.000 | 1.000 |
| stadium | v1 | 25 | 0.571 | 0.600 | 0.326 | 0.250 | 0.817 | 0.000 | 1.000 |
| stadium | v2 | 25 | 0.617 | 0.667 | 0.315 | 0.342 | 0.900 | 0.000 | 1.000 |
| club | v1 | 25 | 0.695 | 0.767 | 0.234 | 0.600 | 0.800 | 0.000 | 1.000 |
| club | v2 | 25 | 0.721 | 0.800 | 0.213 | 0.600 | 0.800 | 0.250 | 1.000 |
| toy | v1 | 25 | 0.451 | 0.433 | 0.292 | 0.250 | 0.675 | 0.000 | 1.000 |
| toy | v2 | 25 | 0.451 | 0.433 | 0.292 | 0.250 | 0.675 | 0.000 | 1.000 |

### Δ score (v2 − v1)

| arquétipo | n | média | mediana | dp | Q1 | Q3 | mín | máx |
|---|---|---|---|---|---|---|---|---|
| todos | 100 | 2.25 | 2.78 | 2.06 | 0.00 | 2.78 | 0.00 | 8.56 |
| federation | 25 | 3.37 | 2.78 | 1.86 | 2.78 | 5.56 | 0.00 | 6.53 |
| stadium | 25 | 2.25 | 2.78 | 2.30 | 0.00 | 2.89 | 0.00 | 8.56 |
| club | 25 | 2.50 | 2.78 | 1.90 | 0.00 | 2.78 | 0.00 | 5.78 |
| toy | 25 | 0.89 | 0.00 | 1.32 | 0.00 | 2.78 | 0.00 | 2.78 |

## 6. Maiores deslocamentos de score

| repo | arquétipo | itens alterados | score v1 | score v2 | Δ | D1 v1→v2 | D5 v1→v2 |
|---|---|---|---|---|---|---|---|
| `firefly-iii/firefly-iii` | stadium | issue_template F→T, funding F→T, security_policy F→T | 50.3 | 58.8 | 8.56 | 0.67→0.89 | 0.80→1.00 |
| `freeCodeCamp/freeCodeCamp` | federation | issue_template F→T, dependency_automation F→T | 81.4 | 87.9 | 6.53 | 0.78→0.89 | 0.50→0.75 |
| `jekyll/jekyll` | stadium | issue_template F→T, security_policy F→T | 61.9 | 68.4 | 6.53 | 0.78→0.89 | 0.50→0.75 |
| `Gentleman-Programming/gentle-ai` | club | issue_template F→T, dependency_automation F→T | 39.1 | 44.9 | 5.78 | 0.44→0.56 | 0.60→0.80 |
| `rails/rails` | federation | issue_template F→T, security_policy F→T | 77.1 | 82.9 | 5.78 | 0.67→0.78 | 0.60→0.80 |
| `rust-lang/rust` | federation | issue_template F→T, dependency_automation F→T | 85.2 | 91.0 | 5.78 | 0.67→0.78 | 0.80→1.00 |
| `elastic/elasticsearch` | federation | issue_template F→T, dependency_automation F→T | 81.4 | 87.2 | 5.78 | 0.56→0.67 | 0.80→1.00 |
| `zed-industries/zed` | federation | issue_template F→T, dependency_automation F→T | 79.9 | 85.7 | 5.78 | 0.67→0.78 | 0.60→0.80 |
| `cilium/tetragon` | club | issue_template F→T, dependency_automation F→T | 85.6 | 91.4 | 5.78 | 0.78→0.89 | 0.77→0.97 |
| `tensorflow/tensorflow` | federation | issue_template F→T, codeowners F→T | 73.9 | 79.5 | 5.56 | 0.44→0.67 | 1.00→1.00 |

## 7. Época

| estatística | contagens |
|---|---|
| epoch_status | ok: 99, unverified: 1 |
| passo do resolvedor | fetch_since_60d: 88, clone_depth_1: 8, fetch_since_365d: 3, fetch_depth_1600: 1 |
| fonte do corte | probes: 100 |
| fonte dos itens (v2_source) | tree: 99, v1_cache: 1 |

Divergências first-parent × `until` (cross-check REST, quando disponível): 0 de 0.

Não verificados (blob v1 divergente na árvore de época; itens v1 mantidos): `dtyq/magic` (workflows).

Inacessíveis (itens v1 mantidos): nenhum.

## 8. Cross-checks descritivos

Asserção `health_percentage = 100 ⇒ issue_template`: violada em v1 por 11 repositórios (`freeCodeCamp/freeCodeCamp`, `affaan-m/ECC`, `godotengine/godot`, `nodejs/node`, `langgenius/dify`, `huggingface/transformers`, `WerWolv/ImHex`, `librenms/librenms`, `mavlink/qgroundcontrol`, `JungHoonGhae/tossinvest-cli`, `ImageMagick/ImageMagick6`); em v2 por 1 (`WerWolv/ImHex`).

Concordância com checks do OpenSSF Scorecard (cache de julho; presença = score do check > 0; descritivo — sobreposição parcial das regras de D5 com os checks declarada):

| check | item | n | concordância v1 | concordância v2 | nosso True / Scorecard False (v2) | nosso False / Scorecard True (v2) |
|---|---|---|---|---|---|---|
| Security-Policy | security_policy | 53 | 48/53 | 50/53 | `firefly-iii/firefly-iii`, `statamic/cms`, `mavlink/qgroundcontrol` | nenhum |
| License | license | 53 | 53/53 | 53/53 | nenhum | nenhum |
| Dependency-Update-Tool | dependency_automation | 3 | 3/3 | 3/3 | nenhum | nenhum |

## 9. Flags não pontuadas (sensibilidades declaradas)

| flag | n | repositórios |
|---|---|---|
| dependabot_yaml | 2 | `openai/codex`, `openinterpreter/openinterpreter` |
| issue_template_config_only | 4 | `fatedier/frp`, `gin-gonic/gin`, `vllm-project/semantic-router`, `NVIDIA/nccl` |
| issue_template_yaml_only | 5 | `fatedier/frp`, `gin-gonic/gin`, `WerWolv/ImHex`, `vllm-project/semantic-router`, `NVIDIA/nccl` |

Sistemas de CI reconhecidos: appveyor 1, buildkite 1, circleci 5, cirrus 1, forgejo_gitea_actions 1, github_actions 83, gitlab_ci 3, travis 3.
Ferramentas de automação de dependências: dependabot 32, renovate 8.
Itens herdados por origem (`inherited_from_org`): code_of_conduct 6, contributing 3, funding 5, issue_template 4, security_policy 12.
Symlinks entre os arquivos casados: `google-gemini/gemini-cli` (docs/contributing.md).

## 10. Trocas por repositório (auditoria completa)

| repo | arquétipo | fonte | itens alterados | Δ score |
|---|---|---|---|---|
| `affaan-m/ECC` | federation | tree | issue_template F→T | 2.78 |
| `asterinas/asterinas` | club | tree | issue_template F→T, codeowners F→T | 5.56 |
| `cilium/tetragon` | club | tree | issue_template F→T, dependency_automation F→T | 5.78 |
| `containers/conmon-rs` | toy | tree | issue_template F→T | 2.78 |
| `danielmiessler/SecLists` | stadium | tree | issue_template F→T | 2.78 |
| `elastic/elasticsearch` | federation | tree | issue_template F→T, dependency_automation F→T | 5.78 |
| `Expensify/App` | club | tree | issue_template F→T | 2.78 |
| `FFmpeg/FFmpeg` | federation | tree | ci_configured F→T | 4.69 |
| `filamentphp/filament` | federation | tree | issue_template F→T | 2.78 |
| `firefly-iii/firefly-iii` | stadium | tree | issue_template F→T, funding F→T, security_policy F→T | 8.56 |
| `flatpak/flatpak` | club | tree | issue_template F→T | 2.78 |
| `freeCodeCamp/freeCodeCamp` | federation | tree | issue_template F→T, dependency_automation F→T | 6.53 |
| `Gentleman-Programming/gentle-ai` | club | tree | issue_template F→T, dependency_automation F→T | 5.78 |
| `Genymobile/scrcpy` | stadium | tree | issue_template F→T | 2.78 |
| `ggml-org/llama.cpp` | federation | tree | issue_template F→T, codeowners F→T | 5.56 |
| `github/explore` | club | tree | codeowners F→T | 2.78 |
| `gitlabhq/gitlabhq` | stadium | tree | ci_configured F→T | 3.75 |
| `gittower/git-flow-next` | toy | tree | issue_template F→T | 2.78 |
| `godotengine/godot` | federation | tree | issue_template F→T | 2.78 |
| `gohugoio/hugo` | stadium | tree | issue_template F→T | 2.78 |
| `golang/go` | federation | tree | issue_template F→T | 2.78 |
| `google-gemini/gemini-cli` | federation | tree | issue_template F→T | 2.78 |
| `guzzle/guzzle` | stadium | tree | security_policy F→T (herdado) | 3.00 |
| `hashicorp/terraform-provider-azurerm` | club | tree | issue_template F→T, codeowners F→T | 5.56 |
| `hashicorp/vagrant` | stadium | tree | issue_template F→T | 2.78 |
| `huggingface/transformers` | federation | tree | issue_template F→T | 2.78 |
| `huginn/huginn` | stadium | tree | dependency_automation F→T | 3.75 |
| `ImageMagick/ImageMagick6` | toy | tree | issue_template F→T | 2.78 |
| `infiniflow/ragflow` | federation | tree | issue_template F→T | 2.78 |
| `JChristensen/Timezone` | toy | tree | issue_template F→T (herdado) | 2.78 |
| `jekyll/jekyll` | stadium | tree | issue_template F→T, security_policy F→T | 6.53 |
| `junegunn/fzf` | stadium | tree | issue_template F→T | 2.78 |
| `JungHoonGhae/tossinvest-cli` | toy | tree | issue_template F→T | 2.78 |
| `justnullname/QuickView` | toy | tree | issue_template F→T | 2.78 |
| `langgenius/dify` | federation | tree | issue_template F→T | 2.78 |
| `laravel/framework` | federation | tree | issue_template F→T | 2.78 |
| `lemonade-sdk/lemonade` | club | tree | issue_template F→T | 2.78 |
| `librenms/librenms` | club | tree | issue_template F→T | 2.78 |
| `lobsters/lobsters` | club | tree | issue_template F→T | 2.78 |
| `mavlink/qgroundcontrol` | club | tree | issue_template F→T | 2.78 |
| `microsoft/FluidFramework` | club | tree | issue_template F→T | 2.78 |
| `monicahq/monica` | stadium | tree | issue_template F→T, pull_request_template F→T | 5.56 |
| `mozilla/uniffi-rs` | club | tree | ci_configured F→T | 3.75 |
| `nodejs/node` | federation | tree | issue_template F→T | 2.78 |
| `NousResearch/hermes-agent` | federation | tree | issue_template F→T | 2.78 |
| `openai/codex` | federation | tree | issue_template F→T | 2.78 |
| `openinterpreter/openinterpreter` | federation | tree | issue_template F→T | 2.78 |
| `pbatard/rufus` | stadium | tree | issue_template F→T | 2.78 |
| `rails/rails` | federation | tree | issue_template F→T, security_policy F→T | 5.78 |
| `rust-lang/rust` | federation | tree | issue_template F→T, dependency_automation F→T | 5.78 |
| `SolaceLabs/solace-agent-mesh` | club | tree | issue_template F→T (herdado) | 2.78 |
| `spring-cloud/spring-cloud-circuitbreaker` | toy | tree | issue_template F→T | 2.78 |
| `statamic/cms` | club | tree | issue_template F→T | 2.78 |
| `supabase/supabase` | federation | tree | issue_template F→T (herdado) | 2.78 |
| `tailuge/billiards` | toy | tree | issue_template F→T | 2.78 |
| `tensorflow/tensorflow` | federation | tree | issue_template F→T, codeowners F→T | 5.56 |
| `tesseract-ocr/tesseract` | stadium | tree | issue_template F→T | 2.78 |
| `tmux/tmux` | stadium | tree | issue_template F→T | 2.78 |
| `ventoy/Ventoy` | stadium | tree | issue_template F→T | 2.78 |
| `vllm-project/aibrix` | club | tree | issue_template F→T | 2.78 |
| `vllm-project/semantic-router` | club | tree | codeowners F→T | 2.78 |
| `X11Libre/xserver` | club | tree | issue_template F→T | 2.78 |
| `zed-industries/zed` | federation | tree | issue_template F→T, dependency_automation F→T | 5.78 |
