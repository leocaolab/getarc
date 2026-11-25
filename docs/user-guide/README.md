# A.R.C. — User Guide

**Let your coding agents write the code. arc checks it before it lands.**

A.R.C. (Adversarial Resolution Cycle) is a code-review tool. Two models work against each other: a **Critic** reads your change and points out problems (each one is a **finding**), and a **Fixer** edits the code and answers each finding. They go back and forth until the Critic says LGTM ("looks good to me"), or a person steps in. arc keeps every finding and every answer in `<repo>/.arc/` (SQLite), with a timeline of events that is only ever added to.

arc has two parts, and you install both:

- **The `arc` command**, on every machine where people or agents write code. Before a change leaves your machine, run `arc local-review` to review it there, and `arc fix` to let the Fixer work on the findings until the Critic says LGTM. Then `arc submit` sends it to the pipeline.
- **The pipeline**, a set of services on one machine you own. A review service reviews every PR. A merge server lands a PR only after its reviewers say LGTM and your own `merge.yml` finds no new failure. A nightly release and deploys ship what landed. Agents and people talk to each other on a chat server (`arc bridge`).

Every flag is in `arc <command> --help`.

## Install it with your coding agent

Paste this into your coding agent (Claude Code, Codex, or another) in the repository you want arc in:

```text wrap
Set up A.R.C. (arc) in this repository with the arc-setup skill. If you're in Claude Code, run `claude plugin marketplace add leocaolab/getarc`, then `claude plugin install arc@getarc`. If you're in another agent, run `npx skills add leocaolab/getarc --skill arc-setup` and select your agent. Use one installation method. You can read the skill directly at https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md (raw: https://raw.githubusercontent.com/leocaolab/getarc/main/skills/arc-setup/SKILL.md). Then use the arc-setup skill to install and configure arc here.
```

The agent installs arc and takes you through each step. It asks before it changes anything outside the repository. **If you are that agent,** read [arc for coding agents](for-agents.md) first: the quick start, the install steps, the commands, the exit codes and the rules, on one page.

To install by hand, start at [Install](install.md).

## Contents

**Install and set up**

- [Install — the `arc` command on each machine, the services on the pipeline machine, upgrading](install.md)
- [Configuration — each settings file, what goes in it, every key of `machine.toml`](configuration.md)
- [Set up the pipeline — prepare the repo, register it, start the services, connect your machines, land a first PR](onboarding.md)
- [Skills and plugins — install the skills, list them, upgrade; arc-room](skills.md)
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

- **It reviews your code, in 9 languages:** Rust, Python, TS, JS, Go, Java, C, C++, Swift. arc picks the language support by the language of the repo it reviews.
- **It reports; it does not block on its own.** A finding does not fail your build. arc tells you what it found, and you (or the Fixer) decide what to do. On the pipeline, two things decide whether a PR lands: the reviewers' LGTM and your own `merge.yml`.
- **It comes with no model.** You choose the models (providers) in tars, and arc uses them.
- **It is not a style linter.** Formatting is the job of `clippy` / `ruff` / `eslint` / `gofmt`. arc looks for problems in what the code means and in how the codebase is put together.

arc reviews at two levels: **L4**, each file against its contracts ([review.md](review.md)), and **L5**, the whole repo for structural rot ([rot.md](rot.md)). Both run on your machine and on the pipeline.

---

*See also: `../usage.md` — exhaustive operations manual · `review_types` README — the finding model · [`../../README.md`](../../README.md) — quickstart.*
