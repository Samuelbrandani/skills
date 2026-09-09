# Assets — originais do Figma, importados com cuidado

Ícone redesenhado de memória, glifo "parecido" de um pacote de ícones, ou caixa placeholder são as três formas mais visíveis de uma tela deixar de bater com o design. O pipeline de assets existe para que o export original seja o único caminho.

## 1. Decida o que é asset

Percorra o `get_metadata` e classifique todo nó visual que não é texto nem caixa simples:

| Nó no Figma | Trate como | Formato |
|---|---|---|
| Ícone (instância de um icon set, 16–32 px, cor única) | **asset de ícone** | SVG monocromático, tingido no código |
| Ícone que já existe na classe de ícones do app **com o mesmo desenho** | reuse a entrada existente — confirme renderizando os dois, não pelo nome | — |
| Ilustração, mascote, logo multicolorido, vetor decorativo | **asset de ilustração** | SVG se `svg_check.py` passa; senão PNG/WebP em 1×, 2×, 3× |
| Foto, fill raster, screenshot dentro do design | **asset de imagem** | WebP (ou PNG quando transparência + qualidade exigem) em 1×, 2×, 3× |
| Vetor com blur, drop shadow, sombra interna, máscara ou blend | **rasterize**, a menos que o design system já tenha o efeito como token | PNG/WebP em 1×, 2×, 3× |
| Forma simples: retângulo, círculo, divisor, caixa com gradiente, ponto | **desenhe em código** com tokens | — |
| Fonte da marca | não é asset desta tela; já deve estar nas fontes do `pubspec` | — |
| Lottie / animação | peça o `.json` ao designer; o nó do Figma é só um frame | — |

Na dúvida se um nó é instância de ícone ou grupo desenhado, `search_design_system` com o nome, ou procure `componentId` no `get_design_context`.

## 2. Obtenha os arquivos

Duas fontes, ambas URLs temporárias (cerca de 7 dias no servidor remoto, `localhost` no servidor desktop). Baixe na hora com o shell (`curl -L -o`) para o destino; nunca deixe a URL no código e nunca referencie a CDN do Figma em runtime.

- **`get_design_context`** já devolve uma URL de SVG por camada vetorial (`const imgIcon = "https://…/asset/<id>.svg"`), com o id do nó no markup ao lado. Para ícones, normalmente é tudo que você precisa.
- **`download_assets(fileKey, nodeId)`** — um nó por chamada — devolve o `export` do nó (PNG em 1× a menos que o nó tenha export settings ou você passe `defaultFormat`/`defaultScale`), `rawImages` (o JPEG/PNG/WebP original por trás dos image fills da subárvore, até 20, com o `format` real) e `svgAssets` (o mesmo conjunto vetorial, até 20). Chame no nó da tela ou seção uma vez por formato/escala:

```
download_assets(fileKey, nodeId: "12:40")                                  # export 1x + raw images + svgs
download_assets(fileKey, nodeId: "12:40", defaultFormat: "png", defaultScale: 2)
download_assets(fileKey, nodeId: "12:40", defaultFormat: "png", defaultScale: 3)
```

- `defaultScale` de 0,01 a 4; o lado maior é limitado em ~4096 px. Para um hero de 375 de largura, 3× é 1125 px, ok; para uma ilustração de 2000, 3× estoura — exporte em 2× e anote.
- Prefira `rawImages` para fotos: é o arquivo que o designer subiu, não um export reencodado.
- Exporte o **frame do ícone**, não o vetor interno: o frame carrega o viewBox 24×24 (ou 20×20) com o padding do glifo; o path interno não, e o ícone renderiza maior que os irmãos.
- Para ícones tingidos no app, exporte a **variante padrão (preto ou neutro)** e tinja no código. Não exporte um SVG por cor.
- Renomeie ao salvar. Nomes do Figma como `Icon / Arrow / Right=Default.svg` viram `arrow_right.svg`. O Figma adiciona `@2x`; o Flutter quer o **mesmo nome de arquivo dentro de `2.0x/`**.

## 2b. Identifique a família do ícone antes de decidir qualquer coisa

Baixe todo SVG de ícone para uma pasta de rascunho e olhe a assinatura: Lucide desenha em viewBox 24 com stroke 2 (exportado em 16 px aparece `stroke-width="1.333"`, `stroke-linecap="round"`, `fill="none"`); Phosphor usa 256; Material Symbols são paths preenchidos em 24 (ou 960 quando exportados da fonte). Compare com a família que o Perfil do Repo diz que o app adota.

- **Mesma família** → o ícone mapeia para o token da família (`AppIcons.star` → `LucideIcons.star`); adicione o token quando faltar. Isso satisfaz "só originais": o token renderiza o mesmo desenho que o designer colocou. Nenhum arquivo entra no repo.
- **Família diferente ou desenho próprio** (marca, ilustração, glifo que a família não tem) → o SVG é o asset; siga §3–§5. Se o repo proíbe SVG vendorizado (um ADR tipo "ícones só pela icon font"), isso é uma linha da tabela 3: peça ao design o equivalente na família, ou registre a exceção.
- **Nunca** decida pelo nome da camada ("Icon / Star") — decida pelo desenho. Duas famílias têm estrela; os traços diferem.

## 3. Cheque todo SVG antes de commitar

```
scripts/svg_check.py --dir <pasta-de-destino>
```

`flutter_svg` / `vector_graphics` não renderizam `<filter>` (blur, drop shadow), `<foreignObject>`, `<text>`, `<image>` embutida, blocos CSS `<style>`, `<pattern>`; máscaras e gradientes complexos são parciais. O script bloqueia nesses casos e avisa sobre opacidade de grupo, stroke sub-pixel, `viewBox` ausente, arquivo enorme e ícone multicolorido que deveria ser monocromático.

Para um **BLOCK**:

- `filter` / sombra → peça ao designer para achatar, ou rasterize (PNG/WebP em 1×/2×/3×), ou reproduza a sombra com token `BoxShadow` no container e exporte o vetor sem ela.
- `text` → converta o texto em curvas no Figma (botão direito → Outline stroke / Flatten) e reexporte.
- bloco `style` → reexporte com "Outline text" e "Simplify stroke" ligados; ou rode `svgo` com `inlineStyles` e `convertStyleToAttrs`.
- `image` → exporte como raster.

Opcional mas recomendado: `svgo --multipass --config '{"plugins":[{"name":"preset-default","params":{"overrides":{"removeViewBox":false}}}]}'` para tirar metadados do Figma e reduzir tamanho. Mantenha o `viewBox`. Para conjuntos com dezenas de ícones, pré-compile com `vector_graphics_compiler` para `.svg.vec` se o repo já faz isso; não introduza por uma tela.

## 4. Coloque onde o repo coloca

O Perfil do Repo diz onde. Típico:

```
packages/<design_system>/assets/icons/<nome>.svg           # ícones que o design system possui
packages/app/assets/images/<nome>.webp                      # imagens de feature
packages/app/assets/images/2.0x/<nome>.webp
packages/app/assets/images/3.0x/<nome>.webp
packages/app/assets/illustrations/<nome>.svg
```

Depois registre:

1. `pubspec.yaml` → `flutter: assets:` com a **pasta** (`assets/images/`) para as pastas de escala resolverem sozinhas. Listar um arquivo não pega o irmão `2.0x`.
2. Se o repo usa `flutter_gen` (`Assets.icons.arrowRight`), rode o gerador (`dart run build_runner build -d`) e use o acessor gerado.
3. Se o repo tem classe de ícones (`AppIcons.arrowRight` → `SvgPicture.asset`), adicione a entrada lá com o mesmo padrão de nome dos irmãos; código de feature nunca chama `SvgPicture.asset('assets/…')` direto quando essa classe existe.
4. Asset de pacote usado por outro pacote: `AssetImage('assets/x.png', package: 'acme_design_system')`, e o asset precisa estar declarado no pubspec **daquele** pacote.

## 5. Renderize e verifique

- Ícone: `SvgPicture.asset(path, width: 24, height: 24, colorFilter: ColorFilter.mode(color, BlendMode.srcIn))`. Tamanho vem do frame do Figma; cor, de token.
- Raster: `Image.asset(path, width, height, fit)`. Nunca `Image.asset` sem tamanho quando o Figma fixa um; o tamanho intrínseco do arquivo 3× é três vezes o pretendido.
- `cacheWidth`/`cacheHeight` para listas grandes; só quando o repo já faz.
- Na fase 7 o probe registra `source`, `width`, `height`, `fit`, `tint`; o olho confirma que o desenho é o mesmo do screenshot do Figma. Desenho diferente com o nome certo continua sendo `DIVERGE` no eixo 8.

## 6. Manifesto de assets (vai no relatório)

| Nó Figma | Nome no Figma | Arquivo | Formato / escalas | Usado por | Check |
|---|---|---|---|---|---|
| `12:34` | Icon / Arrow / Right | `assets/icons/arrow_right.svg` | svg, mono | `AppIcons.arrowRight` | OK |
| `12:40` | Hero / Empty state | `assets/illustrations/empty_orders.webp` | webp 1×/2×/3× | `EmptyOrdersSection` | OK |
| `12:50` | Foto do avatar | — | — | imagem de rede em runtime (`User.avatarUrl`) | n/a |

Todo nó visual do passo 1 tem uma linha aqui, inclusive os que resolveram em "já existe" ou "desenhado em código".

## Regras que não dobram

- **Nunca** substitua um ícone pelo glifo mais próximo de `Icons`, `CupertinoIcons`, Lucide, Phosphor ou qualquer pacote, e nunca adicione pacote por uma tela. Se a classe de ícones do design system é um subconjunto curado de um pacote, o ícone novo ainda vem do export do Figma e é adicionado à classe.
- **Nunca** escreva um path SVG à mão nem "recrie" uma ilustração com `CustomPaint` para evitar um export.
- **Nunca** deixe `Placeholder()`, `Container(color: grey)` ou `Icons.image` no lugar de um asset que o Figma tem. Se o download falha, o relatório diz isso e a tela não está pronta.
- **Nunca** commite asset sem a checagem e sem registrar; asset não registrado quebra em runtime só no dispositivo.
- **Nunca** reescale raster em código para esconder export errado; reexporte na escala certa.
