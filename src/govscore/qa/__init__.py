"""Instrumentos de QA do catálogo v2 — DESCRITIVOS, nunca árbitros de regra.

Registro: docs/decisions/2026-09-13-catalogo-v2-reparo-d1-d5.md, seção
"Instrumentos complementares". Dois módulos:

- `locus`: evidência de locus de coordenação fora do GitHub a partir das
  mensagens de commit em cache (trailers de Gerrit/Phabricator/Piper, espelho
  declarado) → `results/locus_evidence.md`.
- `declarations`: declarações de QA (censura de releases, motivo da retenção
  ausente, CI não detectada) → seção extra de `results/qa_extracao.md`.

Nenhuma função aqui altera scores, amostra ou catálogo.
"""
