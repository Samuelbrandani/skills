# Plan / report template

Use this skeleton for the deliverable of phases 0–5. When the repo demands a plan before code (a `CLAUDE.md` saying "plan mode first"), this document **is** the plan: another agent must be able to execute it without re-reading Figma. Keep the repo's own plan conventions (header, task checkboxes, sub-skill line) if it has them — look at the newest file in `docs/plans/`.

```markdown
# <Feature> — <Figma node> — Implementation Plan (round N: <scope in five words>)

> For agentic workers: use `figma-flutter` phases 4–7 on top of the repo's execution skill. Copy this file to `docs/plans/<date>-<feature>-<node>.md` in the first commit.

**Goal:** one paragraph: what the screen becomes, what is reused, what stays for the next round.
**Architecture:** the repo's rules that constrain this work, in one paragraph (state, DI, where widgets live, lints).
**Tech Stack:** SDK pin + how to run tools (`fvm`, melos), test and snapshot commands.
**Spec / backend delta:** files to update.

**Figma — file `<fileKey>`, node `<id>` (frame width <w>):**
| # | Screen | Node | Width | Elements | States in Figma | Capture |

## 0. Audit verdict (only when the screen already existed)
Composition equal / diverges entirely; defects that survive the redesign.

## 1. Repo Profile
(from `references/repo-scan.md` §5, ≤ 40 lines)

## 2. System finding
Does the node use design-system variables? If `{}`: raw hex → nearest semantic tokens, pending item for design.

## 3. Mapping
### Table 1 — node → widget  (reuse / extend / new + justification)
### Table 2 — Figma value → token
### Table 3 — values without a token (each row: becomes a token | recorded decision)
### Auto layout → widget (the measurements that drive paddings and gaps)

## 4. Assets — manifest
| Node | Figma name | Drawing / family | Token or file | Action |
State the family identification (e.g. stroke 1.333 on viewBox 16 = Lucide 2/24) and the repo's icon policy.

## 5. Data contract
| Element in Figma | Field | Exists today? | Decision |
Seed changes for the app fake and the test fixtures (rule 3).

## 6. State and architecture
Where cubits/providers are created, what state moves where, which routes stay, telemetry that must keep firing.

## 7. Tasks (order that keeps the test suite green)
### A. Design system   ### B. Domain and data   ### C. Feature   ### D. Conformance (phase 7)
Checkbox per task, file path per task, ≤ 1 line each.

## 8. Gates
The skill's gate list, checked.

## 9. Next round
What was scoped out, already sized (nodes, components to promote, measurements still to take).
```

Rules of thumb:

- Every number in tables 2–3 comes from `get_design_context`; cite the node id next to it when it is not obvious.
- Decisions taken with the user (scope, brand color, degradation) carry the date and "user" as the author.
- Pending questions for design go in one list, phrased so that a designer can answer yes/no.
