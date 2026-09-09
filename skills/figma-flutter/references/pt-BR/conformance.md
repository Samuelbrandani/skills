# Conformidade

Nenhuma tela está pronta antes desta fase. Duas conferências, ambas obrigatórias: **medir** e **olhar**. Elas pegam defeitos diferentes.

## Por que não só golden de imagem

Golden de CI renderiza texto com a fonte de teste Ahem — cada glifo vira um retângulo — e desliga sombra. Prova que a estrutura não regrediu; **não enxerga família, tamanho nem peso de fonte, cor de texto ou sombra**. Justamente onde layout diverge do Figma. Golden verde ao lado de tela errada não é contradição: medem coisas diferentes.

Golden com fontes reais (`alchemist`, `flutter_test_goldens`, um `flutter_test_config.dart` que carrega fontes) é boa rede de regressão depois que a tela está certa. Ainda é uma imagem: 2 px de padding deslocado aparece como mancha vermelha, não como "16 → 18". O probe dá o número.

## Conferência 1 — medir (design probe)

Percorre a árvore renderizada e despeja o valor real de cada nó em JSON: rect (x, y, w, h), padding, raio, borda, sombra, gradiente, opacidade, cor, e por texto família, tamanho, peso, altura de linha, letter spacing, overflow; por ícone glifo e tamanho; por imagem asset e fit; alvos de toque. Compare **número contra número** com o que `get_variable_defs` e `get_design_context` devolveram para o nó.

Isso pega o que o olho não pega: 2 px de padding, peso 600 onde o Figma pede 700, letter spacing errado, sombra ausente, fundo derivado da primitiva errada, borda somada ao padding em silêncio.

**Se o repo tem probe** (a varredura lista `probeDesign` / `expectDesignSnapshot` ou similar), use exatamente como os testes vizinhos usam.

**Se não tem**, copie `assets/design_probe.dart` desta skill para o repo (`test/support/design_probe.dart` em pacote único, ou `lib/testing/design_probe.dart` do pacote do design system com um barrel `testing.dart` em monorepo). Não depende de nada além de `flutter_test` e compila em Flutter ≥ 3.10 (Dart 3): cores passam por `Color.value` com ignore de deprecação, e `Flex.spacing` (3.27+) é lido por reflexão e simplesmente não aparece no JSON em SDKs antigos. Então:

```dart
import 'support/design_probe.dart';

void main() {
  setUpAll(loadAppFonts); // fontes reais, senão o texto é medido com Ahem

  testWidgets('OrderCard bate com Figma 7880:10562', (tester) async {
    await tester.binding.setSurfaceSize(const Size(390, 1200)); // largura do frame
    await tester.pumpWidget(appHarness(const OrderCard(order: richOrderFixture)));
    await tester.pumpAndSettle();

    final probe = probeDesign(tester.element(find.byType(OrderCard)), label: 'order_card');
    expectDesignSnapshot(probe, path: 'test/design/snapshots/order_card.json');
    expectMinTapTargets(probe); // 48 dp
  });
}
```

`probeDesign` mede; `expectDesignSnapshot` grava o JSON na primeira vez e, depois, **falha quando um número muda** — rede de regressão em texto que dá diff legível no PR e enxerga exatamente o que o golden de imagem não via. Para aceitar mudança intencional: `UPDATE_DESIGN_SNAPSHOTS=true`.

`appHarness` é o que o repo usa para pumpar um widget com tema e localização; a varredura lista helpers tipo `pumpApp`. Se não há nenhum, embrulhe em `MaterialApp(theme: <tema do app>)`. Widget medido sem o tema do app mede defaults do Material, não o design system.

Leia o JSON ao lado dos valores do Figma e preencha a tabela de eixos. O primeiro snapshot é **medida**, não prova: compare com o Figma antes de commitar como baseline.

## Conferência 2 — olhar

O probe não vê composição: ordem trocada, elemento faltando, hierarquia visual invertida, ícone que é o desenho errado. Para isso, render real com as fontes do app, **na largura do frame do Figma**.

**Componente do design system** → catálogo de componentes (Widgetbook e afins) no browser, que já tem tema, fontes reais e seletor de viewport.

**Seção ou tela inteira** → o app rodando com fakes. Escolha pelo que o Perfil do Repo achou:

| Repo tem | Renderize com | Capture |
|---|---|---|
| target web + flag de fakes | `flutter run -d chrome -t lib/main_dev.dart --dart-define=<FLAG_FAKES>=true` | ferramentas do browser: redimensione a janela para a largura do frame, navegue até o estado exato, screenshot |
| sem target web | simulador iOS ou emulador Android com dispositivo cuja largura lógica é a do frame (390 → iPhone 14/15; 360 → classe Pixel 5) | `flutter screenshot` (precisa de `--observatory-uri` em SDKs novos) ou `xcrun simctl io booted screenshot` / `adb exec-out screencap -p` |
| integration_test configurado | `integration_test` com `binding.takeScreenshot('tela_estado')` | arquivos em `integration_test/screenshots/` |
| Maestro / Patrol configurado | o fluxo que chega ao estado, depois `takeScreenshot` | pasta de saída deles |

Redimensionar para a largura do frame não é opcional: os mesmos padding e fonte dentro de uma caixa 25% mais larga produzem uma tela que parece apertada e pequena, e a divergência é do método, não do código. Navegue até o estado exato que o nó do Figma mostra (aba certa, filtro aplicado, item certo) e capture.

Salve a captura ao lado do PNG do Figma, versionados, com nome que amarre `tela ↔ node`. Depois abra os dois no mesmo tamanho e passe pelos eixos abaixo. Sobreponha a 50% de opacidade quando a composição parece próxima mas "algo está errado"; o deslocamento salta aos olhos.

## Os 12 eixos

| # | Eixo | Quem confere |
|---|---|---|
| 1 | Background do Scaffold e de cada superfície | probe |
| 2 | Borda — existe? cor, espessura, raio, alinhamento do stroke | probe |
| 3 | Sombra — existe? offset, blur, spread, opacidade | probe |
| 4 | Fonte — família, tamanho, peso, altura de linha, letter spacing, **caixa** | probe |
| 5 | Cor de texto por nível hierárquico | probe |
| 6 | Espaçamento — padding, gap, margem | probe |
| 7 | Alinhamento e quem estica | olho |
| 8 | Ícone e imagem — desenho, tamanho, cor, fundo, fit | olho (desenho) + probe (tamanho, cor, asset) |
| 9 | Texto literal, com acento e pontuação | probe |
| 10 | Estados — todo estado do Figma (loading, vazio, erro, desabilitado, selecionado, pressionado) renderizado e capturado | olho, uma captura por estado |
| 11 | Acessibilidade — alvos de toque ≥ 48 dp, semantics em controles só-ícone, contraste do texto sobre o fundo ≥ 4,5:1 | probe (`expectMinTapTargets`) + `meetsGuideline(textContrastGuideline)` + olho |
| 12 | Resiliência — escala de texto 1,3× sem overflow ou corte, texto mais longo do seed, larguras 360 e 430 ainda seguram | probe (`didOverflow`) + olho |

Os eixos 10–12 são o que separa "bate com o screenshot" de "um designer assinaria embaixo". Não são opcionais no modo `implementar`; no modo `auditar`, reporte com o mesmo rigor.

Veredito por eixo, por tela:

| Eixo | Status | Figma | App |
|---|---|---|---|
| 3 Sombra | DIVERGE | `0 2 8 rgba(0,0,0,.08)` | ausente (`elevation: 0`) |
| 4 Fonte | DIVERGE | "Ver detalhes" | "VER DETALHES" |
| 6 Espaçamento | OK | 20 | 20 |
| 11 A11y | DIVERGE | — | botão fechar 32×32 (< 48) |

## Loop

`DIVERGE` → corrigir → medir e olhar de novo. Sem limite de voltas. Sai quando todo eixo está `OK` ou tem justificativa escrita.

Justificativa aceitável: "o Figma usa raio 12; a escala do produto tem 16; decisão de 04/09/2026 mantém 16". Não aceitável: "diferença pequena", "aceitável", "não deu tempo".

Se as duas conferências passarem e o olho ainda vir diferença, o defeito está **nesta lista de eixos ou no probe**: acrescente o eixo que faltou, ensine o probe a medir a propriedade que faltou, e refaça a passada. Os dois são vivos.

## Modo auditar

Mesmo procedimento, sem tocar em código. Entrega: a tabela dos 12 eixos por tela e as correções propostas em ordem de gravidade visual, cada uma apontando o arquivo e o token que deveria ser usado.
