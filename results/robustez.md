# Robustez e validade adicional (pós-revisão adversarial)

## 1. Sensibilidade dos limiares de normalização

Perturbação de best/worst por métrica (individual) e conjunta; ρ do ranking vs base. Pesos intocados.

| perturbação | ρ mín (por métrica) | ρ médio | pior variante | conjunta + | conjunta − |
|---|---|---|---|---|---|
| ±25% | 0.999 | 1.000 | truck_factor -25% | 0.997 | 0.996 |
| ±50% | 0.996 | 0.999 | truck_factor -50% | 0.989 | 0.989 |

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

ρ do score cheio = 0.750; ρ do composto social D2/D3/D4 = 0.626 (n = 53). Teste de Steiger para correlações dependentes (aproximação sobre Spearman): z = 2.99, p = 0.0028 — as dimensões sociais medem construto distinto do Scorecard.

| dimensão | ρ vs Scorecard |
|---|---|
| artifacts | 0.560 |
| distribution | 0.580 |
| responsiveness | 0.497 |
| diversity | 0.497 |
| security | 0.588 |

## 4. Robustez à exclusão de suspeitos de não-software

11 repositórios sinalizados (nome típico de não-software ou nenhuma resposta humana): `AITabby/opencodex`, `Au1rxx/free-vpn-subscriptions`, `EFanZh/LeetCode`, `FFmpeg/FFmpeg`, `MisterBooo/LeetCodeAnimation`, `fustyles/Arduino`, `git/git`, `github/explore`, `gitlabhq/gitlabhq`, `torvalds/linux`, `yolfinance/yolfi-agent`.

- **Estádio × forks**: com suspeitos ρ = -0.455 (n=25); sem suspeitos ρ = -0.456 (n=23). O achado exploratório deve ser reportado com esta análise ao lado.
- Globais sem suspeitos: scorecard ρ=0.738, stars ρ=0.367, forks ρ=0.433.

## 5. Faltantes: taxonomia e sensibilidade de imputação

D3 informativo (silêncio observado): 3 repos; omissão vs imputação de pior caso na 1ª resposta: ρ = 0.999, deslocamento máximo de 9 posições.

| arquétipo | média (omissão) | média (imputação) |
|---|---|---|
| federation | 76.1 | 76.1 |
| stadium | 42.2 | 42.2 |
| club | 70.4 | 70.4 |
| toy | 32.0 | 31.8 |

## 6. Cobertura do Scorecard (ausência estrutural)

Cobertos n=53 (score médio 58.1), não cobertos n=47 (score médio 51.9); Mann–Whitney sobre o score: p = 0.21 (sem evidência de que a subamostra coberta seja melhor no score).

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
| federation | 71.2 | 77.1 | 81.9 |
| stadium | 32.7 | 41.7 | 51.6 |
| club | 61.7 | 75.3 | 79.8 |
| toy | 24.7 | 32.0 | 40.7 |
