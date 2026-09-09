# Assets — originals from Figma, imported with care

An icon redrawn from memory, a "close enough" glyph from an icon pack, or a placeholder box are the three most visible ways a screen stops matching the design. The asset pipeline exists to make the original export the only path.

## 1. Decide what is an asset

Walk `get_metadata` and classify every visual node that is not text or a plain box:

| Node in Figma | Treat as | Format |
|---|---|---|
| Icon (instance from an icon set, 16–32 px, single color) | **icon asset** | SVG, monochrome, tinted in code |
| Icon that already exists in the app's icon class **as the same drawing** | reuse the existing entry — confirm by rendering both, not by name | — |
| Illustration, mascot, multi-color logo, decorative vector | **illustration asset** | SVG if `svg_check.py` passes; otherwise PNG/WebP at 1×, 2×, 3× |
| Photo, raster fill, screenshot inside the design | **image asset** | WebP (or PNG when transparency + quality require it) at 1×, 2×, 3× |
| Vector with blur, drop shadow, inner shadow, mask, or blend | **rasterize** unless the design system already has that effect as a token | PNG/WebP at 1×, 2×, 3× |
| Simple shape: rectangle, circle, divider, gradient box, dot | **draw in code** with tokens | — |
| Brand font | not an asset of this screen; must already be in `pubspec` fonts | — |
| Lottie / animation | ask for the `.json` from the designer; the Figma node is only a frame | — |

When unsure whether a node is an icon instance or a drawn group, `search_design_system` with its name, or check for `componentId` in `get_design_context`.

## 2. Get the files

Two sources, both temporary URLs (about 7 days on the remote server, `localhost` on the desktop server). Download immediately with the shell (`curl -L -o`) into the destination; never leave the URL in code and never reference the Figma CDN at runtime.

- **`get_design_context`** already returns one SVG URL per vector layer (`const imgIcon = "https://…/asset/<id>.svg"`), with the node id in the markup next to it. For icons this is usually all you need.
- **`download_assets(fileKey, nodeId)`** — one node per call — returns the node's `export` (PNG at 1× unless the node has export settings or you pass `defaultFormat`/`defaultScale`), `rawImages` (the original JPEG/PNG/WebP behind image fills in the subtree, up to 20, with their real `format`), and `svgAssets` (the same vector set, up to 20). Call it on the screen or section node once per format/scale you need:

```
download_assets(fileKey, nodeId: "12:40")                                  # export 1x + raw images + svgs
download_assets(fileKey, nodeId: "12:40", defaultFormat: "png", defaultScale: 2)
download_assets(fileKey, nodeId: "12:40", defaultFormat: "png", defaultScale: 3)
```

- `defaultScale` from 0.01 to 4; the longest side is capped at about 4096 px. For a 375-wide hero, 3× is 1125 px, fine; for a 2000-wide illustration, 3× exceeds the cap — export at 2× and note it.
- Prefer `rawImages` for photos: it is the file the designer uploaded, not a re-encoded export.
- Export the **icon frame**, not the inner vector: the frame carries the 24×24 (or 20×20) viewBox with the glyph's padding; the inner path does not, and the icon renders bigger than its siblings.
- For icons that are color-tinted in the app, export the **default (usually black or the neutral) variant** and tint in code. Do not export one SVG per color.
- Rename on save. Figma names like `Icon / Arrow / Right=Default.svg` become `arrow_right.svg`. Figma appends `@2x`; Flutter wants the **same file name inside `2.0x/`**.

## 2b. Identify the icon family before deciding anything

Download every icon SVG to a scratch folder and look at its signature: Lucide draws on a 24 viewBox with stroke 2 (exported at 16 px it shows `stroke-width="1.333"`, `stroke-linecap="round"`, `fill="none"`); Phosphor uses 256; Material Symbols are filled paths on 24 (or 960 when exported from the font). Compare with the family the Repo Profile says the app adopts.

- **Same family** → the icon maps to the family's token (`AppIcons.star` → `LucideIcons.star`); add the token when it is missing. This satisfies "originals only": the token renders the same drawing the designer placed. No file enters the repo.
- **Different family or a custom drawing** (brand mark, illustration, a glyph the family lacks) → the SVG is the asset; follow §3–§5. If the repo forbids vendored SVGs (an ADR like "icons only via the icon font"), that is a table 3 line: ask design for the family's equivalent, or record the exception.
- **Never** decide by layer name ("Icon / Star") — decide by the drawing. Two families both have a star; the strokes differ.

## 3. Check every SVG before committing

```
scripts/svg_check.py --dir <destination-dir>
```

`flutter_svg` / `vector_graphics` do not render `<filter>` (blur, drop shadow), `<foreignObject>`, `<text>`, embedded `<image>`, CSS `<style>` blocks, `<pattern>`; masks and complex gradients are partial. The script blocks on those and warns on group opacity, sub-pixel strokes, missing `viewBox`, huge files, and multi-color icons that should be monochrome.

For a **BLOCK**:

- `filter` / shadow → ask the designer to flatten, or rasterize (PNG/WebP at 1×/2×/3×), or reproduce the shadow with a `BoxShadow` token on the container and export the vector without it.
- `text` → outline the text in Figma (right-click → Outline stroke / Flatten) and re-export.
- `style` block → re-export with "Outline text" and "Simplify stroke" on; or run `svgo` with `inlineStyles` and `convertStyleToAttrs`.
- `image` → export as raster.

Optional but recommended: `svgo --multipass --config '{"plugins":[{"name":"preset-default","params":{"overrides":{"removeViewBox":false}}}]}'` to strip Figma metadata and reduce size. Keep `viewBox`. For icon sets with dozens of files, precompile with `vector_graphics_compiler` to `.svg.vec` if the repo already does so; do not introduce it for one screen.

## 4. Put it where the repo puts it

The Repo Profile says where. Typical:

```
packages/<design_system>/assets/icons/<name>.svg           # icons the design system owns
packages/app/assets/images/<name>.webp                      # feature images
packages/app/assets/images/2.0x/<name>.webp
packages/app/assets/images/3.0x/<name>.webp
packages/app/assets/illustrations/<name>.svg
```

Then register:

1. `pubspec.yaml` → `flutter: assets:` with the **directory** (`assets/images/`) so the scale folders resolve automatically. Listing a file does not pick up its `2.0x` sibling.
2. If the repo uses `flutter_gen` (`Assets.icons.arrowRight`), run the generator (`dart run build_runner build -d`) and use the generated accessor.
3. If the repo has an icon class (`AppIcons.arrowRight` → `SvgPicture.asset`), add the entry there with the same naming as its siblings; feature code never calls `SvgPicture.asset('assets/…')` directly when such a class exists.
4. For a package asset used by another package: `AssetImage('assets/x.png', package: 'acme_design_system')`, and the asset must be declared in **that** package's pubspec.

## 5. Render and verify

- Icon: `SvgPicture.asset(path, width: 24, height: 24, colorFilter: ColorFilter.mode(color, BlendMode.srcIn))`. Size comes from the Figma frame; color from a token.
- Raster: `Image.asset(path, width, height, fit)`. Never a bare `Image.asset` without size when the Figma fixes one; the intrinsic size of the 3× file is three times the intended size.
- Cache-friendly: `cacheWidth`/`cacheHeight` for large lists; only when the repo already does so.
- In phase 7 the probe records `source`, `width`, `height`, `fit`, `tint`; the eye confirms the drawing is the same as the Figma screenshot. A different drawing with the right name is still a `DIVERGE` on axis 8.

## 6. Asset manifest (goes in the report)

| Figma node | Figma name | File | Format / scales | Used by | Check |
|---|---|---|---|---|---|
| `12:34` | Icon / Arrow / Right | `assets/icons/arrow_right.svg` | svg, mono | `AppIcons.arrowRight` | OK |
| `12:40` | Hero / Empty state | `assets/illustrations/empty_orders.webp` | webp 1×/2×/3× | `EmptyOrdersSection` | OK |
| `12:50` | Avatar photo | — | — | runtime network image (`User.avatarUrl`) | n/a |

Every visual node from step 1 has a line here, including the ones that resolved to "already exists" or "drawn in code".

## Rules that do not bend

- **Never** substitute an icon by the closest glyph from `Icons`, `CupertinoIcons`, Lucide, Phosphor, or any pack, and never add a pack for one screen. If the design system's icon class is a curated subset of a pack, the new icon still comes from the Figma export and is added to the class.
- **Never** hand-write an SVG path or "recreate" an illustration with `CustomPaint` to avoid an export.
- **Never** leave a `Placeholder()`, a `Container(color: grey)`, or an `Icons.image` standing in for an asset that the Figma has. If the download fails, the report says so and the screen is not done.
- **Never** commit an asset without the check and without registering it; an unregistered asset throws at runtime only on the device.
- **Never** rescale a raster in code to hide a wrong export; re-export at the right scale.
