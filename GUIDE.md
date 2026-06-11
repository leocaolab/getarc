# A.R.C. — User guide

The deeper manual. For install + the 30-second pitch, see the
[README](README.md). Every command's exhaustive flags live in
`arc <cmd> --help`; this guide is the workflow.

---

## The loop

arc has one shape: **review → read → fix → verify → land**. Everything
below is a station on that line.

```
arc review          Critic reads your code, files findings. Touches NOTHING.
   ↓
arc report          See the findings (or open the VS Code panel).
   ↓
arc fix / arc auto  Fixer edits files in an isolated worktree.
   ↓
arc verify          Verifier re-checks each fix → verified / reopen / escalate.
   ↓
(merge)             A fix lands in your tree only after it compiles.
```

State lives in `<repo>/.arc/` (SQLite + SARIF). No daemon, no server.
A finding is one row, identified by its database id — the handle you
pass to `arc fix 42`. Re-reviewing the same code never duplicates it;
a regression reopens the same finding.

---

## 1. Setup

```bash
arc init                 # interactive: pick a Critic provider + a Fixer provider
export GEMINI_API_KEY=…   # or whatever arc init told you to set
```

`arc init` writes `.arc/config.toml` (see [§4](#4-configuration)). The
two roles that matter:

- **Critic** — finds bugs. A fast, cheap model is ideal (e.g. Gemini Flash).
- **Fixer** — edits files. This must be a tool-capable coding CLI
  (**Claude Code CLI** or **Codex CLI**) — it reads, edits, and runs
  commands in the worktree. A plain chat API can't edit files.

VS Code extension (optional but recommended):

```bash
code --install-extension arc-vscode.vsix
```

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
  **Critic** (found it) → **Fixer** (fixed it) → **Critic** (verified)
  → **Fixer** (merged to main).

### Without the extension (CI, other editors)

Every review writes a SARIF file under `.arc/reviews/`. Point any
SARIF viewer (or your CI's code-scanning tab) at it.

---

## 3. Fixing

```bash
arc fix                 # fix every open finding
arc fix <path>          # fix the findings in one file or folder
arc fix 42              # fix one finding by its id
arc verify              # re-check all fixed findings
arc verify 42           # re-check one
```

Each fix runs in an **isolated git worktree**. The Fixer edits real
files there; arc reads the resulting diff. The patch merges back into
your tree **only after it compiles** (a `cargo check` / build gate) — a
fix that breaks the build is never landed. Conflicts are saved as a
`.patch` under `.arc/fixes/` and never silently applied.

### Hands-off: `arc auto`

```bash
arc auto                       # review → fix → re-review → … → commit
arc auto --file <path>         # scope the whole loop to one file
arc auto --max-turns 5         # cap the convergence rounds
arc auto --no-commit           # apply fixes but stop before committing
```

`arc auto` runs the full convergence loop and commits when it
converges. Each auto-fix commit carries a `Review-Id:` git trailer.

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

`.arc/config.toml` (written by `arc init`, committed or gitignored as
you like). Two halves: **providers** (how to reach a model) and
**roles** (which provider does which job).

```toml
[providers.gemini_flash]
type = "gemini"
default_model = "gemini-2.5-flash"

[providers.claude_cli]
type = "claude_cli"
timeout_secs = 900            # raise it for big files — the fixer's
                              # build-gate compile can be slow on a
                              # large workspace (default is 300s)

[roles]
critic  = "gemini_flash"      # FIND bugs — fast + cheap
fixer   = "claude_cli"        # FIX bugs — must be a tool-capable CLI
```

Provider `type`s: `gemini`, `anthropic`, `openai`, `claude_cli`,
`claude_sdk`, `codex_cli`, or any local OpenAI-compatible endpoint.
Per-provider keys (`timeout_secs`, `api_key_env`, `thinking`) are read
by arc and stripped before the model layer sees them.

**Rubrics** — the rule sets the Critic reviews against — live under
`rubrics/*.yaml`. Each rule carries a one-line `description` (that's the
"Based on…" explanation the panel shows). The defaults ship inside the
binary; drop your own YAML in `rubrics/` to extend them.

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
| `arc init` | configure providers + roles → `.arc/config.toml` |
| `arc review` | Critic reviews; files findings; never edits |
| `arc scan` | deterministic structural-rot scan (no LLM) |
| `arc report` | the current board (`--new`, `--status <s>`) |
| `arc fix [path\|id]` | Fixer repairs open findings |
| `arc auto` | autonomous review→fix→re-review→commit |
| `arc verify [id]` | Verifier re-checks fixes |
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
