# Skills and plugins

Skills let your coding agent run arc for you. A skill does not do arc's work itself: it runs the `arc` command and reads its `--json` output.

You can get the same skills in three ways. Pick one:

| What | Where it comes from | Skills are named |
|---|---|---|
| **`arc` plugin** | the public [getarc](https://github.com/leocaolab/getarc) marketplace (the usual way) | `arc:<skill>` |
| **`arc-skills.tar.gz`** | a file in every [release](install.md#what-a-release-holds); unpack it and load the directory | `arc-skills:<skill>` |
| **`arc-skills` plugin** | this repo's marketplace (`.claude-plugin/marketplace.json`), for licensed users | `arc-skills:<skill>` |

All three carry the same skills: the [skills that run arc](#the-skills-over-the-cli) and the [review skills](#the-review-skills), with the rubrics they cite. **`arc-room`** is a separate plugin in this repo's marketplace ([below](#arc-room--talk-into-a-session)).

## Install

**From getarc, in Claude Code.** From a shell:

```bash
claude plugin marketplace add leocaolab/getarc
claude plugin install arc@getarc
```

Inside a Claude Code session, `/plugin marketplace add leocaolab/getarc` and `/plugin install arc@getarc` do the same.

**From the release tarball**, for one session at a time:

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/arc-skills.tar.gz | tar -xz   # unpacks ./arc-skills
claude --plugin-dir ./arc-skills
```

**In another agent** (Codex, Cursor, …): run `npx skills add leocaolab/getarc --skill arc-setup` and pick your agent. Then ask the agent to "set up arc". The full prompt to paste is on [Install](install.md#or-let-your-coding-agent-set-it-up).

**From a clone of this repo** (licensed users): `claude --plugin-dir plugins/arc-skills` for one session, or add it as a marketplace inside Claude Code:

```text
/plugin marketplace add ./
/plugin install arc-skills@arc
```

## See what you have

- `claude plugin list` lists each installed plugin with its version (`arc@getarc`). A plugin loaded with `--plugin-dir` shows under *Session-only plugins* as `arc-skills@inline`.
- `claude plugin details arc@getarc` lists every skill in the plugin. For the tarball: `claude --plugin-dir ./arc-skills plugin details arc-skills@inline`.
- Inside a session, `/plugin` opens the same list, and typing `/arc:` (or `/arc-skills:`) completes the skill names.

You rarely need a skill's name. Ask for what you want ("set up arc", "is this type needed? name it") and Claude picks the skill.

<a id="upgrade"></a>
## Upgrade

```bash
claude plugin marketplace update getarc
claude plugin update arc@getarc        # then restart Claude Code
```

Claude Code installs a new version only when the plugin's version number changes. To upgrade the tarball, download it again.

<a id="the-skills-over-the-cli"></a>
## The skills that run arc

Call each skill by name (`arc:<skill>` from getarc, `arc-skills:<skill>` otherwise), or just ask and Claude picks it:

| Skill | Ask for it with | What it does |
|---|---|---|
| `arc-setup` | "install arc", "set up arc" | installs and sets up arc with you: the binary from getarc, providers in tars, the roles from `arc init`, a smoke test, presubmit.toml, the merge gate; then the pipeline machine (server suite, machine.toml, arc-web and arc-bridge, the repo registered with its reviewers and services), client.toml and the agent hooks; and finally a first landed PR. It first checks what is already there and does only what is missing. It verifies each step with one command, and stops with the real error when one fails |
| `review` | "review my changes", "arc local-review this" | runs `arc local-review` and shows the reviewer's findings as arc prints them. Changes nothing |
| `fix` | "fix the real issues", "arc fix" | runs `arc fix` after a local review: the Fixer answers the findings of the local PR, one commit per fix on the current branch. Pushes nothing |
| `rot` | "fix the rot", "arc rot" | works through the structural suggestions from `arc rot` as multi-file refactors. It edits and commits, so it asks you first |
| `automate` | "run arc on every commit", "gate merges on arc" | sets up the post-commit hook (`arc hook install`), or the merge gate's `merge.yml` |
| `maintain` | "arc is failing", "reset arc" | finds out why a command fails, resets local state, swaps the provider for a role |

Every skill runs the same checks first (the plugin's `reference/preflight.md`) and reads this user guide, which ships inside the plugin (`docs/`).

The arc-setup skill's steps are stored as data: `skills/arc-setup/roadmap.json` (the steps and how each one is verified), `known_issues.json` (real error lines, each with its cause and fix), and three read-only Python scripts (`probe.py`, `diagnose.py`, `fetch_arc.py`; they need only `python3` and its standard library).

## The review skills

The same plugin carries the methods arc's own team uses to review and write code. They do not need the `arc` binary: they are Markdown plus the rubrics. The plugin's `rubrics/` is the same rule set arc's reviewer reads, not a copy, so what a skill tells you and what `arc local-review` reports come from one set of rules.

Call one by name (`/arc:type-naming`) or just ask, and Claude picks it.

| Skill | Use it when | Ask for it with | You get |
|---|---|---|---|
| `type-naming` | you are about to add or rename a type | "is this type needed? name it" | the four checks in order, and 2–3 candidate names when the type is needed |
| `comment-clean` | comments read verbose, or before a change lands | "clean the comments in this diff" | the comments cut or rewritten down to the why, the contracts and the invariants |
| `coding-convention` | before writing or changing code | loaded with the language's `shift-left-*` | the method: first tables of who owns what, then types, decisions and comments written from them; a checklist for reviewing |
| `coding-principles` | reasoning about a design | "which principle does this break?" | the ~26 principles every other rule comes from |
| `shift-left-<lang>` | writing code in rust, python, typescript, javascript, go, java, c, cpp or swift | picked by the file you edit | the language's checklist, each rule with a bad and a good line |

## `arc-room` — talk into a session

With arc-room, anyone on arc-bridge can write in your session's room (its `feed:<name>` channel), and each message arrives in the session as a prompt, one line per message: `【Mei】words`. It also works the other way: what the model writes goes to the room as it is written.

```text
/plugin install arc-room --marketplace leocaolab/arc
```

It needs Claude Code 2.1.275 or later, `arc` on your `PATH`, and a machine set up for arc-bridge (`~/.arc/client.toml`, see [Team up](bridge.md)). It only brings messages in. Waiting for mail and confirming it was delivered are done by `arc bridge` (`arc bridge await-mail`, then `arc bridge ack`).

---

*Next: [The commands](commands.md) · [Connecting your coding agent](coding-agents.md) · [Team up](bridge.md).*
