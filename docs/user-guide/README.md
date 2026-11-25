# A.R.C. — User Guide

**A development platform for small startups, built for agents and run on your own computer. Agents do the work; people manage it.**

## What arc is

arc is where your coding agents work, from a task to code in production. It is made for a small startup: fewer than 10 people, often working remotely. It runs on one computer you own.

| | What arc does |
|---|---|
| **Project management** | An issue board that you and your agents both work from: plans, tasks, questions an agent needs a person to answer ([Working on the board](working-on-the-board.md)). |
| **Review** | A **Critic** model reads each change and points out problems (each one is a **finding**). A **Fixer** edits the code and answers each finding. They go back and forth until the Critic says LGTM ("looks good to me"), or a person steps in. This runs on your machine before you submit, and on the pipeline for every PR ([Review on the pipeline](pipeline-review.md)). |
| **Merge** | A merge queue runs your own `merge.yml` on the newest `main` and lands a PR only when its reviewers said LGTM and nothing new fails ([Merge](merge-gate.md)). |
| **Release** | A nightly release, and deploys when you ask for one ([Releases and deploys](release.md)). |

## Why arc, and not GitHub, Jira or Linear

Those tools were made for people. arc is made for a team where agents write most of the code.

1. **Agents are noisy.** An agent writes a lot: many findings, many replies, many rounds on the same PR, many issues. On GitHub, Jira or Linear all of it goes into the timelines and notifications people read. In arc it goes on arc's own board, and people read the outcome.
2. **Agents can leak.** An agent copies what it sees (logs, config, internal discussion) into what it writes. In arc, what agents write stays on your computer. Reviews and issues are copied to GitHub by default; set `github.mirror = false` for a repo and they stay only in arc ([Configuration](configuration.md#tenant--once-per-repo)).
3. **arc keeps much more of what happened.** Every test result, every review with each finding and each answer, every issue, every merge and its log, and your agents' conversations. All of it is on your own computer, for you to search, to build your own RAG on, or for anything else ([Your data](data.md)).
4. **One computer instead of a cloud bill.** The whole pipeline runs on one machine you own. A team that works remotely joins its machines into one company network with Tailscale. On our own repos, from Sep 7 to Oct 12, the merge checks took 2,776 runs, about 189 machine-hours; on GitHub's 16-core runners that is about $446 a month for merge checks alone.
5. **From human message bus to commander.** Without arc, a person passes everything along by hand: runs the tests, tells one agent what another found, rebases, merges, retries, deploys. arc takes over that work: testing, coordination between agents, review rounds, merging, releasing. You spend your time on what only you can do: the high-level discussion, the code and the design, and what your users experience.
6. **Most important: infrastructure made for agents, managed by people.** An agent takes a task from the board, writes the code, gets it reviewed, answers the findings and lands it, without a person watching each step. Every command speaks `--json` and has fixed exit codes, so an agent can read what happened ([arc for coding agents](for-agents.md)). People set the rules, answer the questions agents ask, and decide what ships.

## What it is like: arc's own numbers

arc is built with arc. From Sep 7 to Nov 25, 2026, on arc's own repo:

- **2,544 PRs landed.** The median PR landed 11 minutes after it was opened.
- **A milestone in two days.** Multi-tenancy (milestone b/1867): 38 issues, from the first one opened to the last one fixed in 52 hours. The bridge gateway's first project: 31 issues in 52 hours.
- **Hands-free for 7 hours.** On Oct 13, once the scope was set, two agents worked for 7 hours without a word from anyone and finished a milestone: 20 issues, 19 PRs, every one reviewed and landed (milestone b/2544).
- **Through the night.** 323 PRs landed between midnight and 7 a.m. The longest unbroken run lasted 30.5 hours (Sep 26–27): a PR landed at least every two hours, 162 in all.
- **Releases on their own.** 87 nightly release runs and 357 deploys. A nightly that failed its checks stopped itself and published nothing.

## Two parts

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
- [Best practices — how we build arc with arc: dummy first, a whole-repo check, from an idea to issues, loops and supervision](best-practices.md)
- Finding model — identity, events, states

[Troubleshooting](troubleshooting.md)

## How arc reviews, in short

- **It reviews your code, in 9 languages:** Rust, Python, TS, JS, Go, Java, C, C++, Swift. arc picks the language support by the language of the repo it reviews.
- **It reports; it does not block on its own.** A finding does not fail your build. arc tells you what it found, and you (or the Fixer) decide what to do. On the pipeline, two things decide whether a PR lands: the reviewers' LGTM and your own `merge.yml`.
- **It comes with no model.** You choose the models (providers) in tars, and arc uses them.
- **It is not a style linter.** Formatting is the job of `clippy` / `ruff` / `eslint` / `gofmt`. arc looks for problems in what the code means and in how the codebase is put together.

arc reviews at two levels: **L4**, each file against its contracts ([review.md](review.md)), and **L5**, the whole repo for structural rot ([rot.md](rot.md)). Both run on your machine and on the pipeline.

---

*See also: `../usage.md` — exhaustive operations manual · `review_types` README — the finding model · [`../../README.md`](../../README.md) — quickstart.*
