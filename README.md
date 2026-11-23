# A.R.C. — infrastructure for agents

**From watching the screen to autopilot: why we built infrastructure for coding agents
instead of writing one more workflow.**

[Website](https://arc-site.hucao1.workers.dev/) · [Docs](https://arc-site.hucao1.workers.dev/docs/) · [中文文档](https://arc-site.hucao1.workers.dev/zh/docs/) · [Get started](#get-started) · [Report a problem](https://github.com/leocaolab/getarc/issues)

**arc is for you if** you run a one-person company or a tiny team, you have a few
machines of your own, GitHub's CI costs too much for what you build, you can no longer
read every line your agents write, and you want development to run on its own.

A one-person company or a small team cannot afford DevOps. GitHub's free CI is small
and slow, and pull requests, reviews and CI don't talk to agents. arc joins review,
merge, release and project management into one loop an agent can walk end to end.
Our own development went from watching the agent to handing it a task and walking away.

We are a very small team — small enough that everything gets weighed. Set up CI? Have
someone whose job is review? Keep a board for progress? Each one is right, and each
one costs people, machines and money, all three of which we have little of. This is
why we built arc, and what our own way of working became once it existed.

---

## Where small teams get stuck in the age of AI

### 1. The free CI/CD is not enough, and it doesn't talk to agents

GitHub Actions gives private repositories 2,000 free minutes a month, on a default
runner with 2 cores. One Rust build eats a good share of that, and the month runs out
fast. We did our own sums. The machines first:

| | Our server at home | GitHub's runner of the same size |
|---|---|---|
| CPU | 16 cores | 16 cores |
| Memory | 64 GB | 64 GB |
| Disk | 2 TB | 600 GB |
| Price | electricity | $0.042 a minute, on the Team plan; free minutes don't apply |
| Last build's output | kept | gone: every job starts on a fresh machine |

Rust compiles dozens of crates in parallel, so cores and memory decide the speed
directly. Its build cache is huge too: one working directory of ours holds 7–31 GB,
and with several agents working at once we regularly fill a 2 TB disk. GitHub's
runner has 600 GB and wipes it after every job.

Usage — merge checks alone, the build-and-test round each pull request runs on our
own machine before it enters `main`: in the 36 days from September 7 to October 12,
our repositories ran **2,776 rounds, about 189 machine-hours**. Deploys, nightly
releases, reviews, and the builds and tests agents run on their own machines are not
counted.

On GitHub's 16-core, 64 GB runner at $0.042 a minute, with each job rounded up to a
whole minute, those 2,776 rounds come to 12,739 minutes: 12,739 × $0.042 = **$535, or
about $446 a month — for merge checks alone.** That is a floor. GitHub rounds per job,
and one merge check is several jobs. More importantly, a GitHub runner is new for every
job, so nothing from the last build survives and every round compiles from scratch.
We reuse "warm" build directories, which takes the same check from 80–156 seconds cold
to 11 seconds. The cache GitHub lends is 10 GB per repository; one of our directories
does not fit.

What we actually pay is the electricity of a machine that was already running at home.

The minutes are not the main point. GitHub's pull requests, reviews and CI are built
for people: a person opens the PR, reads the comments, clicks merge. An agent can write
the code but cannot reach the rest of that chain. It doesn't know what the review said,
why CI is red, or when its change merged and shipped. With the chain open, the agent
owns only the writing; design, planning, merge and release still pass from hand to hand.

### 2. People spend their time dispatching, not designing

With the chain broken, the founder becomes a human bus: working out where the project
stands, handing each agent its task, resolving merge conflicts, tracking who holds which
machine and which disk. Design and software quality — where the attention belongs — get
squeezed out.

### 3. Agent code: hold it tight and it stalls, let go and it runs off

Agents are good at finding logic errors, but they have no taste for development. They
write spaghetti, put the architecture in the wrong place, and leave smells everywhere.
Watch every step and nothing moves fast; let go and the codebase rots in weeks. Human
line-by-line review costs too much — one person cannot keep up with several agents.

## But we already have the resources

The users we picture are like us: a few friends building a company remotely, their
machines joined into one network with Tailscale. Everyone has a decent machine at home —
strong CPU, large disk, idle most of the time.

So why not use those machines to give agents a development environment built for
agents? CI runs on your own hardware and is not billed by the minute; review, merge and
release leave records an agent can read; and agents and people get a channel to talk on.

## arc: infrastructure for agents

arc gives a one-person company or a small team the whole software development life
cycle, cheaper and faster:

- **Review pipeline**, designed for agents. A reviewer agent raises findings; the author
  agent answers and fixes them one by one, until the reviewer says LGTM on that exact
  commit.
- **Merge pipeline.** Your own `merge.yml` runs on your own machine; only a pull request
  that adds no new failure enters `main`.
- **Deploy and release pipeline.** Releases after merge, nightly builds and deploys, all
  on the record.
- **Project and test management.** The issue board is the source of truth for tasks.
  Test results are collected and analysed: which tests are slow, which are flaky, what a
  change should run.

arc keeps GitHub's shape, so you keep your habits. The issue board and GitHub Issues stay
in sync: import your existing issues once, and the board's changes flow back to GitHub.
Review and merge revolve around real pull requests on GitHub. The merge check and the
release read GitHub Actions–style workflow files in your repository — write
`.github/workflows/merge.yml` with jobs and `run` steps as usual; it simply runs on your
machine.

**arc bridge** connects all of this to Claude Code, Codex, agy and other coding agents,
and closes the loop. On the bridge, agents coordinate, keep an eye on each other and
discuss designs, and they talk to every pipeline: the review's verdict, the merge
result, the release status all come back to the agent that started it. Once the design
is settled, development can genuinely run on its own — like autopilot.

## The person in the loop matters more, not less

While the agents run, a person's job is not to watch every step but to step in where it
counts. **arc web** gives you a project board and dashboards for review, merge and
release, so you can leave the terminal, step back, and see the project from higher up.

Review is more than a fix loop between agents:

- **Reviewers assigned by risk.** Before a pull request gets its reviewers, arc measures
  its size, how many new definitions it adds and how far the change reaches. A simple bug
  fix goes to an agent; large new code across packages calls a person.
- **Highlights for the person.** When a person reviews, arc tells them what the change
  intends and where to look, instead of handing over a diff.

arc also manages the agents themselves — teams and division of work — and measures how
productive agents, conversations and people are, and how healthy the software is: where
it rots, where it repeats.

## No lock-in to any model

This matters a lot: **arc is model-agnostic.**

Claude Code is adding features like these itself — review, background tasks,
multi-agent collaboration. Using them is convenient. But ask yourself: if one day Claude
Code is unavailable — an outage, an exhausted quota, a change in price or policy — what
happens to your project? If your tasks, progress, review records and merge rules all
live inside one agent product, the moment it stops, your whole development line stops.

arc keeps all of it on your own machines: tasks on the issue board, every review verdict
and every change in the review service, merge rules in your repository's `merge.yml`.
The agents just come to work. When Claude Code stops, switch to Codex without a seam: it
reads the same board, the same reviews, the same merge queue, and carries on — and the
other way round. You can split work across model providers too: this role on one, that
role on another; switching is one line of configuration.

It also helps you keep some trade secrets. Your code, design discussions, review records
and the whole development process stay on your machines instead of accumulating inside
one agent product. You decide which work goes to which model, and the parts you'd rather
not hand out can go to a local model on your own hardware.

## Not a workflow — infrastructure

arc does not try to write an agentic workflow and squeeze agents into a flowchart we
drew. We build infrastructure for agents: give them a system they can read, write and
coordinate through, and let them do the rest. What matters most is that an agent can
**see**, **receive** and **speak**:

- **See.** Which step a pull request is at, why a merge check is red, who is doing what
  on the board, which machine's disk is nearly full — facts an agent reads directly, not
  pages drawn only for people.
- **Receive.** Review verdicts, merge results and release status arrive as messages to
  the agent that started them. No polling: when something has an outcome, the message
  comes. When a pull request lands on `main`, for example, the merge service writes to
  the author agent: which working directory still holds the branch, whether it is clean,
  whether the warm-directory pool has room — and the agent decides whether to remove it
  or keep it.
- **Speak.** Agents talk to each other and to people on the bridge: ask a question, hand
  something over, ask another agent for a second look.

An agent that can see, receive and speak is no longer a tool waiting to be fed
instructions. It is a member of the team.

The payoff went beyond what we expected. Agents began coordinating tasks on their own,
and resources too. Rust builds are hungry for disk — one worktree's build cache runs to
tens of gigabytes — and with every agent opening its own tree the disk never sufficed.
Then the agents learned to reuse the "warm trees" that were already compiled, taking one
from the worktree pool instead of each opening a new one and fighting for space. Nobody
wrote a "please reuse warm trees" workflow; the agents learned it from the facts arc
gave them.

**The stronger the model, the more initiative it can take through arc. A workflow limits
a strong model; infrastructure amplifies it.**

## If AI writes all the code, who reads it?

arc's built-in review rules — 24 rule sets, from the smells common in LLM-written code,
type design and architectural layering to each language's best practices — push for
readable, fluent code: a function that stays at one level of abstraction and reads like a
table of contents; one concept, one definition; names that say what a thing is.

Everyone asks: now that AI writes the code, who still reads it?

We ask back: **what if one day AI is not available?** The service stops, the quota runs
out, the next model is dumber, or there's a bug no AI manages to fix. At that moment the
person taking over the code is you. If it is a plate of spaghetti, you won't know where
to start — and it is your company.

Readability is not only for people, either. One line in our rules says it: *readability
is not decoration; it is insurance for correctness.* The next reader of this code may be
a person, or the next LLM sent to change it. Every jump between levels of abstraction
scatters the reader's attention, and where attention breaks is exactly where bugs and
hallucinations get in. The clearer the code, the more precisely the next agent changes it.

## From watching the screen to autopilot

With arc, the way we develop changed. Using an agent used to feel like day-trading: eyes
on it every moment, ready to step in. Now it is closer to autopilot. Given a task, Claude
Code often runs for two days straight — picking up tasks, writing code, passing review,
merging, releasing — and we show up only when it needs a person to decide.

This is measured, not felt. Every line we type to an agent stays in a log on our own
machine, so the human effort can be counted after the fact: the numerator is what people
typed to agents (prompts), the denominator is commits landed on `main`. From watching
every day to now took one month:

| Week | People's prompts | Commits landed | PRs landed | Prompts per commit |
|---|---:|---:|---:|---:|
| 08-31 (before the merge pipeline; watched daily) | 288 | 39 | 1 | 7.4 |
| 09-07 (the week it went live) | 1,116 | 454 | 132 | 2.5 |
| 09-14 | 1,660 | 684 | 256 | 2.4 |
| 09-21 | 1,839 | 709 | 261 | 2.6 |
| 09-28 | 1,471 | 593 | 246 | 2.5 |
| 10-05 | 2,084 | 666 | 200 | 3.1 |

**To land one commit, people went from about 7 prompts to about 2.5 — two thirds fewer —
while weekly output grew from 39 commits to around 600, about 15×.** The total number of
prompts went up, but it is spread over far more output.

The curve doesn't go straight down. In the first week of October it rose back to 3.1 per
commit: that week we were doing a large design and naming overhaul, where many things
needed a person to decide — exactly where a person should be.

Two notes on the numbers. "Prompts" includes one-word replies like "continue" and "ok",
so it is an upper bound on human effort and the true drop can only be larger. The week
before launch had only 4 active days, a small sample; over a longer window (from July 20),
the pre-launch figure is 4 prompts per commit, a drop of about 40%.

---

## Get started

Two steps, each useful on its own:

1. **On the machine you code on** — the `arc` CLI. Your agent's branch is reviewed, the
   fixer answers the findings, you push. No server. Ten minutes.
2. **On one of your other machines** — the pipeline: review service, merge machine,
   releaser, board and arc bridge. Your agents submit, arc reviews and lands their pull
   requests on your hardware, and the results come back to them. This is what lets
   development run on its own. The edition names it "team", but one person with two
   machines is the case we run ourselves.

### Step 1 — the CLI

#### Let your coding agent set it up

Open Claude Code, Codex or another coding agent in the repository you want reviewed, and
paste:

<!-- The one source of this prompt: the arc site's homepage and the arc user guide copy it word for word. -->
```text
Install the arc-setup skill. If you're in Claude Code, run `claude plugin marketplace add leocaolab/getarc`, then `claude plugin install arc@getarc`. If you're in another agent, run `npx skills add leocaolab/getarc --skill arc-setup` and select your agent. Use one installation method. You can read the skill directly at https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md (raw: https://raw.githubusercontent.com/leocaolab/getarc/main/skills/arc-setup/SKILL.md). Then use the arc-setup skill to install and configure arc in this repository.
```

The [arc-setup skill](skills/arc-setup/SKILL.md) installs the binary, picks the models —
with `claude` on your PATH it uses your own Claude Code login, so **no API key** — runs
`arc init` and a smoke check. It asks once before writing anything outside the
repository, and stops with the real error if a step fails.

#### Or by hand

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh
```

The installer checks the build against the release's `SHA256SUMS` and puts `arc` in
`~/.local/bin`; it asks nothing and never runs `sudo`. Then name your models in
`~/.tars/config.toml` — signed in to Claude Code, this is all of it:

```toml
[providers.claude_critic]
type = "claude_cli"            # uses your `claude login`; no key
default_model = "opus"

[providers.claude_fixer]
type = "claude_cli"
default_model = "sonnet"
tools = "default"              # the fixer edits files
timeout_secs = 900
```

Any other model works too — `anthropic`, `openai`, `gemini`, `bedrock`, `codex_cli`,
local servers ([all types](https://arc-site.hucao1.workers.dev/docs/start/configuration/)).
Then, in the repository, on a feature branch:

```bash
arc init           # map the reviewer and the fixer to your models
arc local-review   # review this branch's change; edits nothing
arc fix            # answer every finding, one commit per fix, until LGTM
git push           # you push
```

Run from a coding agent, arc needs nothing else. Run from a plain terminal, it names you
by your GitHub CLI login: install [`gh`](https://cli.github.com) and run `gh auth login`
once. The team edition's `arc submit` always needs it.

#### Skills

This repository is a plugin marketplace with 24 skills: the ones that drive arc, and the
review methods our own team works by.

```bash
# Claude Code: all of them, as one plugin
claude plugin marketplace add leocaolab/getarc
claude plugin install arc@getarc

# Codex, Cursor, Gemini CLI and other agents: pick the ones you want
npx skills add leocaolab/getarc
```

| Group | Skills | Needs `arc` |
|---|---|---|
| Set up and look after arc | [`arc-setup`](skills/arc-setup/SKILL.md) (start here), [`maintain`](skills/maintain/SKILL.md) | yes |
| Drive arc | [`review`](skills/review/SKILL.md), [`fix`](skills/fix/SKILL.md), [`rot`](skills/rot/SKILL.md), [`automate`](skills/automate/SKILL.md) | yes |
| Review code yourself | [`taste-check`](skills/taste-check/SKILL.md), [`smell-check`](skills/smell-check/SKILL.md), [`error-check`](skills/error-check/SKILL.md), [`test-check`](skills/test-check/SKILL.md), [`name-check`](skills/name-check/SKILL.md) | no |
| Write it right the first time | [`coding-principles`](skills/coding-principles/SKILL.md), [`coding-convention`](skills/coding-convention/SKILL.md), [`comment-clean`](skills/comment-clean/SKILL.md), [`type-naming`](skills/type-naming/SKILL.md) | no |
| Per language | `shift-left-` + `rust`, `python`, `typescript`, `javascript`, `go`, `java`, `c`, `cpp`, `swift` | no |

The skills that need no binary cite the rule sets in [`rubrics/`](rubrics/), the same
files arc's reviewer reads.

### Step 2 — the pipeline, on your own machine

Pick an always-on Linux x86_64 machine with systemd, plenty of cores and disk (macOS runs
the services, but has no systemd to deploy or restart them). Then follow
[Set up the pipeline](https://arc-site.hucao1.workers.dev/docs/team/onboarding/):

1. unpack `arc-suite-linux-x64.tar.gz` there and start the services;
2. connect your repository and write its `.github/workflows/merge.yml` — the same
   jobs-and-`run`-steps shape you already know ([the merge gate](https://arc-site.hucao1.workers.dev/docs/team/merge-gate/));
3. point each coding machine at it with `~/.arc/client.toml`, and connect your agents to
   [arc bridge](https://arc-site.hucao1.workers.dev/docs/team/bridge/);
4. from then on an agent runs `arc submit`: the branch is reviewed, and lands on `main`
   only after the reviewers say LGTM and `merge.yml` shows no new failure. Label a pull
   request `arc-hold` to keep it from landing.

One machine serves several repositories; add them one at a time.

### What a release holds

| File | What it is | Platform |
|---|---|---|
| `install.sh` | the one-line installer | macOS arm64, Linux x86_64 |
| `arc-darwin-arm64.tar.gz` | the `arc` CLI | macOS, Apple Silicon |
| `arc-linux-x64.tar.gz` | the `arc` CLI, statically linked: any distribution | Linux x86_64 |
| `arc-suite-darwin-arm64.tar.gz` | the team edition's server suite | macOS, Apple Silicon |
| `arc-suite-linux-x64.tar.gz` | the team edition's server suite; needs glibc ≥ 2.43, and `arc-web` / `arc-tap` need libstdc++ from GCC 13 | Linux x86_64 |
| `arc-skills.tar.gz` | the same skills as the plugin, for `claude --plugin-dir` | any |
| `arc-vscode.vsix` | the VS Code extension: findings by file, the reviewer↔fixer debate per finding | any |
| `SHA256SUMS` | checksums of the files above | — |

No other platform has a build, an Intel Mac included —
[ask for one](https://github.com/leocaolab/getarc/issues).

## License

Free for any use: personal, commercial, internal. You may not redistribute the binaries
(link to this repository instead), reverse-engineer or decompile them. The source is not
public. Full text: [LICENSE](LICENSE).

## Questions and bugs

[Open an issue](https://github.com/leocaolab/getarc/issues), with `arc --version` and
your OS.
