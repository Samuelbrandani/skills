# Figma → Flutter (versão em português)

> Espelho de `SKILL.md`. O arquivo que o agente carrega é o `SKILL.md` em inglês; este existe para leitura humana e revisão. Referências em português em `references/pt-BR/`.

Um layout diverge do Figma por um motivo previsível: alguém implementou a partir de uma **descrição** do design em vez do design. Prosa carrega estrutura e regra; não carrega padding, raio, peso de fonte, sombra nem cor exata. Quem lê prosa acerta a composição e inventa o pixel.

Esta skill existe para que todo número venha do nó do Figma, todo asset seja o export original, o código caia onde a arquitetura do repo manda, e a conferência aconteça sobre um **render real medido número contra número**, não sobre um teste que não enxerga fonte nem sombra.

## Modos

| Modo | Quando | Fases |
|---|---|---|
| `implementar` | tela ou componente que não existe no código | 0 → 7 |
| `redesenhar` | tela existe no código, mas o nó do Figma é outra composição | 0 → 7, com um veredito curto de auditoria antes (abaixo) |
| `auditar` | tela existe e o pedido é "está igual?" — entregar divergências sem tocar em código | 0, 1, 2, 7 |
| `componente` | um único componente do design system (botão, chip, card) | 0 → 7, varredura do repo focada no pacote do design system |

Se o pedido não disser qual: tela existe + pedido é pergunta → `auditar`; tela existe + pedido é "implementa isso" → `redesenhar`. Em `redesenhar`, não meça os 12 eixos de uma composição que vai ser substituída: registre "eixo 7 (composição) diverge por inteiro" mais os poucos defeitos que sobrevivem ao redesenho, e siga. A medição completa acontece na fase 7 sobre o código novo.

## Fase 0 — Pré-voo (bloqueante)

1. `whoami` no MCP do Figma. Se as únicas ferramentas do Figma disponíveis forem `authenticate` / `complete_authentication`, o servidor não está autorizado: chame `authenticate`, entregue a URL ao usuário e **não caia em fallback** por prosa, captura antiga ou memória. Enquanto o usuário autoriza, rode a fase 2 (perfil do repo) — ela não depende do Figma. Depois da autorização as ferramentas reais aparecem como deferred; carregue com `ToolSearch("select:mcp__figma__whoami,mcp__figma__get_metadata,…")` antes de chamar.
2. Extraia do link: `figma.com/design/<fileKey>/...?node-id=7880-15366` → `fileKey`, `nodeId = 7880:15366` (hífen vira dois-pontos).
3. `get_metadata` no nó. Em seção ou página ele **estoura o limite do resultado** e o harness salva num arquivo; não chame de novo — rode `scripts/figma_outline.py <arquivo> --depth 1` para listar as telas com tamanho, e `--node <id> --depth 3` para o outline de uma tela. Anote a **largura do frame** de cada tela. Toda conferência da fase 7 acontece nessa largura; comparar um render de 490 px com um frame de 390 px inventa divergência que não existe.
4. Orce as chamadas. O MCP trunca em ~20 KB por resposta, e seats Starter/View têm 6 chamadas por mês (`whoami` mostra o seat). Uma tela custa no mínimo metadata + screenshot + variáveis + contexto; planeje o lote antes de chamar e agrupe chamadas independentes numa mensagem.
5. Se o `CLAUDE.md` do repo (ou de um diretório pai) exige plan mode antes de implementar, as fases 0–5 **são o plano**: escreva-as com `references/pt-BR/plan-template.md` e entregue o plano; as fases 6–7 rodam depois da aprovação, possivelmente por outro agente.

## Fase 1 — Discovery do nó

Detalhe em `references/pt-BR/discovery.md`. Saída: tabela `# · tela · node (link) · largura · elementos`, o screenshot do Figma de cada tela salvo em disco, as variáveis que o nó usa, e a lista de variantes de componente e estados interativos que o Figma define.

Ler o Figma é também onde se decide o que **não** é UI: conectores de protótipo, anotações de designer, seletores de estado, variantes "DEMO". Na dúvida, pergunte; nunca implemente.

## Fase 2 — Perfil do repo (automático, sempre)

O que já existe vence o que seria criado. Antes de mapear qualquer coisa, rode:

```
scripts/repo_scan.sh <raiz-do-repo>
```

e leia `references/pt-BR/repo-scan.md` para transformar a saída em um **Perfil do Repo**: onde vive o design system (pacote, barrel, classes de token, padrão de acesso), se ele está *pronto*, *parcial* ou *ausente*, onde ficam widgets de feature versus widgets compartilhados, como estado, DI, navegação e entities estão ligados, as convenções de assets, e qual ferramental de verificação já existe. Leia o `CLAUDE.md` e os docs de arquitetura que a varredura listar.

Três regras saem desta fase e não são negociáveis:

- **Componente vai onde a arquitetura manda.** Componente reutilizável vai para o pacote do design system com tudo que os irmãos têm (teste, entrada no catálogo, export no barrel). Seção de tela vai para a pasta de widgets da feature. Nunca uma pasta `widgets/` inventada para a ocasião.
- **Tokens são consumidos do jeito que o repo consome** (`context.colors.primary`, `AppSpacing.md`, `Theme.of(context).extension<…>()`). Se há dois arquivos de token, descubra qual gera código antes de editar.
- **Catálogo escrito é pista, não verdade.** Reconcilie qualquer catálogo contra o barrel e corrija o doc na mesma passada.

## Lote de decisões (pergunte uma vez, cedo)

Algumas decisões são do usuário, e perguntar uma por vez no meio do trabalho trava tudo. Assim que as fases 1 e 2 terminarem, pergunte tudo junto num único `AskUserQuestion`, com a opção recomendada primeiro:

- **Escopo** quando o nó tem vários frames: quais telas ou corpos entram nesta rodada.
- **Cor de marca vs token de acessibilidade** quando o Figma usa um hex que o design system substituiu de propósito (ex.: rosa da marca vs variante AA).
- **Dado sem fonte**: como degrada uma estatística, contador ou toggle que o Figma desenha e nenhuma entity entrega (esconder a célula, esconder o bloco, placeholder). Antes, leia as perguntas abertas e bloqueantes da spec; a resposta costuma já estar escrita.
- **Estados não desenhados** que a tela precisa (botão salvar num form inline, header vazio/incompleto, corpo de seção que o Figma não mostra).

Todo o resto é decisão de rotina: tome, escreva na tabela 3, siga.

## Fase 3 — De-para

O passo que costuma faltar. Regras e formatos em `references/pt-BR/mapping.md`. Três tabelas obrigatórias: nó → widget, variável do Figma → token, e **valores sem token**. Mais a tradução do auto layout e a tabela de armadilhas Figma → Flutter (line-height, letter-spacing em %, alinhamento de stroke, borda somada ao padding, corner smoothing, opacidade de layer versus de fill). Nenhuma medida entra no widget como número solto.

## Fase 4 — Assets (só originais)

Procedimento em `references/pt-BR/assets.md`. Todo ícone, ilustração, logo e imagem vem do nó exato do Figma (URLs de SVG no `get_design_context`, exports e originais raster via `download_assets`), no formato que o design pede. **Nunca** redesenhe um ícone à mão, substitua por um glifo "parecido" ou deixe placeholder. Quando o repo adota uma família de ícones (Lucide, Phosphor, Material) e proíbe SVG vendorizado, baixe os SVGs mesmo assim, identifique a família pela assinatura e mapeie cada um para o token da família — adicionando os que faltam —, porque o token *é* o desenho original; vendorize arquivo só para glifo que a família não tem, e registre. Rode `scripts/svg_check.py` em todo SVG antes de commitar; ele aponta o que o `flutter_svg` não renderiza. Raster entra com as variantes `2.0x/` e `3.0x/`. Registre no `pubspec.yaml` e, quando o repo usa, na classe de assets gerada.

Tela com ícone errado não está "quase certa". É a divergência mais visível da lista.

## Fase 5 — Contrato e dado

Regras em `references/pt-BR/data-contract.md`. Em uma linha: para cada texto do Figma, nomeie o campo da entity que o alimenta, e **o fake que roda o app precisa cobrir o caso rico que o Figma desenha**. Um card que degrada por campo nulo, alimentado por um seed magro, renderiza vazio no app enquanto o teste renderiza cheio — e a divergência só aparece quando alguém abre o app.

## Fase 6 — Implementação

Siga a arquitetura do repo, não a desta skill. O que esta skill acrescenta:

- Componente novo no design system exige o mesmo que os existentes exigem (teste espelho, use case no catálogo, nome de variante igual ao do Figma).
- Nada de variante que o Figma não define. Sem estado inventado, sem placeholder decorativo.
- Seção de tela vira classe `StatelessWidget` própria, nunca método que devolve `Widget`.
- Todo estado que o Figma desenha (loading, vazio, erro, desabilitado, selecionado) é implementado; todo estado que o Figma **não** desenha e a tela precisa é pergunta para o design, não improviso.
- Alvos de toque ≥ 48 dp, `Semantics` em controles só-ícone, texto que sobrevive a 1,3× de escala sem estourar, `SafeArea` onde o frame encosta na borda, dark mode quando o design system tem.

## Fase 7 — Conformidade

**Nenhuma implementação está pronta antes desta fase.** Procedimento em `references/pt-BR/conformance.md`.

Duas conferências, ambas obrigatórias, porque pegam defeitos diferentes:

- **Medir** — despejar a árvore renderizada em JSON (rect, padding, raio, borda, sombra, gradiente, cor, família/tamanho/peso/altura/letter-spacing da fonte, glifo do ícone, asset da imagem, alvos de toque) e comparar número contra número com o Figma. Pega 2 px, peso 600 vs 700, sombra ausente. Use o probe do repo se houver; senão copie `assets/design_probe.dart`.
- **Olhar** — render real com as fontes do app na largura do frame do Figma, ao lado do `get_screenshot`. Pega ordem trocada, elemento faltando, hierarquia invertida, ícone errado.

Cada um dos 12 eixos sai `OK` ou `DIVERGE` com o valor dos dois lados. Loop até zerar. Divergência que não é bug vira linha justificada; nunca some em silêncio.

## Entregável

Relatório com: o veredito da auditoria (quando a tela já existia), o Perfil do Repo, a tabela de telas, as três tabelas do de-para, o manifesto de assets (nó → arquivo → onde é usado), a decisão de degradação por campo, a tabela dos 12 eixos por tela, e o que ficou pendente com motivo. `references/pt-BR/plan-template.md` é o esqueleto; quando o repo exige plano antes de código, o mesmo documento é o plano. Capturas do Figma e renders do app ficam versionados no repo, lado a lado, com nome que amarre `tela ↔ node`.

## Gates

Não declare pronto sem:

- [ ] MCP do Figma lido; nenhuma medida veio de prosa
- [ ] Perfil do Repo escrito; status do design system decidido (pronto / parcial / ausente) e todo arquivo novo no lugar que a arquitetura define
- [ ] todo valor rastreável a um token, ou listado como divergência explícita
- [ ] reuso preferido a componente novo, com justificativa escrita quando novo
- [ ] todo asset é o export original do Figma, checado pelo `svg_check.py`, registrado e renderizado no tamanho certo
- [ ] fake do app cobrindo o caso rico do Figma
- [ ] árvore renderizada medida e comparada número a número
- [ ] os 12 eixos fechados por tela, na largura do frame
- [ ] análise estática e testes de todo pacote tocado, verdes
