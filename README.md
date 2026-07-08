# A.R.C. — Adversarial Resolution Cycle

A code-review tool. A Critic LLM reads your code and files findings.
A Fixer LLM (or Claude / Codex CLI) edits files. They go back and
forth until they converge or you step in. State lives in
`<repo>/.arc/` (SQLite + SARIF).

Single Rust binary. macOS (Apple Silicon) + Linux x86_64.

> **Preview / beta.** arc 0.8.0 is an early public preview. It's free,
> it works today, and it already reviews and fixes its own codebase —
> but expect rough edges. Please kick the tyres and
> [open issues](#questions--bugs); tester feedback is what shapes 1.0.

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
(`arc rot` — god-modules, cross-file duplication, dead code, broken
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
arc --version       # → arc 0.8.0
```

### Linux x86_64

```bash
curl -L https://github.com/leocaolab/getarc/releases/latest/download/arc-linux-x64.tar.gz | tar xz
sudo mv arc /usr/local/bin/
arc --version
```

### Intel Mac / other targets

Build from source via Rust (CLI is pure Rust, no other runtime needed):

```bash
# arc engine source isn't public — see § "Why no source link" below.
# For Intel Mac users specifically: use the Apple Silicon binary
# under Rosetta 2 if you have it installed.
```

If you need an Intel Mac native binary, open an issue.

---

## Quick start

In a git repo you want to review:

```bash
arc init                              # interactive: pick Critic + Fixer providers
export GEMINI_API_KEY=...              # or whatever arc init told you to set
arc review                            # Critic reviews, files findings, does NOT edit code
arc report                            # current findings
arc fix                               # Fixer fixes open findings (merges back when the build passes)
arc auto                              # full loop: review → fix → verify → merge → commit
```

Config is two files: `arc init` writes `<repo>/.arc/config.toml`
(role → provider mapping, safe to commit — no secrets); your providers +
API keys live in `~/.tars/config.toml`, which is never committed. See the
[user guide](GUIDE.md#4-configuration).

Full operations manual + every flag: `arc <cmd> --help`.

---

## What you also get in the tarball

Each release tarball ships:

- `arc` — the CLI binary
- `arc-vscode.vsix` — the [VS Code extension](#vs-code-extension)
- `LICENSE` — terms

---

## VS Code extension

**This is the best way to use arc.** The extension (v0.2.21) turns the
findings board into a live panel inside your editor — read the debate,
jump to code, apply verdicts without leaving VS Code.

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
- **Claude Code skill** — MIT, right here in this repo:
  [`skill/`](skill/). Drop `skill/SKILL.md` into `~/.claude/skills/arc-review/`
  and Claude drives `arc` for you — it even auto-installs the binary on
  first use.

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
in an isolated git worktree, edits real files, and the patch merges
back to your tree only after the worktree compiled. Conflicts are
saved as a `.patch` and never silently apply. Verification is the
Critic re-judging the fix — under `arc auto` a fix is never merged
until it verifies.

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
