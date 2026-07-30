# Rascunho — Seções 4.2 e 4.3 do TCC

> Rascunho para a monografia, gerado a partir dos artefatos versionados do
> repositório (`results/`, `figures/`, `docs/decisions/`). Cada número tem
> fonte indicada em comentário; figuras referenciadas pelo arquivo em
> `figures/` (PNG para visualização, PDF vetorial para o texto).

---

## 4.2 Criação do algoritmo

### 4.2.1 Catálogo final de métricas

A Etapa 2 do método operacionalizou as cinco dimensões teóricas da seção 4.1
em um catálogo de métricas extraíveis (`config/metrics.yaml`), com limiares
de normalização **absolutos** — e não mín–máx amostral — ancorados na
literatura (GOGGINS et al., 2021; COELHO; VALENTE, 2017; AVELINO et al.,
2016), para que o score seja interpretável fora da amostra e cumpra o
objetivo de propor valores de referência. Os pesos iniciais seguiram a centralidade
de cada dimensão na literatura: D1 artefatos 0,25; D2 distribuição 0,25;
D3 responsividade 0,20; D4 diversidade 0,15; D5 segurança 0,15.

A fase piloto (um repositório por arquétipo) motivou uma expansão registrada
do catálogo antes do seu congelamento (registro de decisão de 19/07/2026):
tempo até a primeira resposta em issues — métrica CHAOSS *Time to First
Response* (GOGGINS et al., 2021) — em substituição ao tempo de fechamento,
que confunde atenção do mantenedor com dificuldade da issue; cobertura de
revisão de PRs (CHAOSS *Review Coverage*); *elephant factor* por domínio de
e-mail como proxy de diversidade organizacional; retenção de contribuidores
entre as metades da janela de 12 meses (CONSTANTINOU; MENS, 2017); presença
de FUNDING.yml (OVERNEY et al., 2020); e a proporção de releases com notas
não vazias. Métricas faltantes são omitidas da média da dimensão — nunca
imputadas como zero — e os pesos são renormalizados sobre as dimensões
disponíveis.

O score é um **índice formativo**: as métricas *constituem* o construto
de governança observável, e não o refletem como manifestações
intercambiáveis (BOLLEN; LENNOX, 1991; DIAMANTOPOULOS; WINKLHOFER, 2001).
Disso decorrem duas consequências de avaliação: consistência interna não
é requisito de índices formativos (ainda assim, o α de Cronbach dos cinco
sub-scores é 0,80, n = 96, reportado como resposta secundária); e as
preocupações pertinentes são a colinearidade entre componentes — tratada
na seção 4.2.6 — e a cobertura de conteúdo das dimensões, ancorada na
revisão da seção 4.1.

### 4.2.2 Achados do piloto que moldaram a extração

Quatro achados do piloto tornaram-se decisões de engenharia com implicação
metodológica, e merecem registro por afetarem a validade de construto:

1. **Herança de arquivos de comunidade.** Repositórios herdam CONTRIBUTING,
   código de conduta, SECURITY e templates do repositório especial
   `{organização}/.github` (*default community health files*). O caso real:
   `expressjs/express` não mantém política de segurança no próprio
   repositório — herda-a de `expressjs/.github`. Sem tratamento explícito
   dessa herança, D1 e D5 seriam sistematicamente subestimados.
2. **Limites do endpoint `community/profile`.** A API do GitHub não expõe a
   política de segurança nesse endpoint; a verificação exigiu consulta
   direta às convenções de caminho (raiz, `.github/`, `docs/`), com o
   fallback de herança organizacional.
3. **Infraestrutura própria é invisível a checagens convencionais.** O
   `kubernetes/kubernetes` usa Prow como CI e arquivos OWNERS em vez de
   CODEOWNERS; checagens baseadas nas convenções do GitHub subestimam a
   governança de Federações com tooling próprio — limitação declarada, não
   corrigível sem regras ad hoc que comprometeriam a replicabilidade.
4. **Monorepos inflacionam checagens por caminho.** Padrões não ancorados
   casavam artefatos de dependências vendorizadas (`vendor/**/.circleci/`);
   a correção ancora os padrões à raiz do repositório.

### 4.2.3 Amostra estratificada

A amostragem operacionalizou os quatro arquétipos de Asparouhova (2020)
pelos proxies e limiares da seção 3.1 — contribuidores com ≥2 commits em 12
meses (bots excluídos) cruzados com a base de usuários (stars) — sobre um
universo da Search API estratificado por faixa de stars e dez linguagens,
com exclusão de repositórios que não são software por tópicos e padrões de
nome. Conforme a correção metodológica da seção 3.2.2, a presença de
artefatos de governança **não** foi critério de inclusão (é parte da
variável dependente); os critérios de inclusão foram repositório público e
≥1 commit no branch default na janela, com triagem adicional de forks,
arquivados, templates, mirrors e repositórios sem linguagem detectada. A
Figura `fig_amostra_classificacao` apresenta os 100 selecionados (25 por
arquétipo) sobre as regiões da matriz de classificação, tendo como contexto
os 394 candidatos fora das faixas ou com contagem truncada; o registro
completo em `config/sample_full.yaml` documenta 406 casos ambíguos
(incluindo 12 excluídos por inatividade no branch default) para inspeção
manual.

Três vieses amostrais são declarados: (i) o piso pragmático de 5 stars no
estrato Brinquedo (repositórios com ~0 stars são indescobríveis na Search
API); (ii) a concentração dos Clubes próximo ao teto de 5.000 stars,
consequência da ordenação por stars na busca — na prática, os 25 Clubes
foram amostrados entre 4.724 e 4.997 stars, 6% da banda nominal
(500–4.999), de modo que as leituras sobre o arquétipo descrevem o topo
da banda de nicho; (iii) a contagem de
contribuidores de Federações é um piso (interrompida ao confirmar o limiar
de 100). Os quatro pilotos ficaram fora da amostra completa por terem
calibrado o pipeline.

### 4.2.4 Extração completa e qualidade do dataset

A extração dos 100 repositórios ocorreu em 23–24/07/2026 (janela inferior a
uma semana, requisito de comparabilidade), no modo que combina API REST +
GraphQL (D1, D3, D5, releases) e clone raso do git (D2 e D4 na janela de 12
meses), com cache integral das respostas brutas e retomada ponto a ponto —
100 sucessos, nenhuma falha. O controle de qualidade (`results/
qa_extracao.md`) reporta as métricas faltantes — as maiores: proporção de
releases com notas (26%, repositórios sem release na janela), tempo de
fechamento de issues (14%, métrica extraída para comparabilidade com o
piloto mas fora do score), retenção (12%), e primeira resposta e tempo de
merge de PRs (10% cada) — que, pela regra do método, são omitidas e nunca
imputadas. Nenhum identificador
de contribuidor integra os artefatos processados, que contêm apenas
agregados.

A ausência tem duas naturezas, distinguidas caso a caso: **estrutural**
(prática não observável — repositórios sem release na janela; sem issues
na plataforma, 7 casos) e **informativa** (silêncio observado: issues
existem e nenhuma recebeu resposta humana — 3 casos). Para os casos
informativos, a regra de omissão foi submetida a sensibilidade contra a
imputação de pior caso: ρ = 0,999 entre os rankings, deslocamento máximo
de 9 posições e médias por arquétipo praticamente inalteradas
(`results/robustez.md`). Quatro repositórios — entre eles
`torvalds/linux` e `FFmpeg/FFmpeg`, espelhos com processo fora das issues
do GitHub — são pontuados sobre quatro dimensões; a comparabilidade é
discutida nas limitações.

### 4.2.5 Distribuição do score por arquétipo

A Figura `fig_score_boxplot` e a Tabela de estatística descritiva
(`results/tabelas_tcc.md`) resumem o resultado central da Etapa 2:

| Arquétipo | n | média | mediana | dp | mín–máx |
|---|---|---|---|---|---|
| Federação | 25 | 76,1 | 77,1 | 9,9 | 56,9–94,6 |
| Clube | 25 | 70,4 | 75,3 | 12,7 | 39,1–85,7 |
| Estádio | 25 | 42,2 | 41,7 | 13,7 | 15,9–66,2 |
| Brinquedo | 25 | 32,0 | 32,0 | 12,6 | 6,5–59,4 |

A ordenação é coerente com a teoria: Federações e Clubes — arquétipos de
base contributiva ampla — pontuam alto; Estádios, por definição centrados
em núcleos pequenos de manutenção, pontuam baixo nas dimensões de
distribuição e diversidade mesmo quando bem documentados; Brinquedos exibem
pouca governança formal. Uma cautela de leitura: parte dessa ordenação é
analítica, não empírica — a classificação de arquétipos usa a contagem de
contribuidores ativos, da qual D2 e D4 também derivam, de modo que estratos
de núcleo pequeno pontuarem baixo nessas dimensões é, em parte, garantido
por construção; a evidência não mecânica está nas dimensões D1, D3 e D5 e
na variância intra-estrato. Quantificada: o score restrito a D1/D3/D5
(pesos renormalizados) preserva a separação entre estratos de alta e
baixa contribuição (Federação 66,3 e Clube 67,0 contra Estádio 53,7 e
Brinquedo 41,8), mas não a ordem Federação–Clube — que depende das
dimensões ligadas à classificação e deve ser lida com essa reserva. A variância intra-arquétipo é não trivial (desvios
de 9,9 a 13,7), satisfazendo o critério de capacidade discriminante do
desenho DSR (seção 6.3 do plano): o instrumento diferencia repositórios
*dentro* de cada arquétipo, não apenas entre arquétipos.

### 4.2.6 Correlações entre dimensões

O heatmap de Spearman entre os sub-scores (Figura `fig_dimensoes_heatmap`)
mostra correlações moderadas entre dimensões (0,32 a 0,51), com uma
exceção: D2 distribuição × D4 diversidade, ρ = 0,87. A redundância parcial
é esperada — ambas derivam da distribuição de commits na janela — e é
declarada como limitação de independência entre dimensões, dialogando com a
análise de sensibilidade a seguir.

### 4.2.7 Análise de sensibilidade dos pesos

Conforme a seção 3.2.2, o ranking foi submetido a três verificações
(`results/sensibilidade.md`): pesos iguais versus pesos da literatura
(ρ = 0,996); perturbação de ±25% em cada peso com renormalização (ρ mínimo
de 0,998 entre as dez variantes; W de Kendall de 0,998 entre as onze
ordenações); e *leave-one-dimension-out* (ρ ≥ 0,935 em todas as remoções).
O critério de estabilidade do desenho (ρ ≥ 0,8) é satisfeito com folga: o
ranking mostra-se insensível às variações de ponderação examinadas —
argumento central para a defesa da ponderação proposta, dentro do espaço
de variantes testado. A dimensão cuja remoção mais altera o
ranking é a distribuição (ρ = 0,935), o que indica ser a *menos redundante*
em relação às demais neste dataset; o desenho não permite concluir que seja
a "mais informativa" sobre governança, pois uma dimensão ruidosa também
deslocaria o ranking ao ser removida, e o efeito é parcialmente confundido
com o peso da dimensão.

A verificação análoga para os **limiares** foi executada sobre os dados
extraídos (`results/robustez.md`): perturbar os limiares de normalização
de cada métrica contínua em ±25% e ±50% — individualmente e em conjunto —
mantém ρ ≥ 0,996 e ρ ≥ 0,989, respectivamente; e reclassificar a amostra
com os limiares de classificação da §3.1 variados em ±50% não move nenhum
repositório de um arquétipo para outro: os casos afetados saem das faixas
(tornam-se não classificados), funcionando as zonas deliberadamente
vazias da matriz como amortecimento. Ressalva declarada: elevar o limiar
de Federação é intestável, pois as contagens de contribuidores são pisos
(interrompidas ao confirmar o limiar). Em conjunto com a sensibilidade de
pesos, o ranking mostra-se robusto às duas famílias de decisões
discricionárias do catálogo.

---

## 4.3 Validação do algoritmo

### 4.3.1 Desenho da validação

A Etapa 3 correlacionou o score com indicadores externos **não utilizados
no seu cálculo**: stars e forks (metadata do snapshot de extração), número
de dependentes (API deps.dev, com verificação de que o pacote pertence ao
repositório) e o OpenSSF Scorecard. A frequência de releases, listada
originalmente como indicador de validação, foi **excluída do conjunto** por
circularidade: é insumo da dimensão D5 desde o catálogo — correção
metodológica registrada. Utilizou-se ρ de Spearman (adequado à natureza
ordinal e robusto às caudas pesadas do GitHub), α = 0,05, com correção de
Holm–Bonferroni na família global de testes; testes com n < 10 pares
válidos ficam fora da família e são reportados apenas descritivamente,
pois a aproximação t do p-valor não é confiável em amostras pequenas.

O poder estatístico é declarado por indicador: com n = 100 detecta-se
ρ ≈ 0,28 com ~80% de poder; a exclusão par a par reduz o poder (n ≈ 55 →
ρ ≈ 0,38) e o passo mais rigoroso da correção testa a α/m (ρ ≈ 0,34 com
n = 100). A ausência de dados em dependentes e Scorecard é **estrutural**
(cobertura de ecossistemas do deps.dev; lista de varredura do OpenSSF), e
não aleatória: cada coeficiente refere-se a uma subpopulação distinta e os
coeficientes não são diretamente comparáveis entre indicadores.

### 4.3.2 Resultados globais

| Indicador | n | ρ | p ajustado | Interpretação |
|---|---|---|---|---|
| OpenSSF Scorecard | 53 | 0,750 | <0,001 | validade convergente forte |
| Forks | 100 | 0,454 | <0,001 | popularidade, moderada |
| Stars | 100 | 0,403 | <0,001 | popularidade, moderada |
| Dependentes | 5 | 0,462 | — | sem poder (fora da família) |

Os três indicadores testáveis são significativos na direção esperada após a
correção — o critério de sucesso do desenho (correlação significativa com
≥ 2 indicadores externos) é satisfeito. A correlação forte com o Scorecard
(Figura `fig_validacao_scatters`) é o resultado de validade convergente: um
instrumento independente e consolidado, cuja sobreposição com o score
abrange a dimensão D5 (política de segurança, CI e automação de
dependências), a prática de revisão de código e a presença de licença (D1),
permanecendo independente nas dimensões sociais e organizacionais (D2, D3
em primeira resposta, D4), ordena os repositórios de forma amplamente
compatível. As correlações moderadas
com stars e forks correspondem à expectativa teórica de que popularidade e
saúde de governança são construtos relacionados porém distintos — o
resultado *desejável* para proxies declaradamente fracos; nota-se ainda que
stars estruturou a estratificação amostral, o que torna a leitura global
desse indicador parcialmente artefactual e reforça a preferência pela
leitura por arquétipo.

O indicador conceitualmente mais forte — adoção real por terceiros — ficou
sem poder estatístico: a cobertura efetiva de dependentes do deps.dev
restringe-se aos ecossistemas NPM, Cargo e PyPI (RubyGems e Packagist não
expõem o endpoint; Java/Maven é inviável pelo mapeamento de coordenadas;
Go, C e C++ ficam fora), e a maior parte da amostra não teve pacote
verificado no deps.dev — seja por não publicar pacote, seja por o nome do
pacote não ser derivável do nome do repositório (heurística com até cinco
candidatos) —, restando n = 5 pacotes verificados. A limitação era antecipada
pelo plano de riscos e fica declarada; releases e dependentes constituem
trabalho futuro com fontes complementares (ex.: contagem de *used by* da
própria plataforma).

### 4.3.3 Validade discriminante

Se o score apenas replicasse o Scorecard, sua contribuição seria
redundante frente a um instrumento gratuito e mantido pela Linux
Foundation. A análise discriminante afasta essa leitura (Figura
`fig_validade_discriminante`; `results/robustez.md`): o composto restrito
às dimensões sociais e organizacionais (D2/D3/D4, pesos renormalizados)
correlaciona 0,626 com o Scorecard — significativamente menos que os
0,750 do agregado (teste de Steiger para correlações dependentes,
z = 2,99, p = 0,003; aproximação sobre ρ de Spearman) — e nenhuma
dimensão isolada excede 0,588. O instrumento posiciona-se, portanto, como
**complementar** ao Scorecard, não substituto: mede continuidade
organizacional (concentração de conhecimento, responsividade,
diversidade, retenção) que o Scorecard não cobre, além de alcançar os 47
repositórios da amostra fora da varredura dele (o pipeline roda em
qualquer repositório público). Registra-se a leitura simétrica: nos
critérios externos disponíveis (popularidade), nenhum dos dois
instrumentos demonstra poder preditivo incremental sobre o outro — a
separação está no construto medido, não na predição.

### 4.3.4 Análise por arquétipo (exploratória)

Nas correlações intra-arquétipo (n = 25 por estrato para stars e forks;
para o Scorecard, n varia de 5 a 21; sem correção, poder apenas para
efeitos grandes), o Scorecard mantém associação positiva em
todos os estratos (ρ de 0,544 na Federação a 0,808 no Estádio, nominais;
0,900 no Brinquedo com apenas n = 5). Stars e forks, por sua vez, perdem
associação dentro dos estratos — consequência esperada da restrição de
amplitude imposta pela própria estratificação —, com um resultado
exploratório digno de nota: no arquétipo Estádio, forks correlaciona
**negativamente** com o score (ρ = −0,455, p nominal = 0,022). A leitura
teórica é sugestiva: nos projetos de base de usuários massiva e núcleo
pequeno de mantenedores, mais forks podem sinalizar demanda não atendida
pelo processo de contribuição — exatamente a tensão que Asparouhova (2020)
descreve para o arquétipo — mas, sem correção para múltiplas comparações e
com desenho transversal, o achado deve ser tratado como hipótese para
trabalhos futuros, não como conclusão. Duas verificações o qualificam
(`results/robustez.md`): o achado sobrevive à exclusão dos 11
repositórios suspeitos de não-software sinalizados para inspeção manual
(ρ = −0,456, n = 23), afastando a hipótese de artefato de contaminação
amostral; e permanece a explicação alternativa de forks como marcador
(*bookmark*) sem intenção de contribuição. Para os Clubes, amostrados no
topo da banda de nicho (seção 4.2.3), a restrição de amplitude é ainda
mais severa e limita qualquer leitura intra-estrato.

### 4.3.5 Critérios de avaliação do artefato

Retomando os critérios DSR definidos no desenho (HEVNER et al., 2004):
(i) correlações significativas e na direção esperada com pelo menos dois
indicadores externos — satisfeito (três de três testáveis); (ii)
estabilidade do ranking sob análise de sensibilidade (ρ ≥ 0,8 entre
variantes de pesos) — satisfeito com ρ mínimo de 0,998 na perturbação e
0,935 no leave-one-dimension-out; (iii) capacidade discriminante —
satisfeito, com variância intra-arquétipo não trivial em todos os estratos.
Na taxonomia de avaliação em DSR, esta é uma avaliação *ex ante* e
artificial (VENABLE; PRIES-HEJE; BASKERVILLE, 2016): valida propriedades
técnicas do artefato sem observação de uso real. A avaliação
naturalística — o instrumento apoiando decisões de gestores — permanece
como etapa futura, coerente com o escopo do trabalho.

### 4.3.6 Implicações para a gestão

Três cenários de decisão ilustram o uso do instrumento por organizações
que consomem ou mantêm software open source:

1. **Due diligence de dependências.** Na triagem de bibliotecas
   candidatas, o score complementa a verificação de práticas de segurança
   (Scorecard) com o risco de *continuidade*: dois pacotes funcionalmente
   equivalentes e igualmente seguros podem diferir muito em concentração
   de conhecimento e retenção de contribuidores — exatamente as dimensões
   que a seção 4.3.3 mostra não serem capturadas pelo Scorecard.
2. **Monitoramento de portfólio por um OSPO.** Um *Open Source Program
   Office* pode acompanhar periodicamente os scores das dependências
   críticas; deterioração em responsividade (D3) e retenção (D4) antecipa
   risco de abandono antes que ele apareça em indicadores de
   popularidade, que são defasados.
3. **Risco de cadeia de suprimentos de software.** Diante de exigências
   crescentes de SBOM e avaliação de fornecedores, o score oferece um
   critério auditável — código aberto, cache bruto reprodutível,
   limiares e decisões versionados — para classificar componentes por
   risco de governança.

A leitura correta do número é sempre **relativa ao arquétipo**. Os
valores de referência (quartis) são: Federação 71,2 / 77,1 / 81,9;
Clube 61,7 / 75,3 / 79,8; Estádio 32,7 / 41,7 / 51,6; Brinquedo
24,7 / 32,0 / 40,7. Um Estádio com score 55 está acima do terceiro
quartil do seu arquétipo; o mesmo 55 numa Federação estaria abaixo do
primeiro. O caso `torvalds/linux` (56,9) ilustra a contraindicação:
projetos com governança madura fora das convenções do GitHub são
subestimados, e o instrumento não deve ser usado isoladamente para eles.
O custo de execução é baixo: pipeline aberto, extração completa de 100
repositórios em 2–3 horas com um token pessoal de leitura.

### 4.3.7 Limitações

Além das limitações declaradas no desenho (métricas capturam artefatos
observáveis, não a prática vivida; amostra restrita ao GitHub; snapshot
transversal sem inferência causal; limiares e pesos fundamentados porém
discricionários — a discricionariedade dos **pesos** e a dos **limiares**
foram mitigadas por análises de sensibilidade independentes: ρ ≥ 0,935
entre variantes de pesos e ρ ≥ 0,989 sob perturbação conjunta de limiares
em ±50%, sem nenhuma troca de arquétipo na reclassificação ±50%, seção
4.2.7), a execução acrescentou:
(i) infraestrutura de governança fora das convenções do GitHub é
subestimada (caso Kubernetes/Prow); (ii) a heurística de login para bots
erra nas duas direções — pode reter bots não convencionais e pode tratar
como bot logins humanos terminados em "bot", suprimindo respostas humanas
em D3 (falso positivo aceito em registro de decisão); (iii) a ausência estrutural em
dependentes/Scorecard restringe as subpopulações validadas; (iv) stars
participou da classificação amostral, contaminando parcialmente sua
leitura como indicador global; (v) épocas distintas entre o snapshot de
extração (23–24/07/2026) e a consulta aos indicadores externos
(24/07/2026), registradas nos artefatos.
