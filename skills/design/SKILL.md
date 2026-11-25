---
name: design
description: Use this skill when the user wants to design a feature or subsystem before building it, write a technical design document, or check whether an implementation conforms to its design. Triggers include "design X", "write a design doc for X", "做设计 / 写设计文档 / 出设计方案", "做个 X 的设计", and "does X follow its design / 是否遵守了设计 / conformance check". Produces a development-ready design document (CUJs → features → requirements → infra → components → interfaces → algorithms → E2E tests → success criteria → performance/reliability/security → abstraction & reuse grounded in real code), and can later verify the implementation followed the design. NOTE: the ROADMAP is a SEPARATE skill (`impl-roadmap`), run only AFTER the design is finished (design doc + impl-map gated (≤ 2 rounds; 0 blocking or the rest answered)) — do not produce a roadmap here.
version: 0.1.0
---

# Design

Produce a **development-ready design document**, and (on request) a **conformance check**. The document is written to be *implemented from* — concrete, grounded in the actual codebase, with real `file_path:line` references for everything it reuses or touches. The user may write in Chinese; the document itself follows the repository's prevailing doc language.

> **Roadmap is NOT produced here.** A roadmap authored against an un-finished design freezes decisions the downstream gate can reverse (measured failure: a milestone was written for a component the `impl-design` gate later deleted, leaving a dead work-item). The roadmap is its own skill (`impl-roadmap`), invoked only once the design is **finished** — design doc + `impl-design` impl-map gated (≤ 2 rounds; 0 blocking, or the rest answered by the maintainer). Pipeline: `brainstorm → design → impl-design (gate) → impl-roadmap → build → conformance (Phase 3 here)`.

## Modes — pick from the request

- **Design** (default) — "design X", "写 X 的设计文档" → run Phases 0 → 1. (A request that also asks for a roadmap: produce the design here; the roadmap comes from the `impl-roadmap` skill *after* the design is gated — say so, don't inline it.)
- **Conformance** — "check X against its design", "X 是否遵守了设计", "conformance check" → run Phase 3 against an existing design doc.

If the target or scope is ambiguous (which subsystem? which docs dir? greenfield vs. extending?), ask 2–3 sharp questions first. Otherwise proceed.

## Operating principles (these are why the doc is worth anything)

1. **Ground before you write.** Never design from imagination. Explore the codebase first and cite what already exists. A design that doesn't reference real code is a guess.
2. **Reuse over invention.** Every component states what existing code it calls (`file:line`) and what is genuinely new. The user cares specifically about *which existing functions to reuse* — make that a first-class output, not an afterthought.
3. **Derive, don't list.** Features come FROM CUJs; requirements FROM features; components FROM requirements; tests FROM CUJs. Keep that chain visible with IDs so nothing is orphaned and nothing is invented without a reason upstream.
4. **Concrete over abstract.** A competent engineer must be able to start coding from the doc without re-deriving your decisions. Signatures, not vibes.
5. **Decisions carry their source.** Every decision the owner made is recorded with their verbatim words and date, marked *decided*; the design never reverses one. Your own inference is not a decision — it goes to *open questions* with options and a recommendation. Never add a concept the owner did not ask for; propose it as an open question instead.
6. **Least design.** Every new type, table, knob, command, or notification answers "who uses it today?" — no answer, cut it. Sections are proportional: a section that does not apply says so in one line instead of being padded.
7. **One writer per fact.** For every fact the feature stores, name the single component that writes it, when, and where it lives; everything else reads or derives it. No fact is reconstructed downstream from derived state.

## Phase 0 — Ground in the codebase (always first)

1. Identify the target subsystem and the adjacent modules it will touch.
2. **Look for an existing sibling first.** Before designing anything new, search for a feature, concept, command, or page that already does part of this (a report next to the brief you want, an event kind next to the one you would add). Extend it, or state in one line why it cannot be extended.
3. Use Explore / Grep / Read to find: existing traits, types, and functions to **reuse**; the **interfaces** of neighboring modules (both directions); current patterns/conventions to match; and any prior design docs or related history.
4. Build a **reuse map**: `symbol → file:line → how it's used / how we'll call it`. This single artifact feeds the Reuse section *and* every Component and Interface below. Do not skip it.

For larger surfaces, fan out parallel Explore agents (one per adjacent module) and synthesize their findings into the reuse map.

## Phase 1 — The design document

Read `references/design-doc-spec.md` for the per-section quality bar and a copy-paste skeleton. Write the doc to `<docs-dir>/design/<feature>.md` (match the repo's docs convention; ask if there is no obvious one). Answer **every** section, in order (one line saying why, when it does not apply):

1. **Overview & goal** — the pain first, with the observed evidence (a failure that happened, the owner's words), then what, why, explicit non-goals.
   - **Decisions & open questions** — a *decided* list (each with the owner's verbatim words and date) and an *open questions* list (each: what it is about in one sentence, options, your recommendation). If the repo has an issue board, write each open question there too, so it is answerable without this doc.
2. **CUJs (Critical User Journeys)** — `CUJ-1…`. Each: actor, trigger, steps, success outcome. These drive everything below.
3. **Feature list** — derived from CUJs. Each feature tags the `CUJ-n` it serves.
4. **Requirements** — Functional (`FR-n`) + Non-functional (`NFR-n`: perf / reliability / security / scale). Each traces to a feature.
5. **Infra** — runtime / storage / network / external deps the design needs; mark what already exists vs. what's new. For stored data, a **facts table**: fact → its one writer → when → where it lives → who reads it.
6. **Components** — the component list. Per component: responsibility, **what it does not handle** (what it must not know, decide or wait for), **existing code it reuses (`file:line`)**, what's new, and its public interface (signatures).
7. **Interfaces with other modules** — exact types / traits / endpoints crossed, in *both* directions, with signatures.
8. **Main algorithms** — the non-trivial logic as pseudocode or stepwise prose; call out invariants and edge cases.
9. **Integration / E2E tests** — concrete scenarios; **every `CUJ-n` maps to ≥1 E2E test**. State setup → action → assertion.
10. **Success criteria** — measurable done-conditions (functional + the NFR thresholds from §4).
11. **Performance considerations** — hot paths, budgets, expected costs, what to measure.
12. **Reliability considerations** — failure modes, recovery, idempotency, degradation, fail-closed defaults.
   - **Compatibility & rollout** — the four pairs: old binary × new data/config, new binary × old data/config, during a deploy and after a rollback. Name every stored or shipped thing the change adds or renames (schema, event kind, enum value, config key, file the running service reads) and how the running old version survives it. Destructive or renaming changes ship in two deploys.
13. **Security considerations** — trust boundaries, inputs to validate, authz, sandboxing, secrets.
14. **Abstraction & reuse** — the abstraction approach; the **reuse map** from Phase 0 (existing functions/types to call, `file:line`); the new abstractions introduced and why each is justified.
   - **Moving a type across crates** (to break a cycle, or so a consumer can hold it): list the fields each consumer reads. Only scalars (a class, a kind, the text) → project into the consumer's own type at the boundary instead of moving it.

Keep the traceability visible: `CUJ → FR/NFR → Component → E2E test` via IDs.

**Review the doc at most 2 rounds** (yourself or a fresh reviewer). What is still open after round 2 goes to *open questions*, not a third round.

## Phase 2 — (removed) Roadmap → the `impl-roadmap` skill

The roadmap is **not** produced here. It is a separate skill, gated to run only
after the design is **finished** (design doc + `impl-design` impl-map gated: ≤ 2 rounds, 0 blocking or the rest answered),
so it never freezes a milestone the gate can still reverse. When the design doc is
done, tell the user the next step is `impl-design` (the gate), then `impl-roadmap`. Do
**not** append a `## Roadmap` section to the design doc.

## Phase 3 — Conformance check (run after implementation)

Given the design doc + the current code:

1. Read the doc's **Requirements, Components, Interfaces, and E2E tests**.
2. For each item, inspect the implementation and mark: ✅ met / ⚠️ partial / ❌ missing / ➕ undocumented divergence.
3. Output a **conformance table** (`item → status → evidence file:line → gap`), then a summary: what's conformant, what drifted, what's missing. For each divergence recommend **doc-update vs. code-fix** (sometimes the code is right and the doc is stale — say so).

Never rubber-stamp: cite `file:line` evidence for every ✅. A conformance check with no evidence is worthless.

## Output conventions

- **Write the doc to disk; report the path.** Don't dump the whole document into chat — summarize what you produced and link the file.
- Use `file_path:line` for every reuse and interface reference.
- Prefer tables for the feature list, requirements, components, interfaces, and the conformance report.
- If you discover during Phase 0 that the request is under-specified to design well, stop and ask — a grounded question beats a hallucinated section.
