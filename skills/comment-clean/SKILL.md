---
name: comment-clean
description: Clean up comments and docstrings to remove LLM-style noise — strip out "what" narration, step-by-step body summaries, type echoes, idiom explanations, refactor history, and dead code, while keeping "why" context, failure contracts, invariants, and non-obvious constraints. Use when comments feel verbose or noisy, or before landing changes. The full rule set lives in `rubrics/comment_hygiene.yaml`.
---

# Comment clean

Evaluate every comment against the code it describes, in priority order:

1. **TRUE** — Every claim must match what the code actually does. A false comment is worse than no comment; fix it or delete it, never soften it into a vague hedge.
2. **ONCE** — A "why" explanation belongs in one place: on the entity it constrains. A second copy elsewhere drifts out of sync and becomes a lie. Keep it on the owner and delete duplicates (or leave a one-line pointer if the owner is in another file).
3. **WHY, not HOW** — Across all three comment levels:
   - **Module docs (`//!`)**: A one-line summary + `# Invariants` + `# Core Concepts` (domain terms). Not a table of contents or pseudocode walkthrough.
   - **Function/type docs (`///`)**: The caller's contract — a verb-first summary + `# Side Effects` + `# Errors` / `# Panics`. Not a 1-2-3 walkthrough of the body or a repetition of parameter types.
   - **Inline comments (`//`)**: Use sparingly, only to explain non-obvious reasoning.

## The deletion test

Delete the comment and ask: would a competent reader of this language now want to **change** the code (reorder lines, add a guard, change error handling, replace a return with `unwrap_or_default`)?
- If **yes**, the comment carries a hidden constraint (ordering, concurrency, upstream contract, intentional omission) — **keep it**.
- If deleting it only costs a few seconds of reading the code or standard API docs — **cut it**.

## What to cut

- **Line-by-line narration** (`// open the context` above `Ctx::open()`, or numbered step comments).
- **Body walkthroughs in docstrings** (explaining steps 1-2-3 of the implementation instead of the caller contract).
- **Redundant signature restatements** (`/// The run ID` on `run_id: RunId`).
- **Standard idiom explanations** ("wrapped in `Arc` so it can be shared", "cloned for the borrow checker").
- **Negative comparisons to sibling code** ("generates its own ID instead of using X's") — state what it *does* positively.
- **Refactor history** ("used to do X, now does Y", references to deleted structs, or subjective tags like "god-struct"). Code comments document the present.
- **Over-verbose essays** — if cutting a comment in half loses no information, it was padding. (Genuine complexity — subtle invariants, algorithms, or hazard lists — can still warrant detail.)
- **Duplicated rationales** — the same explanation repeated in multiple places.
- **Internal jargon / planning labels** — internal milestone/phase tags (`M4`, `Phase 2.4`, `§6`) or private vocabulary on public items.
- **Commented-out code and debug residue** — git holds old code; remove stray `println!` / `dbg!` / `console.log` where a real logger exists.
- **Ownerless TODOs** — bare `// TODO` or `// FIXME`; either add `TODO(owner)` / an issue link, or just do it.
- **Missing verb-first summary** — `///` doc comments whose first sentence doesn't start with an active verb (`Loads…`, `Returns…`, `Checks…`).

## What to always keep

- **Failure-mode contracts** ("an unresolved HEAD fails the run rather than skipping" — removing these invites someone to add a silent fallback).
- **Invariants, ordering, concurrency rules, and deliberate omissions**.
- **Units, valid ranges, defaults, and domain meaning** that the type doesn't express (`/// seconds; None means unlimited`).
- **Non-obvious test notes** (explaining what regression fails if a line is removed), external bug/RFC/CVE links, `[arc:intentional-handle]` markers, and explanations of why the obvious idiom was intentionally avoided.

## Rules of thumb

- **Bias toward cutting.** A deleted comment is easy to restore in review; noisy comments tax every future reader.
- **Fix the code, not the comment.** If a line needs a signpost, extract a well-named helper instead.
- Only clean comments in code you were asked to touch or review; leave unrelated pre-existing comments alone.

Full rule set and exemptions: `${CLAUDE_PLUGIN_ROOT}/rubrics/comment_hygiene.yaml`.
