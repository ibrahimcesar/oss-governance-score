# Exploração pós-estudo (13/09/2026)

Pergunta do autor: *há como melhorar o estudo? existe algo "groundbreaking"?
o que pode ser expresso em teoria das categorias?*

Processo: 44 agentes — mapa do estudo e do repo `categories-of-the-commons`;
8 ângulos independentes (configuracional/QCA, teoria da medida, causal/
longitudinal, redes, teoria das categorias aplicada, Ostrom/VSM, ML/escala,
revisor de venue) → 24 ideias → 10 direções → 3 refutadores adversariais por
direção (novidade, viabilidade com estes dados, rigor) → síntese + nota
formal + crítico de completude. Resultado: **1 de 10 direções sobreviveu
intacta** (C1, escada/reticulado de práticas); as demais entram como versões
reduzidas ("salvage") ou foram refutadas.

| arquivo | conteúdo |
|---|---|
| `relatorio_exploratorio.md` | veredito, Tier A (antes da defesa), Tier B (paper), Tier C (moonshots), refutados, TC load-bearing, questões abertas |
| `nota_teoria_das_categorias.md` | formalizações que compram algo (4 leis), decorativas (não usar), ponte com categories-of-the-commons |
| `critica_de_completude.md` | o que está errado/faltando nos dois documentos acima — **ler antes de agir** |

## Verificações feitas pelo autor-assistente após o crítico (dados reais)

| afirmação | verificado | consequência |
|---|---|---|
| `issue_template` = True em só 5/100; `nodejs/node` tem `issue_template: null` no `community_profile` embora tenha `.github/ISSUE_TEMPLATE/` | **confirmado** | defeito de medição em D1 (endpoint só vê o template legado de arquivo único); CODEOWNERS só em `.github/`, GOVERNANCE só na raiz (2/100). Decisão necessária: errata (registro de decisão, snapshot congelado) ou reparo (~300 chamadas à API, viola "nunca reconsulta") |
| A1: baseline de tamanho S0 = ajuste LOO de rank(score) ~ rank(log contribuidores_5+), rank(HHI) | ρ(S0, score) = 0,894; ρ(S0, Scorecard) = 0,652 vs 0,750 do score; médias por arquétipo 80/68/40/33 vs 76/70/42/32 | a versão do relatório (82/63/34/23; "gap Federação–Clube colapsa") está **errada**; a do crítico está certa. Validade incremental da camada de práticas: parcial com Scorecard dado tamanho = 0,53 (bruta 0,71) |
| A2: envelope de gaming (12 binárias → 1) | medianas fed 13,9 / stadium 16,9 / club 14,1 / toy 25,4 pontos | reproduzido, mas **inflado** pelo defeito de `issue_template` (95 repos ganham 2,78 "de graça") — recalcular após a decisão da errata |
| Entropia de commits por arquétipo | Federação 0,695 > Estádio 0,425 | a seta Federação→Estádio do framework CotC falha a checagem de monotonicidade também nestes dados |
| Loevinger H, locus 8/93, "silêncio paga" 22/96, probabilidades (0,35/0,5/0,2) | **não verificados** | tratar como estimativas dos agentes |

## Guardrails do estudo (não violar ao executar qualquer item)

- não ajustar limiares para "melhorar" resultados (Tier C "ancoragem
  comportamental" só como v2 declarada);
- não filtrar a amostra por artefatos de governança;
- stars/forks são proxies de popularidade — não reportar parciais com eles
  como achados;
- a análise nunca reconsulta a API (reparo do `issue_template` exige registro
  de decisão explícito como v2 do catálogo).
