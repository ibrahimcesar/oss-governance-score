# Validação externa (item 7; plano §6)

n = 100; α = 0.05 com correção de Holm–Bonferroni na família global (m = 3 testes realizados).

Cautelas de leitura (declarar na 4.3):
- frequência de releases foi excluída do conjunto (insumo de D5 — circularidade); stars/forks são proxies de popularidade e stars estruturou a amostragem (§3.1) — a leitura por arquétipo é a mais limpa para esses indicadores;
- a ausência em dependentes/scorecard é ESTRUTURAL, não aleatória (cobertura de ecossistema do deps.dev; lista de varredura do OpenSSF) — cada ρ refere-se a uma subpopulação distinta e os coeficientes não são diretamente comparáveis entre indicadores;
- épocas: stars/forks do snapshot de extração (2026-07-23→2026-07-24); dependentes/scorecard consultados em 2026-07-24.

## Família global (corrigida)

| indicador | n | ρ | p | p ajustado | significativo |
|---|---|---|---|---|---|
| stars | 100 | 0.403 | 0.0000 | 0.0000 | ✅ |
| forks | 100 | 0.454 | 0.0000 | 0.0000 | ✅ |
| dependents | 5 | 0.462 | — | — | fora da família (n<10) |
| scorecard | 53 | 0.750 | 0.0000 | 0.0000 | ✅ |

Composição do subamostra de dependentes (linguagens com pacote verificado): python 4, typescript 1. Cobertura efetiva de `:dependents` no deps.dev: NPM/CARGO/PYPI (RubyGems e Packagist retornam 404 — verificado empiricamente); Java/MAVEN fora por mapeamento nome→coordenada inviável; Go sem `:dependents`; C/C++ sem ecossistema (§8 do plano). Com n insuficiente, o indicador é reportado apenas descritivamente.

## Por arquétipo (exploratório, n≈25; sem correção; p pela aproximação t do scipy, SUPRIMIDO quando n < 10 — não confiável em amostras pequenas)

### federation

| indicador | n | ρ | p |
|---|---|---|---|
| stars | 25 | 0.026 | 0.9012 |
| forks | 25 | -0.021 | 0.9215 |
| dependents | 2 | — | — |
| scorecard | 15 | 0.544 | 0.0361 |

### stadium

| indicador | n | ρ | p |
|---|---|---|---|
| stars | 25 | -0.125 | 0.5528 |
| forks | 25 | -0.455 | 0.0222 |
| dependents | 1 | — | — |
| scorecard | 21 | 0.808 | 0.0000 |

### club

| indicador | n | ρ | p |
|---|---|---|---|
| stars | 25 | 0.212 | 0.3101 |
| forks | 25 | 0.298 | 0.1473 |
| dependents | 2 | — | — |
| scorecard | 12 | 0.585 | 0.0459 |

### toy

| indicador | n | ρ | p |
|---|---|---|---|
| stars | 25 | -0.070 | 0.7395 |
| forks | 25 | 0.327 | 0.1105 |
| dependents | 0 | — | — |
| scorecard | 5 | 0.900 | — |

Poder estatístico (Spearman bicaudal, α = 0,05, ~80%): ρ ≈ 0,28 para indicadores com n = 100 (stars/forks); a exclusão par a par reduz o poder (ex.: n ≈ 55 → ρ ≈ 0,38) e o passo mais rigoroso de Holm testa a α/m (n = 100 → ρ ≈ 0,34) — declarar ao interpretar não-significâncias (§6.2).
