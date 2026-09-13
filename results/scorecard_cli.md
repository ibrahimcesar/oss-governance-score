# OpenSSF Scorecard CLI nos 100 repositórios (validação secundária)

Pré-registrado como DESCRITIVO no registro de decisão de 2026-09-13; a API-53 de julho permanece o critério primário. Época do CLI: HEAD em 09/2026 (~7 semanas após o snapshot); *Maintained*, *Vulnerabilities*, *Signed-Releases* e *Branch-Protection* não são retrodatáveis. Versão única do CLI (v5.5.0, 18 checks).

Repositórios com resultado: 100/100; mediana de 33 s por repositório; agregado reportado reproduzido a partir dos checks (diferença máxima 0.0500).

## Concordância CLI × API de julho (n = 53)

- ρ entre o agregado do CLI (18 checks) e o da API: 0.822 — instrumentos com conjuntos de checks distintos (a varredura pública omite CI-Tests, Contributors e Dependency-Update-Tool).
- ρ entre agregados restritos aos checks COMUNS: 0.950; diferença média absoluta 0.18 pontos — a diferença remanescente é a deriva de época (julho → setembro).

## Correlação do score v2 com o agregado do CLI

| subconjunto | n | ρ |
|---|---|---|
| todos | 100 | 0.616 |
| todos, agregado sem os checks sobrepostos ao catálogo (Security-Policy, Dependency-Update-Tool, Code-Review, CI-Tests, License) | 100 | 0.271 |
| só os 53 com resultado na API (comparabilidade com o primário) | 53 | 0.667 |

| arquétipo | n | ρ | média do CLI |
|---|---|---|---|
| federation | 25 | 0.498 | 5.79 |
| stadium | 25 | 0.726 | 5.05 |
| club | 25 | 0.243 | 5.54 |
| toy | 25 | 0.739 | 4.27 |

Leitura: sem correção para múltiplos testes (família secundária, descritiva); poder intra-arquétipo com n = 25 apenas para efeitos grandes (ρ ≳ 0,57). O agregado sem os checks sobrepostos mostra a convergência que não é mecânica.
