# A.R.C. — User guide

The deeper manual. For install + the 30-second pitch, see the
[README](README.md). Every command's exhaustive flags live in
`arc <cmd> --help`; this guide is the workflow.

> **Preview / beta (0.8.0).** arc is an early public preview — free and
> usable today, rough edges expected. Please
> [open issues](#questions--bugs) as you hit them.

---

## The loop

arc has one shape: **review → read → fix → verify → close**. Everything
below is a station on that line.

```
arc review          Critic reads your code, files findings. Touches NOTHING.
   ↓
arc report          See the findings (or open the VS Code panel).
   ↓
arc fix / arc auto  Fixer edits files in an isolated worktree, merges the fix in.
   ↓
arc verify          The Critic re-judges each fix → verified / reopen / escalate.
   ↓
arc close           A finding that's both merged AND verified is closed.
```

A finding walks a single lifecycle:

```
found → fixed → merged → verified → closed
```

`closed` is the only terminal — the *route* it took (fixed & verified,
an agreed won't-fix, or a duplicate) is preserved in the timeline. A
regression reopens the **same** finding, it never spawns a duplicate.

State lives in `<repo>/.arc/` (SQLite + SARIF). No daemon, no server.
A finding is one row, identified by its database id — the handle you
pass to `arc fix 42`. Re-reviewing the same code never duplicates it.

---

## 1. Setup

```bash
arc init                 # interactive: pick a Critic provider + a Fixer provider
export GEMINI_API_KEY=…   # or whatever arc init told you to set
```

Config lives in **two files** (full detail in [§4](#4-configuration)):

- `<repo>/.arc/config.toml` — just the role → provider-name mapping.
  `arc init` writes it; safe to commit (no secrets).
- `~/.tars/config.toml` — your provider definitions and where the API
  keys come from. **Never commit this.**

`arc init` is interactive. In CI / a non-TTY it instead writes
`.arc/config.toml.example` + `.arc/.gitignore` and exits non-zero with
copy-and-edit instructions.

The two roles that matter:

- **Critic** — finds bugs, and re-judges fixes at verify time. A fast,
  cheap model is ideal (e.g. Gemini Flash).
- **Fixer** — edits files. This must be a tool-capable coding CLI
  (**Claude Code CLI** or **Codex CLI**) — it reads, edits, and runs
  commands in the worktree. A plain chat API can't edit files.

VS Code extension (optional but strongly recommended). The
`arc-vscode.vsix` ships inside every release tarball; install it with:

```bash
code --install-extension arc-vscode.vsix
```

(Or in VS Code: Command Palette → **Extensions: Install from VSIX…**.)
See [§2](#in-the-vs-code-panel) for what it shows.

---

## 2. Reading a finding

### In the terminal

```bash
arc review                 # review the working tree (per-file, in parallel)
arc review --commit <sha>  # review just that commit's diff instead
arc report                 # the current board — every open finding, grouped by file
arc report --new           # only findings first-seen in the latest review
arc report --status fixed  # filter to one state
```

### In the VS Code panel

Click a finding in the tree. The panel is built to be read top-to-bottom:

- **Title** — the problem in plain language (no rule IDs, no jargon).
- **status · severity · confidence** — `confidence` is the Critic's
  self-reported certainty, shown as a percentage.
- **Snippet** — the exact code the finding is about.
- **Locations** — a table of `event · commit · file:line · diff`. The
  `file:line` jumps to source; the `diff` column opens the actual change
  for the rounds that changed code (a *review* round has no diff).
- **History** — the conversation as a timeline. Each turn shows **who**
  (Critic / Fixer), **when**, the rule it's grounded in
  (`Based on <rule_id>` + a one-line explanation of that rule), the
  message, and links. A finding's life reads top to bottom:
  **Critic** (found it) → **Fixer** (fixed it) → merged into your tree →
  **Critic** (verified it) → closed.

The panel **auto-refreshes**: it watches `.arc/` and redraws as arc
moves findings across the board, so you never re-open it by hand.

### Without the extension (CI, other editors)

Every review writes a SARIF file under `.arc/reviews/`. Point any
SARIF viewer (or your CI's code-scanning tab) at it.

---

## 3. Fixing

```bash
arc fix                 # fix every open finding
arc fix <path>          # fix the findings in one file or folder
arc fix 42              # fix one finding by its id
arc fix --no-commit     # fix, but leave each on its arc/fix-<id> branch (stop at `fixed`)
arc verify              # re-check all fixed findings
arc verify 42           # re-check one
arc close               # close findings that are BOTH merged AND verified
```

Each fix runs in an **isolated git worktree**. The Fixer edits real
files there; arc reads the resulting diff. A bare `arc fix` is fully
automatic: on a clean build it **merges the fix back onto your tree**
(the finding goes `fixed → merged`). A fix that breaks the build is
never landed; conflicts are saved as a `.patch` under `.arc/fixes/` and
never silently applied. Pass `--no-commit` to stop at `fixed` and keep
the fix on its `arc/fix-<id>` branch for manual review.

`arc verify` then has the Critic re-judge a fixed finding →
`verified` / `reopen` / `escalate`. `arc close` retires a finding that
is **both merged and verified** (it also runs automatically at the tail
of `arc verify` and `arc auto`).

### Hands-off: `arc auto`

```bash
arc auto                       # review → fix → verify → merge → commit
arc auto --file <path>         # scope the whole loop to one file
arc auto --max-turns 5         # cap the convergence rounds (default 3)
arc auto --no-commit           # apply fixes but stop before committing
```

`arc auto` runs the full convergence loop hands-off. Crucially, **verify
gates the merge**: a fix is never merged unverified — it must pass the
Critic's re-judgement first. When a finding is both merged and verified,
`auto` closes it. Each auto-fix commit carries a `Review-Id:` git trailer.

### Manual control

```bash
arc resolve 42 --as wontfix    # set a state directly: new|fixed|verified|
                               #   wontfix|agreed|escalated|duplicate
arc resolve 42 --as dup --of 7 # mark 42 a duplicate of finding 7
arc ack 42                     # acknowledge (alias for --as agreed)
arc revert                     # undo every commit from one fix/auto run
                               #   (greps the Review-Id trailer, git-reverts them)
```

The states a human moves a finding through: **verify** a fix, **won't
fix** it, **agree** with a won't-fix, **reopen** it, **escalate** to a
human decision, or mark a **duplicate**. (Marking something *fixed* is
the Fixer's job, not yours — there's no such button.)

---

## 4. Configuration

arc's model layer **is** [tars](https://github.com/leocaolab/tars), a
provider-abstraction library. Config splits across **two files** — one
private, one committable:

| File | Holds | Commit? |
|---|---|---|
| `~/.tars/config.toml` (or `$ARC_TARS_CONFIG`) | provider definitions + where API keys come from (`[providers.*]`) | **never** |
| `<repo>/.arc/config.toml` | role → provider-name mapping (`[roles]`) + optional tuning | yes — no secrets |

`arc init` sets up both interactively. In CI / a non-TTY it writes
`.arc/config.toml.example` + `.arc/.gitignore` and exits non-zero with
copy-and-edit instructions instead.

### Providers — `~/.tars/config.toml`

Each `[providers.<name>]` block says how to reach one model. The API key
never lives in the file — it's referenced by env-var name:

```toml
[providers.gemini_flash]
type = "gemini"
default_model = "gemini-2.5-flash"
auth = { kind = "secret", secret = { source = "env", var = "GEMINI_API_KEY" } }

[providers.claude_cli]
type = "claude_cli"
default_model = "claude-sonnet-4-5"
tools = "default"             # let the agent Read/Edit/Bash in the worktree
timeout_secs = 900            # raise for big workspaces — the fixer's
                              # build-gate compile is slow when cold
```

Supported `type`s: `gemini`, `anthropic`, `openai`, `deepseek`,
`claude_cli`, `claude_sdk`, `gemini_cli`, `codex_cli`, or `openai_compat`
(a local endpoint — LM Studio / vLLM — with a `base_url`). `deepseek` is
built into tars, so you can reference it by name without a block.

### Roles — `<repo>/.arc/config.toml`

Map each of arc's jobs to a provider you defined above:

```toml
[roles]
default   = "claude_cli"     # fallback for any unset role
critic    = "gemini_flash"   # FIND bugs (and re-judge fixes at verify time)
fixer     = "claude_cli"     # FIX bugs — must be a tool-capable CLI
# critic_l4 = "gemini_flash" # optional: override the per-file (L4) critic
# critic_l5 = "gemini_flash" # optional: override the structural-rot (L5) critic
# audit     = "gemini_flash" # optional: a third-opinion role
```

There is **no `verifier` role** — verification is the **Critic
re-judging** a fix, so it runs under the `critic` role. `.arc/config.toml`
may also carry optional tuning sections (`[review]`, `[gate]`,
`[merge]`); see `arc init`'s output.

---

## 4a. Rubrics

A **rubric** is a YAML rule set the Critic reviews against. The defaults
ship embedded in the binary; each rule carries a one-line `description`
that's exactly the "Based on …" explanation the VS Code panel shows on a
finding.

### The set arc ships

- **L4 — per-file contracts** (`l4_contracts.yaml`): typed-error
  discipline — `untyped-error-origin`, `missing-error-classification`,
  `swallowed-exception`.
- **L5 — structure / architecture** (`l5_architecture.yaml`): god-modules,
  cross-file duplication, dead code, layering / dependency-direction
  violations, weak / stringly-typed state, inheritance fanout,
  driver-seam misuse.
- **Per-language best practices** — one file per language, applied only to
  files in that language. `rust_best_practices.yaml` (no-unwrap-in-library,
  stringly-typed-domain-value, parse-dont-validate, clone-in-hot-path),
  `typescript_best_practices.yaml` (type-assertion-bypasses-checker),
  plus `python`, `go`, `java`. arc's language graph covers 8 languages
  (rust/python/ts/js/go/java/c/cpp); the best-practices rubrics ship for
  the five above today, with more landing.
- **security_common.yaml** (validate-external-input, no-hardcoded-secrets)
  and **fp_lens.yaml** — a functional-programming lens
  (partial-function-as-total).

### What we dogfood

arc reviews its **own** Rust codebase, so the rubrics that fire on it are
L4 contracts + L5 architecture + rust_best_practices + security_common +
fp_lens. Real findings that surfaced this way, and got fixed:

- an untyped error stringified at a boundary (`untyped-error-origin`);
- a hardcoded XOR key (`no-hardcoded-secrets`);
- a diff helper using `--ignore-all-space`, which would hide
  whitespace-only changes from the verifier.

### Add your own rules

Drop a YAML file at `<your-repo>/rubrics/<name>.yaml`. arc reads it at
runtime alongside the embedded defaults — no rebuild. A rule's canonical
id is `<file-stem>::<rule.name>` (so `rubrics/my_rules.yaml` with a rule
`no-foo` → `my_rules::no-foo`, the id you'll see in reports, the panel,
and `--enable`/`--disable`). The format:

```yaml
name: My Rules
description: >
  One-line summary of what this rubric set covers.
language: [rust, python]     # applicability — never fires on other languages
rules:
  - name: no-foo
    status: stable            # stable | experimental | deprecated (fires-by-default gate)
    description: |
      ANTI-PATTERN: <what's wrong and the concrete hazard it causes>.
      It is instantiated by <forms/examples>, NOT any single token.
      FLAG <the concrete call site>. EXEMPT <known false-positive contexts>.
```

Rules are checked by the Critic during `arc review` (L4 per-file); the
top-level `language: [...]` filter decides which files a rubric applies
to. `status: experimental` rules stay off until you pass `--experimental`
(or `--enable <id>`).

---

## 5. CI integration

```bash
arc install-hook        # post-commit hook: review each commit automatically
arc review --commit HEAD
```

- **SARIF** — `.arc/reviews/*.sarif` feeds GitHub/GitLab code-scanning
  or any SARIF tool. arc is **advisory**: finding rot does *not* by
  itself fail your build — wire the exit code into your gate only if you
  want it to.
- **Exit codes** are an API for the agent/CI driving arc: a crashed
  review unit exits non-zero; a clean review exits zero.

---

## 6. Command reference

| Command | Does |
|---|---|
| `arc init` | write the role→provider mapping → `.arc/config.toml` |
| `arc review` | Critic reviews per-file (L4); files findings; never edits |
| `arc rot` | whole-repo structural-rot review (L5); AST-detect then LLM-confirm (`--no-judge` = detect only) |
| `arc report` | the current board (`--new`, `--status <s>`) |
| `arc fix [path\|id]` | Fixer repairs open findings; auto-merges on a clean build |
| `arc auto` | autonomous review→fix→verify→merge→commit |
| `arc verify [id]` | Critic re-checks fixes → verified / reopen / escalate |
| `arc close [id]` | close findings that are both merged and verified |
| `arc resolve <id> --as <state>` | set a finding's state manually |
| `arc ack <id>` | acknowledge (→ agreed) |
| `arc revert` | undo one fix/auto run's commits |
| `arc history` | past runs, newest first |
| `arc progress [--watch]` | progress of a running review/fix |
| `arc reconcile` | apply stranded `.arc/fixes/*.patch` after a crash |
| `arc reset --yes` | wipe arc's history for this repo (keeps config) |
| `arc install-hook` / `uninstall-hook` | the post-commit hook |

Exhaustive flags: `arc <cmd> --help`.

---

## 7. Troubleshooting

- **A run crashed / Ctrl-C left a mess.** `arc reconcile` applies any
  stranded fix patches and prunes orphaned worktrees. A dirty working
  tree before `arc auto` is reconciled automatically at pre-flight.
- **Findings point at moved/deleted code after a big refactor.**
  `arc reset --yes` clears the board (keeps `.arc/config.toml`); re-review.
- **The fixer is slow or times out.** The fixer's build-gate compiles
  the worktree; on a large workspace a cold compile is minutes. Raise
  `timeout_secs` on the fixer's provider, and note arc reuses your warm
  build target so only the first compile is cold.
- **Stuck progress.** `arc progress --watch` shows where a running
  review/fix actually is.

---

## Questions / bugs

Open an issue on [getarc](https://github.com/leocaolab/getarc). Include
`arc --version` + your OS.
