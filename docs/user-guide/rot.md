# Rot — what it is, why it hurts, how arc handles it

To find structural problems across your whole repo, run:

```bash
arc rot              # whole-repo structural review (L5): signals → LLM judge
arc rot --no-judge   # deterministic signals only — no LLM, cheap, CI-friendly
```

Most review tools ask one question: *is this line correct?* `arc rot` asks a second one that no single file can answer: *is the shape of the system getting worse?* arc calls that decay **rot**. This page explains what it is, why it matters, and what arc does about it.

## What rot is

> **Rot is structural decay: a problem whose cause lies in the *shape* of the system — its types, module boundaries, which way dependencies point, what belongs together — not in any single line. You can only see it across files, and only fix it across files.**

Four things set rot apart from an ordinary bug:

1. **You can't see it in one file.** A module that does everything, the same logic written five times, a dependency pointing the wrong way, one concept modelled as three different structs in three crates — each looks fine file by file and only shows up when you look at the whole system.
2. **The cause is structural.** The symptom may be one line, but rot is the weakness in the structure that *forces* that line. Fix the line and the rot is still there.
3. **The fix touches many places.** Widening a return type and updating every caller, splitting a module, reversing a dependency, pulling out a shared type — never a one-line patch.
4. **It builds up over time.** As a codebase grows, modules bloat, copies spread, layers blur and types weaken. Nothing was wrong on day one.

### Two levels: L4 and L5

arc sorts every problem by where its cause lives. Rot is the upper level:

| | **L4 — contract** | **L5 — rot** |
|---|---|---|
| what | a problem inside one file | structural decay across files |
| cause | in this line or this function | in the system's shape (types, layers, what belongs together) |
| fix | in place | restructuring across many places |
| found by | `arc local-review` | `arc rot` |

What decides the level is not the symptom but where its cause is. The same symptom can be either.

**Example: a swallowed error.** A `catch` drops an error and returns nothing.

- If that one handler simply forgot to pass the error on, it is **L4** (`l4_contracts::swallowed-exception`). The fix is local: log it, pass it on, or return a value that carries the failure.
- If the handler swallows the error *because the function returns a bare value* (`Vec`, `dict`, `bool`) that has no way to carry a failure, it is **L5 rot** (`l5-R-swallowed-error-primitive-return`). The swallow is only the symptom; the cause is the weak return type. The fix is structural: change the return type to `Result` / `Option` and update every caller.

Same symptom, two levels. **L4 asks "is this line right?"; rot asks "is the system's skeleton decaying?"**

## Why rot hurts

Rot rarely breaks the build, which is why it is dangerous. Every test stays green while the system gets harder and harder to change:

- **Failures go silent and spread.** An error swallowed behind a bare return value means the rest of the system runs on empty data. Nothing downstream sees a failure, and the fault shows up far from where it started.
- **Every change touches the same place.** A module that has collected unrelated jobs gets touched by every feature. Edits collide, and no change stays small.
- **Copies drift apart.** When the same logic exists in five files, a bug fixed in one copy lives on in the other four.
- **Impossible states become possible.** Weak, string-based or duplicated types let the code represent states that should never exist. The compiler stops helping, and mistakes show up at runtime instead.
- **Pieces can't be tested or reused alone.** A dependency pointing the wrong way (pure logic reaching into IO, a lower layer naming a higher one) ties the piece to everything around it.

None of these is a bug you can point at. They are the interest on structural debt, and they compound until the team hits the "we have to rewrite it" wall.

## How arc finds it

Because rot only shows across files, an LLM reading one file at a time cannot find it. So `arc rot` first runs **deterministic checks** that find candidates, then asks the LLM to judge each one.

What the checks look for:

- **Modules that do too much** — a combined size × fan-out score in the top ~5%, and at least ~300 lines.
- **The same code in several files** — the same pattern in ≥3 files after α-normalization (variable names and literals ignored, called functions and type names kept).
- **Duplicated types** — one concept defined as same-named `struct` / `enum` in ≥2 crates.
- **Other structural signs** — a dependency pointing down (a lower layer named after a higher-layer caller), "driver" or "wiring" code hiding real logic, traits or types that too much is forced through (god-traits), and hard-coded policy constants.

The checks narrow thousands of possible spots to a handful; the LLM then confirms them instead of searching from scratch. `--no-judge` skips the LLM and prints the check results alone — a cheap, repeatable **rot score you can track in CI**.

> Dead-code detection lives in `experimental_lab` until it is accurate enough; `arc rot` does not report dead code yet.

## What arc does about it

arc is deliberately careful here. **It finds and measures rot; it does not refactor it for you.**

`arc rot` prints its findings as **suggestions** in that run's report, and keeps them nowhere else. They are not added to any PR, so `arc fix` never touches them: a structural change is big by nature and should be a decision, not a reflex. To act on one, make the change yourself (or have your coding agent make it) on a branch, then `arc local-review` / `arc submit` it like any other change:

```bash
arc rot --file <path>       # the suggestions for one file or directory
arc rot --no-judge          # cheap rot signal to trend over time
```

In short: **`arc rot` gives you a rot score to watch, not a refactor button.**

Why not fix rot automatically, the way `arc fix` handles an L4 finding? Because the fix is a *plan*, not a patch: move this, split that, reverse this dependency, in this order, touching these places. arc's **refactor** engine, which produces such plans, is experimental and not part of the main workflow. The longer-term idea is a dedicated refactor loop that carries out the plan — mechanical moves by rewriting the syntax tree, the rest by an LLM. Until then, arc shows and scores rot, and *you* decide how to restructure.

---

*See also: [Custom rubrics](custom-rubrics.md) to add your own rules · [The commands](commands.md).*
