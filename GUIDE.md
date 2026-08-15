# A.R.C. — User Guide

A.R.C. (Adversarial Resolution Cycle) is a code-review tool. A **Critic** LLM
reads your code and files findings; a **Fixer** LLM edits files; they debate
per-finding until they converge or you step in. Findings persist as entities in
`<repo>/.arc/` (SQLite + SARIF) with an append-only event timeline.

This is the conceptual + practical manual. For install + the 30-second pitch see
the [README](README.md); every command's exhaustive flags live in
`arc <cmd> --help`.

---

## 0. Install

arc ships as a single binary + an optional VS Code extension — **releases-only,
no source required**. Get both from
**[getarc releases](https://github.com/leocaolab/getarc/releases/latest)**.

**CLI (macOS, Apple Silicon):**

```bash
curl -L https://github.com/leocaolab/getarc/releases/latest/download/arc-darwin-arm64.tar.gz | tar xz
mv arc /usr/local/bin/        # anywhere on your $PATH
arc --version                 # 1.1.0
```

**CLI (Linux x86_64):**

```bash
curl -L https://github.com/leocaolab/getarc/releases/latest/download/arc-linux-x64.tar.gz | tar xz
mv arc /usr/local/bin/        # anywhere on your $PATH
arc --version                 # 1.1.0
```

**VS Code extension (optional):** download `arc-vscode.vsix` from the same
release, then `code --install-extension arc-vscode.vsix`.

Then `arc init` to configure providers (§6) and `arc review` / `arc auto` to run.

---

## 1. What arc is (and is not)

arc runs a loop, not a linter pass:

```
Critic finds  →  Fixer fixes (in an isolated git worktree)  →  Verifier re-checks  →  land on HEAD
     └────────────────────── debate per finding until converged ──────────────────────┘
```

- **It reviews OTHER people's code, in 8 languages** (Rust, Python, TS, JS, Go,
  Java, C, C++). The language drivers fire on the *target* repo's language.
- **It is an advisory detector.** Finding rot or bugs is not a build failure by
  itself; `arc` reports, you (or the Fixer) decide.
- **No LLM is bundled.** You point arc at providers you configure in tars.
- **Not a style linter.** Formatting is for `clippy` / `ruff` / `eslint` /
  `gofmt`. arc targets *semantic* hazards and *structural* rot.

---

## 2. arc's FP bias — why it reviews the way it does

arc is written functional-core / imperative-shell, and it reviews your code
through the same lens. This is not dogma; it is the set of properties that make
LLM-written code safe to keep. The Critic's L4 rubric encodes them, so the
biases below are literally what it flags.

- **Functional core, imperative shell.** Pure logic (no IO) lives in a core the
  shell drives. arc's own `arc_core` is IO-free (enforced by
  `deny(clippy::print_stdout)`). Mixing IO into pure logic is a smell.
- **Parse, don't validate.** Turn unstructured input into a typed value at the
  boundary, once; downstream code consumes the type, not re-checked strings.
- **Errors are typed and carry their cause.** Never stringify a typed error at a
  boundary (`.map_err(|e| e.to_string())`) — carry it with `#[from]` so callers
  branch on the variant, not a `.contains()` grep. (`l4_contracts::untyped-error-origin`.)
- **Closed domains are enums, not magic strings.** A fixed set of states is an
  exhaustive enum the compiler checks, never a stringly-typed value.
  (`rust_best_practices::stringly-typed-domain-value`.)
- **No sentinels leaking to consumers.** `null` / `-1` / `""` standing in for a
  real failure hides the truth. A failure is a typed `Err` / `Option`, surfaced,
  not a buried magic value. (`l4_contracts::missing-error-classification`,
  `llm_generated_code_smells::ambiguous-return-sentinel`.)
- **One source of truth; never backfill from a derived view.** Whoever produces
  a fact writes it in full at the source — don't reconstruct primary data from a
  derived store later.
- **Total functions.** Don't call a partial function (`unwrap` / `head` /
  `fromJust`) as if total; handle the empty/None case.
  (`fp_lens::partial-function-as-total`, `rust_best_practices::no-unwrap-in-library`.)

---

## 3. The system rot LLMs (Claude included) typically produce

LLMs write plausible code fast, and it rots in recognizable ways. arc exists
because these patterns are hard to catch by eye at review time but easy to name.
The rules that catch each live in `rubrics/` (rule id in parentheses):

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
| **Changelog-in-comment** | narrative "changed X to Y" comments instead of describing the code | `llm_generated_code_smells::changelog-narrative-in-comment` |

Two failure modes above the line-level, which are **structural rot** (see §5):
god-modules that accrete unrelated responsibilities, and the same logic
reinvented across files. LLMs produce both readily because each local edit looks
reasonable.

---

## 4. How arc prevents them — two layers

- **L4 — per-file contracts.** The Critic reviews each file against the L4
  rubric (`rubrics/l4_contracts.yaml` + per-language `*_best_practices.yaml` +
  `llm_generated_code_smells.yaml` + `fp_lens.yaml`). Every rule names ONE
  distinct hazard with crisp boundaries so one smell → one finding, not a
  carpet-bomb. Deterministic detectors pre-triage cheap signals (e.g. a swallow
  ending in a sentinel) so the LLM confirms rather than re-derives.
- **L5 — whole-repo structure.** `arc rot` looks across files for emergent rot
  no single file shows (see §5).

Findings then run the debate loop (fix ↔ verify) until converged or escalated,
and a fix only lands after an **independent Verifier** accepts it (never the
Fixer self-grading) and the **gate** (your build/test command) stays green.

An `[arc:intentional-handle]` comment documents a deliberate exception so the
Critic doesn't re-flag it — the escape hatch for the rare justified case.

---

## 5. Measuring how rotten a system is — `arc rot`

arc **detects and quantifies** structural rot; it does **not** auto-refactor it
(refactoring is an experimental capability in `arc_experimental`, off the main
path). Use `arc rot` to get a tracked rot inventory; you decide what to fix.

```bash
arc rot                 # whole-repo structural review (L5)
arc rot --no-judge      # deterministic detect only — no LLM, just the signals
```

L5 detects emergent rot a single file can't reveal, in four layers:

- **God-modules** — a file that accreted too many responsibilities (a blended
  complexity × fan-out score in the top ~5%, past a ~300-line floor).
- **Cross-file duplication (reinvention)** — the same idiom repeated across
  files after α-normalization (variables/literals normalized, callee/type names
  kept), ≥3 copies.
- **Duplicated domain types** — one concept modeled by same-named `struct`/`enum`
  types in ≥2 crates.
- **Structural signals** — layering pointing down (a lower tier named in a
  higher-tier consumer's legacy vocab), driver/wiring seams hiding real logic,
  inheritance fan-out (god-traits), and hardcoded policy constants.

> Dead-code detection currently lives in `arc_experimental` (off the rot path
> until it clears a precision bar) — `arc rot` does not report it yet.

Rot findings land as **`Suggestion`** status: **opt-in**. `arc auto` and
`arc fix` (whole-board) will NOT auto-sweep them — refactors are explicit. To
act on one: `arc fix <id>` (or refactor by hand, optionally with Claude). Track
the trend with `arc report`:

```bash
arc report --status open       # everything still open, L4 + L5
arc rot --no-judge             # cheap, deterministic rot signal — good for a CI trend metric
```

The honest reading: `arc rot` gives you a **rot score to watch over time**, not
a refactor button.

---

## 6. Configuration

Two layers. Models and secrets live in tars; `.arc` only maps roles to tars
provider ids — **no model pins, no secrets in the repo**.

| File | Holds | Commit? |
|---|---|---|
| `<repo>/.arc/config.toml` | role → tars provider id, `[gate]` command | yes |
| `~/.tars/config.toml` (or `$ARC_TARS_CONFIG`) | provider defs: `type`, `default_model`, `auth` | no |

`arc init` reads your tars registry and offers those providers as the menu, then
writes a config that references them by id. A minimal `.arc/config.toml`:

```toml
[roles]
critic = "gemini_flash"     # a provider id from ~/.tars/config.toml (model lives there)
fixer  = "claude_cli"       # a different family — independent review

[gate]
command       = "npx tsc --noEmit"       # fast per-fix check (language-specific)
final_command = "npx tsc --noEmit"       # authoritative gate run at land time
```

The **gate is language-specific** and mandatory for non-Rust repos (arc only
auto-detects `cargo`); `arc init` suggests one for your repo's language. Provider
credentials come from the env vars the tars providers name (e.g.
`GEMINI_API_KEY`); `claude_cli` uses your `claude login` session.

---

## 7. The commands

| Command | What it does |
|---|---|
| `arc init` | write `.arc/config.toml` from your tars registry (interactive; non-TTY writes an example) |
| `arc review` | per-file L4 review; files findings, never edits |
| `arc rot` | whole-repo L5 structural-rot review |
| `arc report` | show the current board |
| `arc fix <id\|path>` | Fixer resolves findings — **FIX-ONLY, does not merge** |
| `arc verify` | independent Verifier re-checks fixed findings |
| `arc close` | land verified fixes onto HEAD — **the single merger** |
| `arc auto` | review → fix → verify → close → commit, hands-off (**ONE pass**) |
| `arc resolve <id> --as <state>` | manual override to any state |
| `arc reconcile` | crash-recovery: land orphaned fix branches, build-gated |
| `arc install-hook [--auto]` | post-commit background review (`--auto` also fixes) |
| `arc affected` | deterministic test-impact selection for a diff (guppy rdeps — which existing tests it can touch) |
| `arc tap <sub>` | **Test Analytics & Profile** — `init` / `test` (ingest JUnit) / `signal` (slow + flaky) / `coverage` (mutant survival) / `plan` (LLM test-impact) / `gaps` |

`arc auto` is **one pass**: review once, drive each finding to `close` in its own
fix↔verify walk, escalate the ones it can't close, commit. There is **no
internal re-review loop** — not satisfied? run `arc auto` again. `--max-turns` is
the per-finding fix↔verify budget, not a round count.

**New in 1.1 — `arc fix` tests the code it changes.** After a fix edits code, a
test phase runs automatically (default on): it computes the affected test set
deterministically (guppy reverse-dependency closure — no grep), plans which new
tests to add, writes each as a compilable test, and **gates every candidate**. A
test that compiles + passes **lands** alongside the fix; one that fails is **not**
pushed into your tree — it's filed as a `coverage_gap` ticket (with the real
compiler/runner output) that `arc tap gaps` surfaces. Turn it off with
`[test] generate = false` in `.arc/config.toml`. To make JUnit a side-effect of
your normal test run so `arc tap` can read your signal, run `arc tap init` once.

The manual pipeline is the same thing unbundled:
`arc review` → `arc fix <id|path>` → `arc verify` → `arc close`.

`arc <cmd> --help` is the source of truth for flags. `--json` makes any command
emit one machine-readable envelope (the agent control bus).

---

## 8. Finding lifecycle — the state machine

One row per real bug, keyed by `fingerprint(file, snippet, rule_id)`.
Re-reviewing the same code does not duplicate it; fixing then reintroducing it
reopens the same finding. Every finding has an append-only event timeline.

States (`Status`):

| State | Meaning |
|---|---|
| `new` | open, found by the Critic |
| `fixed` | a fix exists in a worktree/branch, NOT yet on the integration tree |
| `merged` | the fix's commit has LANDED on HEAD (a real git commit) |
| `verified` | independently re-checked and accepted |
| `closed` | terminal: `merged` ∧ `verified` (landed AND confirmed) |
| `wontfix` | valid but intentionally not fixed |
| `agreed` | acknowledged |
| `escalated` | the loop couldn't resolve it — needs a human |
| `duplicate` | same defect as another finding |
| `in_review` | under human review (scan-suppressed, not terminal) |
| `suggestion` | an L5 rot finding — actionable but opt-in (not auto-swept) |

There are three closure routes (each records the terminal `closed`):

- **fix path** — `new → fixed → merged ∧ verified → closed`. `merged` alone is
  "landed, unconfirmed"; `verified` alone is "confirmed, not landed"; only their
  conjunction closes. A Verifier reopen sends it back to `new` and wipes the
  closure facts (a re-fix must re-earn them).
- **acknowledged** — `new → wontfix → agreed → closed` (a wontfix the Verifier
  agreed with).
- **duplicate** — `new → duplicate ∧ verified → closed` (the dup mark alone is
  not enough).

`escalated` is terminal-pending-human; `suggestion` (rot) is only acted on by an
explicit `arc fix <id>`. Use `arc report <id>` for a finding's full timeline.

---

## 9. Custom rubrics — bring your own rules

arc's rubric is a set of YAML files in `rubrics/`; you can add your own without
touching arc's. A rule is plain YAML:

```yaml
name: My Team Rules
description: House rules for this repo.
rules:
  - name: no-raw-sql-in-handlers
    status: stable          # stable | experimental | deprecated
    description: |
      ANTI-PATTERN: a request handler builds SQL from strings inline instead of
      going through the repository layer. The token (a `SELECT`/`format!` in a
      handler) is only an example — flag the hazard: query construction leaking
      into the transport layer. Do NOT flag parameterized calls through the repo.
```

Feed it in three ways:

```bash
arc review --rubric-file ./my-rules.yaml         # repeatable; appended to the L4 set (review + auto)
ARC_EXTRA_RUBRICS=./a.yaml:./b.yaml arc auto     # colon-separated paths, same effect
```

Or drop it in the repo's own `rubrics/` directory: a file whose stem matches a
built-in (`rust_best_practices.yaml`) **overrides** it; a new stem is **added**.
A missing `--rubric-file` / `ARC_EXTRA_RUBRICS` path is a hard error, never a
silent skip.

`.arc/config.toml`'s `[review]` section does NOT add files — it only *selects*
rules (`enable` / `disable` / `experimental`). Rule ids are
`<file-stem>::<rule-name>`, so the rule above is
`my-rules::no-raw-sql-in-handlers`, usable with `--enable` / `--disable`.

Two things that bite:

- **`status` defaults to `experimental`** — an omitted `status` means the rule is
  OFF in production (it only runs under `--experimental`). Ship a real rule with
  `status: stable`.
- **Unknown fields are rejected** (`deny_unknown_fields`) — a typo'd key fails
  the load, it isn't ignored.
- **Language scope**: a rule runs on ALL languages by default. Limit it with a
  file-level `language: [rust, ...]` header or a per-rule `universality: [rust]`.

> The rule `description` IS the prompt — write it the way the built-ins are
> written: name the hazard, give the token only as an example, and draw the
> boundary against neighbours so one site → one finding.

---

## 10. Using arc with Claude — best practices

arc and Claude compose well: Claude drives arc, and arc keeps Claude honest.

- **Let Claude drive a full run.** The `arc-run` skill captures the whole
  pipeline (init → review → fix → verify → close, or `arc auto`) plus the real
  setup traps. Ask Claude to "run arc on this repo" and it follows it.
- **`--json` is the control bus.** Every command emits one envelope; have Claude
  consume `arc report --json` / `arc review --json` and act on the SARIF it
  points at, rather than scraping human text.
- **Route models by strength.** A non-Claude critic (gemini / deepseek) tends to
  *find* more; Claude is the *fixer*. Keep critic and fixer in different families
  so the review is genuinely independent.
- **Hand Claude the escalated tail.** `arc auto` leaves genuinely hard findings
  `escalated`. Those are the ones worth a human+Claude session — give Claude the
  finding + its debate history (`arc report <id>`).
- **arc reviews Claude's own edits.** Run `arc review` (or the post-commit hook
  `arc install-hook`) on Claude-authored changes — it catches exactly the LLM
  rot in §3 before it lands.
- **Re-run for another pass.** `arc auto` is one pass by design; if open findings
  remain and you want more, run it again — the convergence loop is yours.

---

## 11. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `missing credential: env var X is not set` | the provider's key isn't in the environment — export it (or `source .env`). Honest error, not a bug. |
| `[providers.X] missing model` | old-style config requiring a model — with the tars-driven config the model comes from tars; upgrade the config (`arc init --force`) or add the tars provider's `default_model`. |
| every fix rolls back on a red gate | the `[gate] command` doesn't match this repo's language — set a real build/typecheck (see §6). |
| `arc auto` didn't keep iterating | by design — it's one pass. Re-run for another. |
| a dirty tree stalls `arc auto` | its pre-flight reconcile handles a dirty tree; commit or stash unrelated WIP for a focused run. |
| stale behavior after changing arc's source | you're running the installed binary — `just install` first. |
| weak/empty findings | the critic is too weak for the target — try a stronger critic provider or `--experimental`; don't read "clean" off a weak critic. |

---

## See also

- [README](README.md) — install + quickstart
- `arc <cmd> --help` — exhaustive flags for any command
- **Questions / bugs:** open an issue on
  [getarc](https://github.com/leocaolab/getarc/issues) — include `arc --version`
  + your OS.
