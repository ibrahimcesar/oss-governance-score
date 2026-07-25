# CLAUDE.md

## O que é este projeto

Código de pesquisa do TCC "Proposta de algoritmo para identificação de padrões
de boas práticas de governança em projetos de software open source" (MBA em
Gestão Estratégica de Operações, Projetos e TI — USP/EACH). O pipeline
implementa as Etapas 2 (criação do algoritmo) e 3 (validação) do método:

```
extract (APIs GitHub / git) → score (normalização + agregação) → validate (Spearman)
```

O plano de pesquisa completo (catálogo de métricas, limiares, desenho de
validação, cronograma) está no Claude Project "TCC", doc
`claude/PLANO_DE_PESQUISA_CODIGO.md`. Consulte-o antes de mudanças de escopo.

## Arquitetura

- `config/metrics.yaml` — catálogo: 5 dimensões (D1 artefatos, D2 distribuição,
  D3 responsividade, D4 diversidade, D5 segurança), limiares ABSOLUTOS de
  normalização e pesos. **Congelar após a fase piloto**; mudanças só com
  registro de decisão.
- `config/sample.yaml` — amostra estratificada pelos 4 arquétipos de
  Asparouhova (2020). `pilot`: 4 repos; `full`: alvo de 25 por arquétipo (n=100).
- `src/govscore/` — três modos de extração:
  - `api` (padrão): REST + GraphQL com cache em `data/raw/`, requer
    `GITHUB_TOKEN`. Único que cobre D3 (1ª resposta via GraphQL, métrica
    CHAOSS; review coverage) e releases.
  - `git`: clone raso `--shallow-since="12 months ago"`, sem token; cobre
    D1/D2/D4 e parte de D5, com fallback para arquivos de comunidade herdados
    de `{org}/.github` (achado do piloto — não remover). Único que cobre
    elephant factor e retenção (janela de 12 meses).
  - `both`: API (D1/D3/D5, releases) + git (D2/D4 janelados) — modo canônico
    da fase completa.
- `docs/decisions/` — registros de decisão de mudanças no catálogo (obrigatório).
- Scoring: métricas faltantes são omitidas da média, nunca imputadas como
  zero; pesos renormalizados sobre as dimensões disponíveis.

## Comandos

Ambiente Python **sempre via `uv`** — nunca `python`/`pip` do sistema.
Setup (uma vez): `uv venv && uv pip install -r requirements.txt`.

```bash
make test                 # unit tests (sempre rodar antes de commit)
GITHUB_TOKEN=$(gh auth token) make pilot      # extração+score dos 4 pilotos (backend api)
GITHUB_TOKEN=$(gh auth token) PYTHONPATH=src uv run python -m govscore.cli pilot --backend both
GITHUB_TOKEN=$(gh auth token) PYTHONPATH=src uv run python -m govscore.cli sample   # amostragem n=100
PYTHONPATH=src uv run python -m govscore.cli pilot --backend git    # sem token
PYTHONPATH=src uv run python -m govscore.cli extract --repo owner/name
```

## Convenções

- Toda invocação de Python/pytest via `uv run`; dependências novas entram em
  `requirements.txt` e instalam com `uv pip install`.
- Documentação e comentários voltados ao TCC em PT-BR; código/identificadores em inglês.
- Toda resposta de API é cacheada em `data/raw/` (nunca commitado); a análise
  nunca reconsulta a API — reprodutibilidade em primeiro lugar.
- Logins de contribuidores devem ser anonimizados (SHA-256 + salt) em qualquer
  dataset publicado.
- Funções de cálculo novas exigem teste unitário com caso conhecido.

## Estado atual e próximos passos (ordem do plano)

1. [x] Piloto validado nos 4 arquétipos (scores em `data/processed/pilot_scores.json`)
2. [x] Rodar `make pilot` com `GITHUB_TOKEN` para preencher D3 (responsividade)
   — concluído em 2026-07-19; cache completo dos 4 pilotos em `data/raw/`
3. [x] Migrar D3/D4 para GraphQL (1ª resposta em issues — métrica CHAOSS —
   e contribuidores ativos em janela de 12 meses) — D3 via GraphQL; D4
   janelado via backend git no modo `both`. Catálogo expandido com 6 métricas
   (ver `docs/decisions/2026-07-19-expansao-catalogo-pos-piloto.md`)
4. [x] Script de amostragem: Search API + classificação de arquétipos
   (limiares no plano, §3.1) até n=100 — parâmetros em `config/sampling.yaml`,
   amostra gerada em `config/sample_full.yaml` (com lista `ambiguous` para
   inspeção manual; critério de inclusão: ≥1 commit no branch default em 12m)
5. [x] Extração completa (janela < 1 semana) + QA do dataset — 100/100 em
   2026-07-23→24 (`govscore run`, retomável); dataset em `data/processed/`
   (full_metrics.json, metrics.parquet, scores.csv), QA em
   `results/qa_extracao.md`. Pendência de inspeção manual: possíveis
   não-software na amostra (ex.: `github/explore`, `EFanZh/LeetCode`)
6. [x] Análise de sensibilidade dos pesos (`score/sensitivity.py`: pesos
   iguais, ±25%, leave-one-dimension-out) — ranking robusto (ρ ≥ 0,935 em
   todas as variantes; critério DSR ≥ 0,8 satisfeito). Relatório em
   `results/sensibilidade.md`; comando `govscore sensitivity`
7. [x] Validação: deps.dev (dependentes), OpenSSF Scorecard, stars/forks →
   Spearman + Holm–Bonferroni (`validate/`; `govscore validate`) — scorecard
   ρ=0,750, forks 0,454, stars 0,403, todos p_adj<0,001; releases excluída
   por circularidade com D5; dependentes sem poder (n=5, cobertura
   estrutural). Relatório em `results/validacao.md`
8. [ ] Figuras e tabelas para as seções 4.2/4.3 do TCC

## Cuidados metodológicos (não violar)

- NÃO filtrar a amostra pela presença de artefatos de governança — isso é
  parte da variável dependente (viés de seleção).
- Limiares de normalização são decisões de pesquisa ancoradas na literatura
  (CHAOSS; Coelho & Valente 2017; Avelino et al. 2016) — não ajustar para
  "melhorar" resultados.
- Stars/forks são proxies de popularidade, não de saúde; interpretar com cautela.
