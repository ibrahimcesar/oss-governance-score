# Registro de decisão — inspeção manual da amostra (n=100)

**Data:** 2026-09-12 · **Status:** aceito · **Fase:** pós-extração completa
(fecha a pendência do item 5 do plano e o piso da revisão adversarial)

## Contexto

O notebook `notebooks/01_inspecao_amostra.ipynb` sinaliza suspeitos por duas
heurísticas (padrão de nome típico de não-software; nenhuma resposta humana
nas issues amostradas), totalizando 11 repositórios. A revisão adversarial
(`docs/revisao_adversarial_estudo.md`) identificou mais 4 repositórios de
conteúdo que escapam das duas heurísticas. O autor fez a inspeção manual
no notebook sobre os 11 sinalizados. Os 4 casos adicionais entram na mesma
decisão pelo mesmo critério e foram acrescentados ao notebook (célula
"Casos fora das heurísticas") para que o registro cubra os 15.

## Decisão

**Todos os 100 repositórios são mantidos.** Nenhuma entrada nova em
`config/sampling.yaml` → `exclusions.repos`; nenhuma reextração.

## Casos inspecionados

| categoria | repositório | arquétipo | observação | decisão |
|---|---|---|---|---|
| espelho | `torvalds/linux` | federation | issues desativadas; patches por lista de e-mail | mantido |
| espelho | `FFmpeg/FFmpeg` | federation | "Mirror of git.ffmpeg.org"; issues desativadas | mantido |
| espelho | `git/git` | federation | "publish-only"; PRs viram patches (GitGitGadget) | mantido |
| espelho | `gitlabhq/gitlabhq` | stadium | "GitLab CE Mirror"; issues no GitLab.com | mantido |
| conteúdo | `MisterBooo/LeetCodeAnimation` | stadium | animações de soluções LeetCode | mantido |
| conteúdo | `EFanZh/LeetCode` | toy | soluções de exercícios LeetCode | mantido |
| conteúdo | `github/explore` | club | páginas curadas de tópicos/coleções | mantido |
| conteúdo | `krahets/hello-algo` | stadium | livro de algoritmos (tópico `book`) — não capturado | mantido |
| conteúdo | `doocs/advanced-java` | stadium | guia de entrevista Java — não capturado | mantido |
| conteúdo | `danielmiessler/SecLists` | stadium | listas para testes de segurança — não capturado | mantido |
| conteúdo | `SwiftOldDriver/iOS-Weekly` | club | newsletter semanal — não capturado | mantido |
| conteúdo | `Au1rxx/free-vpn-subscriptions` | toy | feed de assinaturas VPN | mantido |
| software, sinal fraco | `fustyles/Arduino` | toy | sem resposta humana nas issues | mantido |
| software, sinal fraco | `AITabby/opencodex` | toy | sem resposta humana nas issues | mantido |
| software, sinal fraco | `yolfinance/yolfi-agent` | toy | sem resposta humana; triagem de stars (robustez.md §7) | mantido |

## Justificativa

1. **Critérios de inclusão atendidos.** Todos satisfazem os critérios
   definidos antes da extração (público, ≥1 commit no branch default em 12
   meses, não fork/arquivado/template, linguagem detectada). Excluir após ver
   os scores seria decisão *post hoc*, que abre o flanco de seleção
   oportunista de casos.
2. **Resultados centrais robustos.** Sem os 15 casos (n=85), as
   correlações globais quase não mudam: Scorecard 0,750 → 0,725, stars
   0,403 → 0,421, forks 0,454 → 0,508 (`results/robustez.md` §4.1).
3. **O silêncio é o fenômeno medido.** Nos três casos de software sem
   resposta humana, a ausência de resposta é informação de D3 (ausência
   informativa), não defeito de dado.
4. **Espelhos são software.** O limite está no proxy (governança fora do
   GitHub), não na inclusão. Ele é declarado como limitação de medição.

## Consequências para o texto (obrigatórias)

Manter os casos exige reportar os resultados com e sem eles. A análise por
cenários (`govscore robustness`, `results/robustez.md` §4.1) mostra que:

- **Estádio × forks** (ρ = −0,455, p = 0,022) **não é robusto**. Sem os 4
  repositórios de conteúdo do estrato, cai para ρ = −0,257 (p = 0,260,
  n = 21). A leitura fork-como-*bookmark* de guias de estudo é a explicação
  mais parcimoniosa. O achado deve ser apresentado como dependente da
  composição, não como apoio à tensão de Asparouhova.
- **Federação × Scorecard** (ρ = 0,544, p = 0,036) **não é robusto**. Sem
  os 3 espelhos da Federação, cai para ρ = 0,109 (p = 0,737, n = 12). A
  frase "o Scorecard mantém associação positiva em todos os estratos" deve
  ser qualificada.
- **Assimetria de D3 nos espelhos.** Declarar a assimetria em D3: `git/git`
  tem D3 = 0 (artefatos de PR observados abaixo dos pisos), enquanto
  `linux` e `FFmpeg` têm D3 omitido (sem dados de PR). A regra "observado
  conta, ausente omite" é coerente, mas é declarada como limitação.
- **Triagem da §4.2.3.** Declarar que a triagem heurística por tópicos e
  nomes deixou passar 8 repositórios de conteúdo e 4 espelhos, identificados
  na inspeção manual e mantidos pela justificativa acima.
