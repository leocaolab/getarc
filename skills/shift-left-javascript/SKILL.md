---
name: shift-left-javascript
description: How to WRITE genuinely clean JavaScript — universal good-code principles in JS idiom, stated in full so the skill is self-contained and portable (works in any repo; nothing else needed). The positive form of common review anti-patterns, so the code is clean the FIRST time. The aim is the principle itself, not passing any linter. Load before writing or editing JavaScript (a fix, a new function, any codegen). Triggers include writing/editing .js/.mjs, "fix this JavaScript", "add a JS function".
---

# Writing clean JavaScript (shift-left)

The goal in one line: **write the version the next reader — human or model — can
extend without re-reading the whole thing.** Clear structure = the correct next
line is obvious. Checklist, not an essay.

> **Prefer TypeScript when the project allows it.** TS gives you compile-time
> enforcement of most of what follows for free; this skill is for plain JS, where
> the same structural guarantees have to be realized at *runtime* + JSDoc. The
> spirit is identical: **make illegal states hard to build, and validate at the
> edge** — just enforced by JSDoc types, boundary checks, `Object.freeze`, guard
> clauses, and tagged objects instead of by a type-checker.

> **The target is the principle, not passing a reviewer.** Every rule is stated in full
> here, so it works in any repo. A `stem::name` in parentheses names the review-rubric
> rule this one mirrors; the full rule, with its reason and examples, is in the arc-skills
> plugin's `rubrics/<stem>.yaml` — open it when you want more, never because you must.
> Never write code merely to keep a detector quiet — a linter with finite recall
> going silent is not proof the code is clean; gaming its blind spots is the failure.

## Separate IO from logic

1. **Fetch, then decide.** `await` materializes the data; a *pure sync* fn computes.
   - ❌ `for (const u of items) { const s = await store.hash(db, u.p); if (s === cur) keep.push(u); }`
   - ✅ `const rows = await fetchAll(db, items);` → `const { keep, skip } = partition(rows);`  *(pure, no IO)*
2. **A decider returns a plan; it does not do the IO.**
   - ❌ `if (stale) { await db.close(id); await notify(id); }`
   - ✅ `return { kind: 'close', id };` — the caller (shell) performs the effect
3. **Business logic takes data as args** — no db / fs / network / `Date.now()` / `Math.random()` inside, and no `await` wrapped around a pure computation.

## Type your data and errors

4. **Named object with a JSDoc typedef, not a bare tuple / anonymous shape** across a boundary. Validate the raw payload into that shape once, don't pass `JSON.parse(...)` around untyped.
   - ❌ `function loc() { return [path, line]; }` · `obj.file && obj.line`
   - ✅ `/** @typedef {{ path: string, line: number }} Loc */` → `return { path, line };`
5. **Typed errors: a named `Error` subclass with a `cause`,** never `throw 'msg'` or `new Error(String(e))` that flattens a caught error at a boundary.
   - ❌ `catch (e) { throw new Error(e.message); }`
   - ✅ `class DbError extends Error {}` → `catch (e) { throw new DbError('read failed', { cause: e }); }`
6. **Closed set → a frozen set of tagged constants,** not a loose string checked at runtime. Use `{ kind: '…' }` tagged objects or a frozen enum.
   - ❌ `if (verdict === 'accepted')`
   - ✅ `const Verdict = Object.freeze({ Accepted: 'accepted', Ignored: 'ignored' });` → `if (verdict === Verdict.Accepted)`

## Don't swallow, don't hide

7. **No empty `catch {}` in library code** — handle the error, or re-throw with `cause`. A swallowed rejection is a lost traceback.
8. **Don't discard the error arm.** No `.catch(() => {})` and no floating promise — `await` it or return it so a rejection surfaces.
9. **Don't paper a failed own-data unbox with a default.** `row.count ?? 0` on a DB read hides corruption — model real absence explicitly (`null` / `undefined`) and propagate the broken invariant with the id; only default a value you *know* is genuinely optional.

## Subtract, don't patch

10. **Array chain over a mutable accumulator** when clearer: `items.filter(...).map(...)` instead of a `for` loop pushing into a `let result = []`.
11. **`const x = c ? a : b;`,** not `let x; if (c) x = a; else x = b;`. Prefer `const`; reach for `let` only when reassignment is real.
12. **Explicit tagged state + `switch`,** not a few `let` boolean flags mutated across a loop — one `state` value transitioning is checkable; scattered flags are not.
13. **Dispatch table / polymorphism** for an `if (kind === …) else if …` type-ladder repeated at ≥2 sites — a `const handlers = { … }` map, not a growing chain.

## Fluency (流畅) — one altitude, one job, one railway

The bar: a fn reads top-to-bottom at ONE cognitive altitude, does ONE thing, flows
down a single happy-path rail, and reads as a **chain of transformations** — each
step turns one value into the next, with no mutable accumulator threaded through and
nothing to simulate in your head. (Each tell names the rubric rule it mirrors.)

14. **One level of abstraction per fn.** Push `await` plumbing, `console.log`, template-string formatting into named helpers; the top reads like a table of contents. (`llm_generated_code_smells::mixed-abstraction-levels`)
15. **One responsibility — no conjoined verbs.** No `buildAndReview`, no `openAndMigrate`: two verbs = two fns, the caller composes. (`l5_architecture::l5-M-one-responsibility-per-unit-srp`)
16. **Business logic separated from infra.** The pure decision holds no db / fs / network / LLM / `Date.now()`; IO is fetched at the edge and passed in as data. And a **domain object never carries a `db` / connection / context field** — those handles live in the shell, passed alongside the data, never baked into it. (`fp_lens::core-buried-outward`, `decision-executes-its-own-effect`)
17. **Railway-oriented (ROP): linear happy path, short error arm.** Guard-clause early-returns; the `catch` / `else` arm is a one-line bail, NEVER a home for long code. Reading top-to-bottom sees only the success flow. (`l5_architecture::l5-A-errors-as-values` · railway pattern)
18. **Paragraph the body: setup → work → return.** Group the lines into visible phases (gather inputs · do the work · assemble the result), a blank line between; no interleaving. *(no dedicated rubric rule yet — read by a human.)*
19. **Parameter object, not a cross-domain bucket brigade.** Group cohesive params into one options object; never a 13-arg signature threading db + config + flags + raw data. Destructure it at the top. (`l5_architecture::l5-M2-cross-domain-arity`)
20. **A returned object carries facts, not UI.** The `corpus` / `outcome` you hand to the next stage holds domain data only — never a `notifications: string[]` of pre-formatted banner lines, never a stream / emitter. Render banners at the edge FROM the facts. *(arc's Rust baseline `AssemblyResult { notifications: Vec<String> }` was exactly this bug — it got ripped out into a typed outcome.)*

## Say less

21. **Comments say WHY, not WHAT, and are short.** No revision-history diary (git owns it); if a fn needs a paragraph, it needs a better name. And validate JSDoc types actually match the code — a stale `@param` is worse than none.
22. **Reuse a package before hand-rolling** (hashing, parsing, dedup, retries) — check what's already in `package.json` before adding a loop.
23. **Delete dead code** — no commented-out block, no unused export "kept just in case", no "keep it + tolerate it" compat shim.
24. **Magic literal → a named `const` with its unit;** and never an `// eslint-disable` to mask a real design flaw — fix the design. `timeout: 3000` (in 4 places) → `const TERMINATE_TIMEOUT_MS = 3000;`

## JS-specific: enforce the shape at runtime + JSDoc

Plain JS has no compiler, so the structural principles above are held up by five
concrete habits — this is *how* rules 4–6 and 17 are realized without types:

- **(a) JSDoc `@param` / `@returns`** on every exported fn — the shape contract the type-checker would otherwise carry, and what an editor uses to catch a wrong call.
- **(b) Validate once at the boundary, then trust.** Parse/validate an external payload (network, `JSON.parse`, user input) into a known shape at the edge; downstream code assumes it is valid and never re-checks. (`fp_lens::partial-function-as-total` — don't treat unvalidated input as if it were already the right shape.)
- **(c) `Object.freeze` / `const` for immutability.** Freeze domain objects you return so a downstream reader can't mutate shared state; default to `const`.
- **(d) Guard-clause early returns** for the error arm (rule 17) — invalid inputs bail on line 1, the happy path stays flat and un-nested.
- **(e) Tagged objects `{ kind: '…' }` for closed sets** (rule 6) — a discriminant field makes the variant explicit and `switch`-checkable, instead of sniffing which loose properties happen to be present.

