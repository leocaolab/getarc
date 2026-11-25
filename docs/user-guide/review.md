# How arc reviews — the FP lens and per-file contracts (L4)

`arc local-review` checks your change file by file and asks one question: *is this code right?* arc calls this level **L4 — per-file contracts**. Problems that only show up across many files (a module that does everything, the same logic copied into five places) are a different level, L5, and a different command: [Rot](rot.md).

This page covers what L4 flags and why.

## What the reviewer flags, and why

arc's own code is built as a **functional core with an imperative shell**: pure logic in the middle, IO at the edges. The reviewer checks your code against the same principles, because they are what keep LLM-written code safe to keep. Each principle below is written into the L4 rubric, so a violation becomes a finding.

- **Keep IO out of pure logic.** Decisions live in a core with no IO; the shell around it reads files, talks to the network and drives the core. arc's own `review_core` has no IO, and `deny(clippy::print_stdout)` makes printing from it a compile error. Mixing IO into pure logic is flagged.
- **Parse, don't validate.** Turn raw input into a typed value once, at the boundary. Code further in uses that type instead of re-checking strings.
- **Keep errors typed, with their cause.** Don't flatten a typed error into a string at a boundary (`.map_err(|e| e.to_string())`). Carry it with `#[from]`, so callers can match on the variant instead of searching the text with `.contains()`. (`l4_contracts::untyped-error-origin`.)
- **Use an enum for a fixed set of values.** A fixed set of states is an enum the compiler checks for completeness, not a free string. (`rust_best_practices::stringly-typed-domain-value`.)
- **Don't hide failure behind a magic value.** Returning `null`, `-1` or `""` in place of a real failure hides what happened. Return a typed `Err` or `Option` and let the caller see it. (`l4_contracts::missing-error-classification`, `llm_generated_code_smells::ambiguous-return-sentinel`.)
- **Write each fact once, where it is produced.** Whoever produces a piece of data writes all of it at the source. Don't rebuild primary data later from a cache or a summary.
- **Handle every case.** Don't call `unwrap` / `head` / `fromJust` as if the value could never be empty; handle the empty or `None` case. (`fp_lens::partial-function-as-total`, `rust_best_practices::no-unwrap-in-library`.)

## Resources, concurrency and cancellation (experimental)

A second rubric, `effect_state.yaml`, looks for resources that are never released, concurrency with no limit, and cancellations that get lost. It is aimed at the languages where these leak easily — Python, Go, Java, JS, TS, C and C++. Several of its rules say outright that they don't apply in Rust or Haskell, where `Drop` and `bracket` already release resources. Four of its rules:

- **`resource-owned-but-not-released`** — a piece of code opens more resources (locks, files, sockets, connections, subprocesses, HTTP clients) than it closes. The rule counts what is opened against what is closed, so it also catches cleanup that exists but doesn't cover everything: `with sqlite3.connect(...)` commits but never *closes* the connection; a class stops its subprocess but never closes the two `httpx` clients it created (opens 3, closes 1).
- **`unbounded-concurrency-fan-out`** — one thread or task per item of a source with no size limit (a `create_task` per request), with no pool or semaphore to cap it.
- **`cancellation-signal-swallowed`** — a cancellation or interrupt (`CancelledError`, a cancelled `context`, `AbortSignal`, `InterruptedException`) is caught and dropped instead of passed on or obeyed.
- **`exception-logged-and-rethrown`** — a handler both logs an exception *and* rethrows it, so the same stack trace is logged at every layer.

These four rules have `status: experimental` (so does `pure-logic-in-effectful-scope`; `shared-mutable-state-in-decision-layer` is `stable` and always runs). An experimental rule runs only when the clone's `.arc/config.toml` sets `[review] experimental = true`, or names the rule in `[review] enable`; `arc local-review` has no flag for it. They stay experimental until they show a measured improvement over a reviewer without them.

They were written from how LLMs get these things wrong, so that is where they fire most. On hand-written code they are mostly quiet — people reach for a pool, re-raise, or log and return. On LLM-written code the pattern "closes the obvious resource, forgets the quiet ones" shows up right away.

## The mistakes LLMs (Claude included) typically make

LLMs write plausible code fast, and it goes bad in predictable ways. These patterns are hard to spot by eye in review but easy to name, so arc has a rule for each. The rules live in `rubrics/`:

| Typical LLM mistake | What it looks like | arc rule |
|---|---|---|
| **Swallowed failure** | `except: pass`, `let _ = fallible()`, a `catch` that neither rethrows nor returns the error | `l4_contracts::swallowed-exception` |
| **Type lost at a boundary** | a typed error flattened to a string (`e.to_string()`), so callers have to `.contains()`-search it | `l4_contracts::untyped-error-origin` |
| **Strings instead of an enum** | a fixed set of states stored as free strings | `rust_best_practices::stringly-typed-domain-value` |
| **Ambiguous magic return value** | `null` / `-1` / `""` meaning "failed", "empty" or a real value, depending on the call | `llm_generated_code_smells::ambiguous-return-sentinel` |
| **Magic numbers** | unexplained constants scattered through the logic | `llm_generated_code_smells::magic-literal` |
| **Assuming a value is never empty** | `unwrap` / `head` on a value that can be empty, in library code | `fp_lens::partial-function-as-total` |
| **Unchecked external input** | request, environment or file data used without checking it at the boundary | `security_common::validate-external-input` |
| **Error without context** | an error built without the inputs that caused it | `l4_contracts::incomplete-error-context` |
| **Catch-all handler** | a catch-all that also swallows signals and bugs it can't handle | `l4_contracts::over-broad-exception-handler` |
| **Change history in comments** | "changed X to Y" comments instead of describing what the code does | `comment_hygiene::refactor-history-narration` |

Two problems sit above the single file: modules that do too much, and the same logic re-implemented across files. Those are structural rot, covered by [rot.md](rot.md).

## How an L4 review runs

The reviewer (the Critic) checks each file against the L4 rubrics: `rubrics/l4_contracts.yaml`, the per-language `*_best_practices.yaml`, `llm_generated_code_smells.yaml` and `fp_lens.yaml`. Each rule describes exactly one problem and where it stops, so one problem gives one finding, not a pile of overlapping ones. Before the LLM looks, cheap deterministic checks mark likely spots (for example, a swallowed error that ends in a magic return value), so the LLM confirms them instead of searching from scratch.

Each finding is then answered — by `arc fix` or by you — as fixed or won't fix, and the new tip is reviewed again. A change lands only after the reviewers say LGTM and the merge machine runs your `merge.yml` with no new failures ([The merge gate](merge-gate.md)).

When you keep a pattern on purpose, add an `[arc:intentional-handle]` comment that says why. The Critic then stops flagging it. Use it for the rare case that is really justified.

---

*Next: [Rot (L5)](rot.md) · [The commands](commands.md).*
