# Skills and plugins

Skills let your coding agent drive arc for you. They never re-implement arc: they run the `arc` binary and read its `--json` output. The same skills reach you three ways; pick one:

| What | Where it comes from | Skills are called |
|---|---|---|
| **`arc` plugin** | the public [getarc](https://github.com/leocaolab/getarc) marketplace — the usual way | `arc:<skill>` |
| **`arc-skills.tar.gz`** | an asset of every [release](install.md#what-a-release-holds); unpack it and load the directory | `arc-skills:<skill>` |
| **`arc-skills` plugin** | this repo's marketplace (`.claude-plugin/marketplace.json`), for licensed users | `arc-skills:<skill>` |

All three carry the skills below: the [skills over the CLI](#the-skills-over-the-cli) and the [review skills](#the-review-skills), with the rubrics they cite. **`arc-room`** is a separate plugin of this repo's marketplace ([below](#arc-room--talk-into-a-session)).

## Install

**From getarc, in Claude Code** (from a shell; inside a session, `/plugin marketplace add leocaolab/getarc` and `/plugin install arc@getarc` do the same):

```bash
claude plugin marketplace add leocaolab/getarc
claude plugin install arc@getarc
```

**From the release tarball**, for one session at a time:

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/arc-skills.tar.gz | tar -xz   # unpacks ./arc-skills
claude --plugin-dir ./arc-skills
```

**In another agent** (Codex, Cursor, …): `npx skills add leocaolab/getarc --skill arc-setup`, and pick your agent. Then ask the agent to "set up arc" — the full prompt is on [Install](install.md#or-let-your-coding-agent-set-it-up).

**From a clone of this repo** (licensed users): `claude --plugin-dir plugins/arc-skills` for one session, or as a marketplace inside Claude Code:

```text
/plugin marketplace add ./
/plugin install arc-skills@arc
```

## See what you have

- `claude plugin list` names each installed plugin with its version (`arc@getarc`); a `--plugin-dir` one shows under *Session-only plugins* as `arc-skills@inline`.
- `claude plugin details arc@getarc` lists every skill the plugin carries (for the tarball: `claude --plugin-dir ./arc-skills plugin details arc-skills@inline`).
- Inside a session, `/plugin` opens the same list, and typing `/arc:` (or `/arc-skills:`) completes the skill names.

You rarely call a skill by name: ask for what you want ("set up arc", "is this type needed? name it") and Claude picks the skill.

<a id="upgrade"></a>
## Upgrade

```bash
claude plugin marketplace update getarc
claude plugin update arc@getarc        # then restart Claude Code
```

Claude Code takes a new version only when the plugin's version string changes. The tarball is upgraded by fetching it again.

<a id="the-skills-over-the-cli"></a>
## The skills over the CLI

Each skill is called by name (`arc:<skill>` from getarc, `arc-skills:<skill>` otherwise) or picked by Claude from what you ask:

| Skill | Ask for it with | What it does |
|---|---|---|
| `arc-setup` | "install arc", "set up arc" | the install agent: binary from getarc, providers in tars, `arc init` roles, a smoke test, presubmit.toml, the merge gate; then the pipeline machine (server suite, machine.toml, arc-web and arc-bridge, the repo registered with its review routes and services), client.toml and the agent hooks, and a first landed PR. It probes what is already there, does only what is missing, verifies each stage with one command and stops with the real error when one fails |
| `review` | "review my changes", "arc local-review this" | runs `arc local-review` and shows the reviewer's findings as arc prints them. Read-only |
| `fix` | "fix the real issues", "arc fix" | runs `arc fix` after a local review: the Fixer answers the local PR's findings, one commit per fix on the current branch. It pushes nothing |
| `rot` | "fix the rot", "arc rot" | works through `arc rot`'s structural suggestions as multi-file refactors; it edits and commits, so it confirms first |
| `automate` | "run arc on every commit", "gate merges on arc" | the post-commit hook (`arc hook install`), or the merge gate's `merge.yml` |
| `maintain` | "arc is failing", "reset arc" | diagnoses a failing command, resets local state, swaps a provider role |

Every skill runs the same preflight first (the plugin's `reference/preflight.md`) and reads this user guide, which ships inside the plugin (`docs/`). The install agent's route is data: `skills/arc-setup/roadmap.json` (stages and their completion criteria), `known_issues.json` (real error lines → cause and fix), and three read-only Python scripts (`probe.py`, `diagnose.py`, `fetch_arc.py`; `python3` only, standard library).

## The review skills

The same plugin carries the methods arc's own team reviews and writes code by. They need no `arc` binary: they are Markdown and the rubrics — the plugin's `rubrics/` is the very rule set arc's reviewer reads, not a copy, so what a skill tells you and what `arc local-review` flags are one set of rules.

Call one by name (`/arc:type-naming`) or just ask, and Claude picks it.

| Skill | Use it when | Ask for it with | You get |
|---|---|---|---|
| `type-naming` | you are about to add or rename a type | "is this type needed? name it" | the four gates in order, and 2–3 candidate names when one is needed |
| `comment-clean` | comments read verbose, or before a change lands | "clean the comments in this diff" | the comments cut or rewritten to the why, the contracts and the invariants |
| `coding-convention` | before writing or changing code | loaded with the language's `shift-left-*` | the method: ownership tables, then types, decisions and comments translated from them; a check-list for reviewing |
| `coding-principles` | reasoning about a design | "which principle does this break?" | the ~26 axioms every other rule comes from |
| `shift-left-<lang>` | writing code in rust, python, typescript, javascript, go, java, c, cpp or swift | picked by the file you edit | the language's checklist, each rule with a bad and a good line |

## `arc-room` — talk into a session

With it, anyone on arc-bridge can say something in your session's room (its `feed:<name>` channel) and it arrives in the session as a prompt, one line per message: `【Mei】words`. It also speaks for the session: what the model writes goes to the room as it is written.

```text
/plugin install arc-room --marketplace leocaolab/arc
```

It needs Claude Code 2.1.275 or later, `arc` on `PATH`, and a machine configured for arc-bridge (`~/.arc/client.toml`, see [Team up](bridge.md)). It only brings words in: waiting and acknowledging are `arc bridge`'s (`arc bridge await-mail`, then `arc bridge ack`).

---

*Next: [The commands](commands.md) · [Connecting your coding agent](coding-agents.md) · [Team up](bridge.md).*
