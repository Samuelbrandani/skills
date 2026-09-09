# De-para Figma → Flutter

O Code Connect não tem parser Dart, então o de-para é escrito à mão. É o passo que separa "compôs com o design system" de "gerou um widget novo parecido".

## Ordem de preferência, sem exceção

1. **Reusar** um widget que já existe, como está.
2. **Estender** um existente (parâmetro novo, variante nova de enum).
3. **Criar** componente novo — só quando o Figma define algo que nenhum existente cobre, e com justificativa escrita.

Justificativa aceitável: "o Figma define uma faixa de status com ponto colorido e badge à direita; nenhum componente atual combina os dois". Não aceitável: "era mais rápido".

Um **component set** do Figma vira um widget com um enum por eixo de variante; **propriedades booleanas** viram parâmetros nomeados; **instance swap** vira parâmetro `Widget` ou enum de ícones permitidos; **propriedades de texto** viram `String`. Mantenha os nomes do Figma (`kind: primary | secondary`, não `type: 1 | 2`).

## Tabela 1 — nó → widget

| Nó | Nome no Figma | Decisão | Widget | Justificativa |
|---|---|---|---|---|
| `7880:10562` | Card de período | reuso | `AcmeDateRangeCard` | — |
| `7880:10570` | Chip de filtro | extensão | `AcmeFilterChip` + contagem | Figma mostra `Região · 2` |
| `7880:10588` | Faixa de status | novo | `AcmeStatusStrip` | ponto + rótulo + badge, sem equivalente |

## Tabela 2 — variável do Figma → token

Uma linha por variável retornada pelo `get_variable_defs`.

| Variável Figma | Valor | Token Flutter | Nota |
|---|---|---|---|
| `color/semantic/primary` | `#D01165` | `context.acme.colors.primary` | — |
| `typography/card-title` | Titillium 700 16/24 | `context.acme.typography.cardTitle` | — |
| `spacing/md` | 16 | `AcmeSpacing.md` | — |

Regras:

- **Cor** vira slot semântico, nunca primitiva e nunca `Color(0x...)` fora do design system.
- **Texto** vira variante de tipografia inteira (família + tamanho + peso + altura de linha + letter spacing). Nunca `TextStyle` montado no widget, nunca `copyWith(fontSize:)`.
- **Espaço e raio** viram token da escala. Se o Figma usa 12 e a escala tem 8 e 16, isso é uma linha na tabela 3 — não um `EdgeInsets.all(12)` solto.
- **Sombra** vira token nomeado (`AcmeShadows.card`) com `List<BoxShadow>`. `elevation` do Material não reproduz sombra do Figma; use `BoxDecoration.boxShadow`.

## Tabela 3 — valores sem token

A tabela mais importante. Toda medida do Figma que **não** casa com um token existente entra aqui, com um desfecho.

| Valor no Figma | Onde | Desfecho |
|---|---|---|
| sombra `0 2 8 rgba(0,0,0,.08)` | card | **vira token** — não existe token de sombra hoje |
| raio 12 | chip | **decisão registrada**: usa `radii.sm` (16); Figma será alinhado |
| `#ED1E79` | botão | **decisão registrada**: `primary` do produto é `#D01165`; Figma diverge |

Nenhum valor sai desta tabela por omissão. Ou vira token, ou vira decisão escrita.

## Auto layout → widget

| Figma | Flutter |
|---|---|
| Auto layout horizontal / vertical | `Row` / `Column` |
| `gap` (item spacing) | `spacing:` do `Row`/`Column` (Flutter ≥ 3.27) ou o widget de gap do design system |
| `gap: auto` (space between) | `mainAxisAlignment: spaceBetween` |
| Padding | `Padding` com o token, no container, não em cada filho |
| Fill container (largura/altura) | `Expanded` dentro de `Row`/`Column`; `double.infinity` / `SizedBox.expand` fora |
| Hug contents | `mainAxisSize: MainAxisSize.min`; para texto, nada (texto já abraça) |
| Fixed | `SizedBox` com a medida |
| Min / max de largura ou altura | `ConstrainedBox` |
| Wrap | `Wrap` com `spacing` e `runSpacing` |
| Posição absoluta dentro de frame | `Stack` + `Positioned` — confirme que era intencional |
| Constraints: left/right, top/bottom, scale, center | `Positioned` com os dois lados, `Align`, `FractionallySizedBox` |
| Layout grid (colunas, gutter, margem) | padding horizontal = margem; `LayoutBuilder` quando a contagem de colunas muda com a largura |
| Clip content | `ClipRRect` / `ClipRect` com o mesmo raio do container |
| Frame com scroll | `ListView` / `SingleChildScrollView` / `CustomScrollView` com slivers; nunca `Expanded` dentro dele |

## Armadilhas Figma → Flutter (um designer nota todas)

| Propriedade | Figma | Flutter | O que fazer |
|---|---|---|---|
| Altura de linha | px (ex.: 24 numa fonte 16) ou % | `TextStyle.height` é **multiplicador** | `height = lineHeightPx / fontSize` (24/16 = 1,5). O Figma centraliza o leading extra; o Flutter por padrão joga para cima. Use `textHeightBehavior: TextHeightBehavior(leadingDistribution: TextLeadingDistribution.even)` quando o texto está em caixa de altura fixa. |
| Letter spacing | % do tamanho da fonte ou px | `letterSpacing` em px lógico | `% × fontSize / 100`. `get_design_context` já entrega em px. |
| Alinhamento de stroke | inside / center / outside | `BorderSide.strokeAlign` (padrão inside) | Bata igual. Stroke outside em canto arredondado ainda difere um pouco (issue Flutter #117829). |
| Borda e padding | padding medido da borda do frame; stroke não muda layout | `Container(padding, decoration: border)` **soma a largura da borda ao padding** | Subtraia a largura da borda do token de padding, ou coloque a borda num `DecoratedBox` externo e o padding dentro. O probe mostra `padding: 17` onde o Figma diz 16. |
| Números ímpares no `get_design_context` | `p-px` no card mais `pt-[17px]`, `px-[17px]`, `py-[13px]`, `h-[46px]` dentro | — | A saída React já somou o 1 px de borda aos paddings internos. Leia 17 como 16 + borda, 13 como 12 + borda, 46 como 44 + 2; escreva o token (16, 12) e deixe a borda ser borda. Um `.5` numa altura (`212.5`) é o mesmo artefato. |
| Opacidade de layer vs de fill | opacidade de layer afeta o grupo inteiro; de fill só a cor | widget `Opacity` vs alpha na `Color` | Layer → `Opacity` (ou `.withValues(alpha:)` quando é uma cor só). Fill → alpha da cor. Nunca `Opacity` para uma caixa de cor única. |
| Sombra | x, y, blur, spread, cor com alpha | `BoxShadow(offset, blurRadius, spreadRadius, color)` | Mapeie 1:1. Sombra **interna** do Figma não tem equivalente direto; use `BlurStyle.inner` ou aceite a divergência na tabela 3. |
| Blend mode | multiply, screen, overlay | `BlendMode` em `ColorFiltered` / `ShaderMask` / `Paint` | Pergunte se o blend é intencional; a maioria é sobra. |
| Gradiente | ângulo em graus, stops | `LinearGradient(begin, end)` com `Alignment` | Converta o ângulo: 90° no Figma é `topCenter → bottomCenter`; 180° é `centerLeft → centerRight`. Use `GradientRotation` para ângulos quebrados. |
| Corner smoothing | 0–100% (iOS usa 60%) | `BorderRadius` não tem | `ContinuousRectangleBorder` aproxima; senão registre na tabela 3. |
| Image fill | fill / fit / crop / tile | `BoxFit.cover / contain / none / ImageRepeat.repeat` | "fill" do Figma = `BoxFit.cover`; "fit" = `BoxFit.contain`. Crop usa transform; exporte a imagem já cortada. |
| Truncamento de texto | auto height / altura fixa com "truncate text" | `maxLines` + `overflow: TextOverflow.ellipsis` | Também `softWrap: false` quando o Figma é linha única e corta. |
| Texto auto width / auto height / fixed | comportamento de largura | hug → nada; largura fixa → `SizedBox(width)`; fill → `Expanded` | Texto sem `Expanded` dentro de `Row` estoura; texto com `Expanded` fora de `Row` quebra. |
| Caixa do texto | transform "uppercase" no estilo | sem transform | Aplique `.toUpperCase()` na string, ou o helper do token de tipografia. Confira a caixa literal na fase 7. |
| Nomes de peso | Regular/Medium/SemiBold/Bold | `FontWeight.w400/500/600/700` | Confirme que a família tem esse peso nas fontes do `pubspec`; peso ausente cai em silêncio para o mais próximo. |
| Tamanho de ícone | frame 24 com glifo 20 dentro | `Icon(size:)` define o **frame** | Use o tamanho do frame; mantenha o padding interno do glifo no SVG. |
| Área mínima de toque | não é desenhada no Figma | Material adiciona 48 dp com `MaterialTapTargetSize.padded` | Mantenha. Se o Figma desenha botão de ícone com 32 px, o visual é 32 e a área de toque é 48; não encolha para bater. |
| Dp vs px | frame do Figma em 1× | px lógico do Flutter = px do Figma em 1× | Sem conversão. Nunca use escala tipo `flutter_screenutil` para "encaixar" um design. |
| Cores com alpha | `#00000014` (8% preto) | `Color(0x14000000)` — ordem ARGB | O probe imprime ARGB; o Figma mostra RGBA. Compare com cuidado. |
| Mesmo componente, larguras diferentes | constraints por lado | responsivo: `LayoutBuilder`, `Flexible`, `Wrap` | Implemente na largura do frame primeiro; depois confirme que 360 e 430 não quebram. |

## Armadilhas

- **Token divergente entre arquivos.** Se o repo tem mais de um arquivo de tokens (um em `docs/`, outro alimentando o codegen), descubra qual gera código antes de editar. Editar o errado não muda nada e parece que mudou.
- **Ícone de outra família.** O Figma pode desenhar um ícone que não existe no conjunto que o app adota. A resposta é o export original do nó do Figma (veja `assets.md`), registrado na classe de ícones do app — nunca um glifo "parecido" do pacote, e nunca um pacote de ícones novo por um ícone.
- **Componente que o catálogo diz existir e não existe.** Confirme no barrel antes de usar.
- **Defaults do Material vazando.** `ElevatedButton`, `Card`, `Chip`, `AppBar` carregam padding, elevação, forma e cores próprios. Quando o design system os embrulha, tudo bem; quando uma feature usa cru, cada default desses é divergência esperando a fase 7.
