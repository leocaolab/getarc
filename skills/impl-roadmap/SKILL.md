---
name: impl-roadmap
description: Use this skill to turn a FINISHED design into an execution roadmap — sequenced milestones + tracker sync. Triggers include "roadmap for X", "做 X 的 roadmap / 排里程碑 / 拆里程碑", "plan the milestones for X", "sync X to the issue board / issues / milestones". Runs ONLY after the design is finished — the design doc AND its `impl-design` impl-map are gated (≤ 2 rounds; 0 blocking, or the rest answered by the maintainer). Produces `<feature>-roadmap.md` (M0…Mn sequenced by dependency + risk-first, each with scope / deps / delivered components+FRs / the E2E that verifies it / independently shippable) and reconciles the repo's issue board via `arc issues` (create/align/close; GitHub is only a mirror, never written directly), citing the gate decisions that changed scope.
version: 0.1.0
---

# Roadmap

The bridge from a **finished design** to execution. Pipeline:
`brainstorm → design → impl-design (gate) → **impl-roadmap** → build → conformance`.

A roadmap authored against an *un-finished* design freezes decisions the gate can
still reverse. (Measured failure: a roadmap milestone + tracker issue were written
for a component the `impl-design` gate later **deleted**, leaving a dead work-item.)
So this skill runs **last before code**, off the gated artifacts.

## Precondition — HARD GATE (check first, refuse if unmet)

Before writing anything, confirm the design is **finished**:
1. A design doc exists (`<docs-dir>/design/<feature>.md` or the repo's convention).
2. Its `impl-design` impl-map (`<feature>-impl.md`) exists **and its revision
   record shows the gate passed** — within 2 rounds, 0 blocking, or every blocking finding left after round 2 answered by the maintainer.

If either is missing or the gate still has blocking findings: **STOP**. Do not write
a roadmap. Tell the user the next step is `design` / `impl-design` (name which), and
that the roadmap waits for the gate (0 blocking, or the rest answered). A roadmap is only as trustworthy as the
design it is built on.

## Ground in the FINISHED artifacts (not memory)

Read the **current** design doc + impl-map end to end — especially the design's
revision record / §17 (or equivalent): the gate may have **changed the design
after the first draft** (renamed types, removed components, reversed decisions).
The roadmap must reflect the *landed* design, not what it said before the gate.

## Step 1 — Write `<feature>-roadmap.md` (a SEPARATE artifact)

Not a section inside the design doc — its own file, so it can be re-run when the
design changes. Milestones `M0…Mn`. For **each** milestone:

- **Scope** — the components / `FR-n` it delivers (cite the design's IDs).
- **Dependencies** — which earlier milestones it needs.
- **Verification** — the exact `E2E-n` / unit test from the design that proves it
  done (every milestone is independently *verifiable*, not just shippable).
- **Independently shippable** — it lands on its own; state what's usable after it.

Sequencing rules:
- **Risk up front.** The highest-uncertainty / highest-external-risk piece is M0,
  not deferred. (A pure in-memory milestone that proves the core invariant with no
  network is the ideal M0.)
- **Dependency order** otherwise.
- **No dead milestones.** If the gate removed something (a component, an adapter),
  it does not appear as a milestone — and its tracker issue gets closed (Step 2).

## Step 2 — Put the milestones on the board

**Delegate to the `sync-roadmap` skill** (load it; do not re-implement this step).
It files each milestone with its north star, its goal and its criterion, and each
item with a criterion and the verbatim source text behind it — which is what makes
the board checkable against this roadmap months later, by a session that was not
here. It also reconciles: what the roadmap asks for that the board has not got,
and what the board holds that the roadmap no longer mentions.

Two things this step still owes it:

- **Close what the gate removed.** A component or adapter the `impl-design` gate
  deleted gets its issue closed, citing the decision that killed it (e.g.
  "closed: §17 dec-2 removed the token adapter"). Report every close with its
  reason; never silently drop one.
- **The source text.** Every milestone and item you hand `sync-roadmap` cites the
  design's own words — the `FR-n` / `E2E-n` / §17 decision it came from, quoted —
  so the roadmap and the board can be read against each other later.

If the repo has no `arc issues` board, fall back to its own tracker convention.
Report the board state as a table (`milestone → b/<n> → status`).

## Output conventions

- **Write `<feature>-roadmap.md` to disk; report the path.** Don't dump it into chat.
- Cite the design's IDs (`FR-n`, `E2E-n`, component names, `§17` decisions) for every
  milestone's scope and verification — traceable back to the finished design.
- If the precondition gate is unmet, produce **nothing** and route the user to the
  correct prior skill.
