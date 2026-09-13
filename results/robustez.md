# Robustez e validade adicional (pós-revisão adversarial)

## 1. Sensibilidade dos limiares de normalização

Perturbação de best/worst por métrica (individual) e conjunta; ρ do ranking vs base. Pesos intocados.

| perturbação | ρ mín (por métrica) | ρ médio | pior variante | conjunta + | conjunta − |
|---|---|---|---|---|---|
| ±25% | 0.999 | 1.000 | pr_merge_ratio -25% | 0.997 | 0.997 |
| ±50% | 0.997 | 0.999 | truck_factor -50% | 0.991 | 0.991 |

## 2. Reclassificação dos arquétipos (limiares ±50%)

Contagens de Federações são pisos (early stop) — elevar `federation_min` torna esses casos indeterminados, não reclassificados (coluna própria).

| variante | preservados | mudam | fora das faixas | federações indet. | % preservados |
|---|---|---|---|---|---|
| conjunto +50% | 67 | 0 | 8 | 25 | 89.3% |
| conjunto −50% | 42 | 0 | 58 | 0 | 42.0% |
| federation_min_contributors +50% | 75 | 0 | 0 | 25 | 100.0% |
| federation_min_contributors −50% | 100 | 0 | 0 | 0 | 100.0% |
| stadium_max_contributors +50% | 100 | 0 | 0 | 0 | 100.0% |
| stadium_max_contributors −50% | 91 | 0 | 9 | 0 | 91.0% |
| club_min_contributors +50% | 92 | 0 | 8 | 0 | 92.0% |
| club_min_contributors −50% | 100 | 0 | 0 | 0 | 100.0% |
| toy_max_contributors +50% | 100 | 0 | 0 | 0 | 100.0% |
| toy_max_contributors −50% | 81 | 0 | 19 | 0 | 81.0% |
| stars_high_min +50% | 100 | 0 | 0 | 0 | 100.0% |
| stars_high_min −50% | 100 | 0 | 0 | 0 | 100.0% |
| club_stars_max +50% | 100 | 0 | 0 | 0 | 100.0% |
| club_stars_max −50% | 75 | 0 | 25 | 0 | 75.0% |
| toy_stars_max +50% | 100 | 0 | 0 | 0 | 100.0% |
| toy_stars_max −50% | 83 | 0 | 17 | 0 | 83.0% |

## 3. Validade discriminante vs OpenSSF Scorecard

ρ do score cheio = 0.770; ρ do composto social D2/D3/D4 = 0.626 (n = 53). Teste de Steiger para correlações dependentes (aproximação sobre Spearman): z = 3.28, p = 0.0011 — as dimensões sociais medem construto distinto do Scorecard.

| dimensão | ρ vs Scorecard |
|---|---|
| artifacts | 0.652 |
| distribution | 0.580 |
| responsiveness | 0.497 |
| diversity | 0.497 |
| security | 0.639 |

## 4. Robustez à exclusão de suspeitos de não-software

11 repositórios sinalizados (nome típico de não-software ou nenhuma resposta humana): `AITabby/opencodex`, `Au1rxx/free-vpn-subscriptions`, `EFanZh/LeetCode`, `FFmpeg/FFmpeg`, `MisterBooo/LeetCodeAnimation`, `fustyles/Arduino`, `git/git`, `github/explore`, `gitlabhq/gitlabhq`, `torvalds/linux`, `yolfinance/yolfi-agent`.

- **Estádio × forks**: com suspeitos ρ = -0.524 (n=25); sem suspeitos ρ = -0.528 (n=23). O achado exploratório deve ser reportado com esta análise ao lado.
- Globais sem suspeitos: scorecard ρ=0.755, stars ρ=0.380, forks ρ=0.446.

### 4.1 Cenários da inspeção manual (todos mantidos na amostra)

Categorias definidas na inspeção manual (notebook 01; `docs/decisions/2026-09-12-inspecao-manual-amostra.md`). **Conteúdo**: `MisterBooo/LeetCodeAnimation`, `EFanZh/LeetCode`, `github/explore`, `krahets/hello-algo`, `doocs/advanced-java`, `danielmiessler/SecLists`, `SwiftOldDriver/iOS-Weekly`, `Au1rxx/free-vpn-subscriptions`. **Espelhos**: `torvalds/linux`, `FFmpeg/FFmpeg`, `git/git`, `gitlabhq/gitlabhq`. Cenários pré-registrados do catálogo v2 (`docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md`): **sem_locus_externo** = locus de coordenação fora do GitHub (`git/git`, `gitlabhq/gitlabhq`, `golang/go`, `react/react-native`, `tensorflow/tensorflow`) ∪ espelhos — evidência em `results/locus_evidence.md`; **sem_openinterpreter** = par quase-duplicado (`openinterpreter/openinterpreter` ⊃ `openai/codex`). `sem_todos` permanece a união da inspeção manual de 2026-09-12 (heurística ∪ conteúdo ∪ espelhos) e NÃO incorpora os cenários v2, que são lidos isoladamente. Intra-arquétipo: ρ (p nominal, n).

| cenário | n | scorecard | stars | forks | stadium×forks | federation×scorecard |
|---|---|---|---|---|---|---|
| completa | 100 | 0.770 | 0.411 | 0.463 | -0.524 (p=0.007, n=25) | 0.589 (p=0.021, n=15) |
| sem_heuristica | 89 | 0.755 | 0.380 | 0.446 | -0.528 (p=0.010, n=23) | 0.196 (p=0.541, n=12) |
| sem_conteudo | 92 | 0.745 | 0.452 | 0.517 | -0.313 (p=0.167, n=21) | 0.589 (p=0.021, n=15) |
| sem_espelhos | 96 | 0.769 | 0.432 | 0.491 | -0.564 (p=0.004, n=24) | 0.196 (p=0.541, n=12) |
| sem_todos | 85 | 0.737 | 0.436 | 0.522 | -0.326 (p=0.160, n=20) | 0.196 (p=0.541, n=12) |
| sem_locus_externo | 93 | 0.778 | 0.427 | 0.484 | -0.564 (p=0.004, n=24) | 0.347 (p=0.327, n=10) |
| sem_openinterpreter | 99 | 0.770 | 0.411 | 0.464 | -0.524 (p=0.007, n=25) | 0.589 (p=0.021, n=15) |

- **stadium×forks**: perde significância nominal em: `sem_conteudo`, `sem_todos` — achado NÃO robusto à composição da amostra.
- **federation×scorecard**: perde significância nominal em: `sem_heuristica`, `sem_espelhos`, `sem_todos`, `sem_locus_externo` — achado NÃO robusto à composição da amostra.

## 5. Faltantes: taxonomia e sensibilidade de imputação

D3 informativo (silêncio observado): 3 repos; omissão vs imputação de pior caso na 1ª resposta: ρ = 1.000, deslocamento máximo de 7 posições.

| arquétipo | média (omissão) | média (imputação) |
|---|---|---|
| federation | 79.4 | 79.4 |
| stadium | 44.5 | 44.5 |
| club | 72.9 | 72.9 |
| toy | 32.9 | 32.7 |

## 6. Cobertura do Scorecard (ausência estrutural)

Cobertos n=53 (score médio 60.8), não cobertos n=47 (score médio 53.6); Mann–Whitney sobre o score: p = 0.17 (sem evidência de que a subamostra coberta seja melhor no score).

Cobertos por arquétipo: federation 15, stadium 21, club 12, toy 5.

## 7. Triagem de inflação de stars

| repo | arquétipo | stars | forks | stars/fork | mediana do estrato | stars/contrib. ativo |
|---|---|---|---|---|---|---|
| yolfinance/yolfi-agent | toy | 207 | 1 | 207.0 | 7.7 | 104 |

Sinal de plausibilidade (razão >5× a mediana do estrato) — inspecionar manualmente; não é prova de manipulação.

## 8. Valores de referência por arquétipo (quartis)

Leitura correta: comparar um repositório com os quartis do SEU arquétipo — nunca o número absoluto isolado.

| arquétipo | Q1 | mediana | Q3 |
|---|---|---|---|
| federation | 72.7 | 82.1 | 86.7 |
| stadium | 34.0 | 44.3 | 56.8 |
| club | 62.3 | 75.5 | 82.6 |
| toy | 24.7 | 32.0 | 42.1 |
