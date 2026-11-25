# Rot — what it is, why it hurts, how arc handles it

Most review tools ask one question: *is this line correct?* arc asks a second one that no single file can answer — *is the system's shape decaying?* That decay is what arc calls **rot**, and finding it is a distinct capability (`arc rot`) with its own rubric, signals, and workflow. This page is the whole idea in one place.

## What rot is

> **Rot is structural decay: a problem whose root lives in the *shape* of the system — its types, module boundaries, dependency direction, cohesion — not in any single line, and which therefore can only be seen across files and fixed across files.**

Four properties separate rot from an ordinary defect:

1. **It is emergent — cross-file.** You cannot see it in one file. A god-module, the same idiom reinvented in five places, a dependency pointing the wrong way, one concept modelled as three different structs in three crates — each is invisible per file and only appears on the system map.
2. **The root is structural, not local.** The symptom may be a single line, but the rot is the structural weakness that *forces* that line. Fix the line and the rot remains.
3. **The fix spans many sites.** Widening a return type and updating every caller, splitting a module, inverting a dependency, extracting a shared type — never a one-line patch.
4. **It accumulates.** "Rot" is literal: as a codebase grows, modules bloat, duplication creeps, layers blur, types weaken. It is decay over time, not a bug that was always wrong.

### The altitude model — L4 vs L5

arc sorts every problem by **altitude**, and rot is the upper one:

| | **L4 — contract** | **L5 — rot** |
|---|---|---|
| what | a local, per-file correctness/quality violation | structural decay, emergent across files |
| root | in this line / this function | in the system's shape (types, layers, cohesion) |
| fix | local, in place | a restructuring across many sites |
| found by | `arc local-review` | `arc rot` |

The dividing line is not the *symptom* — it is the *altitude of the root*. The same surface symptom can be either, depending on where its cause lives.

**Worked example — a swallowed error.** A `catch` that drops an error and returns nothing:

- If that one handler merely forgot to propagate, it is **L4** (`l4_contracts::swallowed-exception`). Local. The fix is local: log it, propagate it, or return a value that carries the failure.
- But if the handler swallows *because the function returns a bare primitive* (`Vec`, `dict`, `bool`) with no channel to carry a failure, it is **L5 rot** (`l5-R-swallowed-error-primitive-return`). The swallow is only the symptom; the rot is the weak return type. The fix is structural: widen the return to `Result`/`Option` and update every caller.

Same symptom, two altitudes. That is the whole distinction in one example: **L4 asks "is this line right?"; rot asks "is the system's skeleton decaying?"**

## Why rot hurts

Rot rarely breaks the build — which is exactly why it is dangerous. It erodes the system's *capacity to change* while every individual test stays green:

- **Silent-failure blast radius.** A swallowed error behind a primitive return runs the whole system on hollow data — downstream sees no failure, only a black hole, and the fault surfaces far from its cause.
- **Change amplification.** A god-module that accreted unrelated responsibilities means every feature touches it; edits collide, blast radius grows, and no change stays local.
- **Divergent fixes.** The same logic reinvented across files means a bug fixed in one copy stays alive in the other four. Behaviour drifts apart silently.
- **Illegal states.** Weak, stringly-typed, or duplicated domain types let the code represent states that should be impossible; the compiler stops helping and correctness slips to runtime.
- **Lost testability and reuse.** A dependency pointing the wrong way (a pure core reaching into the shell, a lower tier named in a higher one) means the piece can no longer be tested or reused in isolation.

None of these is a bug you can point at. They are the interest payment on structural debt — and they compound, until the system hits the "we have to rewrite it" wall.

## How arc detects it

`arc rot` is the L5 pass. Because rot is *emergent*, a prompt alone cannot find it — you cannot read one file and judge a cross-file pattern. So arc leads with **deterministic signals** that surface candidates, then has the LLM judge them:

```bash
arc rot              # whole-repo structural review (L5): signals → LLM judge
arc rot --no-judge   # deterministic signals only — no LLM, cheap, CI-friendly
```

The signals, by rot family:

- **God-modules** — a blended complexity × fan-out score in the top ~5%, past a ~300-line floor.
- **Cross-file duplication (reinvention)** — the same idiom in ≥3 files after α-normalization (variables/literals normalized, callee/type names kept).
- **Duplicated domain types** — one concept modelled by same-named `struct`/`enum` in ≥2 crates.
- **Structural signals** — a dependency pointing down (a lower tier named in a higher-tier consumer), driver/wiring seams hiding real logic, inheritance fan-out (god-traits), hardcoded policy constants.

The signal narrows thousands of structural candidates to a handful; the LLM then *confirms* rather than re-derives. `--no-judge` gives you the signal alone — a cheap, deterministic **rot score to trend in CI**.

> Dead-code detection currently lives in `experimental_lab`, off the rot path until it clears a precision bar — `arc rot` does not report it yet.

## How arc handles it

Here arc is deliberately conservative. **It detects and quantifies rot; it does not auto-refactor it.**

Rot findings are printed as **suggestions** — **opt-in**. They are kept nowhere but that run's report: they go on no PR, so `arc fix` never sweeps them, because a structural change is large-scale by nature and must be a decision, not a reflex. To act on one, make the restructuring yourself (or have your coding agent make it) on a branch, then `arc local-review` / `arc submit` it like any change:

```bash
arc rot --file <path>       # the suggestions for one file or directory
arc rot --no-judge          # cheap rot signal to trend over time
```

The honest reading: **`arc rot` gives you a rot score to watch, not a refactor button.**

Why not auto-fix rot the way arc fixes an L4 finding? Because the remedy is a *plan*, not a patch — move this, split that, invert this dependency, in this order, with this blast radius. That plan-level capability (the neuro-symbolic **refactor** engine) is experimental and off the main path; longer term the plan it produces is meant to be executed by a dedicated refactor loop — the mechanical moves by AST rewrite, the semantic ones by an LLM. Until then, rot is surfaced and scored, and *you* decide the restructuring.

---

*See also: [Custom rubrics](custom-rubrics.md) to add your own rot axes · [The commands](commands.md) · Finding model.*
