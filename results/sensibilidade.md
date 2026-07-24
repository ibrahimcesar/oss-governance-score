# Análise de sensibilidade dos pesos (item 6; plano §4.3)

n = 100 repositórios; pesos base da literatura: artifacts 0.25, distribution 0.25, responsiveness 0.20, diversity 0.15, security 0.15

## Resultados

- **Pesos iguais vs literatura:** ρ = 0.996
- **Perturbação ±25%:** ρ mínimo = 0.998, médio = 0.999 ✅ (critério DSR: ≥ 0,8)
- **W de Kendall** (base + 10 variantes, n = 100 sem faltantes; sem correção de empates): 0.998

## Perturbação por dimensão (ρ vs base)

| variante | ρ |
|---|---|
| artifacts +25% | 0.999 |
| artifacts -25% | 0.999 |
| distribution +25% | 0.999 |
| distribution -25% | 0.998 |
| responsiveness +25% | 0.999 |
| responsiveness -25% | 0.999 |
| diversity +25% | 1.000 |
| diversity -25% | 0.999 |
| security +25% | 0.998 |
| security -25% | 0.999 |

## Leave-one-dimension-out (ρ vs base)

| dimensão removida | ρ |
|---|---|
| artifacts | 0.981 |
| distribution | 0.935 |
| responsiveness | 0.982 |
| diversity | 0.992 |
| security | 0.980 |

A dimensão cuja remoção mais altera o ranking é **distribution** (ρ = 0.935). Interpretação: é a dimensão menos redundante em relação às demais neste dataset — sua contribuição ao ranking é a que menos se recupera a partir das outras —, efeito parcialmente confundido com o peso da dimensão no índice. O desenho não permite concluir que seja a "mais informativa" sobre governança: uma dimensão ruidosa também deslocaria o ranking ao ser removida.
