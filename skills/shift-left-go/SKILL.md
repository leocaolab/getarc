---
name: shift-left-go
description: How to WRITE genuinely clean Go — universal good-code principles in Go idiom, stated in full so the skill is self-contained and portable (works in any repo; nothing else needed). The positive form of common review anti-patterns, so the code is clean the FIRST time. The aim is the principle itself, not passing any linter. Load before writing or editing Go (a fix, a new function, any codegen). Triggers include writing/editing .go, "fix this Go", "add a Go function".
---

# Writing clean Go (shift-left)

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

1. **Fetch, then decide.** Pull the data first; a *pure* function computes the result.
   - ❌ `for _, u := range items { r, _ := db.Get(ctx, u.P); if r.X == cur { keep = append(keep, u) } }`
   - ✅ `rows, err := fetchAll(ctx, db, items)` → `keep, skip := partition(rows)`  *(pure, no ctx/db)*
2. **A decider returns a plan; it does not do the IO.**
   - ❌ `if stale { db.Close(ctx, id); notify(ctx, id) }`
   - ✅ `return CloseIssue{ID: id}` — the caller (shell) performs the effect
3. **Business logic takes data as arguments** — no `db` / file / net / `time.Now()` *inside* it, and no package-level mutable state reached from within.

## Type your data and errors

4. **A named struct, not a bare `map` / tuple-of-returns,** across a boundary; decode into a concrete struct, not `map[string]any`.
   - ❌ `func loc() (string, int)` · `m["file"].(string)`
   - ✅ `type Loc struct { Path string; Line int }`
5. **Errors as values, wrapped with `%w`,** never a fresh `errors.New(err.Error())` that drops the chain at a boundary.
   - ❌ `return fmt.Errorf("read failed: %s", err)`  *(string — chain is gone)*
   - ✅ `return fmt.Errorf("read config %s: %w", path, err)` → caller can `errors.Is` / `errors.As`
6. **Closed set → typed constants + `iota`,** not bare strings compared with `==`.
   - ❌ `if verdict == "accepted"`
   - ✅ `type Verdict int; const ( Accepted Verdict = iota; Ignored )`

## Don't swallow, don't hide

7. **No naked `panic` in library code** — return an `error` and let the caller decide.
8. **Don't discard the error.** No `_ = f()` and no bare `if err != nil { }` — handle it or `return ...: %w`.
   - ❌ `data, _ := os.ReadFile(p)`
   - ✅ `data, err := os.ReadFile(p); if err != nil { return fmt.Errorf("read %s: %w", p, err) }`
9. **Don't paper a failed own-data read with a zero value.** A dropped error that leaves the zero struct hides corruption — surface real absence (`(T, bool)` / a not-found sentinel via `errors.Is`) and propagate the broken invariant with the id.

## Subtract, don't patch

10. **One declarative pass over a mut accumulator** when clearer: build the filtered slice in a single loop with a guard-continue, not nested `if` pyramids.
11. **`x := b; if c { x = a }` / a small helper returning the value,** not `var x *T; if c { x = &v }` deferred-nil dance.
12. **Explicit typed state + `switch`,** not a few `bool` flags mutated across a loop (a `switch` over a typed state is exhaustively readable in one place).
13. **An interface + method dispatch** for an `if kind == .. else if ..` type-ladder repeated at ≥2 sites, not a growing `switch v.(type)`.

## Fluency (流畅) — one altitude, one job, one railway

The bar: a function reads top-to-bottom at ONE cognitive altitude, does ONE thing,
flows down a single happy-path rail, and reads as a **chain of transformations** —
each step turns one value into the next, with no mutable accumulator threaded
through and nothing to simulate in your head. (Each tell names the rubric rule
it mirrors.)

14. **One level of abstraction per function.** Push plumbing (goroutine/`errgroup` setup, `log`/`slog` calls, `fmt.Sprintf` blocks) into named helpers; the top reads like a table of contents. (`llm_generated_code_smells::mixed-abstraction-levels`)
15. **One responsibility — no conjoined verbs.** No `BuildAndReview`, no `OpenAndMigrate`: two verbs = two functions, the caller composes. (`l5_architecture::l5-M-one-responsibility-per-unit-srp`)
16. **Business logic separated from infra.** The pure function holds no `db` / git / LLM / `time.Now()`; IO is fetched at the edge and passed in as data. **Accept interfaces, return structs** — and a domain struct never carries a `db` / `context.Context` / connection field: those enter at the edge as parameters, never baked into the value. (`fp_lens::core-buried-outward`, `decision-executes-its-own-effect`)
17. **Railway-oriented (ROP): linear happy path, short error arm.** Each `if err != nil { return ..., fmt.Errorf(...: %w) }` is a one-line bail; the guard arm is NEVER a home for long code. Reading top-to-bottom sees only the success flow. (`l5_architecture::l5-A-errors-as-values` · railway pattern)
18. **Paragraph the body: setup → work → return.** Group the lines into visible phases (gather inputs · do the work · assemble the result), a blank line between; no interleaving. *(no dedicated rubric rule yet — read by a human.)*
19. **Parameter object / functional options, not a cross-domain bucket brigade.** Group cohesive params into a struct; never a 13-arg signature threading `ctx` + `db` + config + flags + raw data. (`l5_architecture::l5-M2-cross-domain-arity`)
20. **A returned struct carries facts, not UI.** The `Outcome` you hand to the next stage holds domain data only — never a `Notifications []string` of pre-formatted banner lines, never a `chan` / `io.Writer`. Render banners at the edge FROM the facts. *(arc's baseline `AssemblyResult { notifications }` was exactly this bug — ripped out into a typed `ChangeOutcome`.)*

## Say less

21. **Comments say WHY, not WHAT, and are short.** No revision-history diary (git owns it); a doc comment starts with the name and states intent — if a function needs a paragraph, it needs a better name.
22. **Reuse the stdlib / an existing package before hand-rolling** (hashing, parsing, dedup, retries) — check `go.mod` and stdlib first.
23. **Delete dead code** — no exported-but-unused shim, no `//nolint` "keep it + tolerate it" compat layer.
24. **Magic literal → a named `const` with its unit;** and never `//nolint` to mask a real design flaw — fix the design.

