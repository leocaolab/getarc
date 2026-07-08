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

Extension source: [leocaolab/arc-vscode](https://github.com/leocaolab/arc-vscode) (MIT).
Coming soon to Open VSX (Cursor / VSCodium native discoverability).

---

## Integrations

| Surface | Repo | License |
|---|---|---|
| VS Code extension | [`leocaolab/arc-vscode`](https://github.com/leocaolab/arc-vscode) | MIT |
| Claude Code skill | [`leocaolab/arc-skills`](https://github.com/leocaolab/arc-skills) | MIT |
| MCP server (Cursor / Claude Desktop / Continue / Claude Code) | [`leocaolab/arc-mcp`](https://github.com/leocaolab/arc-mcp) | MIT |
| Homebrew tap | [`leocaolab/homebrew-arc`](https://github.com/leocaolab/homebrew-arc) | MIT |

All the wrappers are open. The engine is closed.

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

The arc engine source is not public — see § "Why no source link" below.

---

## Why no source link

The arc engine is closed because the detectors (~10 today, ~16 on the
queue), the multi-language graph (8 langs), the finding-entity
alignment model, and the webview-to-SARIF emission pipeline took
real iteration against real dogfood. AI-era moats are execution
speed + iteration, not source secrecy — so the wrappers (extension,
skill, MCP server) are open, and the engine isn't.

If that policy ever changes, this section will say so.

---

## Questions / bugs

Open an issue on this repo. Include `arc --version` + your OS.
