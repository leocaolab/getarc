# Merge — how a PR lands, and writing `merge.yml`

On the pipeline, nobody merges by hand. The **merge machine** (`arc-server`) does it, one PR at a time:

1. It takes a PR whose pass points at its current head ([Review on the pipeline](pipeline-review.md)).
2. It merges the PR onto the latest commit of the target branch.
3. It runs your `.github/workflows/merge.yml` before and after the merge.
4. It lands the PR if the merge adds no new failure.

## How a PR lands

- **Which PRs are taken.** Only a PR whose pass (`refs/arc/pass/<pr>`) points at its current head. A new push needs a new LGTM. A PR labelled **`arc-hold`** is never taken, whatever pass it has.
- **Order.** `arc submit --after <N>` lands a change only after PR N has landed. While N is open, the change waits, however long that takes. If N is closed, or lands a different version than the one this branch carries, the change is not run and you are told why.
- **The check.** The gate runs on the target's latest commit and again on the merged tree. The PR lands if the second run shows no failure the first run did not ([details below](#when-it-runs)).
- **What you hear back.** Each round's report is written to the git ref `refs/arc/reports/<cl>`. With the bridge on, it is also posted to the PR's channel:
  - **Sent back:** the message interrupts your session and includes the failing tests' own output.
  - **Landed:** the message says the PR `landed as <sha>`. It also says how the PR ended (landed, discarded, already in) and which worktrees on your machine still have that branch checked out, whether each is clean and whether someone is working in it. arc never touches those worktrees; you decide whether to remove them.
  - Each landing on main is also one line in the `landings` channel ([Team up](bridge.md)).
- **Dropping a PR.** `arc submit --abandon "<why>"` ends the PR's review with your reason and closes it. Do not close a PR by hand.
- **Watching.** The board's **Merge** tab shows the queue, the round running now, each attempt and each gate step's log.

## Architecture rules: a step of the gate

`arc archcheck` runs in the merge gate, not in the review on your machine. Add a `merge.yml` step that runs `arc archcheck --base <merge base>`. It checks the merged tree against the repo's written architecture rules (`.arc/archcheck.toml`, with waivers listed in `.arc/arch_waivers.txt`). It exits 7 when a rule is broken, a waiver is added, or the config is loosened against `--base`; the round treats that as a new failure, like any other step.

## The gate file

The check that decides whether a PR may land is one file in your repo: **`.github/workflows/merge.yml`**. The rest of this page covers when it runs, which copy of it runs, what you can write in it, and how its result is read.

The checks an author runs before submitting are in `presubmit.toml` ([Configuration](configuration.md)). The merge machine reads only `merge.yml`.

## What the file is

`merge.yml` uses GitHub Actions syntax, but GitHub does not run it. The merge machine runs it, in its own clone of the repo, as plain shell. Write the trigger so GitHub never starts it:

```yaml ignore: the `on:` lines of a workflow, an excerpt
on:
  workflow_dispatch: {}
```

The path is fixed: `.github/workflows/merge.yml`, from the repo root. No setting changes it.

All jobs in the file run one after another, **in the order they are written**, as one list of steps. `needs:`, `runs-on:` and `on:` are ignored.

## When it runs

1. A PR enters the merge queue when its **pass** points at its current head. The review service writes the pass when the reviewers your repo's routes name have said LGTM ([Configuration](configuration.md#arcmachinetoml--the-pipeline-machine)). A new push is a new head and needs a new LGTM. A PR labelled `arc-hold` is skipped even with a pass ([`arc-hold`](working-on-the-board.md#keeping-a-pr-from-landing-arc-hold)).
2. The merge machine takes one PR at a time. For that PR it:
   - fetches the target branch and checks out its latest commit — the **base**;
   - reads `merge.yml` and `.arc/gate.toml` from the base;
   - runs the gate on the base (or reuses an earlier result for the same base);
   - merges the PR onto the base;
   - runs the gate again on the merged tree — using the base's gate, or the PR's own gate if the PR changed it ([Which copy runs](#which-copy-runs));
   - **lands the merge if the second run shows no failure the first run did not.**
3. The result is written to `refs/arc/reports/<cl>`. With the chat bridge on, it is also posted to the PR's channel.

Because the result compares two runs, a target branch that is already red does not block everyone: a PR lands as long as it adds no *new* failure.

By default (`[tenant.gate] rerun = "once"`), a new failure is run a second time on the same commit before the PR is sent back, so a one-off flaky test does not send it back.

A head that was sent back is not tested again on the same base. It waits for a new push, or for the target branch to move. If you are sure it was a false alarm (the machine was overloaded, a test failed twice by chance), there is no command to retest the same head on the same base: push a new head with `arc submit --pr <N>`. It is reviewed again and queued after its LGTM.

## Which copy runs

Each tree is judged by its own gate: the base by the base's, the merged tree by the one it contains. The **gate definition** is `merge.yml`, `.arc/gate.toml`, and every file that the base's `.arc/gate.toml` lists:

```toml ignore: .arc/gate.toml, read by arc-server's merger, whose own tests pin its shape
# .arc/gate.toml — the scripts and config the gate runs, as globs
definition = ["dev/check.sh", "dev/gate/**"]
```

This list is read from the base only, so a PR that edits `.arc/gate.toml` is editing the gate.

- **The PR does not touch the gate definition** → the base's gate runs on both trees.
- **The PR only adds steps after the last step of `merge.yml`, and leaves every other gate file byte for byte unchanged** → the merged tree runs the PR's `merge.yml`. If it is green, the PR lands without anyone approving it; anything else needs approval.
- **Any other change** (a step changed, removed or moved, a listed script edited, a file added or removed) → the PR's own gate runs only after a person approves this head.

To ask for approval, the merge machine opens a question on the first issue the PR's title names (`… (b/123)`). The question names the PR and its head and has two options: `approve` and `decline`. Only `approve` lets it through. Until someone answers, the round ends with the verdict *cannot say* and names the question; an answer on that issue puts the PR back in the queue. A new push is a new head and gets a new question: an approval does not carry over, and nothing is written into your commits.

A PR whose title names no issue, or whose target branch has also changed the gate since the PR branched off, gets no question: name an issue in the title, or rebase.

This needs an issue board (`arc-bridge` on the repo's pipeline machine). Without one, a PR that changes the gate ends *cannot say*, saying the board is missing, and waits; once the server has a board, `arc submit` puts it back in the queue. If the board is there but does not answer, nothing is decided and the PR is tried again.

If the target branch's own gate cannot be read (no `merge.yml`, a file that does not parse, a step this machine cannot run), every PR is held the same way: each ends *cannot say* once and waits, instead of being retried on every poll. Land the fix — it is judged by its own gate once a person approves it — then run `arc submit` for the other PRs again.

## How a failure is read

Steps run in order. **The gate stops at the first step that exits non-zero**; later steps do not run.

arc then reads that step's output and picks out the failures it names. It understands the console output of `rustc` / `cargo build`, `cargo test`, `cargo nextest`, `vitest`, `tsc`, Playwright, `pytest`, and lint tools. The result is based on those named failures, not on exit codes.

- **Failures named, none of them new** → the PR lands.
- **New failures** → the PR is sent back, with the failing output in the report.
- **The step failed but arc cannot read any failure in its output** → the round ends with the verdict *cannot say*, and a person has to look. Use test runners arc can read, and let their normal output reach the console.
- **The machine could not run the step** (it did not start, ran longer than `[tenant.gate] timeout_secs`, or ran out of disk or memory) → no PR is blamed; the queue waits for the machine.

Make sure main is green on the merge machine before you start. If a step fails on the base for a reason that is not a test — a missing tool, a missing credential — every PR fails the same way at the same step. A PR that fixes the gate itself is judged by its own gate once a person approves it, and lands if that gate is green.

## What arc runs in a workflow file

arc supports part of the GitHub Actions format, and tells you when it meets something it does not support. The same rules apply to the merge gate, to deploy jobs and to `arc workflow`.

**Supported:**

| Key | Where | What arc does |
|---|---|---|
| `jobs.<id>.steps` | job | the steps, in order |
| `run:` | step | the command; run with `sh -c` at the repo root |
| `name:` | step | the step's name in reports (unnamed: `step 3`) |
| `env:` | workflow, job, step | exported before the command; step overrides job, job overrides workflow |
| `working-directory:` | step | `cd` into it first |
| `defaults.run.working-directory` | workflow, job | the directory for steps that set none |
| `if:` | step | evaluated before the run (below) |
| `strategy.matrix.include` | job | the job's steps run once per entry |
| `uses:` | step | only the few actions listed below |
| `phase:` | step | arc's own key: `build`, `test`, `lint` or `deploy`. It only decides how a failure is recorded for a deploy or release. Any other value makes arc refuse the file. |

Other keys (`runs-on`, `permissions`, `timeout-minutes`, `needs`, `shell`, `continue-on-error`, …) are ignored.

**Each step's command** is your `run:` text, preceded by `set -e`, the `env:` exports and the `cd`. Because of `set -e`, a multi-line `run:` stops at its first failing line, as on GitHub. Two differences from GitHub: `pipefail` is not set, so in `npx vitest run | tee log` the step's status is `tee`'s; and the shell is `sh`, not `bash`.

**`if:`** is evaluated before any step runs. It can read `runner.os` (`Linux`, `macOS`, `Windows`), `runner.arch` (`X64`, `ARM64`, …), `env.*` (the workflow and job `env:`), and `matrix.*`. Operators and the functions `contains`, `startsWith`, `endsWith`, `format`, `join`, `toJSON`, `fromJSON` and `case` work as on GitHub. A step whose condition is false does not run, and `arc workflow --list` shows it as `not run`. A condition that needs anything else — `secrets`, `github`, `steps`, `hashFiles()`, `success()`, `always()`, `failure()`, `cancelled()` — cannot be decided, and arc refuses the step.

**`uses:`** — arc runs no actions. It treats a few of them as checks on the machine instead:

| Action | What arc does |
|---|---|
| `actions/checkout` | nothing: the code is already checked out |
| `actions/setup-node` + `node-version` | checks that `node --version` on the machine matches |
| `actions/setup-python` + `python-version` | same, with `python3 --version` |
| `actions/setup-go` + `go-version` | same, with `go version` |
| `dtolnay/rust-toolchain@<ref>` | same, with `rustc --version` |

These are checked before the first step. If the machine does not match, the round stops as a machine problem and names the tool. Install the toolchain on the machine and add it to `[machine] path`. Any other `uses:` is refused.

**`${{ … }}`** anywhere in a `run:`, an `env:` value or a step name is refused, even `${{ matrix.os }}`. Use shell variables instead: `env:` values arrive as ordinary environment variables, so write `$NODE_ENV`, not `${{ env.NODE_ENV }}`.

**A step with neither `run:` nor `uses:`** is refused.

**What "refused" means for the merge gate:** if any step in the file is refused, every PR's round ends *cannot say*, naming the step and the reason. A merge gate that ran less than the file says would let through changes it never checked.

## Variables a step gets

| Variable | When | What |
|---|---|---|
| `PATH` | always | `[machine] path` from the machine's `~/.arc/machine.toml` |
| `CARGO_NET_GIT_FETCH_WITH_CLI=true` | `[tenant.gate] fetch_private_deps_over_ssh = true` | cargo fetches private git dependencies with the machine user's git credentials |
| `ARC_GATE_OUT` | the repo has test history (TAP) turned on | a directory: copy JUnit XML and build reports there, and arc collects them after the gate. Not set otherwise — guard with `if [ -n "$ARC_GATE_OUT" ]`. |
| `ARC_GATE_BASE` | with `ARC_GATE_OUT` | the base commit, for `arc affected --base "$ARC_GATE_BASE"` |

Every step also gets the variables a GitHub runner provides. The merge gate, `arc workflow` and a deploy all give the same set:

| Variable | What |
|---|---|
| `RUNNER_TEMP` | a directory only this run uses, outside the clone, removed when the run ends. Write temporary files here, never into the repo — an untracked file left in the clone fails the next round. |
| `GITHUB_WORKSPACE` | the root of the tree the steps run in |
| `GITHUB_ENV` | a file. A line `NAME=value` — or `NAME<<DELIM`, then the value's lines, then `DELIM` alone — sets `NAME` for every later step, post steps included. A line in neither form, or a `NAME<<DELIM` with no closing `DELIM`, fails the step that wrote it with GitHub's message (`Unable to process file command 'env' successfully`), and nothing from that file is set. `GITHUB_*`, `RUNNER_*` and arc's own variables (`ARC_GATE_OUT` and the rest) cannot be overwritten |
| `GITHUB_PATH` | a file. Each line is a directory added to the front of `PATH` for every later step, the latest first |
| `GITHUB_STEP_SUMMARY` | a file. Markdown written here goes into the run's report under the step's output (for the merge gate, the round's report). The first 1 MiB is kept, and the report says how many bytes were dropped after that; a summary never fails its step |
| `GITHUB_OUTPUT` | a file a step may write to without failing. Nothing reads it, because `${{ steps.<id>.outputs.<name> }}` is refused (above) |

Each step gets fresh `GITHUB_ENV`, `GITHUB_PATH`, `GITHUB_OUTPUT` and `GITHUB_STEP_SUMMARY` files, as on GitHub.

### What arc reads from `$ARC_GATE_OUT`

> **Temporary:** these names are fixed until artifacts can be declared in the workflow file, the way GitHub does it.

arc picks files by **name**: the name tells it which test runner wrote the report, because JUnit XML itself does not say which language it is. All steps of the gate share one directory, so two runs of the same runner need two different names.

| File name | Runner | Rows are |
|---|---|---|
| `junit-nextest.xml` | `cargo nextest run` | `rust` |
| `junit-vitest-web.xml`, `junit-vitest-vscode.xml`, `junit-playwright.xml` | arc's own front-end suites (their paths are read relative to arc's own directories) | `js/ts` |
| `junit-pytest-<suite>.xml` | `pytest --junitxml`, one file per pytest run; you choose `<suite>` (letters, digits, `-`, `_`), e.g. `default`, `fi`, `bench` | `python` |
| `cargo-timing.html` | `cargo build --timings` | build timings |
| `cargo-messages.json` | `cargo build --message-format=json` | compile diagnostics |
| `plan.json` | `arc affected --emit-plan` | shadow test selection |

Files with any other name are not read, and arc-server's log says so by name (`` `junit-pytest.xml` not read (arc reads no file by that name) ``) — check that line after you add a new runner. A pytest case's id is pytest's own `classname::name` (`tests.test_x::test_f[tpc]`). pytest records each case's file only with `-o junit_family=xunit1`, relative to its rootdir (keep that at the repository root). Without it the file is left empty, and `arc affected` cannot connect the case to a changed file.

A Python gate with two pytest runs, each on its own build of the extension:

```yaml ignore: the steps of one job, an excerpt of a workflow
      - name: pytest (default build)
        run: |
          rc=0
          python -m pytest tests/ -q -rfEs -o junit_family=xunit1 \
            --junitxml="${ARC_GATE_OUT:-$(mktemp -d)}/junit-pytest-default.xml" || rc=$?
          exit "$rc"
      - name: pytest (fault_injection build)
        run: |
          rc=0
          python -m pytest tests/test_faults.py -q -rfEs -o junit_family=xunit1 \
            --junitxml="${ARC_GATE_OUT:-$(mktemp -d)}/junit-pytest-fi.xml" || rc=$?
          exit "$rc"
```

pytest writes the report straight into the directory, so there is no old copy from a previous round to delete first. The `mktemp -d` fallback is for runs without test history (such as `arc workflow` on your machine), so the report never ends up in the working tree.

## A minimal `merge.yml`

A Node project with TypeScript and vitest:

```yaml workflow.yml
name: Merge gate
on:
  workflow_dispatch: {}

jobs:
  web:
    steps:
      - name: Install
        run: npm ci
      - name: Typecheck
        run: npx tsc -b
      - name: Test
        run: npx vitest run
```

A Rust workspace:

```yaml workflow.yml
name: Merge gate
on:
  workflow_dispatch: {}

env:
  CARGO_INCREMENTAL: "0"

jobs:
  rust:
    steps:
      - name: Build
        run: cargo build --locked --workspace --all-targets
      - name: Test
        run: cargo test --locked --workspace
      - name: Clippy
        run: cargo clippy --locked --workspace --all-targets -- -D warnings
```

Keep `--all-targets`: a plain `cargo build` does not compile tests, so a signature change that only breaks callers in tests would pass the build step.

## A real one

arc's own `merge.yml` checks a Rust workspace, a web UI and a VS Code extension. Shortened, with paths and names made generic, it looks like this:

```yaml workflow.yml
name: Merge gate
on:
  workflow_dispatch: {}

env:
  CARGO_INCREMENTAL: "0"   # the gate builds one commit per round; incremental caches only grow

jobs:
  rust:
    steps:
      # First: everything after it is meaningless if the machine cannot fetch
      # the private dependency, and that failure would look the same on both sides.
      - name: Private dependency reachable
        run: |
          export GIT_TERMINAL_PROMPT=0
          git ls-remote https://github.com/acme/private-dep HEAD >/dev/null 2>&1 \
            || { echo "this machine cannot read acme/private-dep"; exit 1; }

      - name: Web UI — typecheck, test, bundle
        working-directory: web
        run: |
          npm ci
          npm run typecheck
          npx vitest run
          npm run build

      - name: Build
        run: cargo build --locked --workspace --all-targets

      - name: Test
        run: |
          rm -f target/nextest/arc-tap/junit.xml
          rc=0
          cargo nextest run --locked --workspace --profile arc-tap --no-fail-fast || rc=$?
          # Hand the JUnit file to arc's test history, when it is collecting.
          if [ -n "$ARC_GATE_OUT" ] && [ -f target/nextest/arc-tap/junit.xml ]; then
            cp target/nextest/arc-tap/junit.xml "$ARC_GATE_OUT/junit-nextest.xml"
          fi
          exit "$rc"

      - name: Clippy
        run: cargo clippy --locked --workspace --all-targets -- -D warnings

  vscode:
    steps:
      - name: Typecheck + build + test
        run: |
          cd vscode-extension
          npm ci
          npm run typecheck
          npm run build
          npx vitest run
```

Worth copying from it:

- **Check the machine first.** A missing credential fails the base and the merge in the same way, so the comparison sees nothing new and would land the change without really checking it. A first step that fails loudly turns that into a visible stop.
- **Save the test exit code, then exit with it.** `rc=0; … || rc=$?; …; exit "$rc"` lets the copy to `$ARC_GATE_OUT` happen even when tests fail, which is exactly when the results matter. Delete the old report first, or a run that writes no report hands over the previous one.
- **One job per language** is easy to read, and all of them run.

## Check it before you commit it

```bash
arc workflow .github/workflows/merge.yml --job rust --list
```

`--list` prints which steps would run and which are turned off by their `if:`, and stops at the first step arc refuses, naming it. Without `--list`, `arc workflow` runs that one job on this machine, with the same step runner the merge machine uses. Its `PATH` is `[machine] path` if this machine has a `~/.arc/machine.toml` that sets one, and your own `PATH` otherwise. It runs **one job**; the merge machine runs all of them, so check each job.

## Common problems

| What you see | Why | What to do |
|---|---|---|
| every PR comes back *cannot say*, naming a step | that step has a `uses:` arc does not know, a `${{ … }}`, or an `if:` arc cannot decide | rewrite it as plain shell; `arc workflow … --list` finds each one |
| every PR stops on a toolchain | a `setup-*` / `rust-toolchain` version the machine does not have | install that version on the merge machine and add it to `[machine] path` |
| a step passes on your machine but fails on the merge machine | the machine's `PATH` is `[machine] path`, not your shell's | list every tool directory there |
| a red test reported green | a pipe: `vitest run \| tee log` returns `tee`'s status | drop the pipe, or save the runner's exit code yourself |
| a bash-only line fails | steps run under `sh` | write POSIX shell, or run `bash -c '…'` inside the step |
| your edit to `merge.yml` did not apply to its own PR | the base's copy judges the PR, unless the PR only added steps at the end or a person approved its gate change ([Which copy runs](#which-copy-runs)) | expected: it applies from the next PR on |
| a step failed, but the PR got *cannot say* instead of being sent back | arc cannot read any failure in the step's output | use a runner arc reads (cargo, nextest, vitest, tsc, pytest, Playwright) and keep its output on the console |
| every PR fails at the same step | main is red on the merge machine for a reason that is not a test | make main green; a PR that fixes the gate is judged by its own gate once a person approves it |
| a matrix job runs only once | arc only expands `strategy.matrix.include` lists | write the combinations under `include:` |
| `needs:` ordering is ignored | jobs run in the order the file lists them | put the jobs in the order you want |

---

*Next: [Releases and deploys](release.md) · [Configuration](configuration.md) · [Onboarding](onboarding.md).*
