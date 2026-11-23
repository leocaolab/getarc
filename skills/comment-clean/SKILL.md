---
name: comment-clean
description: Clean comment/doc TEXT to a strict comment-hygiene standard — cut WHAT-narration, body step-lists, type-echo, idiom-teaching, refactor-history, sibling-contrast, verbose essays, duplicated WHYs, planning labels, commented-out code and debug residue; keep the WHY, failure-mode contracts, invariants, and non-obvious constraints. Use when comments read verbose / "typical LLM", when asked to clean comments or notes, or after writing/editing code before it lands. The exhaustive rule set, boundaries, and exemptions live in the plugin's `rubrics/comment_hygiene.yaml` (the same file arc's reviewer reads) — this is its operational distillation.
---

# Comment clean

Judge each comment against the code it sits on. Three clauses, severity order:

1. **TRUE** — what it asserts must be what the code does. A false claim outranks
   everything else; a hedged lie is still a lie. Fix = make it true or delete it,
   never soften.
2. **ONCE** — a WHY has one owner: the entity it constrains. A second copy is a fork
   that drifts silently into a lie. Keep it on the owner; at the copy site delete it,
   or leave a one-line pointer (only when the owner is in another file).
3. **WHY, not HOW** — over three layers:
   - module `//!` — a one-line elevator pitch + `# Invariants` (do-not-cross lines) +
     `# Core Concepts` (jargon). NOT a table of contents, NOT a pseudocode flow of `run`.
   - function `///` — the caller's contract: a verb-first summary + `# Side Effects` +
     `# Errors`/`# Panics`. NOT a 1-2-3 of the body, NOT a type-echo of the signature.
   - inline `//` — miserly. Only to justify the non-obvious.

## The deletion test (the one judgement)

Delete the comment, then ask: would a competent reader of THIS language now want to
CHANGE the code — reorder a line, add a missing guard, thread a type differently,
`unwrap_or_default` an absence? If **yes**, the comment carried a hidden constraint
(ordering, concurrency, an upstream contract, a deliberate omission) — **keep it**. If
deleting only costs a few seconds of reading the code or an API doc — **cut it**.
"Tells the reader something" is not the bar; almost any sentence does.

## Cut — WHAT wearing prose

- **what-narration** — `//` translating the line into English (`// open the ctx` over
  `Ctx::open()`, `// read the clock` over `let now = …`); step-number preambles.
- **doc-narrates-steps** — a `///` walking the body's 1-2-3 instead of the contract.
- **redundant-signature-restatement** — doc re-says the types/names (`/// the run_id`
  on `run_id: RunId`).
- **explains-known-idiom** — teaching a standard practice: "`Arc` so it's shared",
  "cloned to satisfy the borrow checker", "injected at the composition root".
- **contrast-with-sibling** — defining code by how it differs from a LIVE sibling
  ("mints its OWN id rather than adopting X's"). Rewrite positively.
- **refactor-history-narration** — past-tense migrations, deleted structs, "used to …
  now …", subjective markers ("god-struct", "finally"), dead proper nouns that no
  longer resolve. The codebase documents the PRESENT tense.
- **over-verbose-comment** — a correct WHY said as an essay. Cut it in half; if nothing
  is lost, it was padding. (Length is not the smell: a subtle invariant / algorithm /
  a real list of distinct hazards can be worth 100 lines.)
- **duplicated-why** — the same rationale in two or more places.
- **internal-vocab / planning-labels** — vocabulary the reader can't reach on a PUBLIC
  item; and ALWAYS cut planning labels anywhere (`M4`, `Block 3`, `Phase 2.4`, `§6`,
  `Doc 19 §10`, `runtime2`) — they name nothing in the tree.
- **commented-out-code / debug-residue** — dead code blocks (VCS holds them); stray
  `println!` / `dbg!` / `console.log` on a path that has a real logger.
- **todo-without-owner** — a bare `// TODO`/`FIXME`. Add `TODO(owner)` or an issue ref,
  or do the thing.
- **missing-verb-first-summary** — an item `///` whose first sentence isn't a
  verb-first `Loads…` / `Returns…` / `Checks…` (it is extracted alone into the index).

## Keep — load-bearing, never cut

- **Failure-mode contracts** — "an unresolved HEAD fails the run, it is not skipped";
  "a crashed unit is not an `Err`". Deleting invites an `unwrap_or_default` or a
  swallowed branch. Rewrite positively if you can, but never drop it.
- **Invariants, ordering, concurrency, deliberate omissions** — the hidden constraints.
- **Unit / range / default / domain meaning** a type can't carry
  (`/// seconds; None ⇒ no budget`).
- **NON-VACUOUS test notes** (which code deletion makes the test red), external
  bug/spec/RFC/CVE refs, `[arc:intentional-handle]` blocks (the marker arc's reviewer
  reads as a deliberate, explained swallow), and "why the obvious idiom was NOT used here".

## Discipline

- **Lean toward cutting.** A cut comment costs a human seconds to reject; a kept-noise
  comment costs every future reader. Silence is the expensive answer.
- **Fix the code, not the comment.** A line that needs a signpost wants a better-named
  helper; a doc that must be long wants a self-evident body.
- Match ONE comment to its most specific rule. Do not touch what is already tight, or
  the pre-existing comments you weren't asked to review.

Full rule set + boundaries + exemptions: `${CLAUDE_PLUGIN_ROOT}/rubrics/comment_hygiene.yaml`.
