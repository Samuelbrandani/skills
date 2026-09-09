# Modelo de plano / relatório

Use este esqueleto para o entregável das fases 0–5. Quando o repo exige plano antes de código (um `CLAUDE.md` dizendo "plan mode primeiro"), este documento **é** o plano: outro agente precisa executá-lo sem reler o Figma. Mantenha as convenções de plano do próprio repo (cabeçalho, tarefas com checkbox, linha de sub-skill) se existirem — olhe o arquivo mais novo em `docs/plans/`.

```markdown
# <Feature> — <nó do Figma> — Implementation Plan (rodada N: <escopo em cinco palavras>)

> For agentic workers: use as fases 4–7 da `figma-flutter` por cima da skill de execução do repo. Copie este arquivo para `docs/plans/<data>-<feature>-<nó>.md` no primeiro commit.

**Goal:** um parágrafo: o que a tela vira, o que é reaproveitado, o que fica para a próxima rodada.
**Architecture:** as regras do repo que limitam este trabalho, num parágrafo (estado, DI, onde widgets vivem, lints).
**Tech Stack:** pin do SDK + como rodar as ferramentas (`fvm`, melos), comandos de teste e snapshot.
**Spec / backend delta:** arquivos a atualizar.

**Figma — arquivo `<fileKey>`, nó `<id>` (largura do frame <w>):**
| # | Tela | Node | Largura | Elementos | Estados no Figma | Captura |

## 0. Veredito da auditoria (só quando a tela já existia)
Composição igual / diverge por inteiro; defeitos que sobrevivem ao redesenho.

## 1. Perfil do Repo
(de `references/repo-scan.md` §5, ≤ 40 linhas)

## 2. Achado do sistema
O nó usa variáveis do design system? Se `{}`: hex cru → tokens semânticos mais próximos, pendência para o design.

## 3. De-para
### Tabela 1 — nó → widget  (reuso / extensão / novo + justificativa)
### Tabela 2 — valor do Figma → token
### Tabela 3 — valores sem token (cada linha: vira token | decisão registrada)
### Auto layout → widget (as medidas que definem paddings e gaps)

## 4. Assets — manifesto
| Nó | Nome no Figma | Desenho / família | Token ou arquivo | Ação |
Registre a identificação da família (ex.: stroke 1.333 em viewBox 16 = Lucide 2/24) e a política de ícones do repo.

## 5. Contrato e dado
| Elemento no Figma | Campo | Existe hoje? | Decisão |
Mudanças de seed no fake do app e nas fixtures de teste (regra 3).

## 6. Estado e arquitetura
Onde cubits/providers nascem, que estado muda de lugar, quais rotas ficam, telemetria que precisa continuar disparando.

## 7. Tarefas (ordem que mantém a suíte verde)
### A. Design system   ### B. Domínio e dado   ### C. Feature   ### D. Conformidade (fase 7)
Checkbox por tarefa, caminho de arquivo por tarefa, ≤ 1 linha cada.

## 8. Gates
A lista de gates da skill, marcada.

## 9. Próxima rodada
O que ficou de fora, já dimensionado (nós, componentes a promover, medidas ainda por tirar).
```

Regras práticas:

- Todo número das tabelas 2–3 vem do `get_design_context`; cite o id do nó ao lado quando não for óbvio.
- Decisões tomadas com o usuário (escopo, cor de marca, degradação) levam data e "usuário" como autor.
- Perguntas pendentes para o design ficam numa lista só, frasadas para um designer responder sim/não.
