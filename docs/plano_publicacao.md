# Plano de publicação pós-defesa

Sequência recomendada (cada etapa funciona sozinha; nenhuma cria
obrigação de manutenção antes de haver tração). Congelar tudo até a
defesa.

## 1. Fundação (semana seguinte à defesa — custo baixo)

- [ ] **DOI via Zenodo** para repositório + dataset (`scores.csv`,
      `metrics.parquet`) — citável e permanente. Dataset é publicável por
      construção (agregados, zero PII).
- [ ] **README em inglês** ao lado do PT-BR (público: OSPOs, mantenedores,
      comunidade CHAOSS — internacional).
- [ ] **Post contando a história** (site pessoal + cross-post dev.to):
      os 4 arquétipos, boxplot, prevalência de práticas, forks negativo
      no Estádio como hipótese. As 14 figuras em 300 dpi já existem.

## 2. Interativo

- [ ] **Explorador estático do dataset** (protótipo como Artifact desta
      sessão; produção no GitHub Pages do repo): mapa da amostra,
      boxplots, tabela filtrável, painel por repositório com leitura
      relativa ao arquétipo. Zero backend, zero manutenção.
- [ ] **GitHub Action + badge** — o produto acionável: mantenedor roda no
      próprio CI (token dele, clone local → modo `both` completo, zero
      operação nossa, opt-in resolve a questão ética de rankear projetos
      alheios). Recurso-chave: como D1/D5 são binárias com pesos
      conhecidos, reportar o **valor em pontos de cada prática ausente**
      ("adicionar SECURITY.md + CONTRIBUTING = +4,2 pontos, P25 → P50 do
      arquétipo") — transforma diagnóstico em plano de ação.
- [ ] Evitar: leaderboard público de projetos nomeados (backlash; ver
      discussões do próprio Scorecard).

## 3. Aberto ou fechado

**Manter aberto (Apache-2.0, como está).** (i) A reprodutibilidade é tese
do próprio TCC; (ii) ferramenta de governança OSS fechada não teria
credibilidade no público-alvo; (iii) o retorno realista é capital de
reputação, que se maximiza aberto. Se surgir demanda comercial: open
core (ferramenta aberta; hospedagem/relatórios corporativos pagos) —
não desenhar para isso agora.

## 4. Canais que multiplicam

- [ ] **CHAOSS working group** — apresentar; virar ferramenta listada é o
      melhor selo possível.
- [ ] **MSR (data/tools track) ou SBES** — short paper com o orientador a
      partir do TCC.
- [ ] **CHAOSScon / FOSDEM** — palestra de 20 min; as figuras contam a
      história.

## Pré-requisitos antes de qualquer publicação

- [ ] Concluir a inspeção manual da amostra (notebook 01) e reextração de
      substitutos, se houver.
- [ ] Decidir nome definitivo (checar colisões de "govscore").
- [ ] Revisar o que fica público: paper/monografia ficam FORA do repo
      (decisão já tomada); dataset e resultados ficam.
