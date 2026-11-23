---
name: shift-left-java
description: How to WRITE genuinely clean Java — universal good-code principles in modern Java idiom, stated in full so the skill is self-contained and portable (works in any repo; nothing else needed). The positive form of common review anti-patterns, so the code is clean the FIRST time. The aim is the principle itself, not passing any linter. Load before writing or editing Java (a fix, a new method, any codegen). Triggers include writing/editing .java, "fix this Java", "add a Java method".
---

# Writing clean Java (shift-left)

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

1. **Fetch, then decide.** Load the data first; a *pure* method computes the result.
   - ❌ `for (var u : items) { var s = store.hash(db, u.path()); if (s.equals(cur)) keep.add(u); }`
   - ✅ `var rows = store.fetchAll(db, items);` → `var kept = partition(rows, cur);`  *(pure, testable)*
2. **A decider returns a plan; it does not do the IO.**
   - ❌ `if (stale) { db.close(id); notify(id); }`
   - ✅ `return new Close(id);` — the caller (shell) performs the effect
3. **Business logic takes data as arguments** — no `db` / file / network / `Instant.now()` *inside* it, and no blocking call wrapped around a pure computation.

## Type your data and errors

4. **`record`, not a bag** across a boundary. A named `record` / value type, not a `Map<String,Object>`, an `Object[]`, or a `Map.Entry` pair.
   - ❌ `Object[] loc() { ... }` · `map.get("file")`
   - ✅ `record Loc(Path path, int line) {}`
5. **Typed exceptions, not stringly.** A specific checked or domain exception class, never a bare `new RuntimeException("msg")` or `IllegalStateException("msg")` at a boundary; chain the cause.
   - ❌ `throw new RuntimeException("no base commit");`
   - ✅ `class NoBaseCommit extends AppException {}` → `throw new NoBaseCommit(cause);`
6. **Closed set → `enum`,** not `String` constants compared with `.equals`.
   - ❌ `if (verdict.equals("accepted"))`
   - ✅ `enum Verdict { ACCEPTED, IGNORED }` → exhaustive `switch`

## Make illegal states unrepresentable

7. **Sum type → `sealed interface` + `record`s,** switched exhaustively — not a tag field + nullable payloads. The compiler then forces every case.
   - ❌ `class Result { String kind; T value; Err error; }` *(both fields nullable, kind un-checked)*
   - ✅ `sealed interface Result<T> permits Ok, Err {}` → `switch (r) { case Ok<T> ok -> ..; case Err e -> ..; }`
8. **`Optional<T>` (or a sealed `Result`) instead of returning `null`.** A method that may find nothing says so in its type; callers can't forget the empty case.
   - ❌ `User find(Id id) { ... return null; }`
   - ✅ `Optional<User> find(Id id)` — and never `Optional` for a field or parameter, only a return.
9. **Immutable by default.** `record` for product types; `final` fields; return unmodifiable / defensively-copied collections. No public setter chain someone can mutate mid-flight.

## Don't swallow, don't hide

10. **Never `catch (Exception e) {}`.** Catch the specific type; log with the throwable (`log.warn("skip {}", f, e)` — pass `e` last, not `e.getMessage()`, to keep the stack trace) or rethrow wrapped with the cause.
    - ❌ `catch (Exception e) {}`
    - ✅ `catch (IOException e) { log.debug("skip {}", f, e); }`
11. **Don't discard the failure.** No empty catch, no `catch (X e) { return null; }` that erases a real fault — handle it or let it propagate.
12. **Fail fast on your OWN corrupt data** (a bad DB row, a failed parse) — throw with the id, don't paper it over with a default. `getOrDefault(id, 0)` on a read you expect to exist hides corruption; model true absence as `Optional`, surface the broken invariant with its id.

## Subtract, don't patch

13. **Stream pipeline over a mutable accumulator** when clearer: `items.stream().filter(..).map(..).toList()`.
    - ❌ `var res = new ArrayList<>(); for (var x : xs) if (a(x) && b(x)) res.add(x);`
    - ✅ `var res = xs.stream().filter(x -> a(x) && b(x)).toList();`
14. **`var x = c ? a : b;`,** not `X x = null; if (c) x = a; else x = b;`.
15. **Explicit `enum` state + exhaustive `switch`,** not a few `boolean` flags mutated across a loop (the compiler then checks you handled every state).
16. **Polymorphism / sealed `switch`** for an `if (kind == ..) else if ..` type-ladder repeated at ≥2 sites — not a growing `instanceof` chain.

## Fluency (流畅) — one altitude, one job, one railway

The bar: a method reads top-to-bottom at ONE cognitive altitude, does ONE thing,
flows down a single happy-path rail, and reads as a **chain of transformations** —
each step turns one value into the next, with no mutable accumulator threaded
through and nothing to simulate in your head. (Each tell names the rubric rule
it mirrors.)

17. **One level of abstraction per method.** A high-level method reads like a table of contents; push plumbing (thread/executor wiring, logging, `String.format` / builder blocks) into named helpers. (`llm_generated_code_smells::mixed-abstraction-levels`)
18. **One responsibility — no conjoined verbs.** No `buildAndReview`, no `openAndMigrate`: two verbs = two methods, the caller composes. (`l5_architecture::l5-M-one-responsibility-per-unit-srp`)
19. **Business logic separated from infra.** The pure method holds no `db` / file / network / `Instant.now()`; IO is fetched at the edge and passed in as data. **Inject dependencies (DB, `Clock`, HTTP client) through the constructor** — never reach a static singleton (`Database.getInstance()`, `Clock.systemUTC()` buried inside) — and a **domain type never carries a `db` / connection / context field**; those handles live in the shell, passed alongside the data, never baked into it. (`fp_lens::core-buried-outward`, `decision-executes-its-own-effect`)
20. **Railway-oriented (ROP): linear happy path, short error arm.** Guard-clause early returns / a single throw caught at the edge; the `catch` / `else` arm is a one-line bail, NEVER a home for long code. Reading top-to-bottom sees only the success flow. (`l5_architecture::l5-A-errors-as-values` · railway pattern)
21. **Paragraph the body: setup → work → return.** Group the lines into visible phases (gather inputs · do the work · assemble the result), a blank line between; no interleaving. *(no dedicated rubric rule yet — read by a human.)*
22. **Parameter object, not a cross-domain bucket brigade.** A `record` of cohesive params; never a 13-arg signature threading `db` + config + flags + raw data. And **no raw types / no `Object` across a boundary** — a `List<User>`, a domain type, not a raw `List` or `Object` a caller must cast. (`l5_architecture::l5-M2-cross-domain-arity`, `rust_best_practices::primitive-obsession-long-param-list`)
23. **A returned type carries facts, not UI.** The `Corpus` / `Outcome` you hand to the next stage holds domain data only — never a `List<String> notifications` of pre-formatted banner lines, never a `Consumer` / queue. Render banners at the edge FROM the facts. *(arc's baseline `AssemblyResult { notifications }` was exactly this bug — ripped out into a typed `ChangeOutcome`.)*

## Place types by owner

24. **Package-private first.** No `public` on a class, constructor or method without a caller outside the package; tests sit in the same package and can still reach it. With JPMS / a multi-module build, `exports` (or the published API module) names only the API package — internals live in a non-exported `…internal` package.
    - ❌ `public class ReviewContext` in `com.x.common.model`, read by one service
    - ✅ `final class ReviewContext` (package-private) next to the review service that builds and consumes it
25. **Owner's module, not the reader's — and no shared `String`.** Two concepts that are both "just a `String`" get two `record` wrappers and one conversion where the reader consumes; never one class parked in a `common` / `shared-model` module because several modules import it.
    - ❌ `Set<String> failures` flowing from the test-output parser straight into the merge gate
    - ✅ `record ParsedFailure(String value)` (test side) · `record FailureId(String value)` (merge side) · `FailureId.of(ParsedFailure p)` at the merge gate's read
26. **Adapter types stay in the adapter.** `@Entity` / `@Table` / Spring Data `@Document` / Jackson DTOs live in the persistence or web package and are mapped at the edge (a static `from` / constructor, or MapStruct); the domain `record` carries no framework annotation, and an `@Entity` never reaches a domain service. (JPA wants a no-arg constructor and mutable fields — exactly why it cannot be your domain type.)
27. **Depend on the owner, or invert with a port.** If module A needs B's concept, A imports B's API package, or A declares an `interface` for what it needs and B implements it — never copy B's class into a shared module to avoid the dependency.

## Say less

28. **Comments say WHY, not WHAT, and are short.** No revision-history diary (git owns it); no Javadoc restating the signature; if a method needs a paragraph, it needs a better name.
29. **Reuse before reinvent.** Reach for the JDK / an existing library before hand-rolling (hashing, parsing, dedup, retries) — check what's already on the classpath.
30. **Delete dead code** — no `@SuppressWarnings("unused")` shim, no "keep it + tolerate it" compat layer.
31. **Magic literal → a named `static final` constant with its unit;** parse external input **at the boundary into a validated type** (a `record` whose constructor checks its invariants), never thread a raw `String` deep and validate late. And never `@SuppressWarnings` to mask a real design flaw — fix the design. (`security_common::validate-external-input`)

