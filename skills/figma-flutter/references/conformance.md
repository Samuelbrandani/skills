# Conformance

No screen is done before this phase. Two checks, both mandatory: **measure** and **look**. They catch different defects.

## Why not image goldens alone

CI goldens render text with the Ahem test font — every glyph a rectangle — and disable shadows. They prove the structure did not regress; **they do not see font family, size, or weight, text color, or shadow**. Exactly where layouts diverge from Figma. A green golden next to a wrong screen is not a contradiction: they measure different things.

Goldens with real fonts (`alchemist`, `flutter_test_goldens`, a `flutter_test_config.dart` that loads fonts) are a good regression net once the screen is right. They are still a picture: a 2 px padding drift shows as a red smear, not as "16 → 18". The probe gives the number.

## Check 1 — measure (design probe)

Walk the rendered tree and dump the real value of every node to JSON: rect (x, y, w, h), padding, radius, border, shadow, gradient, opacity, color, and for text the family, size, weight, line height, letter spacing, overflow; for icons the glyph and size; for images the asset and fit; tap targets. Compare **number against number** with what `get_variable_defs` and `get_design_context` returned for the node.

This catches what the eye does not: 2 px of padding, weight 600 where the Figma asks 700, wrong letter spacing, missing shadow, background derived from the wrong primitive, a border silently added to the padding.

**If the repo has a probe** (the scan lists `probeDesign` / `expectDesignSnapshot` or similar), use it exactly as the neighboring tests do.

**If it does not**, copy `assets/design_probe.dart` from this skill into the repo (`test/support/design_probe.dart` for a single package, or `lib/testing/design_probe.dart` of the design-system package with a `testing.dart` barrel for a monorepo). It has no dependencies beyond `flutter_test`. Then:

```dart
import 'support/design_probe.dart';

void main() {
  setUpAll(loadAppFonts); // real fonts, or text is measured with Ahem

  testWidgets('OrderCard matches Figma 7880:10562', (tester) async {
    await tester.binding.setSurfaceSize(const Size(390, 1200)); // frame width
    await tester.pumpWidget(appHarness(const OrderCard(order: richOrderFixture)));
    await tester.pumpAndSettle();

    final probe = probeDesign(tester.element(find.byType(OrderCard)), label: 'order_card');
    expectDesignSnapshot(probe, path: 'test/design/snapshots/order_card.json');
    expectMinTapTargets(probe); // 48 dp
  });
}
```

`probeDesign` measures; `expectDesignSnapshot` writes the JSON the first time and **fails when a number changes** afterwards — a regression net in text that diffs legibly in a PR and sees exactly what the image golden did not. Accept an intentional change with `UPDATE_DESIGN_SNAPSHOTS=true`.

`appHarness` is whatever the repo uses to pump a widget with its theme and localization; the scan lists existing `pumpApp`-style helpers. If there is none, wrap in `MaterialApp(theme: <the app's theme>)`. A widget probed without the app's theme measures Material defaults, not the design system.

Read the JSON next to the Figma values and fill the axis table. The first snapshot is a **measurement**, not a proof: compare it to the Figma before committing it as the baseline.

## Check 2 — look

The probe does not see composition: swapped order, missing element, inverted visual hierarchy, an icon that is the wrong drawing. For that, a real render with the app's fonts, **at the Figma frame width**.

**Design-system component** → the component catalog (Widgetbook or similar) in the browser, which already has the theme, real fonts, and a viewport selector.

**Section or whole screen** → the app running with fakes. Choose by what the Repo Profile found:

| Repo has | Render with | Capture |
|---|---|---|
| web target + fakes flag | `flutter run -d chrome -t lib/main_dev.dart --dart-define=<FAKES_FLAG>=true` | browser tools: resize the window to the frame width, navigate to the exact state, screenshot |
| no web target | iOS simulator or Android emulator with a device whose logical width equals the frame (390 → iPhone 14/15; 360 → Pixel 5-class) | `flutter screenshot` (needs `--observatory-uri` on newer SDKs) or `xcrun simctl io booted screenshot` / `adb exec-out screencap -p` |
| integration_test set up | `integration_test` with `binding.takeScreenshot('screen_state')` | files under `integration_test/screenshots/` |
| Maestro / Patrol set up | the flow that reaches the state, then `takeScreenshot` | their output dir |

Resizing to the frame width is not optional: the same padding and fonts inside a box 25% wider produce a screen that looks cramped and small, and the divergence is in the method, not in the code. Navigate to the exact state the Figma node shows (right tab, filter applied, right item) and capture.

Save the capture next to the Figma PNG, versioned, with a name that ties `screen ↔ node`. Then open both at the same size and go through the axes below. Overlay them at 50% opacity when the composition looks close but "something is off"; the offset jumps out.

## The 12 axes

| # | Axis | Who checks |
|---|---|---|
| 1 | Background of the Scaffold and of every surface | probe |
| 2 | Border — exists? color, width, radius, stroke alignment | probe |
| 3 | Shadow — exists? offset, blur, spread, opacity | probe |
| 4 | Font — family, size, weight, line height, letter spacing, **case** | probe |
| 5 | Text color per hierarchy level | probe |
| 6 | Spacing — padding, gap, margin | probe |
| 7 | Alignment and who stretches | eye |
| 8 | Icon and image — drawing, size, color, background, fit | eye (drawing) + probe (size, color, asset) |
| 9 | Literal text, with accents and punctuation | probe |
| 10 | States — every Figma state (loading, empty, error, disabled, selected, pressed) rendered and captured | eye, one capture per state |
| 11 | Accessibility — tap targets ≥ 48 dp, semantics on icon-only controls, contrast of text on its background ≥ 4.5:1 | probe (`expectMinTapTargets`) + `meetsGuideline(textContrastGuideline)` + eye |
| 12 | Resilience — 1.3× text scale without overflow or clipped text, longest seed text, 360 and 430 widths still hold | probe (`didOverflow`) + eye |

Axes 10–12 are what separates "matches the screenshot" from "a designer would sign it off". They are not optional in `implement` mode; in `audit` mode report them with the same rigor.

Verdict per axis, per screen:

| Axis | Status | Figma | App |
|---|---|---|---|
| 3 Shadow | DIVERGE | `0 2 8 rgba(0,0,0,.08)` | absent (`elevation: 0`) |
| 4 Font | DIVERGE | "See details" | "SEE DETAILS" |
| 6 Spacing | OK | 20 | 20 |
| 11 A11y | DIVERGE | — | close button 32×32 (< 48) |

## Loop

`DIVERGE` → fix → measure and look again. No limit on rounds. Exit when every axis is `OK` or has a written justification.

Acceptable justification: "the Figma uses radius 12; the product scale has 16; decision of 2026-09-04 keeps 16". Not acceptable: "small difference", "acceptable", "no time".

If both checks pass and the eye still sees a difference, the defect is **in this axis list or in the probe**: add the missing axis, teach the probe to measure the missing property, and redo the pass. Both are living artifacts.

## Audit mode

Same procedure, without touching code. Deliverable: the 12-axis table per screen and the proposed fixes ordered by visual severity, each pointing at the file and the token that should be used.
