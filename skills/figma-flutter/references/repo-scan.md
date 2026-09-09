# Repo profile — design system and architecture

The skill does not carry an architecture of its own. It discovers the repo's and obeys it. This file turns the output of `scripts/repo_scan.py` into decisions.

## 1. Run the scan

```
python3 scripts/repo_scan.py <repo-root> [feature]   # read-only, < 2 s on a 20-package monorepo; standard library only
```

Windows: `py -3 scripts\repo_scan.py …` or `.\scripts\repo_scan.ps1 …`. macOS/Linux shells can also call `scripts/repo_scan.sh …`, a wrapper around the same Python file. The `feature` argument spotlights that feature's package, docs and tests.

It prints: toolchain (fvm, melos/workspace), architecture docs, every package with a design-system / feature / catalog tag, barrels, `ThemeExtension` classes, token-like classes, `BuildContext` extensions, styling and codegen packages, fonts, asset dirs and scale folders, icon families used in code, the top-level layout under each `lib/`, and the verification tooling that already exists (probe, goldens, font loader, widgetbook, entrypoints, fake-data flags).

Then **read the docs it lists** (`CLAUDE.md` — including one inherited from a parent directory in a monorepo —, `ARCHITECTURE.md`, `docs/README.md`, the ADRs about tokens, widgets, tests and icons, and the feature's spec). They override anything inferred below. A parent `CLAUDE.md` saying "plan first" or "never bump the root SDK" applies to the sub-project too.

## 2. Decide the design-system status

| Status | Evidence | What it means for the job |
|---|---|---|
| **ready** | a package or dir with a barrel exporting components; token classes for color, typography, spacing, radius (and ideally shadow, icons); a `BuildContext` extension or `ThemeExtension` as the access pattern; components already used by feature screens | Compose from it. New tokens or components go through its conventions (test, catalog, export). Raw values in a feature are a defect. |
| **partial** | tokens exist (`AppColors`, `AppTextStyles`) but few or no shared components; or components exist but tokens are scattered/duplicated; or a catalog doc that does not match the barrel | Use what exists, extend it where the screen needs (new token, new component), and write the extension in the design-system location, not in the feature. Note in the report what was missing. |
| **absent** | no token classes; `Color(0x…)` and `TextStyle(...)` inline across features; no shared widgets beyond Material defaults | Do not invent a design system inside a feature. Create the minimum foundation the screen needs (`AppColors`, `AppTypography`, `AppSpacing`, `AppRadii`, `AppShadows`) in `lib/core/theme/` or `lib/ui/core/` following the repo's layout, wire it into `ThemeData`/`ThemeExtension`, and state in the report that a foundation was created. |

When two token sources exist (a `docs/tokens.json` and a `lib/src/foundation/*.dart`), find which one **generates code** (look for `tool/generate_*.dart`, `build.yaml`, `style-dictionary`, `theme_tailor` annotations). Edit the source, run the generator, never the output.

## 3. Locate where things go

Answer these six questions and write the answers in the profile. The scan gives the evidence; the docs give the rule.

1. **Design-system component** (reusable, no domain knowledge: button, chip, card shell, input, badge) → `packages/<name>_design_system/lib/src/<atoms|molecules|components>/`, exported from the barrel, with the same test and catalog entry its siblings have.
2. **Domain organism** (reusable inside the product but knows the domain: `PatientCard`, `OrderSummary`) → wherever the repo already puts them (`core_ui`, `shared/widgets`, `ui/core/ui`). If nothing like it exists yet, the feature's own widget folder, and flag it as a candidate for promotion.
3. **Screen section** (used once) → the feature's widget folder, next to the page: `features/<f>/presentation/widgets/`, `lib/src/sections/`, `lib/ui/<f>/widgets/`. Follow the sibling feature that is most similar.
4. **Page / route** → the feature's `pages/` or `screens/` and the router file the scan found (`go_router`, `auto_route`, `flutter_modular`).
5. **Assets** → the asset dir of the package that owns the widget: design-system icons in the design-system package, feature illustrations in the app or feature package. Follow the existing subfolder names (`icons/`, `images/`, `illustrations/`) and scale folders.
6. **Tests** → mirror of the widget path under `test/`, plus `test/design/` (or wherever the scan found existing probe/golden tests) for the conformance snapshot.

## 4. Summarize the architecture (short, but written)

One paragraph each, from evidence, not from assumptions:

- **State**: bloc/cubit, riverpod, provider, mobx, signals. Where the screen's cubit lives and how the page obtains it (constructor injection, `BlocProvider`, `ref.watch`).
- **DI**: `get_it` module, riverpod providers, modular binds. How a new dependency is registered; whether views are allowed to resolve anything themselves (usually only the screen cubit in `initState`).
- **Navigation**: router package, how routes are declared, how params are typed.
- **Data**: how entities reach the view (typed entity from a use case, never a raw `Map`), where fakes/fixtures live, which `--dart-define` flag switches to fakes.
- **Lint and conventions**: custom lint package, `analysis_options`, rules like "no raw `EdgeInsets`" or "no `Colors.*`". The scan lists lint rule classes when there is a lint package; read them, they encode the design-system contract.
- **Entrypoints**: `main_dev.dart` vs `main.dart`, flavors, web target enabled or not (decides how phase 7 renders the screen).
- **Promotion rule**: what the repo says about a widget used by two features (typical: "the PR that creates the second use promotes it to the shared package, with test and catalog entry"). This decides where the reused onboarding/checkout/whatever pieces go.

## 5. Repo Profile template

Write it at the top of the report and keep it under 40 lines.

```
## Repo Profile
- Toolchain: fvm 3.x · melos monorepo · web target: yes
- Design system: READY — packages/acme_design_system (barrel acme_design_system.dart, 77 exports)
  tokens: AcmeColors, AcmeTypography, AcmeSpacing, AcmeRadii, AcmeShadows via context.acme.* (ThemeExtension)
  icons: AcmeIcons (lucide subset) · svg via SvgPicture · catalog: widgetbook/ (+ docs/design-system/catalog.md, reconcile)
  new component requires: test/<name>_test.dart + widgetbook use case + export in barrel
- Domain organisms: packages/core_ui (PatientCard, OpportunityCard …)
- Feature layout: packages/feature_<x>/lib/src/{pages,sections,components,cubit}
- State/DI/Nav: cubit + get_it module per feature · go_router with typed params
- Data: entities from core_domain; fakes behind --dart-define=ACME_FAKES=true; seeds in core_data/lib/src/fakes/
- Assets: design-system icons in packages/acme_design_system/assets/icons (svg); app images in packages/app/assets/images with 2.0x/3.0x
- Verification: design probe present (acme_design_system/testing.dart) · fonts loaded in tests · no goldens
- Docs read: CLAUDE.md, docs/adr/0007-design-system-tokens.md
```

## 6. Respecting it

- Never create `lib/widgets/`, `lib/components/`, `common/` or a `utils.dart` when the repo has a place for the thing already.
- Never add a styling dependency (`flutter_screenutil`, `google_fonts`, an icon pack, `styled_widget`) to satisfy a screen. If the repo has none, the screen does not need one either.
- Never bypass the access pattern (`Theme.of(context).extension<AcmeColors>()!` when the repo uses `context.acme.colors`).
- If the architecture forbids something the Figma seems to require (a raw color, a one-off font), the answer is a token or a written divergence, never an exception in the feature.
