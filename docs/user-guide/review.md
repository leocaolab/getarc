# How arc reviews — the FP lens and per-file contracts (L4)

This is the lower of arc's two altitudes: **L4 — per-file contracts**, run by `arc local-review`. (The upper one, structural rot, is [rot.md](rot.md).) L4 asks the local question — *is this line right?* — through a specific lens.

## The FP lens — why arc reviews the way it does

arc is written functional-core / imperative-shell, and it reviews your code through the same lens. This is not dogma; it is the set of properties that make LLM-written code safe to keep. The Critic's L4 rubric encodes them, so the biases below are literally what it flags.

- **Functional core, imperative shell.** Pure logic (no IO) lives in a core the shell drives. arc's own `review_core` is IO-free (enforced by `deny(clippy::print_stdout)`). Mixing IO into pure logic is a smell.
- **Parse, don't validate.** Turn unstructured input into a typed value at the boundary, once; downstream code consumes the type, not re-checked strings.
- **Errors are typed and carry their cause.** Never stringify a typed error at a boundary (`.map_err(|e| e.to_string())`) — carry it with `#[from]` so callers branch on the variant, not a `.contains()` grep. (`l4_contracts::untyped-error-origin`.)
- **Closed domains are enums, not magic strings.** A fixed set of states is an exhaustive enum the compiler checks, never a stringly-typed value. (`rust_best_practices::stringly-typed-domain-value`.)
- **No sentinels leaking to consumers.** `null` / `-1` / `""` standing in for a real failure hides the truth. A failure is a typed `Err` / `Option`, surfaced, not a buried magic value. (`l4_contracts::missing-error-classification`, `llm_generated_code_smells::ambiguous-return-sentinel`.)
- **One source of truth; never backfill from a derived view.** Whoever produces a fact writes it in full at the source — don't reconstruct primary data from a derived store later.
- **Total functions.** Don't call a partial function (`unwrap` / `head` / `fromJust`) as if total; handle the empty/None case. (`fp_lens::partial-function-as-total`, `rust_best_practices::no-unwrap-in-library`.)

## The effect & state discipline lens (experimental)

A second FP-grounded lens, `effect_state.yaml`, reframes **resource, concurrency and cancellation** hazards through the same Haskell north-star — `bracket` (borrowed must be returned), a bounded effect graph, async-exception propagation. It targets the imperative languages arc reviews (Python / Go / Java / JS / TS / C / C++) and several of its rules are deliberately **INERT in RAII / GC-scope languages** (Rust's `Drop`, Haskell's `bracket` already guarantee release). Four of its rules:

- **`resource-owned-but-not-released`** — a unit acquires more releasable resources (lock / file / socket / connection / subprocess / HTTP client) than it releases. The test is *ownership vs release count*, not "is there a `with`/`finally` somewhere" — it catches the subtle case where a cleanup exists but doesn't cover everything: `with sqlite3.connect(...)` commits but never *closes* the connection; a class that stops its subprocess but never closes the two `httpx` clients it created (owns 3, releases 1).
- **`unbounded-concurrency-fan-out`** — one concurrent task per item of an unbounded source (a thread/`create_task` per request) with no bounded pool or semaphore.
- **`cancellation-signal-swallowed`** — a cancellation / interrupt (`CancelledError`, a cancelled `context`, `AbortSignal`, `InterruptedException`) caught and dropped without re-propagating or honouring it.
- **`exception-logged-and-rethrown`** — a handler that both logs *and* rethrows, duplicating the stack trace at every layer.

These four are `experimental` (so is `pure-logic-in-effectful-scope`; `shared-mutable-state-in-decision-layer` is `stable` and runs) — candidates that must earn a measured delta over a bare critic before promotion (`arc local-review` has no `--experimental` flag; the review plane's reviewer asks under stable rules only). They were mined from how LLMs write these hazards, which is exactly where they fire hardest: on hand-written code they mostly stay quiet (people reach for a pool, re-raise, log-and-return), but on LLM-generated code the "handles the obvious resource, forgets the quiet ones" shape shows up immediately.

## The rot LLMs (Claude included) typically produce

LLMs write plausible code fast, and it rots in recognizable ways. arc exists because these patterns are hard to catch by eye at review time but easy to name. The rules that catch each live in `rubrics/` (rule id in parentheses):

| Typical LLM rot | What it looks like | arc rule |
|---|---|---|
| **Swallowed failure** | `except: pass`, `let _ = fallible()`, a `catch` that neither rethrows nor returns the error | `l4_contracts::swallowed-exception` |
| **Type erasure at a boundary** | a typed error flattened to a string (`e.to_string()`) so callers must `.contains()`-grep it | `l4_contracts::untyped-error-origin` |
| **Stringly-typed domain** | a closed set of states modeled as free strings instead of an enum | `rust_best_practices::stringly-typed-domain-value` |
| **Ambiguous sentinel return** | `null` / `-1` / `""` conflating "failure" with "empty" with a real value | `llm_generated_code_smells::ambiguous-return-sentinel` |
| **Magic literals** | unexplained constants threaded through logic | `llm_generated_code_smells::magic-literal` |
| **Partial-as-total** | `unwrap` / `head` on a maybe-empty value in library code | `fp_lens::partial-function-as-total` |
| **Unvalidated external input** | request/env/file data used without a boundary check | `security_common::validate-external-input` |
| **Incomplete error context** | an error constructed without the inputs that caused it | `l4_contracts::incomplete-error-context` |
| **Over-broad catch** | a catch-all sweeping in signals/bugs it can't handle | `l4_contracts::over-broad-exception-handler` |
| **Changelog-in-comment** | narrative "changed X to Y" comments instead of describing the code | `comment_hygiene::refactor-history-narration` |

Two failure modes above the line level are **structural rot**, not L4 — god-modules and cross-file reinvention. Those are [rot.md](rot.md)'s territory.

## How L4 works

The Critic reviews each file against the L4 rubric (`rubrics/l4_contracts.yaml` + per-language `*_best_practices.yaml` + `llm_generated_code_smells.yaml` + `fp_lens.yaml`). Every rule names ONE distinct hazard with crisp boundaries, so one smell → one finding, not a carpet-bomb. Deterministic detectors pre-triage cheap signals (e.g. a swallow ending in a sentinel) so the LLM confirms rather than re-derives.

Findings are then answered — by `arc fix` or by you — each one fixed or won't fix, and the new head is reviewed again. A change lands only after the reviewers say LGTM and the merge machine's run of your `merge.yml` shows no new failure ([The merge gate](merge-gate.md)).

An `[arc:intentional-handle]` comment documents a deliberate exception so the Critic doesn't re-flag it — the escape hatch for the rare justified case.

---

*Next: [Rot (L5)](rot.md) · [The commands](commands.md) · Finding model.*
