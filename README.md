# A.R.C. — Adversarial Resolution Cycle

**Website and docs: <https://arc-site.hucao1.workers.dev/>** · [Docs](https://arc-site.hucao1.workers.dev/docs/) · [中文文档](https://arc-site.hucao1.workers.dev/zh/docs/)

Code review for the code your coding agent writes. A Critic LLM reviews your
branch and files findings. A Fixer (Claude Code, Codex CLI, or another LLM)
answers them, one commit per fix, until the reviewer says LGTM. Findings are
kept in `<repo>/.arc/` (SQLite) with an append-only history.

One binary. macOS (Apple Silicon) and Linux x86_64. Bring your own model.

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh
```

**Free to use**, personal or commercial. The source is closed; the binaries are
free downloads. See [LICENSE](LICENSE).

---

## Install

### One line

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh
```

The script picks this machine's build, checks it against the release's
`SHA256SUMS`, runs it once, and puts `arc` in `~/.local/bin`. It never runs
`sudo` and never edits your shell profile: if the directory is not writable or
not on `PATH`, it prints the line to fix it.

```bash
curl -fsSL …/install.sh | sh -s -- --version v1.3.0   # a named release
curl -fsSL …/install.sh | sh -s -- --to ~/bin         # another directory
```

`--from URL` fetches the assets from a mirror or a `file://` directory instead.
To update, run the same line again.

### What a release holds

Every release from `v1.3.0` on carries these files, under these names:

| File | What it is | Platform |
|---|---|---|
| `install.sh` | the one-line installer above | macOS arm64, Linux x86_64 |
| `arc-darwin-arm64.tar.gz` | the `arc` CLI | macOS, Apple Silicon |
| `arc-linux-x64.tar.gz` | the `arc` CLI, statically linked (musl): runs on any distro | Linux x86_64 |
| `arc-suite-darwin-arm64.tar.gz` | the server suite (team edition), with a README | macOS, Apple Silicon |
| `arc-suite-linux-x64.tar.gz` | the server suite (team edition), with a README. Dynamically linked: needs glibc ≥ 2.43; `arc-web` and `arc-tap` also need libstdc++ from GCC 13 (`GLIBCXX_3.4.32`) | Linux x86_64 |
| `arc-skills.tar.gz` | the `arc-skills` Claude Code plugin | any |
| `arc-vscode.vsix` | the VS Code extension | any |
| `SHA256SUMS` | checksums of the files above | — |

By hand, without the script:

```bash
# macOS (Apple Silicon)
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/arc-darwin-arm64.tar.gz | tar -xz
# Linux x86_64
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/arc-linux-x64.tar.gz | tar -xz

mv arc ~/.local/bin/          # anywhere on your PATH
arc --version
```

No other platform has a build, an Intel Mac included. If you need one,
[open an issue](https://github.com/leocaolab/getarc/issues).

### Or let your coding agent set it up

Paste this into Claude Code, Codex or another coding agent, in the repository you
want arc on:

```text
Set up A.R.C. (arc) in this repository with the arc-setup skill. If you're in Claude Code, run `claude plugin marketplace add leocaolab/getarc`, then `claude plugin install arc@getarc`. If you're in another agent, run `npx skills add leocaolab/getarc --skill arc-setup` and select your agent. Use one installation method. You can read the skill directly at https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md (raw: https://raw.githubusercontent.com/leocaolab/getarc/main/skills/arc-setup/SKILL.md). Then use the arc-setup skill to install and configure arc here.
```

The [arc-setup skill](skills/arc-setup/SKILL.md) checks what is already there and
walks the stages in order: the binary, your LLM providers in tars, `arc init`'s
roles, optional hooks, then a first run. It asks before anything global or
outward and stops with the real error when a stage fails.

---

## Quick start

arc comes in two editions. The **personal edition** is the CLI alone: arc reviews
your agent's change on your machine, the Fixer answers the findings, and you push.
No server. The **team edition** adds a self-hosted pipeline that reviews, merges
and releases ([below](#team-edition)).

**1. Define a provider** in `~/.tars/config.toml`. This is the only place a model
or a key is written; never commit it.

```toml
[providers.gemini_flash]
type = "gemini"
default_model = "flash@latest"
auth = { kind = "secret", secret = { source = "env", var = "GEMINI_API_KEY" } }

[providers.claude_cli]
type = "claude_cli"            # uses your `claude login`; no key
default_model = "sonnet"
tools = "default"              # a Fixer must be allowed to edit files
```

Provider types include `anthropic`, `openai`, `openai_compat`, `gemini`,
`bedrock`, `claude_cli`, `codex_cli`, `antigravity` and local servers
([all of them](https://arc-site.hucao1.workers.dev/docs/start/configuration/)).

**2. Map arc's roles** in the repo you want reviewed:

```bash
arc init        # asks which provider reviews and which one fixes; writes .arc/config.toml
```

**3. Review and fix**, on a feature branch:

```bash
arc local-review     # review this branch's change against origin's default branch; never edits
arc fix              # the Fixer answers each finding: one commit per fix on this branch, reviewed again until LGTM
git push             # you push it
```

- `arc local-review` keeps the review as a local PR in this clone's
  `.arc/review.db` and prints a report: each open finding with its place, its
  rule, the reviewer's words and the code around it. Nothing is posted anywhere.
- `arc fix` needs a clean working tree and a local PR (run `arc local-review`
  first). It works in your working tree, on your current branch, and never pushes.
  `git reset --hard refs/arc/before-fix/<branch>` undoes the whole run.
- `arc fix <path>` or `arc fix <id>` narrows it to a file, a folder or one finding.

**Other commands**, all local:

```bash
arc rot              # whole-repo structural rot (L5): suggestions, never applied for you
arc rot --no-judge   # the deterministic signals only, no LLM
arc hook install     # review each commit in the background
arc tap init         # make JUnit XML a side effect of your normal test run; then `arc tap test`
arc affected         # which tests a change can reach
```

`arc <cmd> --help` is the source of truth for every command and flag. `--json`
makes any command print one machine-readable envelope, for agents and scripts.

### Team edition

The team edition is the same CLI plus a server suite you host
(`arc-suite-*.tar.gz`): a review service, a merge machine, a nightly releaser, a
web board and a chat server. `arc submit` pushes the branch, opens (or reuses) its
PR and hands it to the review service. The merge machine lands a PR only after the
reviewers say LGTM and your own `.github/workflows/merge.yml` shows no new failure.
Label a PR `arc-hold` to keep it from landing. During the preview an arc engineer
installs the suite with you.
[The docs →](https://arc-site.hucao1.workers.dev/docs/)

---

## Why not just ask an agent to review?

### 1. The perception vs. the reality

![Two panels. Left, "The perception: grand codebase projection" — people imagine the agent standing before a giant holographic projection of the whole codebase, saying "Amazing! It can see everything and make perfect high-level decisions!" Right, "The reality: localized telescope patching" — the agent actually squints through a telescope at one small block of code, drowning in tangled wires, with no visible context: "I can only see one small block at a time! This blind, line-by-line review is a nightmare."](perception-vs-reality.png)

People picture an agent reviewing your code like a *grand projection*: it sees
everything and makes perfect high-level calls. The reality is a **telescope**.
Attention is finite, so the agent looks at one small block at a time, with little
context around it. It never holds the whole codebase at once.

### 2. So the review is buckshot

![Two panels. Left, "Agent's review (unsystematic)": a robot sprays a codebase wall with a machine gun, leaving scattered holes labelled MISSING BUG, SECURITY HOLE, LOGIC ERROR MISSED, MAJOR OMISSION. Right, "Our systematic review (thorough)": a code-review engine and robotic rollers lay uniform coverage over the wall.](agent-vs-arc.png)

Because it only sees a narrow slice, an agent's review is not **systematic**: no
fixed rule set, no whole-repo pass, no memory of what it checked last time. A few
shots land, most miss, and the bugs live in the gaps. Re-run it and you get
different holes.

arc is built the other way. **Rubrics** pin the rules, and each rule names one
hazard, so one smell is one finding. **Deterministic detectors** surface cheap
signals first, so the LLM confirms rather than re-derives. **Findings are
records** with an append-only history, kept across review rounds: each one is
answered — fixed or won't fix — instead of scrolling away.

### 3. And left unmeasured, the codebase rots

![One panel, "The problem we are solving: spaghetti agent programming" — a frazzled AI robot tangled in a mess of spaghetti wiring, slapping a band-aid over code in the wrong place, surrounded by warnings: 5 broken connections (dangling threads, dead-end paths) and 6 identical redundant logic implementations. Speech bubble: "It's not simplification... it's overwriting in the wrong places! And now there are 5 threads and 6 identical implementations!"](spaghetti-rot.png)

The same blindness compounds. Patch after patch, the agent edits in the wrong
place, leaves dead ends, and re-implements logic that already exists, because it
cannot see it. That is **rot**: structural decay whose root is the shape of the
system, not any one line. It rarely breaks the build; it erodes the code's
capacity to change.

`arc rot` finds it. Deterministic signals surface the candidates — god-modules,
the same idiom in three or more files, one concept modelled as same-named types
in several crates, dependencies pointing the wrong way — and an LLM judge
confirms each one. The result is a set of suggestions, not a refactor button:
the restructuring is your decision, made on a branch and reviewed like any
change. `arc rot --no-judge` gives the signals alone, cheap enough to trend in CI.

### In one line

Review is a **coverage** problem, not an intelligence problem. arc aims fixed
rules at the mistakes agents actually make (there is a rubric for LLM-generated
code smells), reviews nine languages (Rust, Python, TypeScript, JavaScript,
Go, Java, C, C++, Swift), and keeps every finding as a record with a status and a
history, not a line in a chat log.

---

## VS Code extension

`arc-vscode.vsix` is on every release from `v1.3.0` on:

```bash
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/arc-vscode.vsix
code --install-extension arc-vscode.vsix
```

It shows the findings on your branch's last local PR (`arc local-review --show`)
as a tree by file, with the Critic↔Fixer debate per finding, CodeLens above each
finding's line, optional squiggles, and a **Review Branch** button that runs one
review round. It runs the `arc` CLI and refreshes when a review or fix in a
terminal changes `.arc/review.db`. Findings are answered with `arc fix`, not from
the editor.

## Skills and plugins

This repo is a Claude Code plugin marketplace. Its `arc` plugin carries the
skills of arc's `arc-skills` plugin (the one `arc-skills.tar.gz` packs):

```bash
claude plugin marketplace add leocaolab/getarc
claude plugin install arc@getarc
```

In another agent: `npx skills add leocaolab/getarc`, and pick the skills.

To see them: `claude plugin list` names `arc@getarc` and its version, `claude plugin details arc@getarc`
lists every skill, and inside a session `/plugin` shows the same and `/arc:` completes the skill
names; you can also just ask ("set up arc", "taste check `src/pool.rs`") and Claude picks the skill.
To upgrade: `claude plugin marketplace update getarc`, then `claude plugin update arc@getarc` and
restart Claude Code. Without the marketplace, the release's `arc-skills.tar.gz` holds the same skills:
unpack it and run `claude --plugin-dir ./arc-skills` (the skills are then `arc-skills:<name>`).

| Skill | What it does |
|---|---|
| [`arc-setup`](skills/arc-setup/SKILL.md) | installs and configures arc, stage by stage |
| [`review`](skills/review/SKILL.md) | runs `arc local-review`, real findings first; read-only |
| [`fix`](skills/fix/SKILL.md) | runs `arc fix` on the local PR; pushes nothing |
| [`rot`](skills/rot/SKILL.md) | works through `arc rot`'s suggestions as refactors; asks first |
| [`automate`](skills/automate/SKILL.md) | the post-commit review hook, or the merge gate's `merge.yml` |
| [`maintain`](skills/maintain/SKILL.md) | diagnoses a failing command, resets local state, swaps a role |

The review methods arc's own team works by need no `arc` binary:
`taste-check`, `smell-check`, `error-check`, `test-check`,
`name-check`, `type-naming`, `comment-clean`, `coding-convention`,
`coding-principles` and `shift-left-<lang>` for nine languages (Rust, Python,
TypeScript, JavaScript, Go, Java, C, C++, Swift). They cite the
rule sets in [`rubrics/`](rubrics/), the same files arc's reviewer reads.

---

## License

Free for any use (personal, commercial, internal). You may not redistribute the
binaries (link to this repo instead), reverse-engineer, or decompile. See
[LICENSE](LICENSE) for the full text. The arc engine source is not public.

## Questions / bugs

[Open an issue](https://github.com/leocaolab/getarc/issues) on this repo. Include
`arc --version` and your OS.
