# A.R.C. — Adversarial Resolution Cycle

A code-review tool. A Critic LLM reads your code and files findings.
A Fixer LLM (or Claude / Codex CLI) edits files. They go back and
forth until they converge or you step in. State lives in
`<repo>/.arc/` (SQLite + SARIF).

Single Rust binary. macOS (Apple Silicon) + Linux x86_64.

> **Two tracks.** **v1.1.0** is the public release (`latest`): free, runs
> entirely on your machine. **v1.2.0-preview.1** is a prerelease for design
> partners: reviews and landings go through a PR, a review service and a merge
> machine you host yourself. [What differs and how to install each](#install).
>
> **Documentation:** <https://arc-site.hucao1.workers.dev/docs/> (written for
> the 1.2 preview). The rest of this README describes **1.1.0** unless a
> section says otherwise. Hit a rough edge? Please [open an issue](#questions--bugs).

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

| | **1.1.0** — `latest` | **1.2 preview** — `v1.2.0-preview.1` |
|---|---|---|
| For | anyone | design partners |
| How it runs | the CLI alone, on your machine: review → fix → verify → close, locally | the CLI **plus a self-hosted server suite** (review service, merge machine, web UI, chat bridge, deployer, nightly releaser): `arc review` opens the PR, reviewers file findings, the author answers them, LGTM grants a pass, and the merge machine lands the PR when your `.github/workflows/merge.yml` shows no new failure |
| Local `arc auto` / `arc verify` / `arc close` | yes | **paused** — they run nothing and exit non-zero |
| VS Code extension | yes | not shipped in this preview |
| Docs | this README + [the 1.1.0 guide](https://github.com/leocaolab/getarc/blob/9a4ff4d/GUIDE.md) | [the website](https://arc-site.hucao1.workers.dev/docs/) |

### 1.1.0 (latest)

```bash
# macOS (Apple Silicon)
curl -L https://github.com/leocaolab/getarc/releases/latest/download/arc-darwin-arm64.tar.gz | tar xz
sudo mv arc /usr/local/bin/
arc --version       # → arc 1.1.0

# Linux x86_64
curl -L https://github.com/leocaolab/getarc/releases/latest/download/arc-linux-x64.tar.gz | tar xz
sudo mv arc /usr/local/bin/
```

### 1.2 preview (design partners)

`latest` still points at 1.1.0, so install from the tag:

```bash
# macOS (Apple Silicon)
curl -fsSL https://github.com/leocaolab/getarc/releases/download/v1.2.0-preview.1/arc-darwin-arm64.tar.gz | tar -xz && sudo mv arc /usr/local/bin/

# Linux x86_64 (glibc 2.39+, OpenSSL 3)
curl -fsSL https://github.com/leocaolab/getarc/releases/download/v1.2.0-preview.1/arc-linux-x64.tar.gz | tar -xz && sudo mv arc /usr/local/bin/

arc --version       # → 1.2.0-dev (<commit> …)
```

The server suite (`arc-suite-*.tar.gz` on [the same release](https://github.com/leocaolab/getarc/releases/tag/v1.2.0-preview.1))
is self-hosted; during the preview **an arc engineer installs it with you**.
`arc local-review`, `arc fix` and `arc install-hook` need it; `arc rot`,
`arc workflow`, `arc tap` and `arc affected` work on their own. Setup and every
command: [the docs](https://arc-site.hucao1.workers.dev/docs/start/install/).

### Or let your coding agent set it up

Paste this into Claude Code, Codex or another coding agent, in the repository you
want arc on:

```text
Set up A.R.C. (arc) in this repository with the arc-setup skill. If you're in Claude Code, run `claude plugin marketplace add leocaolab/getarc`, then `claude plugin install arc@getarc`. If you're in another agent, run `npx skills add leocaolab/getarc --skill arc-setup` and select your agent. Use one installation method. You can read the skill directly at https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md (raw: https://raw.githubusercontent.com/leocaolab/getarc/main/skills/arc-setup/SKILL.md). Then use the arc-setup skill to install and configure arc here.
```

The skill ([`skills/arc-setup`](skills/arc-setup/SKILL.md)) probes what is already
there and walks the stages in order — the binary, LLM providers in tars, `arc init`
roles, an optional merge gate and coding-agent hooks, a smoke test — asking before
anything global or outward, and stopping with the real error when a stage fails. It
follows the 1.2 route: a design partner gives it the preview tag; on `latest`
(1.1.0) it stops at the binary stage and says which verbs are missing.

### Intel Mac / other targets

The arc engine source isn't public, so there's no from-source build. On
an **Intel Mac**, run the Apple Silicon binary above under Rosetta 2. If
you need a native Intel-Mac (or other-target) binary, open an issue.

---

## Quick start (1.1.0)

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
[1.1.0 guide](https://github.com/leocaolab/getarc/blob/9a4ff4d/GUIDE.md#6-configuration).

Full operations manual + every flag: `arc <cmd> --help`.

## Quick start (1.2 preview)

The commands changed: `arc review` now opens the PR, and the old per-file
review is `arc local-review`.

```bash
arc init                              # pick Critic + Fixer providers (from ~/.tars/config.toml)
arc rot                               # whole-repo structural rot — needs no server
arc review                            # push, open/reuse the PR, hand it to the review service
arc local-review                      # optional: per-file review of your tree, sent as a reply on the PR; never edits
arc fix                               # the Fixer answers the PR's findings, each fix on its own arc/fix-<id> branch; never merges
```

Once the reviewers say LGTM, the merge machine lands the PR. Label it
`arc-hold` to keep it from landing. The whole loop, `merge.yml`, deploys and
connecting Claude Code / Codex / agy:
<https://arc-site.hucao1.workers.dev/docs/>.

---

## Test intelligence — arc tests what it changes, and measures your coverage

New in 1.1. arc doesn't just change code; it verifies the change is *tested*,
and reads back your test suite's real signal.

```bash
arc tap init                          # make JUnit a side-effect of your normal test run (once)
arc tap test 'target/**/junit.xml'    # ingest what your runner produced into .arc/tap.db
arc tap signal                        # slowest + flaky tests, from real run history
arc tap coverage                      # coverage as MUTANT SURVIVAL, not an llvm-cov %
arc tap gaps                           # open coverage-gap tickets arc couldn't auto-cover
arc affected                          # which existing tests a diff can touch (guppy rdeps)
```

- **`arc fix` generates + gates tests for the code it changes** (default on). It
  computes the affected test set deterministically, writes new tests, and
  **gates each one**: a test that compiles + passes lands with the fix; one that
  fails is filed as a `coverage_gap` ticket (with the real runner output), never
  pushed into your tree. Turn it off with `[test] generate = false`.
- **Coverage = mutant survival, not a percentage.** A changed region that *was*
  run but no test flipped is an uncovered gap — a line-coverage % can't see that.
  `arc tap coverage` separates the survival rate, the actionable survivor list,
  and the untested count (so "0 gaps" can never masquerade as "fully covered").
- **arc is a *consumer* of your test results** — your runner writes the JUnit XML,
  `arc tap` records and reads it back. It never imposes its own runner.

## Refactor structural rot — `arc refactor <target>`

`arc rot` finds structural rot (god-modules, cross-file duplication, weak types);
`arc refactor` acts on it. It hands a **named target's** L5 suggestions to the
Agent, which rewrites **across files** — moving a symbol carries its call sites
*and* tests — then lands the change only through the **full verify-gated
build+test gate**: accepted only if the whole tree still builds and passes.

```bash
arc rot                               # seed structural (L5) suggestions
arc refactor src/core/god_module.rs   # or: arc refactor F-42  (a suggestion id)
```

Unlike `arc fix`, `arc refactor` **always names a target** (a file/folder path or
an `F-<id>`) — a target-less refactor is refused, never a whole-board sweep — and
it acts on `suggestion` findings, not just `new` ones.

---

## What you also get in the tarball (1.1.0)

Each 1.1.0 release ships:

- `arc` — the CLI binary
- `arc-vscode.vsix` — the [VS Code extension](#vs-code-extension)
- `LICENSE` — terms

---

## VS Code extension (1.1.0)

Not shipped in the 1.2 preview. **On 1.1.0, this is the best way to use arc.** The extension (v0.2.27) turns the
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

## Integrations (1.1.0)

The Claude Code skill below runs `arc auto`, which is paused in the 1.2 preview.

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

## What arc actually does (1.1.0)

In the 1.2 preview the landing path moved onto a PR, a review service and a
self-hosted merge machine — see [the docs](https://arc-site.hucao1.workers.dev/docs/guides/commands/).

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
