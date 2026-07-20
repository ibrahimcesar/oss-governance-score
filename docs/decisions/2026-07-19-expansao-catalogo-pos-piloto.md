# Registro de decisão — expansão do catálogo de métricas (pós-piloto)

**Data:** 2026-07-19 · **Status:** aceito · **Fase:** piloto (anterior ao
congelamento do catálogo)

## Contexto

O piloto nos 4 arquétipos validou o pipeline mas expôs lacunas: D3 media tempo
de *fechamento* (conflate dificuldade da issue com atenção do mantenedor), e o
catálogo não capturava prática de revisão de código, diversidade
organizacional, retenção de contribuidores nem sustentabilidade financeira.
Seis métricas são adicionadas ANTES do congelamento; todas entram na análise
de sensibilidade (item 6 do plano).

## Métricas adicionadas

| Métrica | Dim. | Fundamentação | Limiar best | Limiar worst |
|---|---|---|---|---|
| `median_first_response_hours` | D3 | CHAOSS *Time to First Response*; substitui `median_issue_close_hours` no score | 48 h | 720 h (30 d) |
| `pr_review_coverage` (share de PRs merged com ≥1 review) | D3 | CHAOSS *Review Coverage*; OpenSSF exige revisão nos changesets recentes | 0.9 | 0.3 |
| `elephant_factor` (mín. de organizações com ≥50% dos commits) | D4 | CHAOSS *Elephant Factor* / *Organizational Diversity* | 3 | 1 |
| `contributor_retention` (ativos na 1ª metade da janela que seguem na 2ª) | D4 | Constantinou & Mens (2017) — abandono de contribuidores | 0.5 | 0.1 |
| `funding` (FUNDING.yml, com herança de `{org}/.github`) | D1 | Asparouhova (2020); Overney et al. (2020) — doações em OSS | binária | — |
| `release_notes_share` (releases 12m com notas não vazias) | D5 | comunicação de mudanças; adjacente a CHAOSS *Release Frequency* | 0.8 | 0.0 |

`median_issue_close_hours` continua sendo EXTRAÍDA (comparabilidade com o
piloto) mas sai do cálculo do score.

## Decisões de implementação

- **D3 via GraphQL** (item 3 do plano): uma query por repositório (últimas 50
  issues fechadas + últimos 50 PRs merged), cacheada em `data/raw/` como as
  respostas REST.
- **1ª resposta**: primeiro comentário cujo autor não é o autor da issue e não
  é bot. Heurística de bot: `__typename == "Bot"` ou login terminando em
  `bot`/`[bot]` (captura `k8s-ci-robot`, `dependabot`; falso positivo aceito e
  declarado como limitação).
- **Elephant factor por domínio de e-mail** (proxy de organização, prática
  GrimoireLab): domínios de provedores genéricos (gmail, outlook,
  users.noreply.github.com, …) contam por INDIVÍDUO, não por domínio.
  Compatível com a regra de anonimização (domínios podem ser publicados;
  e-mails individuais são hasheados).
- **Retenção**: janela de 12 meses dividida em metades ancoradas na data de
  extração; retenção = |ativos nas duas metades| / |ativos na 1ª metade|.
  `None` se a 1ª metade não tem contribuidores.
- **D2/D4 na janela de 12 meses vêm do backend git** (clone raso), não de
  GraphQL `history(since:)`: paginar o histórico do kubernetes custaria
  centenas de páginas por repo e ameaçaria a janela de extração < 1 semana
  para n=100. O item 3 do plano fica satisfeito com D3 via GraphQL + D4
  janelado via git.
- **Novo modo `--backend both`**: extração API (D1/D3/D5, releases, stars) +
  git (D2/D4 na janela); é o modo canônico da fase completa.

## O que ficou de fora (e por quê)

- Sub-checks do OpenSSF Scorecard como INSUMO: Scorecard é critério de
  validação (item 7) — usá-lo dos dois lados seria circular. A sobreposição
  parcial de `pr_review_coverage` com o check *Code-Review* fica declarada.
- Branch protection via API: exige permissão de admin; inviável para amostra
  de terceiros.
- `security_and_analysis` do metadata: só visível com permissão no repo
  (confirmado no piloto) — não é uniforme na amostra.

## Limiares — natureza e revisão

Limiares novos são decisões de pesquisa calibradas no piloto e na prática
CHAOSS/OpenSSF, não derivados da amostra (mantém interpretabilidade fora
dela). Sensibilidade: pesos iguais, ±25% e leave-one-dimension-out (item 6)
devem incluir as métricas novas. NÃO ajustar limiares para "melhorar"
resultados (cuidado metodológico do plano).
