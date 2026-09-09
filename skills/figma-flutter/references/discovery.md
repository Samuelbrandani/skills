# Node discovery

## Tools, in order

| Step | Tool | For what |
|---|---|---|
| 1 | `get_metadata` (`nodeId`) | sparse XML outline: id, name, type, position, and **size** of each layer. It is the map. Without `nodeId` it lists the file's pages. |
| 2 | `get_screenshot` (`nodeId`) | PNG of **one** node, with layout fidelity. It is the reference for phase 7. One per screen; save it to disk. |
| 3 | `get_variable_defs` (`nodeId`) | variables and styles applied — color, spacing, typography — with name and value. The token mapping comes from here. |
| 4 | `get_design_context` (`nodeId`) | structured representation: hierarchy, auto layout, typography, color, and component properties. Comes out as React + Tailwind by default; **do not copy the code**, read it as the source of measurements. Pass `clientLanguages: "dart"`, `clientFrameworks: "flutter"`; the server has no Flutter preset, but it drops web-only noise. |
| 5 | `get_code_connect_map` (`nodeId`) | existing Code Connect mappings for the file. Code Connect has no Dart parser, but teams can register Flutter widgets through the template (parserless) mode. If a mapping exists, it names the widget to reuse. |
| 6 | `search_design_system` (`queries`) | finds the library component behind an instance. Use when the layer name is generic. |
| 7 | `download_assets` (`nodeId`, `defaultFormat?`, `defaultScale?`) | one node per call: the node's export, the original raster images used as fills in its subtree (up to 20), and the SVGs of its vector layers (up to 20, the same set `get_design_context` lists). Details in `assets.md`. |

## Is the node using tokens?

`get_variable_defs` on the component node. An empty response (`{}`) means **that drawing uses no design-system variable** — it was built with raw hex. This changes the whole job: there is no token mapping possible, and chasing color parity with that node means leaving the design system.

That finding **is not a code bug and is not solved by implementing**. Record it as a product/design pending item, map every color to the nearest semantic token, and move on. Never copy the raw hex into the widget.

Known quirks: the tool sometimes returns the resolved value instead of the alias, and only the default mode of a collection. When the file has modes (light/dark, brand A/B), ask which mode the screen is in and read the collection in the Figma UI if needed.

## What a designer would also read

Beyond measurements, a senior implementer reads the file for intent:

- **Component set variants.** A button instance inside the screen belongs to a component set with variants (`size=md, kind=primary, state=default`). Read the set, not just the instance: the variants are the widget's enum, and the naming should match.
- **Interactive states.** Hover, pressed, focused, disabled, selected, error. If the Figma draws them, they are part of the scope. If it does not and the widget needs them, it is a question for design, not an improvisation.
- **Screen states.** Loading, empty, error, partial data, long text. Look for sibling frames named "Empty", "Loading", "Error", "Skeleton". A screen without an empty state in Figma still needs a decision written down.
- **Annotations and dev resources.** Designers leave behavior notes (scroll, sticky header, animation, responsive rule) in annotations. `get_design_context` includes them when present.
- **Constraints and resizing.** How the frame behaves at other widths (fill, hug, fixed, min/max). This is the responsive contract.
- **Layout grid.** Column count, gutter, margin. Feeds the horizontal padding decision.
- **Corner smoothing.** Figma's "iOS smoothing" makes squircles; Flutter's `BorderRadius` does not. Note it as a known divergence or use `ContinuousRectangleBorder`.

## Cautions

- **Big responses.** A whole flow board overflows the ~20 KB limit. Split: `get_metadata` on the root to discover the children, then one pass per screen.
- **`get_screenshot` is one node at a time.** A whole board becomes an unreadable image; capture screen by screen.
- **Prototype frames are not UI.** State selectors, flow captions, designer annotations, and "DEMO" variants exist in Figma and not in the app. When in doubt, ask before implementing.
- **`get_design_context` asks for the Figma skill loaded first.** Claude Code: read the resource once with `ReadMcpResourceTool(server: "figma", uri: "skill://figma/figma-design-to-code/SKILL.md")` (or `/figma-design-to-code` if the plugin is installed) and pass `skillNames: "resource:figma-design-to-code"`. Agents without a resource reader (Codex): install the curated `figma` skill or just call the tool — `skillNames` is a logging parameter (see `agents.md`). Also pass `clientLanguages: "dart", clientFrameworks: "flutter"` and `excludeScreenshot: true` when you already saved the PNG — the response is smaller.
- **`get_metadata` on a section overflows** (150 KB+ of XML). The harness saves it to a file; outline it with `scripts/figma_outline.py <file> --depth 1` (screens) and `--node <id> --depth 3` (one screen). Never re-call the tool to "see it again".
- **Screenshot URLs expire in minutes.** `curl -L -o` them immediately into the repo's capture folder (the scan lists an existing one, e.g. `docs/design/<feature>/`), named `<screen>_<node>.png`, then read them from disk.
- **Duplicate frames.** Sections often hold two copies of a screen (an older version, a "V2"). Compare their sizes and screenshots; if identical, treat the pair as one screen and say so. A duplicate may be the only one linked to variables — check `get_variable_defs` on both before concluding the design uses raw hex.
- **`search_design_system` in batch is cut.** Asking 4 queries returns 1 and warns that 3 were discarded. One query per call.
- **The React + Tailwind that comes back is a measurement reference, not an implementation.** Read the numbers; do not translate the markup. Tailwind classes hide values (`p-4` = 16, `rounded-xl` = 12, `text-sm` = 14/20): resolve them before writing them down.
- **Layer names lie.** A layer called "Button" may be a `Container` with text. Trust the type and geometry from `get_metadata`, not the name.
- **Rate limits.** Starter and View/Collab seats: 6 calls per month. Dev/Full seats on paid plans: per-minute limits like the REST API tier 1. Batch `download_assets` and avoid re-reading a node you already saved.
- **Write down the frame width per screen**, and the `nodeId` of each. Both are needed in phase 7.

## Phase output

Table, in the format the repo's spec already uses:

| # | Screen | Node | Width | Elements | States in Figma |
|---|---|---|---|---|---|
| 1 | List — Open tab | [`7880:9398`](url) | 390 | header, filter chips, period card, card list | default, empty, loading |

Plus, per screen: the Figma PNG saved to disk (the repo's capture folder, e.g. `docs/design/<feature>/<screen>_<node>.png`), the variable list from `get_variable_defs`, and the component sets touched with their variants.
