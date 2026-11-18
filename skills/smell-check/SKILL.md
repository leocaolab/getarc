---
name: smell-check
description: Adversarial review of a design doc, an implementation plan or a diff against structural principles (SRP, hexagonal, layering, clean merge, no sentinel, single source of truth) — catches bad smells BEFORE they enter the system. Every verdict needs file:line or quoted evidence; blocking vs advisory. Use when asked for a smell check, to review a plan or design before building it, or to gate a diff on structure.
---

# Smell Check (设计/计划/diff 的坏味道门)

Run against an implementation plan, a design doc, or a diff. The reviewer is **adversarial**: its job is to find reasons to block,
not to approve. Every finding cites evidence (`file:line` or a quoted doc section);
a finding with no evidence does not count. Output a table
`smell → evidence → severity(blocking/advisory) → concrete fix`, then a verdict.

## The checklist (each item is a lesson already paid for)

1. **Layer bypass** — does anything import a raw backend (rusqlite, reqwest, a provider
   SDK) past the layer that owns it? A dependency added where an owning abstraction
   already exists = blocking. ("Does a layer already own this? Consume it.")
2. **Client-driven core edits** — does the plan edit a core crate's `src/` to quiet a
   client's compile error? Adapt the client, report the friction; core changes need
   their own justification = blocking.
3. **SRP violations** — any module/type with two reasons to change; any "manager/util/
   helper" grab-bag; any function doing decide AND execute AND persist.
4. **Hex violations** — domain core importing adapters; dependencies pointing outward;
   business logic living in an edge adapter.
5. **Compat shims / dead-code retention** — merge/refactor keeping the old path "just in
   case", tolerant fallbacks, unused code defended into staying. Default is removal;
   burden of proof is on keeping. Existence is not justification.
6. **Sentinel leakage** — `parse_failed` / `unknown` / magic strings reaching any
   human- or consumer-facing position. Failures carry the raw data + real error.
   Typed enums internally only.
7. **Cover-not-cause** — a fix that feeds a consumer what it wants (backfilling a field,
   catching-and-defaulting) instead of asking whether the entity owns that field at all.
   Regression tests freezing a false invariant.
8. **Derived-state backfill** — fold/synthesize/backfill reconstructing primary data from
   projections; producer's words not written at the source at production time.
9. **Shortcut-over-structure** — the plan recommending the "省事" path where a clean
   structure exists; skipping listed as a recommendation.
10. **Test edits without a verdict** — any step touching an existing test without the
    frozen-correct vs frozen-wrong judgment written down + human sign-off = blocking.
11. **Refactor-cascade dodge** — "this changes N callers" used as a reason to not do the
    right type-level fix. The cascade IS the deliverable.
12. **Green-build blindness** — nothing in the plan verifies the *architecture* (only
    compilation). Require at least one mechanical detector where feasible: a dependency
    direction check, a grep-able invariant, a layering assertion.
13. **Moving a type to break a dependency cycle, without the field list** — a plan that moves a
    type (or a whole module) to another crate so a consumer can hold it must list which of its
    fields each consumer reads. When the list is only scalars (a class, a kind, the text),
    the consumer does not need the type: project it into the consumer's own type at the
    boundary, and do not move it. A move with no field list = blocking. (A real case: a
    plan to move a whole module, 240 files, into a runtime crate so one consumer could hold
    its error type; the consumer read only the error's class and text.)

## Verdict

- **BLOCKED**: any blocking finding → the doc/plan goes back to its author.
- **PASS (with advisories)**: list them; they carry into the plan as explicit steps, not
  vibes. Never rubber-stamp: a pass with zero findings on a non-trivial design is
  suspicious — say what you actually checked.
