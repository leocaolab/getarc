---
name: shift-left-c
description: How to WRITE genuinely clean C — universal good-code principles in C idiom, stated in full so the skill is self-contained and portable (works in any repo; nothing else needed). The positive form of common review anti-patterns, so the code is clean the FIRST time. The aim is the principle itself, not passing any linter. Load before writing or editing C (a fix, a new function, any codegen). Triggers include writing/editing .c/.h, "fix this C", "add a C function".
---

# Writing clean C (shift-left)

The goal in one line: **write the version the next reader — human or model — can
extend without re-reading the whole thing.** Clear structure = the correct next
line is obvious. Checklist, not an essay.

> **The target is the principle, not passing a reviewer.** Every rule is stated in full
> here, so it works in any repo. A `stem::name` in parentheses names the review-rubric
> rule this one mirrors; the full rule, with its reason and examples, is in the arc-skills
> plugin's `rubrics/<stem>.yaml` — open it when you want more, never because you must.
> Never write code merely to keep a detector quiet — a linter with finite recall
> going silent is not proof the code is clean; gaming its blind spots is the failure.

> **C's type system is weak — several principles are best-effort here.** "Make illegal
> states unrepresentable", "typed errors", and "const-correctness" are enforced by the
> compiler in stronger languages; in C you approximate them with `enum`s, tagged unions,
> explicit status codes, and `const` discipline. Where the compiler won't catch a slip,
> the convention IS the guardrail — hold it deliberately.

## Separate IO from logic

1. **Fetch, then decide.** Read the data first; a *pure* function computes the result — no `read()` / `fopen` inside the loop that decides.
   - ❌ `for (i=0;i<n;i++){ hash_file(items[i].path,buf); if(!strcmp(buf,cur)) keep[k++]=items[i]; }`
   - ✅ `load_hashes(items, n, rows);` → `partition(rows, n, &keep, &skip);`  *(pure, no IO)*
2. **A decider returns a plan; it does not do the IO.**
   - ❌ `if (stale) { db_close(id); notify(id); }`
   - ✅ `*out_cmd = (Command){ .kind = CMD_CLOSE, .id = id };` — the caller (shell) performs the effect
3. **Business logic takes data as parameters** — no file / socket / `time(NULL)` / global read inside, and no side effect wrapped around a pure computation.

## Type your data and errors

4. **Named `struct`, not parallel arrays or an opaque `void*`,** across a boundary; and a `typedef`'d domain type, not a bare `int`/`char*` that secretly means "id".
   - ❌ `int find_loc(const char *p, int *out_line);` returning `(path, line)` split across args
   - ✅ `typedef struct { const char *path; size_t line; } Loc;`
   - ❌ `void close_issue(int id);`  *(what int? row? handle?)*
   - ✅ `typedef struct { uint64_t value; } IssueId;` → `void close_issue(IssueId id);`
5. **Explicit status code, CHECKED at the call site** — never ignore a return, never lean on a hidden `errno` the caller forgets. Return the value via out-parameter + a status, or `NULL` + status; document ownership in the signature.
   - ❌ `parse(buf, &out);`  *(return value dropped)* · `char *s = get(); use(s);`  *(NULL unchecked)*
   - ✅ `Status st = parse(buf, &out); if (st != OK) return st;`
   - ✅ `/* returns owned buffer, caller frees; NULL + sets *st on error */ char *render(const Node *n, Status *st);`
6. **Closed set → `enum`,** not magic `int` / `#define` numbers or a stringly-typed value compared at runtime.
   - ❌ `if (verdict == 2)` · `if (!strcmp(verdict, "accepted"))` · `#define ST_OPEN 0`
   - ✅ `typedef enum { VERDICT_ACCEPTED, VERDICT_IGNORED } Verdict;`
   - **Sum type → tagged union:** `typedef struct { enum { R_OK, R_ERR } tag; union { Value ok; Error err; }; } Result;` — the `tag` says which arm is live; never read the other.

## Don't swallow, don't hide

7. **No `assert` / `abort` / `exit` as error handling in library code** — return a `Status` and let the caller decide. `assert` is for impossible-by-construction invariants, not for input that can legitimately be bad.
8. **Don't discard the error path.** No unchecked `malloc` / `fopen` / `write`; every fallible call's result is inspected before the value is used.
   - ❌ `FILE *f = fopen(p, "r"); fread(buf, 1, n, f);`  *(f may be NULL)*
   - ✅ `FILE *f = fopen(p, "r"); if (!f) return ERR_IO;`
9. **Don't paper a failed own-data read with a default.** `atoi` on a corrupt row silently yields `0`; a `?:` fallback hides corruption — surface real absence explicitly (a status + out-flag) and propagate the broken invariant with the id.

## Subtract, don't patch

10. **One clear pass over an accumulator,** not a pile of nested `if` flags accreted over time — compute the predicate once.
    - ❌ `for(..){ if(a(x)){ if(b(x)){ res[k++]=x; } } }`
    - ✅ `for(..){ if (a(x) && b(x)) res[k++] = x; }`
11. **Initialize at the declaration; no deferred mutable.** `int x = c ? a : b;`, not `int x; if (c) x=a; else x=b;` — a declared-then-maybe-assigned variable risks a read of garbage.
12. **Explicit `enum` state + `switch`,** not a few `bool` flags mutated across a loop (and `switch` over the enum with no `default` lets `-Wswitch` flag a missed case — the closest C gets to exhaustiveness).
13. **Function-pointer table (vtable) or a dispatch `switch`** for a `if (kind==A) … else if (kind==B) …` type-ladder repeated at ≥2 sites — one place decides, not many.

## Fluency (流畅) — one altitude, one job, one railway

The bar: a function reads top-to-bottom at ONE cognitive altitude, does ONE thing,
flows down a single happy-path rail, and reads as a **chain of transformations** —
each step turns one value into the next, with no mutable accumulator threaded
through and nothing to simulate in your head. (Each tell names the rubric rule
it mirrors.)

14. **One level of abstraction per function.** Push buffer wrangling, `snprintf` formatting, and `fprintf(stderr, …)` logging into named helpers; the top reads like a table of contents. (`llm_generated_code_smells::mixed-abstraction-levels`)
15. **One responsibility — no conjoined verbs.** No `parse_and_validate`, no `open_and_migrate`: two verbs = two functions, the caller composes. (`l5_architecture::l5-M-one-responsibility-per-unit-srp`)
16. **Business logic separated from infra.** The pure computation holds no `FILE*` / socket / `time(NULL)`; IO is done at the edge and the data passed in. And a **domain struct never carries a `FILE*` / connection / context field** — those handles live in the shell, passed alongside the data, never baked into the struct. And **no global mutable state** — no non-`const` file-scope variable smuggling state between calls; pass it in, return it out. (`fp_lens::core-buried-outward`, `decision-executes-its-own-effect`)
17. **Railway-oriented: linear happy path, short error arm.** An early `if (st != OK) return st;` guard (or a single `goto cleanup;` for resource release) bails in one line; the error arm is NEVER a home for long code. Reading top-to-bottom sees only the success flow. (`l5_architecture::l5-A-errors-as-values` · railway pattern)
18. **Paragraph the body: setup → work → return.** Group the lines into visible phases (gather inputs · do the work · assemble the result), a blank line between; no interleaving. *(no dedicated rubric rule yet — read by a human.)*
19. **Parameter struct, not a cross-domain bucket brigade.** Group cohesive params into a `typedef`'d struct passed by `const` pointer; never a 13-arg signature threading handle + config + flags + raw data. (`l5_architecture::l5-M2-cross-domain-arity`, `rust_best_practices::primitive-obsession-long-param-list`)
20. **A returned struct carries facts, not UI.** The `Corpus` / `Outcome` you hand to the next stage holds domain data only — never a `char *notifications[]` of pre-formatted banner lines, never a `FILE*` sink. Render banners at the edge FROM the facts. *(arc's baseline `AssemblyResult { notifications }` was exactly this bug — it was ripped out into a typed outcome.)*

## Say less

21. **Comments say WHY, not WHAT, and are short.** No revision-history diary (git owns it); if a function needs a paragraph, it needs a better name. Do document the non-obvious contract C can't express in types: **ownership** (who frees), buffer size expectations, and NULL-ability.
22. **Reuse before reinvent** — a vetted library or an existing helper (hashing, string ops, dynamic arrays) before hand-rolling a fragile `memcpy` loop; check what's already linked.
23. **Delete dead code** — no `#if 0` graveyard, no unused static function kept "just in case", no "keep it + tolerate it" compat shim.
24. **Magic literal → `enum` / `#define` / `const` with its unit;** buffer sizes especially (`char buf[256]` scattered → one named constant used at both the declaration and the `snprintf` bound). Never silence a real warning with a cast or a pragma — fix the design.

