# oss-governance-score

Algoritmo para identificação de padrões de boas práticas de governança em
projetos de software open source — código do TCC (MBA Gestão Estratégica de
Operações, Projetos e TI, USP/EACH).

## Visão geral

O pipeline tem três estágios, espelhando as Etapas 2 e 3 do método:

```
extract  →  score  →  validate
(APIs GitHub)  (normalização + agregação ponderada)  (Spearman vs. indicadores externos)
```

Cinco dimensões de governança (ver `config/metrics.yaml`):

- **D1** Artefatos de governança (CONTRIBUTING, CODEOWNERS, CoC, licença…)
- **D2** Distribuição das contribuições (concentração / truck factor)
- **D3** Responsividade da manutenção (issues e PRs)
- **D4** Diversidade da base de contribuidores
- **D5** Práticas de segurança (SECURITY.md, CI, automação de dependências)

## Uso rápido

```bash
pip install -r requirements.txt
export GITHUB_TOKEN=ghp_...   # opcional, mas necessário para a amostra completa

# Extrai e pontua os pilotos definidos em config/sample.yaml
python -m govscore.cli pilot

# Um repositório específico
python -m govscore.cli extract --repo expressjs/express
```

Toda resposta de API é cacheada em `data/raw/` — a análise nunca reconsulta a
plataforma, garantindo reprodutibilidade.

## Estrutura

```
config/metrics.yaml    catálogo de métricas, limiares de normalização e pesos
config/sample.yaml     amostra estratificada pelos 4 arquétipos (Asparouhova, 2020)
src/govscore/          extração, scoring, sensibilidade e validação
data/raw/              cache JSON bruto por repositório
data/processed/        métricas e scores consolidados
tests/                 testes unitários das funções de cálculo
```

```bash
# Sem token (backend git puro — D1, D2, D4, parte de D5):
python -m govscore.cli pilot --backend git
```

## Status

- [x] Cliente de API (REST) com cache e tratamento de rate limit
- [x] Extração D1–D5 (versão piloto; D3 usa tempo-até-fechamento via REST)
- [x] Backend git (clone raso, sem token) com fallback para arquivos de
      comunidade herdados de `{org}/.github` — validado nos 4 pilotos
- [x] Normalização por limiares absolutos + score composto
- [ ] Migrar D3/D4 para GraphQL (1ª resposta em issues, contribuidores ativos 12m)
- [ ] Script de amostragem e classificação de arquétipos (n=100)
- [ ] Análise de sensibilidade dos pesos
- [ ] Validação: deps.dev, OpenSSF Scorecard, Spearman + Holm–Bonferroni
