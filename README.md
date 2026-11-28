# A.R.C. — infrastructure for agents

## Agent setup

Open Claude Code, Codex, or another coding agent inside the repository you want to use, and paste:

<!-- The one source of this prompt: the arc site's homepage and the arc user guide copy it word for word. -->
```text
Install the arc-setup skill. If you're in Claude Code, run `claude plugin marketplace add leocaolab/getarc`, then `claude plugin install arc@getarc`. If you're in another agent, run `npx skills add leocaolab/getarc --skill arc-setup` and select your agent. Use one installation method. You can read the skill directly at https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md (raw: https://raw.githubusercontent.com/leocaolab/getarc/main/skills/arc-setup/SKILL.md). Then use the arc-setup skill to install and configure arc in this repository.
```

The [arc-setup skill](skills/arc-setup/SKILL.md) installs the binary, configures your models (if `claude` is on your PATH, it reuses your Claude Code login with **no API key** needed), runs `arc init`, and verifies everything with a smoke check. It asks before writing anything outside your repo and stops with the exact error if anything fails.

---

**From watching the screen to autopilot: why we built infrastructure for coding agents instead of writing one more workflow.**

**arc is for you if** you run a solo company or a small team, you have a few machines of your own, GitHub Actions costs too much or runs too slow for what you build, you can no longer read every line your agents write, and you want development to run on its own.

A solo founder or small team cannot afford DevOps. GitHub's free CI is small and slow, and pull requests, reviews, and CI don't talk to coding agents. **arc** connects code review, merge checks, releases, and project tracking into one loop an agent can run end to end. Our own workflow went from watching the agent step by step to handing it a task and walking away.

We are a very small team — small enough that every piece of process has to earn its keep. Set up CI? Dedicate someone to code review? Maintain a task board? Every one of those is good practice, and every one costs people, machines, and money — all three of which we have little of. That is why we built arc, and how our own way of working changed once it existed.

---

## Where small teams get stuck in the age of AI

### 1. Free CI/CD isn't enough, and it doesn't talk to agents

GitHub Actions gives private repositories 2,000 free minutes a month on a default 2-core runner. One Rust build eats a large chunk of that, and the allowance runs out fast. We did the math on our own usage. First, the hardware:

| | Our home server | GitHub's equivalent runner |
|---|---|---|
| CPU | 16 cores | 16 cores |
| Memory | 64 GB | 64 GB |
| Disk | 2 TB | 600 GB |
| Price | electricity | $0.042/min on the Team plan (free minutes don't apply) |
| Build cache | kept between runs | wiped: every job starts on a fresh VM |

Rust compiles dozens of crates in parallel, so CPU cores and RAM directly determine build speed. Its build cache is huge too: a single working directory in our repo holds 7–31 GB, and with several agents working concurrently we regularly fill a 2 TB disk. GitHub's runner only has 600 GB and wipes it after every job.

Now look at actual usage — just for merge checks (the build-and-test run each pull request executes on our machine before landing on `main`). In the 36 days from September 7 to October 12, our repositories ran **2,776 merge-check rounds, totaling ~189 machine-hours**. That doesn't even count deploys, nightly releases, code reviews, or the builds agents run locally.

On GitHub's 16-core, 64 GB runner at $0.042/minute (with each job rounded up to the nearest whole minute), those 2,776 rounds come to 12,739 minutes: **12,739 × $0.042 = $535, or about $446/month — for merge checks alone.** And that is a floor: GitHub rounds per job, and one merge check spans multiple jobs. More importantly, a fresh GitHub runner starts from zero every time. Because we reuse warm build directories locally, the exact same check drops from 80–156 seconds (cold) to **11 seconds**. GitHub's 10 GB per-repo cache wouldn't even fit one of our build directories.

What we actually pay is the electricity for a machine that was already running at home.

Cost isn't even the main issue. GitHub's PRs, reviews, and CI are built for humans: a person opens the PR, reads the comments, and clicks merge. An agent can write code, but it is locked out of the rest of that loop. It doesn't know what the reviewer flagged, why CI turned red, or when its change landed and shipped. With that loop broken, agents only handle the coding — planning, review, merging, and releasing still fall back on you.

### 2. You spend your time dispatching instead of designing

When the loop is broken, the founder turns into a human router: figuring out where the project stands, handing each agent its next task, resolving merge conflicts, and tracking who owns which machine and disk. Architecture and software quality — the things that actually need your attention — get squeezed out.

### 3. Agent code: micromanage it and it stalls, let go and it rots

Agents are good at catching local logic bugs, but they have no taste for system design. They write spaghetti code, put logic in the wrong layer, and leave code smells everywhere. Watch every step and nothing moves fast; look away and the codebase rots in weeks. Human line-by-line review doesn't scale either — one developer cannot keep up with several agents.

## You already have the hardware

The users we picture are like us: a small team or solo builder with machines connected over Tailscale. Everyone has a capable machine at home or in the office — strong CPU, plenty of disk, sitting idle most of the day.

So why not use those machines to give agents a development environment built for them? CI runs on your own hardware with no per-minute billing; review, merge, and release leave structured records an agent can read; and agents and humans get a shared channel to coordinate.

## arc: infrastructure for agents

arc gives a solo founder or small team the full software development lifecycle, faster and without per-minute CI bills:

- **Review pipeline**, designed for agents. A reviewer agent raises specific findings; the fixer agent answers and resolves them one by one until the reviewer signs off (LGTM) on that exact commit.
- **Merge pipeline.** Your own `merge.yml` runs on your own machine; a pull request only lands on `main` if it introduces no new failures.
- **Deploy and release pipeline.** Post-merge releases, nightly builds, and deploys — all tracked on the record.
- **Project and test tracking.** An issue board serves as the single source of truth for tasks. Test results are collected and analyzed automatically: which tests are slow, which are flaky, and which tests a given change needs to run.

arc keeps GitHub's familiar shape, so you don't have to change your habits. The issue board stays in sync with GitHub Issues (import once, and board updates flow back to GitHub). Reviews and merges revolve around real GitHub pull requests. Merge checks and releases read standard GitHub Actions-style workflow files in your repo — write `.github/workflows/merge.yml` with `jobs` and `run` steps as usual; it simply executes on your own machine.

**arc bridge** ties all of this to Claude Code, Codex, agy, and other coding agents, closing the loop. Over the bridge, agents coordinate, check on each other, and discuss designs, while receiving results from every pipeline: review verdicts, merge outcomes, and release status all route straight back to the agent that started the work. Once a design is settled, development can genuinely run on autopilot.

## The human in the loop matters more, not less

While agents run, your job isn't to watch every step — it's to step in where judgment counts. **arc web** gives you a project board and dashboards for review, merge, and release so you can step back from the terminal and see the whole project at a glance.

Review is more than an automated fix loop:

- **Risk-based reviewer assignment.** Before assigning reviewers, arc measures a PR's size, new definitions, and how many packages it touches. A small bug fix goes to an agent; a large cross-package change calls in a human.
- **Focused highlights for human reviewers.** When you do step in to review, arc summarizes what the change is trying to do and where to look, instead of dumping a raw diff in your lap.

arc also tracks agent teams, task division, throughput, and codebase health — showing where the code is rotting or repeating itself.

## No lock-in to any model

This matters a lot: **arc is model-agnostic.**

Coding tools like Claude Code are adding their own built-in review, background tasks, and multi-agent features. They're convenient — until you ask: what happens if one day Claude Code is unavailable due to an outage, rate limits, or a pricing change? If your tasks, progress, review history, and merge rules all live inside one vendor's product, the moment it goes down, your entire pipeline stops.

arc keeps all of that state on your own machines: tasks on your issue board, every review verdict and round in your review service, and merge rules in your repo's `merge.yml`. Coding agents simply clock in. If Claude Code hits a limit, switch to Codex seamlessly: it reads the same board, the same review findings, and the same merge queue, and picks up right where things left off (and vice versa). You can also split roles across providers — reviewer on one model, fixer on another — and swap them with a one-line config change.

It also keeps sensitive work in-house. Your code, design discussions, and review records stay on your hardware instead of accumulating inside a single vendor's cloud. You decide which tasks go to which model, and anything you'd rather keep private can run on a local model on your own GPU.

## Infrastructure, not a rigid workflow

arc doesn't try to force agents into a hardcoded flowchart. We build infrastructure for agents: give them a system they can read, write, and coordinate through, and let them figure out the rest. What matters most is that an agent can **see**, **receive**, and **speak**:

- **See.** Which step a PR is on, why a merge check failed, who is working on what, which machine's disk is filling up — structured facts an agent can read directly, not dashboards built only for human eyes.
- **Receive.** Review verdicts, merge outcomes, and release status arrive as push notifications to the agent that triggered them. No polling: when a job finishes, the message arrives. For example, when a PR lands on `main`, the merge service notifies the author agent which worktree still holds that branch, whether it's clean, and whether the warm-worktree pool has room — letting the agent decide whether to keep or clean it up.
- **Speak.** Agents talk to each other and to humans over the bridge: asking questions, handing off tasks, or requesting a second pair of eyes.

An agent that can see, receive, and speak is no longer a tool waiting to be fed instructions. It works like a member of the team.

The payoff surprised even us. Agents started coordinating tasks and shared resources on their own. Rust builds eat disk fast — a single worktree's build cache can hit tens of gigabytes — and with every agent creating its own worktree, we kept running out of space. Once agents could see the pool state, they began reusing pre-compiled "warm" worktrees instead of each spinning up a fresh one and fighting over disk. Nobody wrote a "please reuse warm worktrees" rule; the agents figured it out from the facts arc exposed.

**The stronger the model, the more initiative it takes through arc. Rigid workflows cap a strong model; good infrastructure amplifies it.**

## If AI writes all the code, who reads it?

arc ships with 24 built-in review rule sets — covering common LLM-generated code smells, type design, architectural layering, and language-specific best practices. They push for readable, maintainable code: functions that stay at one level of abstraction, one definition per concept, and names that say what things are.

People often ask: now that AI writes the code, does readability even matter?

We ask back: **what happens on the day AI isn't available?** The service goes down, your quota runs out, a model regresses, or a bug stumps every model. At that moment, the person stepping in to fix the code is you. If the codebase is a bowl of spaghetti, you won't know where to start — and it's your company.

Readability isn't just for humans, either. As one of our rules puts it: *readability is not decoration; it is insurance for correctness.* The next reader might be you, or it might be the next LLM asked to modify that file. Jumping across abstraction levels scatters attention, and wherever attention breaks, bugs and hallucinations slip in. Cleaner code leads directly to more accurate edits from the next agent.

## What the review catches

Here is a real run on a three-function Python file written by an agent, reviewed via Claude Code:

```text
$ arc local-review
- finding F-3 — calc.py:14 [l4_contracts::pure-function-mutates-input]
  reviewer: `median` advertises itself as a read-only statistic yet `xs.sort()`
  reorders the caller's list in place. A caller computing `median(records)` silently
  loses its own ordering. Use `ys = sorted(xs)` and index `ys`.
    13 | def median(xs):
  > 14 |     xs.sort()

- finding F-4 — calc.py:15 [structural::free-review]
  reviewer: For an even-length input this does not return the median.
  `median([1, 2, 3, 4])` returns 3, while the median is 2.5 …

[A.R.C.] 5 finding(s) open — fix them in this working tree and run `arc local-review` again, or run `arc fix`
```

![Two panels. Left, "Agent's review (unsystematic)": a robot sprays a codebase wall with a machine gun, leaving scattered holes labelled MISSING BUG, SECURITY HOLE, LOGIC ERROR MISSED, MAJOR OMISSION. Right, "Our systematic review (thorough)": a code-review engine and robotic rollers lay uniform coverage over the wall.](agent-vs-arc.png)

Ask a generic agent to "review this" and you get buckshot: it looks at one snippet at a time, follows no fixed rules, and forgets what it checked last round. A few shots land, bugs slip through the gaps, and running it again hits completely different spots. arc reviews systematically:

- **Explicit rule sets (rubrics).** Each rule targets one specific hazard, so one code smell maps cleanly to one finding.
- **Deterministic checks first.** Static detectors run before the LLM, so the model verifies concrete signals instead of guessing from scratch.
- **Tracked findings.** Every finding has a status and an append-only history across review rounds. Each one gets resolved — fixed or marked won't-fix — instead of scrolling out of sight.

Beyond individual diffs, `arc rot` scans the entire repository for structural decay — god-modules, idioms duplicated across three or more files, one concept modeled as multiple conflicting types, inverted dependencies — and outputs concrete refactoring suggestions (never a blind auto-refactor button). Running `arc rot --no-judge` runs only the deterministic checks, fast and cheap enough to track in CI.

## From watching the screen to autopilot

arc changed how we ship software. Working with an agent used to feel like day-trading: eyes glued to the terminal, ready to intervene at any second. Now it feels like autopilot. Given a task, Claude Code routinely runs for two days straight — picking up issues, writing code, passing review, merging, and releasing — and we only step in when a real design decision is needed.

We measured this rather than guessing. Every prompt we type stays logged locally, so we can divide human prompts by commits landed on `main`. Going from daily babysitting to autopilot took one month:

| Week | Human prompts | Commits landed | PRs landed | Prompts per commit |
|---|---:|---:|---:|---:|
| 08-31 (before merge pipeline; watched daily) | 288 | 39 | 1 | 7.4 |
| 09-07 (launch week) | 1,116 | 454 | 132 | 2.5 |
| 09-14 | 1,660 | 684 | 256 | 2.4 |
| 09-21 | 1,839 | 709 | 261 | 2.6 |
| 09-28 | 1,471 | 593 | 246 | 2.5 |
| 10-05 | 2,084 | 666 | 200 | 3.1 |

**Human effort per landed commit dropped by two-thirds — from ~7 prompts to ~2.5 — while weekly output grew 15×, from 39 commits to ~600.** Total prompts went up simply because we were shipping far more work.

The curve isn't strictly monotonic. In the first week of October it ticked up to 3.1 prompts per commit: that week we did a major architecture and naming overhaul where humans *should* be making the calls.

Two caveats on the numbers: "Prompts" counts one-word nudges like `"continue"` and `"ok"`, so it is an upper bound on human effort — the true drop is likely larger. Also, the pre-launch week only had 4 active days; over a longer baseline window (starting July 20), the pre-launch average was 4 prompts per commit, making the drop ~40%.

---

## Get started

arc has two parts, and installing arc means installing both ([install guide](docs/user-guide/install.md)):

1. **The `arc` CLI, on every machine where people or agents write code** — reviews your branch, runs an automated fixer over the findings, and submits your PRs.
2. **The server suite, on one machine you own** — the pipeline: review service, merge runner, releaser, issue board, and `arc bridge`. Agents submit PRs, arc reviews and merges them on your hardware, and results route back to the agents. You can also write code on that same machine; the two parts only need to reach each other over the network.

### Step 1 — the CLI

#### Option A: Let your coding agent set it up

Paste the prompt in [Agent setup](#agent-setup) at the top of this page.

#### Option B: Install manually

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh
```

The installer verifies the binary against `SHA256SUMS` and places `arc` in `~/.local/bin` (no prompts, no `sudo`).

Next, define your model providers in `~/.tars/config.toml` (the shared provider config file arc reads). If you're already signed in to Claude Code, this is all you need:

```toml
[providers.claude_critic]
type = "claude_cli"            # reuses your `claude login`; no API key required
default_model = "opus"

[providers.claude_fixer]
type = "claude_cli"
default_model = "sonnet"
tools = "default"              # lets the fixer edit files
timeout_secs = 900
```

Other providers work too — `anthropic`, `openai`, `gemini`, `bedrock`, `codex_cli`, or local servers ([full list](docs/user-guide/configuration.md)).

Then, inside your repository on a feature branch:

```bash
arc init           # map reviewer and fixer roles to your configured providers
arc local-review   # review this branch's changes (read-only)
arc fix            # resolve findings one commit per fix until LGTM
git push           # push when ready
```

When run inside a coding agent session, arc needs no extra identity setup. When run from a plain terminal, it identifies you via GitHub CLI — install [`gh`](https://cli.github.com) and run `gh auth login` once (`arc submit` always requires `gh`).

#### Skills

This repository is also a plugin marketplace containing 24 skills: workflows that drive `arc`, plus the coding and review standards our own team uses.

```bash
# Claude Code: install the full plugin
claude plugin marketplace add leocaolab/getarc
claude plugin install arc@getarc

# Codex, Cursor, Gemini CLI, and other agents: pick individual skills
npx skills add leocaolab/getarc
```

| Category | Skills | Requires `arc` |
|---|---|---|
| Setup & maintenance | [`arc-setup`](skills/arc-setup/SKILL.md) (start here), [`maintain`](skills/maintain/SKILL.md) | yes |
| Run arc | [`review`](skills/review/SKILL.md), [`fix`](skills/fix/SKILL.md), [`rot`](skills/rot/SKILL.md), [`automate`](skills/automate/SKILL.md) | yes |
| Write clean code upfront | [`coding-principles`](skills/coding-principles/SKILL.md), [`coding-convention`](skills/coding-convention/SKILL.md), [`comment-clean`](skills/comment-clean/SKILL.md), [`type-naming`](skills/type-naming/SKILL.md) | no |
| Language-specific guides | `shift-left-` + `rust`, `python`, `typescript`, `javascript`, `go`, `java`, `c`, `cpp`, `swift` | no |

The standalone skills cite the same rule sets in [`rubrics/`](rubrics/) that arc's reviewer uses.

### Step 2 — the pipeline, on your own machine

Pick an always-on Linux x86_64 machine with `systemd`, plenty of CPU cores, and ample disk (macOS can run the services too, but lacks `systemd` for managed restarts). Then follow [Set up the pipeline](docs/user-guide/onboarding.md):

1. Unpack `arc-suite-linux-x64.tar.gz` and start the services.
2. Register your repository and add `.github/workflows/merge.yml` using standard `jobs` and `run` steps ([merge gate docs](docs/user-guide/merge-gate.md)).
3. Point each dev machine at your server via `~/.arc/client.toml` and connect your agents to [arc bridge](docs/user-guide/bridge.md).
4. From then on, agents run `arc submit`: the branch gets reviewed and only lands on `main` after reviewers approve (LGTM) and `merge.yml` introduces no new failures. Add the `arc-hold` label to pause a PR from landing.

One server can host multiple repositories; add them one at a time.

### Release artifacts

| File | Description | Platform |
|---|---|---|
| `install.sh` | One-line CLI installer | macOS arm64, Linux x86_64 |
| `arc-darwin-arm64.tar.gz` | `arc` CLI binary | macOS (Apple Silicon) |
| `arc-linux-x64.tar.gz` | `arc` CLI binary (statically linked, runs on any distro) | Linux x86_64 |
| `arc-suite-darwin-arm64.tar.gz` | Server suite | macOS (Apple Silicon) |
| `arc-suite-linux-x64.tar.gz` | Server suite (requires glibc ≥ 2.43; `arc-web` / `arc-tap` require libstdc++ from GCC 13) | Linux x86_64 |
| `arc-skills.tar.gz` | Skills bundle for `claude --plugin-dir` | any |
| `arc-vscode.vsix` | VS Code extension (browse findings by file and view reviewer–fixer debates) | any |
| `SHA256SUMS` | Checksums for all release files | — |

No other platforms (including Intel Macs) have prebuilt binaries yet — [open an issue](https://github.com/leocaolab/getarc/issues) if you need one.

## License

Free for personal, commercial, and internal use. You may not redistribute the binaries (link to this repository instead), reverse-engineer, or decompile them. The source code is not public. See [LICENSE](LICENSE) for the full text.

## Questions and bugs

[Open an issue](https://github.com/leocaolab/getarc/issues) and include `arc --version` along with your OS.
