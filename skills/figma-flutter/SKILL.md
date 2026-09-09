---
name: figma-flutter
description: Implements or audits a Flutter screen or component from a Figma node with designer-level fidelity, reading the node through the Figma MCP instead of inferring from prose. It auto-detects the repo's design system and architecture (where tokens and components live, how features are laid out) and respects them, downloads every icon and image as the original Figma export, and closes with a measured, number-against-number conformance pass. Use it whenever a Figma link appears (figma.com/design/...?node-id=), when asked to implement, port, or "make it look like" a screen or component, when someone asks whether the app matches the design, or when the complaint is a divergence of border, color, shadow, font, spacing, background, icon, or composition. Triggers (en/pt) - "Figma link", "node-id", "implement this screen", "pixel perfect", "audit layout", "looks different from Figma", "link do Figma", "implementar essa tela", "de-para Figma Flutter", "auditar layout", "ficou diferente do Figma".
license: MIT
metadata:
  author: Samuel Brandani
  version: "1.0.0"
  source: https://github.com/Samuelbrandani/skills
  languages: "en, pt-BR"
  requires: "Figma MCP server (official), Flutter SDK >= 3.10, python3 >= 3.8 (stdlib only; bash/PowerShell wrappers optional)"
---

# Figma → Flutter

> Versão em português: `SKILL.pt-BR.md` (mesmo conteúdo; as referências em `references/pt-BR/`).

A layout diverges from Figma for a predictable reason: someone implemented from a **description** of the design instead of the design. Prose carries structure and rules; it does not carry padding, radius, font weight, shadow, or exact color. Whoever reads prose gets the composition right and invents the pixel.

This skill exists so that every number comes from the Figma node, every asset is the original export, the code lands where the repo's architecture says it lands, and the check happens on a **real render measured number against number**, not on a test that cannot see fonts or shadows.

## Modes

| Mode | When | Phases |
|---|---|---|
| `implement` | screen or component that does not exist in code | 0 → 7 |
| `redesign` | screen exists in code but the Figma node is a different composition | 0 → 7, with a short audit verdict first (see below) |
| `audit` | screen exists and the request is "is it equal?" — report divergences without touching code | 0, 1, 2, 7 |
| `component` | a single design-system component (button, chip, card) | 0 → 7, repo scan focused on the design-system package |

If the request does not say which: screen exists in code + request is a question → `audit`; screen exists + request is "implement this" → `redesign`. In `redesign`, do not measure the 12 axes of a composition that will be replaced: record "axis 7 (composition) diverges entirely" plus the few defects that survive the redesign, and move on. The full measurement happens in phase 7 on the new code.

## Phase 0 — Preflight (blocking)

1. `whoami` on the Figma MCP. If the only Figma tools available are `authenticate` / `complete_authentication`, the server is not authorized: call `authenticate`, hand the user the URL, and **do not fall back** to prose, an old screenshot, or memory. While the user authorizes, run phase 2 (repo profile) — it does not depend on Figma. After authorization the real tools appear as deferred tools; load them with `ToolSearch("select:mcp__figma__whoami,mcp__figma__get_metadata,…")` before calling.
2. Parse the link: `figma.com/design/<fileKey>/...?node-id=7880-15366` → `fileKey`, `nodeId = 7880:15366` (hyphen becomes colon).
3. `get_metadata` on the node. On a section or page it **overflows the tool-result limit** and the harness saves it to a file; do not call it again — run `scripts/figma_outline.py <saved-file> --depth 1` to list the screens and their sizes, and `--node <id> --depth 3` to outline one screen. Write down the **frame width** of every screen. Every check in phase 7 happens at that width; comparing a 490 px render with a 390 px frame invents divergence that does not exist.
4. Budget the calls. The MCP truncates around 20 KB per response, and Starter/View seats get 6 calls per month (`whoami` shows the seat). One screen costs at least metadata + screenshot + variables + context; plan the batch before calling, and batch independent calls in one message.
5. If the repo's `CLAUDE.md` (or a parent's) demands plan mode before implementing, phases 0–5 **are the plan**: write them with `references/plan-template.md` and hand the plan over; phases 6–7 run after approval, possibly by another agent.

## Phase 1 — Node discovery

Detail in `references/discovery.md`. Output: a table `# · screen · node (link) · width · elements`, the Figma screenshot of each screen saved to disk, the variables the node uses, and the list of component variants and interactive states the Figma defines.

Reading Figma is also where you decide what is **not** UI: prototype connectors, designer annotations, state selectors, "DEMO" variants. Ask when in doubt; never implement them.

## Phase 2 — Repo profile (automatic, always)

What already exists wins over what would be created. Before mapping anything, run:

```
python3 scripts/repo_scan.py <repo-root> [feature]     # macOS / Linux (or scripts/repo_scan.sh)
py -3 scripts\repo_scan.py <repo-root> [feature]       # Windows (or scripts\repo_scan.ps1)
```

and read `references/repo-scan.md` to turn the output into a **Repo Profile**: where the design system lives (package, barrel, token classes, access pattern), whether the design system is *ready*, *partial*, or *absent*, where feature widgets go versus shared widgets, how state, DI, navigation, and entities are wired, the asset conventions, and which verification tooling already exists. Read the `CLAUDE.md` and architecture docs the scan lists.

Three rules come out of this phase and are not negotiable:

- **Components go where the architecture says.** A reusable component goes into the design-system package with everything its siblings have (test, catalog entry, export in the barrel). A screen section goes into the feature's widget folder. Never a `widgets/` folder invented for the occasion.
- **Tokens are consumed the way the repo consumes them** (`context.colors.primary`, `AppSpacing.md`, `Theme.of(context).extension<…>()`). If there are two token files, find the one that generates code before editing.
- **Catalog docs are a hint, not the truth.** Reconcile any written catalog against the barrel and fix the doc in the same pass.

## Decision batch (ask once, early)

Some decisions are the user's, and asking them one at a time mid-flight stalls the work. As soon as phases 1 and 2 are done, ask them together in one `AskUserQuestion`, with a recommended option first:

- **Scope** when the node has several frames: which screens or bodies enter this round.
- **Brand color vs accessibility token** when the Figma uses a hex that the design system deliberately replaced (e.g. brand pink vs its AA variant).
- **Data without a source**: how a stat, count, or toggle the Figma draws but no entity provides degrades (hide the cell, hide the block, placeholder). Check the spec's open questions or blockers first; the answer is often already written.
- **Undrawn states** the screen needs (save button in an inline form, empty/incomplete header, a section body the Figma does not show).

Everything else is a routine call: make it, write it in table 3, move on.

## Phase 3 — Mapping (de-para)

The step that usually goes missing. Rules and formats in `references/mapping.md`. Three mandatory tables: node → widget, Figma variable → token, and **values without a token**. Plus the auto-layout translation and the Figma → Flutter pitfalls table (line-height, letter-spacing in %, stroke alignment, border added to padding, corner smoothing, layer versus fill opacity). No measurement enters a widget as a loose number.

## Phase 4 — Assets (originals only)

Procedure in `references/assets.md`. Every icon, illustration, logo, and image comes from the exact Figma node (SVG URLs in `get_design_context`, exports and raster originals via `download_assets`), in the format the design calls for. **Never** redraw an icon by hand, substitute it with a "close enough" glyph, or leave a placeholder. When the repo adopts an icon family (Lucide, Phosphor, Material) and forbids vendored SVGs, download the SVGs anyway, identify the family by their signature, and map each one to the family's token — adding missing tokens — because the token *is* the original drawing; vendor a file only for a glyph the family does not have, and record it. Run `scripts/svg_check.py` on every SVG before committing; it flags what `flutter_svg` will not render. Raster goes in with the `2.0x/` and `3.0x/` variants. Register in `pubspec.yaml` and, when the repo uses one, in the generated assets class.

A screen with the wrong icon is not "almost right". It is the most visible divergence on the list.

## Phase 5 — Data contract

Rules in `references/data-contract.md`. In one line: for every text in the Figma, name the entity field that feeds it, and **the fake data that runs the app must cover the rich case the Figma draws**. A card that degrades on a null field, fed by a thin seed, renders empty in the app while the test renders full, and the divergence only shows up when someone opens the app.

## Phase 6 — Implementation

Follow the repo's architecture, not this skill's. What this skill adds:

- A new design-system component requires what the existing ones require (mirror test, catalog use case, variant names equal to the Figma's).
- No variant the Figma does not define. No invented state, no decorative placeholder.
- A screen section becomes its own `StatelessWidget` class, never a method returning `Widget`.
- Every state the Figma draws (loading, empty, error, disabled, selected) is implemented; every state the Figma **does not** draw and the screen needs is a question for design, not an improvisation.
- Tap targets ≥ 48 dp, `Semantics` labels on icon-only controls, text that survives 1.3× text scaling without overflowing, `SafeArea` where the frame touches the edge, dark mode when the design system has it.

## Phase 7 — Conformance

**No implementation is done before this phase.** Procedure in `references/conformance.md`.

Two checks, both mandatory, because they catch different defects:

- **Measure** — dump the rendered tree to JSON (rect, padding, radius, border, shadow, gradient, color, font family/size/weight/height/letter-spacing, icon glyph, image asset, tap targets) and compare number against number with the Figma. Catches 2 px, weight 600 vs 700, a missing shadow. Use the repo's probe if it has one; otherwise copy `assets/design_probe.dart` in (compiles on Flutter ≥ 3.10).
- **Look** — real render with the app's fonts at the Figma frame width, next to `get_screenshot`. Catches swapped order, missing element, inverted hierarchy, wrong icon.

Each of the 12 axes comes out `OK` or `DIVERGE` with the value on both sides. Loop until clear. A divergence that is not a bug becomes a justified line; it never disappears in silence.

## Deliverable

A report with: the audit verdict (when the screen existed), the Repo Profile, the screen table, the three mapping tables, the asset manifest (node → file → where it is used), the degradation decision per field, the 12-axis table per screen, and what is pending with a reason. `references/plan-template.md` is the skeleton; when the repo requires a plan before code, the same document is the plan. Figma captures and app renders are versioned in the repo, side by side, named so that `screen ↔ node` is obvious.

## Gates

Do not declare done without:

- [ ] Figma MCP read; no measurement came from prose
- [ ] Repo Profile written; design-system status decided (ready / partial / absent) and every new file placed where the architecture puts it
- [ ] every value traceable to a token, or listed as an explicit divergence
- [ ] reuse preferred over new component, with a written justification when new
- [ ] every asset is the original Figma export, checked by `svg_check.py`, registered, and rendered at the right size
- [ ] fake data covering the Figma's rich case
- [ ] rendered tree measured and compared number against number
- [ ] the 12 axes closed per screen, at the frame width
- [ ] static analysis and the tests of every touched package green
