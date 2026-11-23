---
name: shift-left-cpp
description: How to WRITE genuinely clean C++ — universal good-code principles in modern C++17/20 idiom, stated in full so the skill is self-contained and portable (works in any repo; nothing else needed). The positive form of common review anti-patterns, so the code is clean the FIRST time. The aim is the principle itself, not passing any linter. Load before writing or editing C++ (a fix, a new function, any codegen). Triggers include writing/editing .cpp/.hpp/.cc/.h, "fix this C++", "add a C++ function".
---

# Writing clean C++ (shift-left)

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

1. **Fetch, then decide.** Materialize the data first; a *pure `const`* function computes the result.
   - ❌ `for (auto& u : items) { auto s = store::hash(db, u.p); if (s == cur) keep.push_back(u); }`
   - ✅ `auto rows = fetch_all(db, items);` → `auto [keep, skip] = partition(rows);`  *(pure, no IO)*
2. **A decider returns a plan; it does not do the IO.**
   - ❌ `if (stale) { db.close(id); notify(id); }`
   - ✅ `return Command::Close{id};` — the caller (shell) performs the effect
3. **Business logic takes data as parameters** — no db / fs / net / `std::chrono::system_clock::now()` inside, and no side effects wrapped around a pure computation.

## Type your data and errors

4. **Named `struct`, not a `std::pair` / `std::tuple`** across a boundary; a parsed value type, not a raw `nlohmann::json` / `std::string` blob threaded through.
   - ❌ `std::pair<std::string, int> loc();` · `j.at("file").get<std::string>()` far from the boundary
   - ✅ `struct Loc { std::string path; std::size_t line; };`
5. **Typed, non-ignorable errors: `std::expected<T, E>` (C++23) or an error type — never a silently-dropped return code.** Mark fallible functions `[[nodiscard]]`; carry the cause as a typed `E`, not a stringified message at the boundary.
   - ❌ `int close(Id id); /* returns errno, caller ignores it */`
   - ✅ `[[nodiscard]] std::expected<void, DbError> close(Id id);` → propagate the typed `DbError`
6. **Closed set → `enum class`,** not a bare `int` / `#define` / stringly-typed value checked at runtime.
   - ❌ `if (verdict == "accepted")` · `#define ACCEPTED 0`
   - ✅ `enum class Verdict { Accepted, Ignored };`
   - For a sum type with payloads, use `std::variant<...>` + `std::visit`, not a tag `int` plus a union of fields.

## Don't swallow, don't hide

7. **No `throw` you never catch, no `abort` / `assert` as control flow in library code** — return `std::expected` / `std::optional` and let the caller decide. Reserve exceptions for truly exceptional, and never let one escape a boundary untyped.
8. **Don't discard the error result.** No `(void)fallible();` and no ignoring a `[[nodiscard]]` — handle it or propagate it.
9. **Don't paper a failed own-data unbox with a default.** `opt.value_or(0)` on a DB read hides corruption — model real absence as `std::optional<T>`, and propagate the broken invariant with the id instead of substituting a plausible-looking zero.

## Subtract, don't patch

10. **Algorithm / ranges over a hand-rolled mutable accumulator** when clearer: `std::ranges::filter` + `transform` → a `std::vector`, not a `for` loop pushing into a scratch vector.
11. **`const auto x = c ? a : b;` / init-in-`if`,** not `T x{}; if (c) x = ...;` (a deferred non-`const` mutable).
12. **Explicit `enum class State` + `switch`,** not a few `bool` flags mutated across a loop (the `switch` then gets compiler-checked exhaustiveness with `-Wswitch`).
13. **Virtual dispatch / a polymorphic type** for an `if (kind == ...) else if ...` type-ladder repeated at ≥2 sites — or `std::visit` over a `std::variant`.

## Fluency (流畅) — one altitude, one job, one railway

The bar: a function reads top-to-bottom at ONE cognitive altitude, does ONE thing,
flows down a single happy-path rail, and reads as a **chain of transformations** —
each step turns one value into the next, with no mutable accumulator threaded through
and nothing to simulate in your head. (Each tell names the rubric rule it
mirrors.)

14. **One level of abstraction per function.** Push threading, logging, `std::format` / stream-building blocks into named helpers; the top reads like a table of contents. (`llm_generated_code_smells::mixed-abstraction-levels`)
15. **One responsibility — no conjoined verbs.** No `buildAndReview`, no `openAndMigrate`: two verbs = two functions, the caller composes. (`l5_architecture::l5-M-one-responsibility-per-unit-srp`)
16. **Business logic separated from infra.** The pure decision holds no DB / git / LLM / clock; IO is fetched at the edge and passed in as data. And a **domain type never carries a `db` / connection / context field** — those handles live in the shell, passed by reference at the edge (a dependency, not a singleton `getInstance()`), never baked into the value or reached through global mutable state. (`fp_lens::core-buried-outward`, `decision-executes-its-own-effect`)
17. **Railway-oriented (ROP): linear happy path, short error arm.** Return early on the error; `and_then` / a guard-clause `if (!r) return std::unexpected(...)` short-circuits; the failure arm is a one-line bail, NEVER a home for long code. Reading top-to-bottom sees only the success flow. (`l5_architecture::l5-A-errors-as-values` · `llm_generated_code_smells` railway pattern)
18. **Paragraph the body: setup → work → return.** Group the lines into visible phases (gather inputs · do the work · assemble the result), a blank line between; no interleaving. *(no dedicated rubric rule yet — read by a human.)*
19. **Parameter object, not a cross-domain bucket brigade.** Group cohesive params into a `struct`; never a 13-arg signature threading DB + config + flags + raw data. (`l5_architecture::l5-M2-cross-domain-arity`, `cpp_best_practices::primitive-obsession-long-param-list`)
20. **A returned struct carries facts, not UI.** The `Corpus` / `Outcome` you hand to the next stage holds domain data only — never a `std::vector<std::string> notifications` of pre-formatted banner lines, never a `std::ostream&` / channel. Render banners at the edge FROM the facts. *(arc's baseline `AssemblyResult { notifications }` was exactly this bug — it got ripped out into a typed `ChangeOutcome`.)*

## Say less

21. **Comments say WHY, not WHAT, and are short.** No revision-history diary (git owns it); if a function needs a paragraph, it needs a better name.
22. **Reuse the standard library / an existing dep before hand-rolling** (hashing, parsing, dedup, spans) — reach for `<algorithm>` / `<ranges>` / `std::string_view` before writing a loop.
23. **Delete dead code** — no `#if 0` block, no commented-out body, no "keep it + tolerate it" compat shim.
24. **Magic literal → `constexpr` with its unit,** value-semantics and `const` / `constexpr` by default; no manual `new` / `delete` and no raw owning pointers — use RAII and `std::unique_ptr` / `std::shared_ptr` for ownership, references / `std::span` / `std::string_view` for borrows. And never a pragma-suppress to mask a real design flaw — fix the design.

