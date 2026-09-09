# Mapping Figma → Flutter (de-para)

Code Connect has no Dart parser, so the mapping is written by hand. It is the step that separates "composed with the design system" from "generated a new widget that looks similar".

## Order of preference, no exceptions

1. **Reuse** a widget that already exists, as is.
2. **Extend** an existing one (new parameter, new enum variant).
3. **Create** a new component — only when the Figma defines something no existing one covers, with a written justification.

Acceptable justification: "the Figma defines a status strip with a colored dot and a badge on the right; no current component combines both". Not acceptable: "it was faster".

A Figma **component set** maps to one widget with one enum per variant axis; **boolean properties** map to named parameters; **instance swap** properties map to a `Widget` parameter or an enum of allowed icons; **text properties** map to `String` parameters. Keep the Figma names (`kind: primary | secondary`, not `type: 1 | 2`).

## Table 1 — node → widget

| Node | Figma name | Decision | Widget | Justification |
|---|---|---|---|---|
| `7880:10562` | Period card | reuse | `AcmeDateRangeCard` | — |
| `7880:10570` | Filter chip | extend | `AcmeFilterChip` + count | Figma shows `Region · 2` |
| `7880:10588` | Status strip | new | `AcmeStatusStrip` | dot + label + badge, no equivalent |

## Table 2 — Figma variable → token

One line per variable returned by `get_variable_defs`.

| Figma variable | Value | Flutter token | Note |
|---|---|---|---|
| `color/semantic/primary` | `#D01165` | `context.acme.colors.primary` | — |
| `typography/card-title` | Titillium 700 16/24 | `context.acme.typography.cardTitle` | — |
| `spacing/md` | 16 | `AcmeSpacing.md` | — |

Rules:

- **Color** becomes a semantic slot, never a primitive and never `Color(0x...)` outside the design system.
- **Text** becomes a whole typography variant (family + size + weight + line height + letter spacing). Never a `TextStyle` assembled in the widget, never `copyWith(fontSize:)`.
- **Space and radius** become a token from the scale. If the Figma uses 12 and the scale has 8 and 16, that is a line in table 3 — not a loose `EdgeInsets.all(12)`.
- **Shadow** becomes a named token (`AcmeShadows.card`) holding a `List<BoxShadow>`. Material `elevation` does not reproduce a Figma shadow; use `BoxDecoration.boxShadow`.

## Table 3 — values without a token

The most important table. Every Figma measurement that does **not** match an existing token goes here with an outcome.

| Value in Figma | Where | Outcome |
|---|---|---|
| shadow `0 2 8 rgba(0,0,0,.08)` | card | **becomes a token** — no shadow token today |
| radius 12 | chip | **recorded decision**: uses `radii.sm` (16); Figma will be aligned |
| `#ED1E79` | button | **recorded decision**: product `primary` is `#D01165`; Figma diverges |

No value leaves this table by omission. It becomes a token or a written decision.

## Auto layout → widget

| Figma | Flutter |
|---|---|
| Auto layout horizontal / vertical | `Row` / `Column` |
| `gap` (item spacing) | `spacing:` on `Row`/`Column` (Flutter ≥ 3.27) or the design system's gap widget |
| `gap: auto` (space between) | `mainAxisAlignment: spaceBetween` |
| Padding | `Padding` with the token, on the container, not on each child |
| Fill container (width/height) | `Expanded` inside a `Row`/`Column`; `double.infinity` / `SizedBox.expand` outside one |
| Hug contents | `mainAxisSize: MainAxisSize.min`; for text, nothing (text hugs by default) |
| Fixed | `SizedBox` with the measure |
| Min / max width or height | `ConstrainedBox` |
| Wrap | `Wrap` with `spacing` and `runSpacing` |
| Absolute position inside a frame | `Stack` + `Positioned` — confirm it was intentional |
| Constraints: left/right, top/bottom, scale, center | `Positioned` with both sides, `Align`, `FractionallySizedBox` |
| Layout grid (columns, gutter, margin) | horizontal padding = margin; a `LayoutBuilder` when the column count changes with width |
| Clip content | `ClipRRect` / `ClipRect` with the same radius as the container |
| Scrolling frame | `ListView` / `SingleChildScrollView` / `CustomScrollView` with slivers; never `Expanded` inside it |

## Figma → Flutter pitfalls (a designer notices all of these)

| Property | Figma | Flutter | What to do |
|---|---|---|---|
| Line height | px (e.g. 24 on a 16 font) or % | `TextStyle.height` is a **multiplier** | `height = lineHeightPx / fontSize` (24/16 = 1.5). Figma centers the extra leading; Flutter's default puts it top-heavy. Use `textHeightBehavior: TextHeightBehavior(leadingDistribution: TextLeadingDistribution.even)` when text sits inside a fixed box. |
| Letter spacing | % of font size or px | `letterSpacing` in logical px | `% × fontSize / 100`. `get_design_context` already gives px. |
| Stroke alignment | inside / center / outside | `BorderSide.strokeAlign` (default inside) | Match it. Outside strokes on rounded corners still differ slightly (Flutter issue #117829). |
| Border and padding | padding measured from the frame edge; stroke does not change layout | `Container(padding, decoration: border)` **adds the border width to the padding** | Subtract the border width from the padding token, or put the border on an outer `DecoratedBox` and the padding inside. The probe shows `padding: 17` where the Figma says 16. |
| Odd numbers in `get_design_context` | `p-px` on the card plus `pt-[17px]`, `px-[17px]`, `py-[13px]`, `h-[46px]` inside | — | The React output already added the 1 px border to the inner paddings. Read 17 as 16 + border, 13 as 12 + border, 46 as 44 + 2; write the token (16, 12) and let the border be the border. A `.5` in a height (`212.5`) is the same artifact. |
| Layer opacity vs fill opacity | layer opacity affects the whole group; fill opacity only the color | `Opacity` widget vs alpha in the `Color` | Layer opacity → `Opacity` (or `.withValues(alpha:)` when it is a single color). Fill opacity → color alpha. Never `Opacity` for a single colored box. |
| Shadow | x, y, blur, spread, color with alpha | `BoxShadow(offset, blurRadius, spreadRadius, color)` | Map 1:1. Figma **inner** shadow has no direct equivalent; use `BlurStyle.inner` or accept the divergence in table 3. |
| Blend mode | multiply, screen, overlay | `BlendMode` in `ColorFiltered` / `ShaderMask` / `Paint` | Ask whether the blend is intentional; most are a leftover. |
| Gradient | angle in degrees, stops | `LinearGradient(begin, end)` with `Alignment` | Convert the angle: 90° in Figma is `topCenter → bottomCenter`; 180° is `centerLeft → centerRight`. Use `GradientRotation` for odd angles. |
| Corner smoothing | 0–100% (iOS uses 60%) | `BorderRadius` has none | `ContinuousRectangleBorder` approximates; otherwise record in table 3. |
| Image fill | fill / fit / crop / tile | `BoxFit.cover / contain / none / ImageRepeat.repeat` | Figma "fill" = `BoxFit.cover`; "fit" = `BoxFit.contain`. Crop uses the crop transform; export the cropped image instead. |
| Text truncation | auto height / fixed height with "truncate text" | `maxLines` + `overflow: TextOverflow.ellipsis` | Also `softWrap: false` when the Figma is single-line and clips. |
| Text auto width / auto height / fixed | width behavior | hug → nothing; fixed width → `SizedBox(width)`; fill → `Expanded` | A text without `Expanded` inside a `Row` overflows; a text with `Expanded` outside a `Row` throws. |
| Text case | "uppercase" transform in the text style | no transform | Apply `.toUpperCase()` on the string, or the typography token's helper. Check the literal case in phase 7. |
| Font weight names | Regular/Medium/SemiBold/Bold | `FontWeight.w400/500/600/700` | Confirm the family ships that weight in `pubspec` fonts; a missing weight silently falls back to the nearest one. |
| Icon size | icon frame 24 with a 20 glyph inside | `Icon(size:)` sets the **frame** | Use the frame size; keep the glyph's internal padding in the SVG. |
| Min tap area | not drawn in Figma | Material adds 48 dp with `MaterialTapTargetSize.padded` | Keep it. If the Figma draws a 32 px icon button, the visual is 32 and the tap area is 48; do not shrink to match. |
| Dp vs px | Figma frame at 1× | Flutter logical px = Figma px at 1× | No conversion. Never use `flutter_screenutil`-style scaling to "fit" a design. |
| Colors with alpha | `#00000014` (8% black) | `Color(0x14000000)` — ARGB order | The probe prints ARGB; Figma shows RGBA. Compare carefully. |
| Same component, different device widths | constraints per side | responsive: `LayoutBuilder`, `Flexible`, `Wrap` | Implement at the frame width first; then confirm 360 and 430 do not break. |

## Traps

- **Divergent tokens between files.** If the repo has more than one token file (one in `docs/`, one feeding codegen), find out which one generates code before editing. Editing the wrong one changes nothing and looks like it did.
- **Icon from another family.** The Figma may draw an icon that does not exist in the set the app adopts. The answer is the original export from the Figma node (see `assets.md`), registered in the app's icon class — never a "close enough" glyph from the pack, and never a new icon package for one icon.
- **Component the catalog says exists and does not.** Confirm in the barrel before using.
- **Material defaults leaking.** `ElevatedButton`, `Card`, `Chip`, `AppBar` carry their own padding, elevation, shape, and colors. When the design system wraps them, fine; when a feature uses them raw, every one of those defaults is a divergence waiting for phase 7.
