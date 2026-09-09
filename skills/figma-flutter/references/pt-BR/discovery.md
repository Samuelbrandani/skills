# Discovery do nó

## Ferramentas, em ordem

| Passo | Ferramenta | Para quê |
|---|---|---|
| 1 | `get_metadata` (`nodeId`) | outline esparso em XML: id, nome, tipo, posição e **tamanho** de cada camada. É o mapa. Sem `nodeId`, lista as páginas do arquivo. |
| 2 | `get_screenshot` (`nodeId`) | PNG de **um** nó, com a fidelidade do layout. É a referência da fase 7. Um por tela; salve em disco. |
| 3 | `get_variable_defs` (`nodeId`) | variáveis e estilos aplicados — cor, espaçamento, tipografia — com nome e valor. É daqui que sai o de-para de token. |
| 4 | `get_design_context` (`nodeId`) | representação estruturada: hierarquia, auto layout, tipografia, cor e propriedades de componente. Sai como React + Tailwind por padrão; **não copie o código**, leia como fonte de medidas. Passe `clientLanguages: "dart"`, `clientFrameworks: "flutter"`; não há preset Flutter, mas reduz ruído web. |
| 5 | `get_code_connect_map` (`nodeId`) | mapeamentos Code Connect existentes no arquivo. Code Connect não tem parser Dart, mas times podem registrar widgets Flutter pelo modo template (parserless). Se existe mapeamento, ele nomeia o widget a reusar. |
| 6 | `search_design_system` (`queries`) | acha o componente de biblioteca por trás de uma instância. Use quando o nome da camada for genérico. |
| 7 | `download_assets` (`nodeId`, `defaultFormat?`, `defaultScale?`) | um nó por chamada: o export do nó, as imagens raster originais usadas como fill na subárvore (até 20) e os SVGs das camadas vetoriais (até 20, o mesmo conjunto que o `get_design_context` lista). Detalhes em `assets.md`. |

## O nó usa tokens?

`get_variable_defs` no nó do componente. Resposta vazia (`{}`) significa **que aquele desenho não usa nenhuma variável do design system** — foi montado com hex cru. Isso muda o trabalho inteiro: não existe de-para de token possível, e buscar paridade de cor com esse nó significa sair do design system.

Esse achado **não é bug de código e não se resolve implementando**. Registre como pendência de produto/design, mapeie cada cor para o token semântico mais próximo, e siga. Nunca copie o hex cru para dentro do widget.

Peculiaridades conhecidas: a ferramenta às vezes devolve o valor resolvido em vez do alias, e só o modo padrão da coleção. Quando o arquivo tem modos (light/dark, marca A/B), pergunte em qual modo a tela está e leia a coleção na UI do Figma se necessário.

## O que um designer também leria

Além das medidas, quem implementa em nível sênior lê o arquivo buscando intenção:

- **Variantes do component set.** Uma instância de botão dentro da tela pertence a um component set com variantes (`size=md, kind=primary, state=default`). Leia o set, não só a instância: as variantes são o enum do widget, e os nomes devem bater.
- **Estados interativos.** Hover, pressed, focused, disabled, selected, error. Se o Figma desenha, faz parte do escopo. Se não desenha e o widget precisa, é pergunta para o design, não improviso.
- **Estados de tela.** Loading, vazio, erro, dado parcial, texto longo. Procure frames irmãos chamados "Empty", "Loading", "Error", "Skeleton". Tela sem estado vazio no Figma ainda precisa de uma decisão escrita.
- **Anotações e dev resources.** Designers deixam notas de comportamento (scroll, header fixo, animação, regra responsiva) em anotações. `get_design_context` inclui quando existem.
- **Constraints e redimensionamento.** Como o frame se comporta em outras larguras (fill, hug, fixo, min/max). É o contrato responsivo.
- **Layout grid.** Contagem de colunas, gutter, margem. Alimenta a decisão de padding horizontal.
- **Corner smoothing.** O "iOS smoothing" do Figma faz squircles; o `BorderRadius` do Flutter não. Anote como divergência conhecida ou use `ContinuousRectangleBorder`.

## Cuidados

- **Resposta grande.** Prancha de fluxo inteiro estoura o limite de ~20 KB. Quebre: `get_metadata` na raiz para descobrir os filhos, depois uma passada por tela.
- **`get_screenshot` é um nó por vez.** Prancha inteira vira imagem ilegível; capture tela a tela.
- **Frame de prototipagem não é UI.** Seletor de estado, legenda de fluxo, anotação de designer e variante "DEMO" existem no Figma e não existem no app. Na dúvida, pergunte antes de implementar.
- **`get_design_context` exige a skill do Figma carregada antes.** Leia o recurso uma vez com `ReadMcpResourceTool(server: "figma", uri: "skill://figma/figma-design-to-code/SKILL.md")` (ou `/figma-design-to-code` se o plugin estiver instalado) e passe `skillNames: "resource:figma-design-to-code"`. Passe também `clientLanguages: "dart", clientFrameworks: "flutter"` e `excludeScreenshot: true` quando o PNG já estiver salvo — a resposta fica menor.
- **`get_metadata` em seção estoura** (150 KB+ de XML). O harness salva num arquivo; faça o outline com `scripts/figma_outline.py <arquivo> --depth 1` (telas) e `--node <id> --depth 3` (uma tela). Nunca chame de novo "para ver de novo".
- **URLs de screenshot expiram em minutos.** Baixe na hora com `curl -L -o` para a pasta de capturas do repo (a varredura lista a existente, ex.: `docs/design/<feature>/`), com nome `<tela>_<node>.png`, e leia do disco.
- **Frames duplicados.** Seções costumam guardar duas cópias de uma tela (versão antiga, "V2"). Compare tamanho e screenshot; se idênticas, trate o par como uma tela e diga isso. Uma duplicata pode ser a única ligada a variáveis — rode `get_variable_defs` nas duas antes de concluir que o design usa hex cru.
- **`search_design_system` em lote é cortado.** Pedir 4 consultas devolve 1 e avisa que 3 foram descartadas. Uma consulta por chamada.
- **O React + Tailwind que volta é referência de medida, não de implementação.** Leia os números; não traduza o markup. Classes Tailwind escondem valores (`p-4` = 16, `rounded-xl` = 12, `text-sm` = 14/20): resolva antes de anotar.
- **Nome da camada mente.** Camada chamada "Button" pode ser um `Container` com texto. Confie no tipo e na geometria do `get_metadata`, não no nome.
- **Rate limit.** Seats Starter e View/Collab: 6 chamadas por mês. Seats Dev/Full em plano pago: limite por minuto como o tier 1 da REST API. Agrupe `download_assets` e evite reler nó que já salvou.
- **Anote a largura do frame por tela**, e o `nodeId` de cada uma. Vai precisar dos dois na fase 7.

## Saída da fase

Tabela, no formato que a spec do repo já usa:

| # | Tela | Node | Largura | Elementos | Estados no Figma |
|---|---|---|---|---|---|
| 1 | Lista — aba Abertas | [`7880:9398`](url) | 390 | header, chips de filtro, card de período, lista de cards | default, vazio, loading |

Mais, por tela: o PNG do Figma salvo em disco (pasta de capturas do repo, ex.: `docs/design/<feature>/<tela>_<node>.png`), a lista de variáveis do `get_variable_defs`, e os component sets tocados com suas variantes.
