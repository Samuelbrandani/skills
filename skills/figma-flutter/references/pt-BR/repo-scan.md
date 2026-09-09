# Perfil do repo — design system e arquitetura

A skill não carrega arquitetura própria. Ela descobre a do repo e obedece. Este arquivo transforma a saída de `scripts/repo_scan.sh` em decisões.

## 1. Rode a varredura

```
scripts/repo_scan.sh <raiz-do-repo> [feature]   # só leitura, ~5–15 s; o nome da feature destaca pacote, docs e testes dela
```

Ela imprime: toolchain (fvm, melos/workspace), docs de arquitetura, todo pacote com tag de design system / feature / catálogo, barrels, classes `ThemeExtension`, classes com cara de token, extensions de `BuildContext`, pacotes de estilo e codegen, fontes, pastas de assets e de escala, famílias de ícone usadas no código, o layout de primeiro nível sob cada `lib/`, e o ferramental de verificação que já existe (probe, goldens, carregador de fontes, widgetbook, entrypoints, flags de fake).

Depois **leia os docs que ela lista** (`CLAUDE.md` — inclusive o herdado de um diretório pai em monorepo —, `ARCHITECTURE.md`, `docs/README.md`, os ADRs sobre tokens, widgets, testes e ícones, e a spec da feature). Eles sobrepõem qualquer inferência abaixo. Um `CLAUDE.md` pai dizendo "plano primeiro" ou "nunca suba o SDK da raiz" vale para o subprojeto também.

## 2. Decida o status do design system

| Status | Evidência | O que significa para o trabalho |
|---|---|---|
| **pronto** | pacote ou pasta com barrel exportando componentes; classes de token para cor, tipografia, espaçamento, raio (idealmente sombra e ícones); extension de `BuildContext` ou `ThemeExtension` como padrão de acesso; componentes já usados pelas telas de feature | Componha a partir dele. Token ou componente novo passa pelas convenções dele (teste, catálogo, export). Valor cru em feature é defeito. |
| **parcial** | tokens existem (`AppColors`, `AppTextStyles`) mas poucos ou nenhum componente compartilhado; ou componentes existem mas tokens estão espalhados/duplicados; ou catálogo que não bate com o barrel | Use o que existe, estenda onde a tela precisa (token novo, componente novo), e escreva a extensão no lugar do design system, não na feature. Registre no relatório o que faltava. |
| **ausente** | sem classes de token; `Color(0x…)` e `TextStyle(...)` inline pelas features; nenhum widget compartilhado além dos defaults do Material | Não invente um design system dentro de uma feature. Crie a fundação mínima que a tela precisa (`AppColors`, `AppTypography`, `AppSpacing`, `AppRadii`, `AppShadows`) em `lib/core/theme/` ou `lib/ui/core/` seguindo o layout do repo, ligue em `ThemeData`/`ThemeExtension`, e declare no relatório que uma fundação foi criada. |

Quando existem duas fontes de token (um `docs/tokens.json` e um `lib/src/foundation/*.dart`), descubra qual **gera código** (procure `tool/generate_*.dart`, `build.yaml`, `style-dictionary`, anotações `theme_tailor`). Edite a fonte, rode o gerador, nunca a saída.

## 3. Localize onde cada coisa vai

Responda estas seis perguntas e escreva as respostas no perfil. A varredura dá a evidência; os docs dão a regra.

1. **Componente do design system** (reutilizável, sem conhecimento de domínio: botão, chip, casca de card, input, badge) → `packages/<nome>_design_system/lib/src/<atoms|molecules|components>/`, exportado do barrel, com o mesmo teste e entrada de catálogo que os irmãos têm.
2. **Organismo de domínio** (reutilizável dentro do produto mas conhece o domínio: `PatientCard`, `OrderSummary`) → onde o repo já os coloca (`core_ui`, `shared/widgets`, `ui/core/ui`). Se ainda não existe nada parecido, a pasta de widgets da própria feature, sinalizado como candidato a promoção.
3. **Seção de tela** (usada uma vez) → a pasta de widgets da feature, ao lado da página: `features/<f>/presentation/widgets/`, `lib/src/sections/`, `lib/ui/<f>/widgets/`. Siga a feature irmã mais parecida.
4. **Página / rota** → o `pages/` ou `screens/` da feature e o arquivo de rotas que a varredura achou (`go_router`, `auto_route`, `flutter_modular`).
5. **Assets** → a pasta de assets do pacote dono do widget: ícones do design system no pacote do design system, ilustrações de feature no app ou no pacote da feature. Siga os nomes de subpasta existentes (`icons/`, `images/`, `illustrations/`) e as pastas de escala.
6. **Testes** → espelho do caminho do widget sob `test/`, mais `test/design/` (ou onde a varredura achou testes de probe/golden existentes) para o snapshot de conformidade.

## 4. Resuma a arquitetura (curto, mas escrito)

Um parágrafo cada, a partir de evidência, não de suposição:

- **Estado**: bloc/cubit, riverpod, provider, mobx, signals. Onde vive o cubit da tela e como a página o obtém (injeção por construtor, `BlocProvider`, `ref.watch`).
- **DI**: módulo `get_it`, providers riverpod, binds do modular. Como uma dependência nova é registrada; se views podem resolver algo sozinhas (normalmente só o cubit da tela no `initState`).
- **Navegação**: pacote de rotas, como rotas são declaradas, como params são tipados.
- **Dado**: como entities chegam à view (entity tipada de um use case, nunca `Map` cru), onde vivem fakes/fixtures, qual flag `--dart-define` liga os fakes.
- **Lint e convenções**: pacote de lint próprio, `analysis_options`, regras como "sem `EdgeInsets` cru" ou "sem `Colors.*`". A varredura lista classes de regra quando há pacote de lint; leia, elas codificam o contrato do design system.
- **Entrypoints**: `main_dev.dart` vs `main.dart`, flavors, target web habilitado ou não (decide como a fase 7 renderiza a tela).
- **Regra de promoção**: o que o repo diz sobre widget usado por duas features (típico: "o PR que cria o segundo uso promove para o pacote compartilhado, com teste e catálogo"). Isso decide onde vão as peças reaproveitadas de onboarding/checkout/etc.

## 5. Modelo de Perfil do Repo

Escreva no topo do relatório, em até 40 linhas.

```
## Perfil do Repo
- Toolchain: fvm 3.x · monorepo melos · target web: sim
- Design system: PRONTO — packages/acme_design_system (barrel acme_design_system.dart, 77 exports)
  tokens: AcmeColors, AcmeTypography, AcmeSpacing, AcmeRadii, AcmeShadows via context.acme.* (ThemeExtension)
  ícones: AcmeIcons (subconjunto lucide) · svg via SvgPicture · catálogo: widgetbook/ (+ docs/design-system/catalog.md, reconciliar)
  componente novo exige: test/<nome>_test.dart + use case no widgetbook + export no barrel
- Organismos de domínio: packages/core_ui (PatientCard, OpportunityCard …)
- Layout de feature: packages/feature_<x>/lib/src/{pages,sections,components,cubit}
- Estado/DI/Nav: cubit + módulo get_it por feature · go_router com params tipados
- Dado: entities de core_domain; fakes atrás de --dart-define=ACME_FAKES=true; seeds em core_data/lib/src/fakes/
- Assets: ícones do DS em packages/acme_design_system/assets/icons (svg); imagens do app em packages/app/assets/images com 2.0x/3.0x
- Verificação: design probe presente (acme_design_system/testing.dart) · fontes carregadas em teste · sem goldens
- Docs lidos: CLAUDE.md, docs/adr/0007-design-system-tokens.md
```

## 6. Respeitando o perfil

- Nunca crie `lib/widgets/`, `lib/components/`, `common/` ou um `utils.dart` quando o repo já tem lugar para a coisa.
- Nunca adicione dependência de estilo (`flutter_screenutil`, `google_fonts`, pacote de ícones, `styled_widget`) para atender uma tela. Se o repo não tem, a tela também não precisa.
- Nunca contorne o padrão de acesso (`Theme.of(context).extension<AcmeColors>()!` quando o repo usa `context.acme.colors`).
- Se a arquitetura proíbe algo que o Figma parece exigir (cor crua, fonte avulsa), a resposta é um token ou uma divergência escrita, nunca uma exceção na feature.
