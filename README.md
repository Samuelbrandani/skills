# skills

Agent skills by [Samuel Brandani](https://github.com/Samuelbrandani), published on [skills.sh](https://skills.sh). Each skill lives in `skills/<name>/` and follows the [Agent Skills](https://agentskills.io) format: a `SKILL.md` with frontmatter, plus `references/`, `scripts/`, and `assets/` loaded on demand.

| Skill | What it does | Install |
|---|---|---|
| [`figma-flutter`](skills/figma-flutter/SKILL.md) | Implements, redesigns, or audits a Flutter screen from a Figma node with designer-level fidelity: reads the node through the Figma MCP, auto-detects the repo's design system and architecture, uses only original Figma assets, and closes with a measured, number-against-number conformance pass. | `npx skills add Samuelbrandani/skills --skill figma-flutter` |

## Install

```bash
# one skill, globally (user level), for every agent the CLI knows
npx skills add Samuelbrandani/skills --skill figma-flutter -g

# or project level, Claude Code only
npx skills add Samuelbrandani/skills --skill figma-flutter -a claude-code

# list what the repo offers without installing
npx skills add Samuelbrandani/skills --list
```

Works with Claude Code, Cursor, Codex, Gemini CLI, and any agent that reads `SKILL.md`. Skills are symlinked into the agent's skills directory by default; pass `--copy` to copy instead.

## figma-flutter in one minute

1. Paste a Figma link (`figma.com/design/<file>?node-id=…`) and say what you want: implement, redesign, or audit a screen.
2. The skill refuses to guess from prose: it authenticates the Figma MCP, reads metadata, screenshots, variables, and design context for every frame.
3. It scans the repo (`scripts/repo_scan.sh`) to find the design system, token access pattern, feature layout, fakes, and existing verification tooling, and obeys them.
4. It produces three mapping tables (node → widget, Figma value → token, values without a token), an asset manifest, and a data contract. When the repo demands a plan before code, that document is the plan.
5. Implementation happens in the repo's architecture. Conformance is measured with `assets/design_probe.dart` (rendered tree → JSON) and checked visually at the Figma frame width across 12 axes.

The full method is in [`skills/figma-flutter/SKILL.md`](skills/figma-flutter/SKILL.md). A Portuguese mirror is in [`SKILL.pt-BR.md`](skills/figma-flutter/SKILL.pt-BR.md) and `references/pt-BR/`.

## Bundled scripts and assets

Everything in `scripts/` is **read-only and dependency-free** (bash + coreutils, python3 standard library). Nothing phones home; nothing modifies the repository it inspects.

| File | Purpose |
|---|---|
| `scripts/repo_scan.py <root> [feature]` | Prints a Repo Profile: packages, barrels, `ThemeExtension`s, token classes, icon families, asset dirs, feature layout, probe/golden/widgetbook tooling, architecture docs (including a parent `CLAUDE.md`). Under 2 s on a 20-package monorepo. `repo_scan.sh` (bash) and `repo_scan.ps1` (PowerShell) are thin wrappers around it. |
| `scripts/figma_outline.py <saved-metadata> [--node ID] [--depth N]` | Outlines an overflowing `get_metadata` result (a section with many frames) into screens and sizes without loading the XML into context. |
| `scripts/svg_check.py --dir <folder>` | Flags SVG features `flutter_svg` / `vector_graphics` do not render (filters, CSS `<style>`, `<text>`, embedded images) and export leftovers, before an asset is committed. |
| `assets/design_probe.dart` | Test helper the agent copies into repos without one: dumps the rendered tree (rect, padding, radius, border, shadow, gradient, fonts, icons, images, tap targets) to JSON, snapshots it, and checks 48 dp tap targets. Requires only `flutter_test`. |

### Platform and version support

| | Supported | Notes |
|---|---|---|
| OS | macOS, Linux, Windows | all scripts are Python 3.8+ standard library; on Windows use `py -3 scripts\repo_scan.py` or `.\scripts\repo_scan.ps1` |
| Flutter (probe) | ≥ 3.10 (Dart 3) | `Color.value` is used instead of `toARGB32()` (3.27+); `Flex.spacing` (3.27+) is read reflectively and omitted from the JSON on older SDKs. Validated on 3.22, 3.35 and 3.47 |
| Figma | official Figma MCP server (remote or desktop) | `get_design_context` requires the `figma-design-to-code` skill resource loaded first; the skill does this |

## Requirements

- The official **Figma MCP server** connected to your agent (`whoami` must succeed). A Dev or Full seat on a paid plan avoids the 6-calls-per-month limit of Starter seats.
- A Flutter repo; the skill adapts to any architecture it can detect (monorepo or single package, any state-management library).
- `python3` (3.8+) on the machine running the agent. Bash or PowerShell are optional conveniences.

## Contributing

Issues and PRs welcome. Keep `SKILL.md` and `SKILL.pt-BR.md` in sync (same sections, same tables), keep scripts dependency-free, and explain the *why* of any new rule rather than adding a MUST.

## License

[MIT](LICENSE)

---

## Em português

Skills de agente publicadas no [skills.sh](https://skills.sh). Cada skill fica em `skills/<nome>/` no formato [Agent Skills](https://agentskills.io).

**`figma-flutter`** implementa, redesenha ou audita uma tela Flutter a partir de um nó do Figma com fidelidade de designer: lê o nó pelo MCP do Figma, detecta automaticamente o design system e a arquitetura do repo, usa só assets originais do Figma e fecha com conferência medida, número contra número. Instale com:

```bash
npx skills add Samuelbrandani/skills --skill figma-flutter -g
```

O método completo está em [`SKILL.md`](skills/figma-flutter/SKILL.md) (inglês, o arquivo que o agente carrega) e no espelho [`SKILL.pt-BR.md`](skills/figma-flutter/SKILL.pt-BR.md). Os scripts em `scripts/` são somente leitura, rodam em macOS, Linux e Windows, e não têm dependência além do Python 3 padrão. O `design_probe.dart` compila em Flutter 3.10 ou mais novo.
