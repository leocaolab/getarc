---
name: shift-left-python
description: How to WRITE genuinely clean Python — universal good-code principles in Python idiom, stated in full so the skill is self-contained and portable (works in any repo; nothing else needed). The positive form of common review anti-patterns, so the code is clean the FIRST time. The aim is the principle itself, not passing any linter. Load before writing or editing Python (a fix, a new function, any codegen). Triggers include writing/editing .py, "fix this Python", "add a Python function".
---

# Writing clean Python (shift-left)

The goal in one line: **write the version the next reader — human or model — can
extend without re-reading the whole thing.** Clear structure = the correct next
line is obvious. Every rule below serves that.

Use the DRAFT below when you write or fix Python. It is a checklist, not an essay.

> **The target is the principle, not passing a reviewer.** Every rule is stated in full
> here, so it works in any repo. A `stem::name` in parentheses names the review-rubric
> rule this one mirrors; the full rule, with its reason and examples, is in the arc-skills
> plugin's `rubrics/<stem>.yaml` — open it when you want more, never because you must.
> Never write code merely to keep a detector quiet — a linter with finite recall
> going silent is not proof the code is clean; gaming its blind spots is the failure.

## Separate IO from logic

1. **Fetch, then decide.** Pull the data first; a *pure* function computes the result.
   - ❌ `for u in items: row = db.get(u); if row.x == y: keep.append(u)`
   - ✅ `rows = [(u, db.get(u)) for u in items]` → `kept = partition(rows)`  *(pure, testable)*
2. **A decider returns a plan; it does not do the IO.**
   - ❌ `if stale: db.close(id); notify(id)`
   - ✅ `return CloseIssue(id)` — the caller performs the effect
3. **Business logic takes data as arguments** — no `db` / file / network / `datetime.now()` *inside* it.

## Type your data and errors

4. **Structured data, not a bag** across a boundary. `@dataclass` / `TypedDict` / Pydantic, not a `dict` or `(a, b)` tuple.
   - ❌ `def loc() -> tuple[str, int]:` · `return {"file": f, "line": n}`
   - ✅ `@dataclass class Loc: path: str; line: int`
5. **Typed errors, not stringly.** A specific exception class, never `Exception("msg")`.
   - ❌ `raise Exception("no base commit")`
   - ✅ `class NoBaseCommit(AppError): ...` → `raise NoBaseCommit()`
6. **Closed set → `Enum`,** not string constants compared with `==`.
   - ❌ `if status == "closed"`
   - ✅ `class Status(Enum): CLOSED = auto()`

## Don't swallow, don't hide

7. **Never `except Exception: pass`.** Catch the specific type; log with context or re-raise.
   - ❌ `except Exception: pass`
   - ✅ `except OSError as e: log.debug("skip %s: %s", f, e)`
8. **Log the error object, not `str(e)`** — `log.exception(...)` keeps the traceback.
9. **Fail fast on your OWN corrupt data** (a bad DB row, a failed parse) — raise with the id, don't silently skip.

## Subtract, don't patch

10. **Collapse conditionals; don't accrete.** A pile of `if` / filter / flag → one declarative expression.
    - ❌ `res = []; for x in xs: if a(x): if b(x): res.append(x)`
    - ✅ `res = [x for x in xs if a(x) and b(x)]`
11. **No deferred mutable.** `x = None; if c: x = v` → `x = v if c else None`.
12. **Explicit state machine,** not a flag mutated across a loop → `Enum` state + transitions.
13. **Type dispatch → polymorphism or a dict,** not a growing `if isinstance(...)` ladder.

## Fluency (流畅) — one altitude, one job, one railway

The bar: a function reads top-to-bottom at ONE cognitive altitude, does ONE thing,
flows down a single happy-path rail, and reads as a **chain of transformations** —
each step turns one value into the next, with no mutable accumulator threaded
through and nothing to simulate in your head. (Each tell names the rubric rule
it mirrors.)

14. **One level of abstraction per function.** A high-level fn reads like a table of contents; push plumbing (event loop, logging, f-string/console formatting) into named helpers. (`llm_generated_code_smells::mixed-abstraction-levels`)
15. **One responsibility — no conjoined verbs.** No `build_and_review`, no `load_and_validate`: two verbs = two functions, the caller composes. (`l5_architecture::l5-M-one-responsibility-per-unit-srp`)
16. **Business logic separated from infra.** The pure function holds no `db` / file / network / `datetime.now()`; IO is fetched at the edge and passed in as data. And a **domain type never carries a `db` / connection / context field** — those handles live in the shell, passed alongside the data, never baked into it. (`fp_lens::core-buried-outward`, `decision-executes-its-own-effect`)
17. **Railway-oriented (ROP): linear happy path, short error arm.** Guard-clause early-returns / a single `raise` caught at the edge; the `except` / `else` arm is a one-line bail, NEVER a home for long code. Reading top-to-bottom sees only the success flow. (`l5_architecture::l5-A-errors-as-values` · railway pattern)
18. **Paragraph the body: setup → work → return.** Group the lines into visible phases (gather inputs · do the work · assemble the result), a blank line between; no interleaving. *(no dedicated rubric rule yet — read by a human.)*
19. **Parameter object, not a cross-domain bucket brigade.** Group cohesive params; never a 15-arg signature threading `db` + config + flags + raw data. (`l5_architecture::l5-M2-cross-domain-arity`)
20. **A returned object carries facts, not UI.** The result/outcome you hand to the next stage holds domain data only — never a `notifications: list[str]` of pre-formatted console lines, never a queue/channel. Render banners at the edge FROM the facts. *(the same bug arc's Rust baseline had: an `AssemblyResult` with a `notifications: Vec<String>` field.)*

## Say less

21. **Comments: minimal; the default is none.**
    - First fix the code: rename, extract, simplify. A comment that re-says the code or the signature is deleted (`"""Return the user ID."""` on `def user_id`).
    - Keep only what the code cannot say: **why** (an outside constraint, a bug worked around, an ordering or concurrency rule, why *not* the obvious way) and what a caller cannot see (side effects, raised exceptions, units, edge cases).
    - A docstring opens with one imperative sentence (`Wait until …`, PEP 257); an attribute doc only when it adds a unit, range or invariant.
    - Every comment is a complete sentence with a subject and a verb, never a fragment (`"""Performance cores only."""` is a fragment).
    - One or two plain sentences a newcomer understands. No history (git has it), no step lists, no private jargon; an issue number points to the story, it is not the reason.
    - Test: hide the code and read only the comments — you learn the intent and the traps, not the steps.
22. **Reuse before reinvent.** Reach for stdlib / an existing helper before hand-rolling (hashing, parsing, dedup, retries).
23. **Delete dead code.** Unused fields / functions go; no "keep it + tolerate it" shim.
24. **Magic literal → named constant** with its unit. `timeout=3` (in 4 places) → `TERMINATE_TIMEOUT_SEC = 3`.

