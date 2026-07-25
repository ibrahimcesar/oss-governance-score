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
consequência da ordenação por stars na busca; (iii) a contagem de
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
na variância intra-estrato. A variância intra-arquétipo é não trivial (desvios
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
instrumento independente e consolidado, cuja sobreposição conceitual com o
score se restringe à dimensão D5 e à prática de revisão de código, ordena
os repositórios de forma amplamente compatível. As correlações moderadas
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
Go, C e C++ ficam fora), e a maioria da amostra são aplicações sem pacote
publicado, restando n = 5 pacotes verificados. A limitação era antecipada
pelo plano de riscos e fica declarada; releases e dependentes constituem
trabalho futuro com fontes complementares (ex.: contagem de *used by* da
própria plataforma).

### 4.3.3 Análise por arquétipo (exploratória)

Nas correlações intra-arquétipo (n = 25 por estrato, sem correção, poder
apenas para efeitos grandes), o Scorecard mantém associação positiva em
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
trabalhos futuros, não como conclusão.

### 4.3.4 Critérios de avaliação do artefato

Retomando os critérios DSR definidos no desenho (HEVNER et al., 2004):
(i) correlações significativas e na direção esperada com pelo menos dois
indicadores externos — satisfeito (três de três testáveis); (ii)
estabilidade do ranking sob análise de sensibilidade (ρ ≥ 0,8 entre
variantes de pesos) — satisfeito com ρ mínimo de 0,998 na perturbação e
0,935 no leave-one-dimension-out; (iii) capacidade discriminante —
satisfeito, com variância intra-arquétipo não trivial em todos os estratos.

### 4.3.5 Limitações

Além das limitações declaradas no desenho (métricas capturam artefatos
observáveis, não a prática vivida; amostra restrita ao GitHub; snapshot
transversal sem inferência causal; limiares e pesos fundamentados porém
discricionários — mitigados pela sensibilidade), a execução acrescentou:
(i) infraestrutura de governança fora das convenções do GitHub é
subestimada (caso Kubernetes/Prow); (ii) a exclusão de bots por heurística
de login pode reter bots não convencionais; (iii) a ausência estrutural em
dependentes/Scorecard restringe as subpopulações validadas; (iv) stars
participou da classificação amostral, contaminando parcialmente sua
leitura como indicador global; (v) épocas distintas entre o snapshot de
extração (23–24/07/2026) e a consulta aos indicadores externos
(24/07/2026), registradas nos artefatos.
