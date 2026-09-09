# Data contract

A screen can be implemented right and look wrong because the data feeding it is poorer than the Figma's. That defect is invisible in tests — the test uses a rich fixture — and only appears when someone opens the app.

## Rule 1 — every text in the Figma has an owner

For every text, number, and image in the Figma, name the entity field that feeds it.

| Element in Figma | Field | Exists today? |
|---|---|---|
| "Maria Helena Souza" | `Opportunity.patientName` | yes |
| "~4 km from your home" | `OpportunityDetail.distanceKm` | no — backend does not deliver it |

An element without an owner is a question for product, not a hard-coded string in the widget. The entity is a typed class with `fromJson`/`toJson`; the view never reads a raw `Map`.

Before deciding how an orphan degrades, read the feature's spec for **open questions and blockers**: a stat with no backend source, a toggle with no field, a label whose origin nobody confirmed are usually already written down with a proposed endpoint or a "do not model until product answers". The decision in this table cites that line; it does not reinvent it.

## Rule 2 — degradation is a decision, not an accident

A field the backend does not deliver becomes optional in the entity. What the screen does when it is null is a written decision: **the section does not render**, or **renders with a named fallback value**. Never a decorative placeholder, never an invented number, never an eternal skeleton.

Write the decision per field. It is what explains, later, why the app's screen has less than the Figma.

## Rule 3 — the fake data that runs the app covers the Figma's rich case

This is the rule that catches the defect.

If the Figma card shows name, address, date, and summary, the fake seed shows name, address, date, and summary. A thin seed plus rule 2 produces an empty screen in the app while the test shows a full screen — and nobody notices, because the two artifacts are never compared.

Seed checklist:

- [ ] at least one item exercises **every** optional field the Figma draws
- [ ] at least one item exercises the **degradation** (null fields), to see how it looks
- [ ] every tab, filter, or state of the screen has an item that lands in it — a branch without an item is never seen
- [ ] at least one item with the **longest realistic text** (name with 40 characters, address with two lines) to see wrapping and truncation
- [ ] text in the product's real language, plausible names and addresses, dates relative to today

## Rule 4 — test fixture and app seed tell the same story

If they diverge, the divergence is intentional and written. The normal case is the seed being the superset: it has to cover what the eye will check in phase 7.

## Rule 5 — fakes do not prove the contract

Running with fakes checks **layout**. The **contract** is checked against the real backend, without the fakes flag. A `200` with an empty list proves no field name.
