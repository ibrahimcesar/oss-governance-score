# Kit de defesa — Q&A antecipado da banca

> Preparado a partir do painel adversarial (20 críticas julgadas,
> `docs/revisao_adversarial_estudo.md`) e das análises de resposta
> (`results/robustez.md`). Cada resposta cita a fonte do número — tudo é
> regenerável pelos comandos do README.

---

## Mensagens-âncora (30 segundos)

Um algoritmo aberto e reprodutível que mede governança observável de
repositórios OSS em 5 dimensões, aplicado a 100 repositórios
estratificados pelos arquétipos de Asparouhova. Três resultados:
**discrimina** (medianas de 77,1 nas Federações a 32,0 nos Brinquedos,
com variância intra-estrato), **é robusto** (ρ ≥ 0,935 sob variação de
pesos E limiares; nenhuma troca de arquétipo sob reclassificação ±50%) e
**converge sem ser redundante** (ρ = 0,750 com o OpenSSF Scorecard, mas
as dimensões sociais medem construto distinto — Steiger p = 0,003).

## Os três números que sustentam tudo

| Afirmação | Número | Fonte |
|---|---|---|
| Validade convergente | ρ = 0,750 (n=53, p aj. < 0,001) | `results/validacao.md` |
| Não-redundância | composto social 0,626 < 0,750 (Steiger z=2,99, p=0,003) | `results/robustez.md` §3 |
| Robustez total | pesos ρ≥0,935 · limiares ρ≥0,989 · reclassificação: 0 trocas | `results/sensibilidade.md`, `robustez.md` §1–2 |

---

## A. Contribuição e posicionamento

**A1. "Com ρ=0,75 contra o Scorecard, você não reinventou uma ferramenta
gratuita da Linux Foundation?"**
Não — e o dado mostra. O composto restrito às dimensões sociais
(D2/D3/D4) correlaciona 0,626 com o Scorecard, significativamente menos
que o agregado (Steiger p=0,003), e nenhuma dimensão isolada passa de
0,588. O Scorecard mede práticas de segurança; este instrumento mede
**continuidade organizacional** — concentração, responsividade,
diversidade, retenção — que ele não cobre. E alcança os 47 repositórios
da amostra fora da varredura do OpenSSF: o pipeline roda em qualquer
repositório público. Posicionamento: complementar, não substituto.
*(Fonte: robustez.md §3; figura fig_validade_discriminante.)*

**A2. "O que isso acrescenta ao CHAOSS?"**
O CHAOSS define métricas; não define agregação, limiares de referência
nem validação. A contribuição é o *artefato DSR completo*: catálogo
ponderado ancorado no CHAOSS + normalização por limiares absolutos +
validação externa com correção múltipla + valores de referência por
arquétipo — reprodutível de ponta a ponta.

**A3. "Qual o valor gerencial? Quem decide o quê com isso?"**
Três cenários (seção 4.3.6): due diligence de dependências (risco de
continuidade complementando o de segurança), monitoramento de portfólio
por OSPO (D3/D4 antecipam abandono antes da popularidade cair) e
avaliação de cadeia de suprimentos de software (critério auditável).
Regra de leitura: sempre relativa ao arquétipo, pelos quartis de
referência. Custo: pipeline aberto, ~2–3 h com token pessoal.

## B. Mensuração

**B1. "O índice é formativo ou reflexivo? Cadê o alfa de Cronbach?"**
Formativo: as métricas constituem o construto, não o refletem (BOLLEN;
LENNOX, 1991; DIAMANTOPOULOS; WINKLHOFER, 2001). Consistência interna
não é requisito para índices formativos — as preocupações corretas são
colinearidade (tratada: D2×D4 = 0,87, declarada) e cobertura de conteúdo
(ancorada na revisão). Ainda assim, se quiserem o número: α = 0,80
(n=96).

**B2. "Os pesos são arbitrários."**
São decisões fundamentadas — e quase não importam: pesos iguais vs
literatura dá ρ = 0,996; ±25% em cada peso, ρ mínimo 0,998; W de Kendall
0,998; leave-one-dimension-out ≥ 0,935. O ranking não depende da
ponderação dentro do espaço testado. *(sensibilidade.md)*

**B3. "E os limiares de normalização? Esses sim moldam os sub-scores."**
Perturbados em ±25% e ±50%, por métrica e em conjunto: ρ ≥ 0,996 e
≥ 0,989. E a figura `fig_metricas_limiares` mostra onde os limiares
cortam as distribuições empíricas — eles são anteriores aos dados e
nunca foram ajustados a eles. *(robustez.md §1)*

**B4. "Média simples dentro da dimensão? Renormalizar faltantes muda o
construto entre repos."**
Média simples evita dupla ponderação indefensável. Faltantes: taxonomia
declarada — 7 estruturais (sem issues) e 3 informativos (silêncio
observado); imputar pior caso nos informativos dá ρ = 0,999 e desloca no
máximo 9 posições. Apenas 4 repos são pontuados com 4 dimensões, todos
declarados. *(robustez.md §5)*

## C. Amostra

**C1. "Asparouhova é uma tipologia dinâmica (crescimento); você a reduziu
a um corte transversal."**
Correto e declarado: usamos proxies transversais (ativos 12m × stars)
por replicabilidade. A mitigação é dupla: limiares explícitos
versionados e reclassificação ±50% sem nenhuma troca de arquétipo — a
classificação é estável no espaço de operacionalizações vizinhas.
Medir o crescimento longitudinal é trabalho futuro.

**C2. "Os Clubes estão todos colados em 5.000 stars."**
Verdade e quantificado: 4.724–4.997 stars, 6% da banda nominal —
consequência da ordenação por stars na busca. As leituras sobre Clubes
descrevem o topo da banda de nicho; restrição declarada na 4.2.3 e
reiterada na análise por arquétipo.

**C3. "Tem LeetCode e listas curadas na amostra."**
A triagem automatizada excluiu por tópicos e nomes, e a inspeção manual
documentada (notebook 01) está em curso com 11 sinalizados. A robustez
já foi computada: excluir todos os 11 praticamente não muda nada
(scorecard 0,738; Estádio×forks −0,456). Nenhum resultado central
depende deles. *(robustez.md §4)*

**C4. "Stars podem ser compradas."**
Triagem de plausibilidade executada: um único caso destoante
(yolfi-agent: 207 stars, 1 fork — 27× a mediana do estrato), sinalizado
para inspeção. Os demais 99 têm razões stars/forks dentro do padrão do
estrato. *(robustez.md §7)*

**C5. "Por que os pilotos ficaram fora da amostra?"**
Out-of-sample deliberado: calibraram o pipeline e os achados de extração
(herança de `.github`, caso Prow). Incluí-los contaminaria a avaliação.

## D. Validação

**D1. "Dependentes — o indicador mais forte — deu n=5."**
Limitação antecipada no plano de riscos e declarada: cobertura do
deps.dev restrita a NPM/Cargo/PyPI, e a verificação pacote↔repositório é
conservadora por desenho (evita herdar dependentes de pacote homônimo).
Reportado descritivamente (ρ=0,462), fora da família corrigida. Fontes
complementares são trabalho futuro.

**D2. "A cobertura do Scorecard (53%) não enviesa?"**
A ausência é estrutural (lista de varredura do OpenSSF), não seleção
por qualidade: cobertos e não cobertos não diferem no score
(Mann–Whitney p=0,21). Composição declarada: Federação 15, Estádio 21,
Clube 12, Brinquedo 5. *(robustez.md §6)*

**D3. "Por que excluir frequência de releases da validação?"**
Circularidade: `releases_12m` é insumo de D5 desde o catálogo. Usá-la
dos dois lados inflaria a validação — correção metodológica registrada.

**D4. "Estádio × forks negativo é ruído."**
Tratado como hipótese, não conclusão: exploratório, sem correção,
transversal. Mas sobrevive à exclusão dos suspeitos (−0,456) e tem
leitura teórica na tensão do arquétipo (demanda sem via de
contribuição); a alternativa fork-como-bookmark está declarada.

**D5. "Poder estatístico?"**
Declarado por indicador: n=100 → ρ≈0,28 com 80%; exclusão par a par
reduz (n≈55 → ρ≈0,38); passo mais rígido de Holm → ρ≈0,34. Por
arquétipo (n≈25) só efeitos grandes — por isso é exploratório.

**D6. "A avaliação DSR não tem usuário."**
Correto: é avaliação *ex ante* e artificial na taxonomia de Venable,
Pries-Heje & Baskerville (2016) — valida propriedades técnicas.
Avaliação naturalística com gestores é a continuação natural, fora do
escopo do TCC.

## E. Construto e limitações — concessões preparadas

**E1. "O Linux tem a governança mais madura do planeta e pontua 56,9."**
A concessão certa: o instrumento mede governança *nas convenções do
GitHub*; Federações com infraestrutura própria (Prow, mailing lists) são
subestimadas — limitação de validade de construto declarada e
transformada em regra de uso: contraindicação para projetos com processo
fora da plataforma (seção 4.3.6).

**E2. "D2×D4 = 0,87 — não são a mesma coisa?"**
Redundância parcial esperada (mesma base de commits) e declarada. O LODO
mostra que remover qualquer uma mantém ρ ≥ 0,935. E a interpretação é
disciplinada: distribuição é a *menos redundante*, não "a mais
informativa".

**E3. "Federação > Clube não é garantido por construção?"**
Parcialmente — e o texto diz isso com números: sem D2/D4, Federação 66,3
≈ Clube 67,0; a ordem Federação–Clube depende das dimensões ligadas à
classificação. O que é evidência não mecânica: a separação alto-vs-baixo
contributivo (>12 pontos sobre Estádio/Brinquedo em D1/D3/D5) e a
variância intra-estrato.

**E4. "Bots: sua heurística falha."**
Nas duas direções, declaradas: pode reter bots não convencionais e pode
tratar humanos terminados em "bot" como bots (falso positivo aceito em
registro de decisão). O impacto está limitado a D3/classificação e a
análise de imputação mostra sensibilidade mínima do ranking.

**E5. "Só GitHub, só um snapshot, sem causalidade."**
Tudo declarado no desenho: amostra restrita ao GitHub; corte transversal
— o desenho não estabelece causalidade entre governança e
sustentabilidade; épocas registradas (extração 23–24/07, externos
24/07).

## F. Reprodutibilidade (se perguntarem "como confio nos números?")

Cache bruto integral antes de qualquer análise (a análise nunca
reconsulta a API); hash do código carimbado no QA; decisões de catálogo
com registro datado em `docs/decisions/`; limiares nunca ajustados a
posteriori; zero PII nos artefatos publicados; 66 testes unitários;
`make test && make figures` regenera tudo.

## O que NÃO afirmar (armadilhas)

- ~~"Distribuição é a dimensão mais informativa"~~ → menos redundante.
- ~~"O score prevê sustentabilidade"~~ → desenho transversal; associação.
- ~~"Valores de referência universais"~~ → sempre por arquétipo.
- ~~"O instrumento substitui o Scorecard"~~ → complementar.
- ~~"A amostra representa o OSS"~~ → GitHub, ativos, estratos definidos.
- Comparar scores *entre* arquétipos como se fossem a mesma régua.
