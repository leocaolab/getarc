---
name: coding-principles
description: "A high-level coding standard — 26 language-neutral principles distilled from recurring bugs and review rubrics. `shift-left-<lang>` applies these per language, and the review rubrics check for violations. Load when writing, reviewing, or designing code to understand the 'why' behind each rule."
---

# Coding principles

Language-neutral engineering principles distilled from recurring bugs and our review rubrics. `shift-left-<lang>` applies these per language, and `${CLAUDE_PLUGIN_ROOT}/rubrics/` checks for violations. The core question behind all of them: **can we shape the types and API so the bug is impossible to express, instead of guarding against it at runtime?**

## Types make illegal states impossible

1. **Make data types total.** Use sum types (enums) instead of loose combinations of fields or nullable flags, so invalid states cannot even be constructed. Represent absence with `Option`/nullable types rather than sentinel values like `0`, `""`, or `null`. An empty collection already means "none" — avoid `Option<Vec<T>>` unless "not provided" and "provided empty" genuinely mean different things. Never overload an existing enum variant as a sentinel for a separate fact (e.g., using `Unknown` to mean "spans multiple actors").
2. **Use typed errors.** Preserve the underlying error cause (`#[from]`, wrapped exceptions) and let callers branch on variants — never return stringified errors or `Result<_, String>` across module boundaries.
3. **Parse, don't validate.** Convert raw input into a validated domain type at the system boundary so inner code can never receive an invalid value.
4. **One concept, one type.** Keep a shared core type with per-layer views rather than N drifting copies of the same struct. Every new type should be describable in one sentence, and its name should be a noun describing its domain role rather than its internal structure (see `type-naming`).

## Effects live at the edge

5. **Functional core, imperative shell.** Keep side effects at the boundary and make decision logic pure functions that take data as arguments.
6. **Separate fetching from deciding.** Load/materialize the data first, then pass it to a pure decision function — never tangle business logic inside an IO or retry loop.
7. **No hidden side effects.** Function signatures should make IO and mutation obvious; pure functions should return the same output for the same inputs.
8. **Never swallow errors.** Propagate typed errors or log them with full context. Fail fast on your *own* corrupt data (bad rows, malformed internal JSON) rather than silently skipping it.
9. **Surface failures instead of papering over them.** Don't substitute silent defaults for missing values just to keep a consumer running; understand why it failed instead of hiding it.

## Single source of truth, explicit flow

10. **Single writer per fact.** Write data once at its source in an append-only or canonical store; never reconstruct primary state from a derived cache.
11. **Use explicit state machines.** Model lifecycles with an explicit `State` enum and compiler-checked transitions, not a tangle of boolean flags mutated inside a loop.
12. **One level of abstraction per function.** A function should read like a high-level outline, with low-level plumbing pushed down into helpers.
13. **Prefer declarative dataflow.** Transform values cleanly (`A → B → C`) so readers don't have to mentally simulate hidden mutable state or statement ordering.

## Least power, least machinery

14. **Use the least powerful construct that works.** Don't reach for `async` where sync works, or untyped `Value`/JSON maps where a typed struct works.
15. **Pass structured data, not raw strings.** Don't pass `Value`, `(String, String)`, or `Msg(String)` across boundaries — deserialize into a domain type at the edge.
16. **Enforce invariants structurally, not by convention.** Design the API so misuse fails to compile, rather than relying on warning comments, tripwire tests, or "remember to call X".
17. **Keep policy as data, not buried constants.** Tunable rules belong in injected config rather than hardcoded constants — and don't build a rule engine for a one-line rule.
18. **Reuse existing libraries; delete dead code.** Use standard libraries instead of hand-rolling, and remove obsolete code rather than keeping compatibility shims.
19. **Avoid over-engineering.** Build only what today's measured pain requires, then stop. Don't add extra knobs, tables, modes, or extension points "just in case" — every one has to be parsed, tested, documented, and maintained. Wait for a second real use case before abstracting.

## Types live with their owner

21. **Private by default.** Keep types at the narrowest visibility the language allows (Rust private / `pub(crate)`, Java package-private, Go unexported, Python `_name`, TS unexported). Expose a type publicly only when it is a contract another module must speak, and place it in the owner's package — not a generic `common-model` bucket.
22. **Place types by owner, not by consumer.** A type belongs to the module that creates and mutates it, never to the modules that merely read it. If two domains both use a string ID, they are usually borrowing a primitive — keep each domain's own type and convert once at the boundary.
23. **Separate domain, adapter, and shared kernel types.** Domain types live with their domain and know nothing about ORMs, DB rows, or HTTP DTOs (only add serializer derives when the type itself is a wire contract). Adapter types (DB rows, HTTP DTOs, CLI reports) live in their adapter and convert at the edge. The shared kernel holds only small, stable primitives (IDs, paths, timestamps) — never a catch-all dumping ground.
24. **Ask why a shared helper is needed before creating a shared package.** Often it signals a structural issue (such as a sync↔async bridge needed only because the outer shell isn't async); fix the root cause instead of housing the symptom.

## Subtract and verify

25. **Simplify instead of patching.** Collapse accumulated special cases rather than bolting another `if` branch onto the side, and delete whatever a refactor makes obsolete.
26. **Verify premises and find root causes.** Check assumptions against the actual design doc or runtime behavior before making irreversible changes — never act on guesses.
