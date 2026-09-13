# QA da extração completa (item 5)

**Extração:** 2026-07-23 → 2026-07-24 · **código:** `ee25f09-dirty` · **ok:** 100 · **falhas:** 0

## Scores por arquétipo

| Arquétipo | n | média | mediana | dp | mín | máx |
|---|---|---|---|---|---|---|
| federation | 25 | 79.4 | 82.1 | 10.7 | 56.9 | 97.4 |
| stadium | 25 | 44.5 | 44.3 | 14.4 | 15.9 | 68.9 |
| club | 25 | 72.9 | 75.5 | 13.0 | 44.9 | 91.4 |
| toy | 25 | 32.9 | 32.0 | 13.4 | 6.5 | 62.1 |

## Métricas faltantes (None — omitidas do score, nunca zero)

| métrica | faltantes | % |
|---|---|---|
| distribution_contributor_retention | 12 | 12% |
| responsiveness_median_first_response_hours | 10 | 10% |
| responsiveness_median_issue_close_hours | 14 | 14% |
| responsiveness_median_pr_merge_hours | 10 | 10% |
| responsiveness_pr_merge_ratio | 4 | 4% |
| responsiveness_pr_review_coverage | 6 | 6% |
| security_release_notes_share | 26 | 26% |
| subscore_responsiveness | 4 | 4% |

## Avisos

Sem resposta humana observada nas issues amostradas (D3 parcial): `torvalds/linux`, `FFmpeg/FFmpeg`, `git/git`, `gitlabhq/gitlabhq`, `github/explore`, `fustyles/Arduino`, `AITabby/opencodex`, `yolfinance/yolfi-agent`, `EFanZh/LeetCode`, `Au1rxx/free-vpn-subscriptions`

## Declarações de QA (v2)

Instrumentos descritivos pré-registrados (`docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md`); nenhum altera scores.

Registros: 100 · `catalog_version`: v2 (100).

### Censura de releases (`per_page = 30`)

- **Saturados** (25): 30 releases devolvidas, todas na janela de 12 meses — `releases_12m` é PISO e `release_notes_share` foi calculado sobre as 30 mais recentes: `Au1rxx/free-vpn-subscriptions`, `Expensify/App`, `Gentleman-Programming/gentle-ai`, `JungHoonGhae/tossinvest-cli`, `Martian-Engineering/lossless-claw`, `SolaceLabs/solace-agent-mesh`, `SwiftOldDriver/iOS-Weekly`, `amalshaji/dbcooper`, `elastic/elasticsearch`, `filamentphp/filament`, `firefly-iii/firefly-iii`, `ggml-org/llama.cpp`, `gohugoio/hugo`, `google-gemini/gemini-cli`, `hashicorp/terraform-provider-azurerm`, `huggingface/transformers`, `justnullname/QuickView`, `laravel/framework`, `lemonade-sdk/lemonade`, `microsoft/FluidFramework`, `nodejs/node`, `openai/codex`, `react/react-native`, `statamic/cms`, `zed-industries/zed`.
- **Prereleases na janela**: 177 de 1241 releases (14.3%) — o catálogo não distingue prereleases de releases.
- **`published_at` não monotônico na ordem devolvida** (19; a API ordena por `created_at`): `WerWolv/ImHex`, `X11Libre/xserver`, `amalshaji/dbcooper`, `cilium/tetragon`, `elastic/elasticsearch`, `filamentphp/filament`, `flatpak/flatpak`, `google-gemini/gemini-cli`, `huggingface/transformers`, `infiniflow/ragflow`, `laravel/framework`, `microsoft/FluidFramework`, `openai/codex`, `react/react-native`, `spring-cloud/spring-cloud-gateway`, `tensorflow/tensorflow`, `tesseract-ocr/tesseract`, `ydb-platform/ydb`, `zed-industries/zed`.

### Retenção de contribuidores (`contributor_retention`)

| motivo | n | repositórios |
|---|---|---|
| observed | 88 | — |
| young_repo (criado na 2ª metade da janela — 1ª metade vazia por construção) | 9 | `AITabby/opencodex`, `Au1rxx/free-vpn-subscriptions`, `Gentleman-Programming/gentle-ai`, `JungHoonGhae/tossinvest-cli`, `Martian-Engineering/lossless-claw`, `erickong/penecho`, `garrytan/gstack`, `yan-labs/serenity-aleabitoreddit`, `yolfinance/yolfi-agent` |
| first_half_empty (repositório antigo sem autores na 1ª metade — dormência) | 3 | `MisterBooo/LeetCodeAnimation`, `bcoles/kasld`, `dtyq/magic` |

### CI não detectada (`ci_configured = False`)

Significa "sem configuração de CI reconhecida no repositório" (lista fechada de provedores do registro), NÃO "sem CI" — CI externa (KernelCI, LUCI, FATE, Prow central) é invisível declarada. 13 repositórios: `AITabby/opencodex`, `Aleksefo/react-native-webp-format`, `Au1rxx/free-vpn-subscriptions`, `JChristensen/Timezone`, `NVIDIA/nccl`, `anthropics/skills`, `edbrowse/edbrowse`, `fustyles/Arduino`, `golang/go`, `macrozheng/mall`, `morshedalam/rename`, `torvalds/linux`, `yan-labs/serenity-aleabitoreddit`.
