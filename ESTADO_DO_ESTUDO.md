# Estado do estudo — 12/09/2026

**Em uma linha:** a pesquisa está concluída; resta a redação. Os itens 1–10
do plano de código estão fechados. A inspeção manual da amostra, última
pendência de dados, foi concluída hoje.

## Concluído

| Frente | Resultado | Fonte |
|---|---|---|
| Instrumento | 5 dimensões; limiares e pesos congelados após o piloto; mudanças com registro de decisão | `config/metrics.yaml`, `docs/decisions/` |
| Amostra | n = 100 (25 por arquétipo); extração em 23–24/07/2026 com cache integral | `config/sample_full.yaml`, `data/processed/` |
| Inspeção manual | 15 casos limítrofes (8 de conteúdo, 4 espelhos, 3 softwares sem resposta humana); **todos mantidos** | `docs/decisions/2026-09-12-inspecao-manual-amostra.md`, notebook 01 |
| Validação externa | Scorecard ρ = 0,750; forks 0,454; stars 0,403 — todos p_adj < 0,001 (Holm–Bonferroni) | `results/validacao.md` |
| Robustez | pesos ρ ≥ 0,935; limiares ±50% ρ ≥ 0,989; reclassificação ±50% sem trocas de arquétipo; discriminante vs Scorecard (Steiger p = 0,003) | `results/sensibilidade.md`, `results/robustez.md` |
| Cenários de exclusão | correlações globais robustas em todos os cenários (Scorecard 0,725–0,754; stars 0,367–0,442; forks 0,433–0,508) | `results/robustez.md` §4.1 |
| Texto de apoio | rascunho das seções 4.2/4.3; 14 figuras (PNG + PDF); tabelas; kit de defesa; plano de publicação | `docs/`, `figures/`, `results/tabelas_tcc.md` |

## Mudou em 12/09/2026

Os dois achados intra-arquétipo **não são robustos** à composição da amostra:

- **Estádio × forks:** ρ = −0,455 (p = 0,022) cai para −0,257 (p = 0,26)
  sem os 4 repositórios de conteúdo do estrato.
- **Federação × Scorecard:** ρ = 0,544 (p = 0,036) cai para 0,109
  (p = 0,74) sem os 3 espelhos da Federação.

A seção 4.3.4 foi reescrita: os dois resultados passam a ser apresentados
como dependentes da composição da amostra, não como conclusões. As
seções 4.2.3 e 4.3.7 (limitações vi e vii), o kit de defesa e o plano de
publicação foram atualizados de acordo.

## Pendências de redação (críticas da revisão adversarial ausentes do rascunho)

| Item | Custo |
|---|---|
| Vieses da amostragem de D3: últimas 50 issues fechadas, sem janela de 12 meses, e truncamento em 10 comentários — não declarados | 1 parágrafo |
| Enquadrar o construto como "governança visível na plataforma" — transforma o caso Linux em discussão de construto declarado | 1 parágrafo |
| Inflação de stars ausente da 4.3.7 (`affaan-m/ECC` e `garrytan/gstack` apontados na revisão; a triagem só sinalizou `yolfinance/yolfi-agent`) | 1 parágrafo |
| Citar Munaiah et al. (2017, *reaper*) como referência de critérios para excluir não-software | 1 citação |
| Rodar o Scorecard CLI nos 47 repositórios fora da varredura pública | dados novos; opcional |
| Validade de face: leitura humana estruturada de ~10 repositórios (top-5, bottom-5, maiores discordâncias com o Scorecard) | dados novos; opcional (ou declarar como limitação) |

Já cobertos no rascunho: validade incremental, sobreposição de licença com
o Scorecard, quartis de referência por arquétipo e reclassificação.

## Texto final (12/09/2026)

Monografia completa montada em `monografia/` (pasta ignorada pelo git):
capítulos 1–3 e 4.1 da VERSÃO 2 (Google Doc), 4.2/4.3 e conclusão
novos, capítulo 3 reescrito do plano para o método executado. As quatro
pendências de redação de 1 parágrafo acima estão incorporadas na 4.2/4.3.
Compila em abnTeX2 (31 páginas) e converte para Word com citações ABNT.
Restam: revisão do resumo e do capítulo 3 com o orientador; venue de
`he2024fakestars`; template Word do departamento para o docx.

## Catálogo v2 — reparo de D1/D5 (13/09/2026)

Defeito de medição confirmado (perfil comunitário cego a
`.github/ISSUE_TEMPLATE/`; CODEOWNERS/GOVERNANCE em caminho único; `contents`
sensível a caixa; herança org incompleta; só GitHub Actions/Dependabot) e
reparado por re-medição dos 12 binários na árvore do commit *first-parent* na
época da sondagem v1 (git apenas, 0 chamadas à API; regras fixadas antes da
re-pontuação; `docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md`).

| resultado | v1 | v2 |
|---|---|---|
| trocas | — | 78 F→T em 63 repos; 0 T→F; ρ v1×v2 = 0,997 |
| medianas Fed / Clube / Estádio / Brinquedo | 77,1 / 75,3 / 41,7 / 32,0 | 82,1 / 75,5 / 44,3 / 32,0 |
| Scorecard (API-53) / forks / stars | 0,750 / 0,454 / 0,403 | 0,770 / 0,463 / 0,411 |
| discriminante (composto social; Steiger) | 0,626; p = 0,003 | 0,626; p = 0,001 |
| pesos (LODO mín.) / limiares ±50% | 0,935 / 0,989 | 0,939 / 0,991 |
| Estádio×forks sem conteúdo | −0,257 (p = 0,26) | −0,313 (p = 0,17) |
| Scorecard CLI nos 100 (secundária, época 09/2026) | — | ρ = 0,616 (n = 100); 0,271 sem checks sobrepostos |

Saídas v1 arquivadas (`data/processed/v1/`, `results/v1/`, `figures/v1/`);
comparação em `results/reparo_v1_v2.md`. Monografia atualizada com os números
v2 e nova seção 4.2.5 (reparo). Deferido: v3 (D3 em janela fixa) com registro
próprio; regra de locus e Scorecard CLI ficaram como instrumentos descritivos.

## Fora deste repositório

- **Demais capítulos** (1–3, 4.1 e conclusão): no Claude Project "TCC". O
  estado deles não é rastreado aqui.
- **Publicação:** DOI via Zenodo e dataset (agregados, sem PII) ficam para
  depois da defesa — ver `docs/plano_publicacao.md`.
