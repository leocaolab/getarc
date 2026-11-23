---
name: coding-principles
description: "A high-level coding standard — ~26 language-neutral axioms, each distilled from a recurring failure or a review-rubric axis. These are the SOURCE: shift-left-<lang> instantiates them per language, the review rubrics detect their violation. Load when writing, reviewing, or reasoning about a design — the \"why\" under every specific rule."
---

# Coding principles (the standard)

Language-neutral axioms, each distilled from a recurring failure or a review-rubric
axis. `shift-left-<lang>` is these instantiated; the rubrics (`${CLAUDE_PLUGIN_ROOT}/rubrics/`)
are these violated; this is the source. The one question under all of them: **can I change
the SHAPE (type / driver / API) so the bug is UNREPRESENTABLE, instead of guarding
it at runtime?**

## Types make illegal states impossible

1. **Total data types.** Sums over products, a closed variant universe, named
   representations — an illegal state cannot be constructed. Absence is `Option`,
   never a `0` / `""` / `null` sentinel. An empty collection already says "none":
   `Option<Vec<T>>` is two ways to say it, unless "not given" and "given empty"
   mean different things. Nor is an existing variant a sentinel for another fact
   ("spans several actors" written as `Unknown`) — that fact is an `Option` or its
   own variant.
2. **Errors are typed values.** Carry the source (`#[from]`), branch on the
   variant — never a stringified error or `Result<_, String>` at a boundary.
3. **Parse, don't validate.** Convert to a domain type at the edge; inner code
   cannot receive an invalid one.
4. **One concept, one type.** A shared core + per-layer views — never N copies of
   the same struct drifting apart.
   A new type must be sayable in one sentence; a data type's name is a noun that
   says its role, not its structure (`type-naming` skill).

## Effects live at the edge

5. **Functional core, imperative shell.** Effects in the type / at the boundary;
   the decision logic pure, taking data as arguments.
6. **Separate fetch from decide.** Materialize the data, then a pure function
   computes — never business logic tangled inside a `block_on` / IO loop.
7. **No hidden effects.** A signature says if it does IO or mutates; same inputs,
   same outputs.
8. **Don't swallow errors.** Propagate typed, or log with context; fail fast on
   your OWN corrupt data (a bad row / parse) — never a silent skip.
9. **Null / failure is the truth.** Don't default over an absent value to feed a
   consumer; understand the crash, don't cover it.

## One source, explicit flow

10. **Single writer per (entity, event).** Write at the source, append-only;
    never reconstruct primary data from a derived store.
11. **Explicit state machines.** `enum State` + transitions the compiler checks,
    not mutable flags threaded across a loop.
12. **One level of abstraction per function.** Reads like a table of contents;
    plumbing pushed one level down.
13. **Declarative dataflow.** `A → B → C` values; nothing mutable to simulate,
    no order-of-statements to remember.

## Least power, least machinery

14. **Least power.** The weakest construct that solves it — no async where sync
    works, no `Value` where a struct works.
15. **Structured data over strings.** No `Value` / `(String, String)` /
    `Msg(String)` across a boundary — a domain type, deserialized at the edge.
16. **Structural enforcement over discipline.** Change the API so misuse won't
    COMPILE — not a defensive comment, a tripwire test, or "remember to…".
17. **Policy is data, not a buried const.** A tunable rule is injected config,
    not a hardcoded constant — and a one-line rule is not an engine.
18. **Reuse, don't hand-roll; delete, don't tolerate.** Use the framework /
    library; kill dead code — no "keep it + a compat shim".
19. **No over-design.** Build what today's measured pain needs, then stop. No
    knob, notification, table, counter, mode or extension point that no current
    user asked for and no measurement demands — each one must be parsed,
    tested, documented and kept consistent for ever. When a design keeps
    growing blockers under review, cut its scope before fixing its details. A
    second real use earns an abstraction; a guess does not.

## Types live with their owner

21. **Private by default.** A type used inside one module / package stays
    there at the narrowest visibility the language offers (Rust private /
    `pub(crate)`, Java package-private, Go lowercase, Python `_name` + `__all__`,
    TS unexported). It becomes public only when it IS a contract another unit
    must speak — and then it lives in the owner's types package, not a shared bucket.
22. **Place by owner, not by user.** A type belongs to whoever owns its
    lifecycle (produces / mutates it), never to whoever reads it. "Two domains
    both use it" is almost always borrowing — an alias (`type X = String`) or
    simply the same bare `String` — not one shared concept: each domain keeps
    its own type and they convert once at the boundary between them.
23. **Three kinds, three homes.** Domain types live with their domain and know
    no DB (no ORM mapping, no row derive); a serializer derive only where the
    type IS a wire contract. Adapter types — DB rows, ORM entities, HTTP DTOs,
    CLI reports — live in their adapter and are converted at the edge (a row
    never reaches the core). The shared kernel holds only small, stable
    vocabulary that infrastructure itself needs (ids, paths, timestamps) — never
    "whatever many crates / modules import" (a `common-model` module is the
    same bucket).
24. **Ask why it exists before finding it a home.** A type or helper that seems
    to need a new shared package is often the symptom of a structural problem
    (e.g. a sync↔async bridge that only exists because the shell isn't async);
    remove the cause instead of housing the symptom.

## Subtract and verify

25. **Subtract, don't patch.** Collapse accreted conditions; never bolt a branch
    beside the trunk as the reflex, never keep the thing a refactor removes.
26. **Verify the premise; find the root cause.** Prove the assumption before an
    irreversible act; the design doc is the oracle, not a grep — don't act on a
    hallucinated world.

