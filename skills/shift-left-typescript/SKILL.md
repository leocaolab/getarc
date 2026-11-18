---
name: shift-left-typescript
description: How to WRITE genuinely clean TypeScript — universal good-code principles in TypeScript idiom, stated in full so the skill is self-contained and portable (works in any repo; nothing else needed). The positive form of common review anti-patterns, so the code is clean the FIRST time. The aim is the principle itself, not passing any linter. Load before writing or editing TypeScript (a fix, a new function, any codegen). Triggers include writing/editing .ts/.tsx, "fix this TypeScript", "add a TS function".
---

# Writing clean TypeScript (shift-left)

The goal in one line: **write the version the next reader — human or model — can
extend without re-reading the whole thing.** Clear structure = the correct next
line is obvious. Checklist, not an essay.

> **The target is the principle, not passing a reviewer.** Every rule is stated in full
> here, so it works in any repo. A `stem::name` in parentheses names the review-rubric
> rule this one mirrors; the full rule, with its reason and examples, is in the arc-skills
> plugin's `rubrics/<stem>.yaml` — open it when you want more, never because you must.
> Never write code merely to keep a detector quiet — a linter with finite recall
> going silent is not proof the code is clean; gaming its blind spots is the failure.

## Separate IO from logic

1. **Fetch, then decide.** `await` materializes the data; a *pure sync* fn computes.
   - ❌ `for (const u of items) { const s = await store.hash(db, u.p); if (s === cur) keep.push(u) }`
   - ✅ `const rows = await fetchAll(db, items);` → `const { keep, skip } = partition(rows);`  *(pure, no await)*
2. **A decider returns a plan; it does not do the IO.**
   - ❌ `if (stale) { await db.close(id); await notify(id); }`
   - ✅ `return { kind: 'close', id };` — the caller (shell) performs the effect
3. **Business logic takes data as args** — no db / fs / `fetch` / `Date.now()` inside, and no `await` wrapped around a pure computation.

## Type your data and errors

4. **Named `interface` / `type`, not a tuple or `object`** across a boundary; a declared shape, never `any` or an untyped `{}`.
   - ❌ `function loc(): [string, number]` · `const v: any = JSON.parse(s)`
   - ✅ `interface Loc { path: string; line: number }`
5. **Typed errors: a discriminated `Result<T, E>` or a named `Error` subclass** — never `throw 'msg'` or a bare `Error` stringified across a boundary.
   - ❌ `.catch(e => { throw new Error(String(e)) })`
   - ✅ `type Result<T, E> = { ok: true; value: T } | { ok: false; error: E }` → branch on `.ok`
6. **Closed set → discriminated union / union literal,** not a stringly-typed value checked at runtime.
   - ❌ `if (verdict === 'accepted')` where `verdict: string`
   - ✅ `type Verdict = { kind: 'accepted' } | { kind: 'ignored' }` (or `type Verdict = 'accepted' | 'ignored'`)

## Don't swallow, don't hide

7. **No `any` and no `!` non-null assertion papering over a nullable** — narrow the type or return a typed absence; let the caller decide.
   - ❌ `const name = user!.profile!.name`
   - ✅ `if (!user?.profile) return { ok: false, error: 'no profile' }; const name = user.profile.name`
8. **Don't swallow the rejection.** No empty `.catch(() => {})` / `catch {}` — handle it, log with context, or rethrow. `catch (e)` types `e` as `unknown`; narrow before use, never `catch (e: any)`.
9. **Don't paper a failed own-data unbox with a default.** `??  0` on a DB read hides corruption — model real absence as `T | null`, propagate the broken invariant with the id.

## Subtract, don't patch

10. **Array pipeline over a mutable accumulator** when clearer: `xs.filter(a).map(b)` instead of a `for` pushing into `const res = []`.
11. **`const x = c ? a : b;`,** not `let x; if (c) x = a; else x = b;` — and prefer `const` + `readonly` / `as const` over reassignable `let`.
12. **Explicit discriminated-union state + `switch`,** not a few `let` boolean flags mutated across a loop (the union + exhaustive `switch` lets the compiler check you handled every case).
13. **Polymorphism / a lookup map** for an `if (x.kind === 'a') … else if (x.kind === 'b') …` type-ladder repeated at ≥2 sites.

## Fluency (流畅) — one altitude, one job, one railway

The bar: a fn reads top-to-bottom at ONE cognitive altitude, does ONE thing, flows
down a single happy-path rail, and reads as a **chain of transformations** — each
step turns one value into the next, with no mutable accumulator threaded through and
nothing to simulate in your head. (Each tell names the rubric rule it mirrors.)

14. **One level of abstraction per fn.** Push `await` orchestration, `console.log`, template-string formatting into named helpers; the top reads like a table of contents. (`llm_generated_code_smells::mixed-abstraction-levels`)
15. **One responsibility — no conjoined verbs.** No `buildAndReview`, no `openAndMigrate`: two verbs = two fns, the caller composes. (`l5_architecture::l5-M-one-responsibility-per-unit-srp`)
16. **Business logic separated from infra.** The pure decision holds no DB / `fetch` / LLM / clock; IO is awaited at the edge and passed in as data. And a **domain type never carries a `db` / client / context field** — those handles live in the shell, passed alongside the data, never baked into it. (`fp_lens::core-buried-outward`, `decision-executes-its-own-effect`)
17. **Railway-oriented (ROP): linear happy path, short error arm.** An early `return { ok: false, … }` guard or a single `throw` caught at the edge; the error arm is a one-line bail, NEVER a home for long code. Reading top-to-bottom sees only the success flow. (`l5_architecture::l5-A-errors-as-values` · railway pattern)
18. **Paragraph the body: setup → work → return.** Group the lines into visible phases (gather inputs · do the work · assemble the result), a blank line between; no interleaving. *(no dedicated rubric rule yet — read by a human.)*
19. **Parameter object, not a cross-domain bucket brigade.** Group cohesive params into one typed options object; never a 13-arg signature threading db + config + flags + raw data. (`l5_architecture::l5-M2-cross-domain-arity`, `rust_best_practices::primitive-obsession-long-param-list`)
20. **A returned object carries facts, not UI.** The `Corpus` / `Outcome` you hand to the next stage holds domain data only — never a `notifications: string[]` of pre-formatted banner lines, never an `EventEmitter` / callback. Render banners at the edge FROM the facts. *(arc's baseline result-with-`notifications` was exactly this bug — it was ripped out into a typed outcome.)*

## Say less

21. **Comments say WHY, not WHAT, and are short.** No revision-history diary (git owns it); if a fn needs a paragraph, it needs a better name.
22. **Reuse a package before hand-rolling** (hashing, parsing, dedup, validation) — check what's already in `package.json`.
23. **Delete dead code** — no `// eslint-disable-next-line` shim, no `@ts-ignore` kept + tolerated compat layer.
24. **Magic literal → a `const` (with `as const`) carrying its unit;** and never `@ts-expect-error` / `eslint-disable` to mask a real design flaw — fix the design. And **parse at the boundary into a validated type** (zod / io-ts `.parse()`), then TRUST the type — no re-validation and no `as` casts downstream.

