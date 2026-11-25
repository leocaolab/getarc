# A.R.C. — User Guide

## Agent setup

Paste this into your coding agent (Claude Code, Codex, or another) in the repository you want arc in:

```text wrap
Set up A.R.C. (arc) in this repository with the arc-setup skill. If you're in Claude Code, run `claude plugin marketplace add leocaolab/getarc`, then `claude plugin install arc@getarc`. If you're in another agent, run `npx skills add leocaolab/getarc --skill arc-setup` and select your agent. Use one installation method. You can read the skill directly at https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md (raw: https://raw.githubusercontent.com/leocaolab/getarc/main/skills/arc-setup/SKILL.md). Then use the arc-setup skill to install and configure arc here.
```

The agent installs arc and walks you through each step, asking before it touches anything outside the repository. **If you are that agent,** start with [arc for coding agents](for-agents.md): the quick start, the install route, the commands, the exit codes and the rules, on one page.

---

A.R.C. (Adversarial Resolution Cycle) is a code-review tool. A **Critic** LLM reads your code and files findings; a **Fixer** LLM edits files; they go round per finding until the reviewer says LGTM or a person steps in. Findings persist as entities in `<repo>/.arc/` (SQLite) with an append-only event timeline.

arc is two halves that you install together:

- **The `arc` CLI**, on every machine where people or agents write code. Before a change leaves your machine, arc reviews it there (`arc local-review`) and the Fixer answers the findings until the reviewer says LGTM (`arc fix`). `arc submit` then hands it to the pipeline.
- **The pipeline**, a self-hosted server suite on one machine you own: a review service reviews every PR, a merge server lands it only on the reviewers' LGTM and your own `merge.yml`, a nightly release and deploys ship what landed, and agents and people team up on a chat server (`arc bridge`).

Every flag is in `arc <command> --help`.

## Contents

**Install and set up**

- [Install — the CLI on each machine, the server suite on the pipeline machine, upgrading](install.md)
- [Configuration — the files, whose fact each one holds, every key of `machine.toml`](configuration.md)
- [Set up the pipeline — initialize the repo, register it, start the services, connect the clients, land a first PR](onboarding.md)
- [Skills and plugins — install the skills, see them, upgrade; arc-room](skills.md)
- [Connecting your coding agent — Claude Code, Codex CLI, agy](coding-agents.md)

**Review your change before you submit**

- [The commands — review your change, fix it, submit it](commands.md)
- [How arc reviews — the FP lens and per-file contracts (L4)](review.md)
- **[Rot — what it is, why it hurts, how arc handles it (L5)](rot.md)** — the core concept
- [Custom rubrics — bring your own rules](custom-rubrics.md)
- [Code conventions — an opt-in demo, off by default](code-conventions.md)

**The pipeline**

- [Working on the board — the pages, from a plan to landed work, what works well, `arc-hold`](working-on-the-board.md)
- [Review on the pipeline — submit, answer, LGTM, pass](pipeline-review.md)
- [Team up — arc bridge: rooms, messages, teams](bridge.md)
- [Merge — how a PR lands, and writing `merge.yml`](merge-gate.md)
- [Releases and deploys — the nightly, `arc deploy`, the release page](release.md)
- [Your data — what the pipeline collects and where it lives](data.md)
- Finding model — identity, events, states

[Troubleshooting](troubleshooting.md)

## What arc is (and is not)

- **It reviews OTHER people's code, in 9 languages** (Rust, Python, TS, JS, Go, Java, C, C++, Swift). The language drivers fire on the *target* repo's language.
- **It is an advisory detector.** Finding rot or bugs is not a build failure by itself; `arc` reports, you (or the Fixer) decide. On the pipeline, what decides a landing is the reviewers' LGTM and your own `merge.yml`.
- **No LLM is bundled.** You point arc at providers you configure in tars.
- **Not a style linter.** Formatting is for `clippy` / `ruff` / `eslint` / `gofmt`. arc targets *semantic* hazards and *structural* rot.

arc works at two altitudes: **L4** — per-file contracts ([review.md](review.md)) — and **L5** — whole-repo structural rot ([rot.md](rot.md)). Both run on your machine and on the pipeline.

---

*See also: `../usage.md` — exhaustive operations manual · `review_types` README — the finding model · [`../../README.md`](../../README.md) — quickstart.*
