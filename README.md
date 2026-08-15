# A.R.C. — Adversarial Resolution Cycle

A code-review tool. A Critic LLM reads your code and files findings.
A Fixer LLM (or Claude / Codex CLI) edits files. They go back and
forth until they converge or you step in. State lives in
`<repo>/.arc/` (SQLite + SARIF).

Single Rust binary. macOS (Apple Silicon) + Linux x86_64.

> **v1.1.0 — released.** arc is free, runs entirely locally, and reviews +
> fixes its own codebase every release. **New in 1.1:** `arc fix` now
> generates + gates tests for the code it changes, and `arc tap` records
> and reads back your test signal (slow / flaky / coverage-as-mutant-survival).
> Hit a rough edge? Please [open an issue](#questions--bugs).

**Free.** Use it for whatever you want. Source is closed; binaries are
free downloads. See [LICENSE](LICENSE).

---

## Why not just ask an agent to review?

### 1. The perception vs. the reality

![Two panels. Left, "The perception: grand codebase projection" — people imagine the agent standing before a giant holographic projection of the whole codebase, saying "Amazing! It can see everything and make perfect high-level decisions!" Right, "The reality: localized telescope patching" — the agent actually squints through a telescope at one small block of code, drowning in tangled wires, with no visible context: "I can only see one small block at a time! This blind, line-by-line review is a nightmare."](perception-vs-reality.png)

People picture an agent reviewing your code like a *grand projection* —
it sees **everything** and makes perfect high-level calls. The reality
is a **telescope**: attention is finite, so the agent squints at one
small block at a time, with almost no context around it. It never holds
the whole codebase at once.

### 2. So the review is buckshot

![Two panels. Left, "Agent's review (unsystematic)": a robot sprays a codebase wall with a machine gun, leaving scattered holes labelled MISSING BUG, SECURITY HOLE, LOGIC ERROR MISSED, MAJOR OMISSION. Right, "Our systematic review (thorough)": a code-review engine and robotic rollers lay complete, uniform coverage over the wall — results: all errors caught, final verification OK.](agent-vs-arc.png)

Because it only ever sees a narrow slice, an agent's review isn't
**systematic**: no fixed rule set, no whole-repo pass, no memory of what
it checked last time. It's buckshot — a few shots land, most miss, and
the bugs live in the gaps. Re-run it and you get different holes.

arc is the other thing by construction. **Deterministic recall hooks**
sweep the *whole* codebase and gate the LLM judge on their signals;
**rubrics** pin the rules; the **finding-entity model** remembers every
finding across runs, so nothing silently drops. The model is smart —
the system is what makes it thorough, with no big omissions.

### 3. And left unmeasured, the codebase rots

![One panel, "The problem we are solving: spaghetti agent programming" — a frazzled AI robot tangled in a mess of spaghetti wiring, slapping a band-aid over code in the wrong place, surrounded by warnings: 5 broken connections (dangling threads, dead-end paths) and 6 identical redundant logic implementations. Speech bubble: "It's not simplification... it's overwriting in the wrong places! And now there are 5 threads and 6 identical implementations!"](spaghetti-rot.png)

The same blindness compounds. Patch after patch, the agent overwrites
in the wrong places, leaves dead-ends, and re-implements the same logic
six times — because it can't see that it already exists. That's **rot**,
and it's why agent-driven velocity flattens and then goes **negative**:
eventually there are so many broken paths and duplicates that the agent
itself can't find its way. arc **detects and measures** that rot
(`arc rot` — god-modules, cross-file duplication, broken
layering, weak types) and hands you the **diagnosis**, finding by
finding, so you can treat it before it compounds.

### The philosophy, in one line

Review is a **coverage** problem, not an intelligence problem. arc goes
for coverage, aims the rules squarely at the mistakes agents actually
make (there's even a rubric for LLM-generated code smells), measures how
much your codebase has rotted, and turns every problem into something
**visible, manageable, and quantifiable** — a tracked finding with a
status, a history, and a fingerprint, not a line in a chat log that
scrolls away. You see the whole board, act on each finding, and measure
whether you're converging. (More in
[§ What arc actually does](#what-arc-actually-does).)

---

## Install

### macOS (Apple Silicon)

```bash
curl -L https://github.com/leocaolab/getarc/releases/latest/download/arc-darwin-arm64.tar.gz | tar xz
sudo mv arc /usr/local/bin/
arc --version       # → arc 1.1.0
```

### Linux x86_64

```bash
curl -L https://github.com/leocaolab/getarc/releases/latest/download/arc-linux-x64.tar.gz | tar xz
sudo mv arc /usr/local/bin/
arc --version       # → arc 1.1.0
```

### Intel Mac / other targets

The arc engine source isn't public, so there's no from-source build. On
an **Intel Mac**, run the Apple Silicon binary above under Rosetta 2. If
you need a native Intel-Mac (or other-target) binary, open an issue.

---

## Quick start

In a git repo you want to review:

```bash
arc init                              # interactive: pick Critic + Fixer providers
export GEMINI_API_KEY=...              # or whatever arc init told you to set
arc review                            # Critic reviews, files findings, does NOT edit code
arc report                            # current findings
arc fix                               # Fixer fixes open findings (FIX-ONLY — does not merge)
arc verify                            # independent Verifier re-checks the fixes
arc close                             # land verified fixes onto HEAD (the single merger)
arc auto                              # or all of the above in ONE pass: review → fix → verify → close → commit
```

Config is two files: `arc init` writes `<repo>/.arc/config.toml`
(role → provider mapping, safe to commit — no secrets); your providers +
API keys live in `~/.tars/config.toml`, which is never committed. See the
[user guide](GUIDE.md#6-configuration).

Full operations manual + every flag: `arc <cmd> --help`.

---

## What you also get in the tarball

Each release tarball ships:

- `arc` — the CLI binary
- `arc-vscode.vsix` — the [VS Code extension](#vs-code-extension)
- `LICENSE` — terms

---

## VS Code extension

**This is the best way to use arc.** The extension (v0.2.27) turns the
findings board into a live panel inside your editor — read the debate,
jump to code, apply verdicts without leaving VS Code.

![The arc VS Code extension in action. Left: the findings tree grouped crate / file → finding, each with a status (AGREED / VERIFIED / NEW) and the rule it's grounded in (`l4_contracts::…`); ✨ marks findings first seen in the latest review. Middle: the reviewed source with inline decorations. Right: the per-issue panel — the snippet, a Locations table (found / agreed, each row linking its commit and a real diff), and the full History: the Critic files a `boolean-trap-parameter` finding, it's acknowledged, and in a later round the Critic itself concludes "this function has one parameter — no boolean trap exists — not a finding."](vscode-review.png)

### Install the .vsix

The `arc-vscode.vsix` file ships **inside every release tarball** (next
to the `arc` binary), so if you unpacked the tarball above you already
have it:

```bash
code --install-extension arc-vscode.vsix
```

Prefer to grab just the extension? Download it standalone from the
release:

```bash
curl -LO https://github.com/leocaolab/getarc/releases/latest/download/arc-vscode.vsix
code --install-extension arc-vscode.vsix
```

(Or in VS Code: Command Palette → **Extensions: Install from VSIX…** →
pick `arc-vscode.vsix`.)

### What it gives you

- **Findings tree** rooted on `crate / file → finding`, deduped by
  fingerprint. `✨` marks findings first-seen in the latest review.
- **Per-issue webview** with the full Critic↔Fixer debate, clickable
  Locations (file:line jumps to source, the commit cell opens a real diff
  of what that round changed).
- **Inline squiggles**, **CodeLens**, and **Cmd+. lightbulb** for the
  verdict actions (verify / mark-fixed / won't-fix / agreed / reopen /
  escalate / mark-duplicate).
- **Status-bar `⚡ Arc Scan`** + per-file debounced scan-on-save.
- **Auto-refresh** — the panel watches `.arc/` and updates itself as arc
  moves findings across the board, so you always see the current state.

The extension ships as a free `.vsix` in every release — see § above.

---

## Integrations

- **VS Code extension** — a free `.vsix`, bundled in every release
  tarball (and downloadable on its own). See
  [§ VS Code extension](#vs-code-extension).
- **Claude Code skill (recommended way to use A.R.C.)** — let Claude drive it.

  One-command install (plugin):
  ```bash
  claude plugin marketplace add leocaolab/getarc
  /plugin install arc@getarc
  ```
  Or copy it manually:
  ```bash
  mkdir -p ~/.claude/skills/arc-review
  curl -L https://raw.githubusercontent.com/leocaolab/getarc/main/skills/arc-review/SKILL.md \
    -o ~/.claude/skills/arc-review/SKILL.md
  ```
  Then just tell Claude **"review and fix this repo with arc"**. The skill
  **installs the binary if missing, configures your providers for you, and runs
  `arc auto`** (or a step-by-step review) — the whole download → configure →
  review → fix flow, hands-off. See [`skills/arc-review/SKILL.md`](skills/arc-review/SKILL.md).

The CLI itself runs on [tars](https://github.com/leocaolab/tars) for
provider access (Anthropic / OpenAI / Gemini / Claude CLI / Codex CLI /
local OpenAI-compatible endpoints).

---

## What arc actually does

**Neural-symbolic.** Pure-LLM code review is slow and hallucinates;
pure-symbolic (linters) misses semantics. arc runs deterministic
recall hooks across the codebase — god-modules, copy-paste duplication,
swallowed exceptions, stringly-typed state, dependency-direction
violations, inheritance fanout, driver-seam misuse, and ~half a dozen
others (with more landing) — and gates the LLM judge on those
signals. Each finding then goes through a Critic↔Fixer debate that
converges to fixed / verified / won't-fix / escalated.

**One row per real bug.** Findings are identified by
`fingerprint(file, snippet, rule_id)` and carry an append-only event
timeline (`found → fixed → merged → verified → closed`). Re-reviewing
the same code doesn't create duplicates; a regression reopens the same
finding.

**Fix actually fixes.** The Fixer runs Claude Code CLI (or Codex CLI)
in an isolated git worktree and edits real files; the worktree must
compile. `arc fix` is **FIX-ONLY — it never merges**. An independent
Verifier re-judges the fix, and only `arc close` lands verified fixes
onto your tree (verify-gated). `arc auto` chains this in one pass:
review → fix → verify → close. Conflicts are saved as a `.patch` and
never silently apply.

**You stay in control.** Everything runs locally. Findings + the
debate + the SQLite database live in `<repo>/.arc/` — no daemon, no
port, no server. You configure your own LLM provider (Anthropic /
OpenAI / Gemini / Claude CLI / Codex CLI / local OpenAI-compat —
anything [tars](https://github.com/leocaolab/tars) supports).

---

## License

Free for any use (personal, commercial, internal). You may not:
redistribute the binaries (link to this repo instead), reverse-engineer,
or decompile. See [LICENSE](LICENSE) for the full text.

The arc engine source is not public.

---

## Questions / bugs

Open an issue on this repo. Include `arc --version` + your OS.
