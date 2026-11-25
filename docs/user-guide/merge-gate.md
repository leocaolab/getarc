# Merge — how a PR lands, and writing `merge.yml`

On the pipeline, nobody merges by hand. The **merge machine** (`arc-server`) takes one PR at a time whose pass matches its head ([Review on the pipeline](pipeline-review.md)), puts it on the target branch's tip, runs your `merge.yml`, and lands it when the merge adds no new failure.

## How a PR lands

- **Admission.** A PR is taken only when its pass (`refs/arc/pass/<pr>`) is its current head. A new push needs a new LGTM. A PR labelled **`arc-hold`** is never taken, whatever pass it holds.
- **Order.** `arc submit --after <N>` lands a change only after PR N has landed; if N closes, lands another version, or does not land in time, nothing is run and you are told why.
- **The run.** The gate runs on the target's tip and again on the merged tree; the PR lands if the second run shows no failure the first did not (details below).
- **What comes back.** Each round's report is written to `refs/arc/reports/<cl>` and, with the bridge on, posted into the PR's channel: a bounce interrupts your session and carries the failing tests' own output; a landing says the PR `landed as <sha>`. The landing letter also says how the PR ended (landed, discarded, already in) and which worktree on your machine still holds that branch — clean or not, whether someone is working in it. It never touches the worktree; you decide whether to remove it. Each landing on main is also one line in the `landings` channel ([Team up](bridge.md)).
- **Not landing it.** `arc submit --abandon "<why>"` ends the PR's review with your reason and closes it; do not close a PR by hand.
- **Watching.** The board's **Merge** tab shows the queue, the running round, each attempt and each gate step's log.

## Architecture rules: a step of the gate

`arc archcheck` belongs to the merge gate, not to the review you run on your machine. A `merge.yml` step runs `arc archcheck --base <merge base>`, which judges the merged tree against the repo's written architecture rules (`.arc/archcheck.toml`, waivers registered in `.arc/arch_waivers.txt`). A broken rule, an added waiver row or a raised register value exits 7, and the round reads it as a new failure like any other step's.

## The gate file

When a merge machine lands your PRs, the check that decides whether a PR may land is one file in your repo: **`.github/workflows/merge.yml`**. This page says when that file runs, which copy of it runs, what you may write in it, and how it decides.

What an author runs before submitting is `presubmit.toml` ([Configuration](configuration.md)); the merge machine reads only `merge.yml`.

## What the file is

`merge.yml` is a workflow file in GitHub Actions syntax, but GitHub does not run it — the merge machine does, on its own clone, as a plain shell. Write it so GitHub never starts it by itself:

```yaml ignore: the `on:` lines of a workflow, an excerpt
on:
  workflow_dispatch: {}
```

The path is fixed: `.github/workflows/merge.yml`, at the repo root. There is no setting to point elsewhere.

All jobs in the file run, one after another, **in the order they are written**, as one list of steps. `needs:`, `runs-on:` and `on:` are not read.

## When it runs

1. A PR enters the merge queue when its **pass** matches its current head. The review service grants the pass when the reviewers your repo's routes name say LGTM ([Configuration](configuration.md#arcmachinetoml--the-pipeline-machine)). A new push is a new head, so it needs a new LGTM. A PR labelled `arc-hold` gets no pass.
2. The merge machine takes one PR at a time. For it, it:
   - fetches the target branch and checks out its tip — the **base**;
   - reads `merge.yml` and `.arc/gate.toml` from the base;
   - runs the gate on the base (or reuses an earlier reading of the same base);
   - merges the PR onto the base;
   - runs the gate again on the merged tree — the base's, or the PR's own when it edited the gate ([Which copy runs](#which-copy-runs));
   - **lands the merge if the second run shows no failure the first run did not.**
3. The result is written to `refs/arc/reports/<cl>`; with the chat bridge on, it also reaches the PR's channel.

Because the verdict compares two runs, a target branch that is already red does not block everyone: a PR lands as long as it adds no *new* failure.

By default (`[tenant.gate] rerun = "once"`), a new failure is read a second time on the same commit before the PR bounces, so a one-off flake does not bounce it.

A bounced head is not tested again on the same base: it waits for a new push, or for the target branch to move. If you are sure the bounce was a false alarm (the machine was overloaded, a test flaked twice), no command asks for the same head to be tested again on the same base: hand the PR a new head with `arc submit --pr <N>`, which is reviewed again and queued after its LGTM.

## Which copy runs

Each tree is judged by its own gate: the base by the base's, the merged tree by the one it carries. The **gate definition** is `merge.yml`, `.arc/gate.toml`, and every file `.arc/gate.toml` names on the base:

```toml ignore: .arc/gate.toml, read by arc-server's merger, whose own tests pin its shape
# .arc/gate.toml — the scripts and config the gate runs, as globs
definition = ["dev/check.sh", "dev/gate/**"]
```

The declaration is read from the base only, so a PR that edits `.arc/gate.toml` edits the gate.

- **The PR leaves the gate definition alone** → the base's gate runs on both trees, as before.
- **The PR only appends steps after the last step of `merge.yml`, and changes no other gate file byte for byte** → the merged tree runs the PR's `merge.yml`. Green lands with no approval; anything else needs one.
- **Any other edit** (a step changed, removed or moved, a declared script edited, a file added or removed) → the PR's own gate runs only after a person approves this head.

To ask, the merge machine opens a question on the first issue the PR's title names (`… (b/123)`), naming the PR and its head, with two options: 「批」 and 「不批」. Only 「批」 counts. Until then the round ends *cannot say* and names the question; a ruling on that issue puts the PR back in the queue. A new push is a new head and a new question: an approval does not carry to it, and nothing is written into your commits.

A PR whose title names no issue, or whose target branch also edited the gate since it branched, is not asked about: name an issue, or rebase.

The merge machine needs an issue board for this (`arc-bridge` on the tenant's machine). Without one, a gate edit ends *cannot say* naming the missing seat, and the PR waits: once the server has a seat, `arc submit` puts it back. A board that is there but does not answer judges nothing, and the PR is tried again.

A target branch whose own gate does not read (no `merge.yml`, a file that does not parse, a step this machine cannot run) holds every PR the same way: each ends *cannot say* once and waits, rather than being run again on every poll. Land the repair — it is judged by its own gate once approved — then `arc submit` the others again.

## How a failure is read

Steps run in order. **The gate stops at the first step that exits non-zero**, and the rest do not run.

arc then reads that step's output and picks out the failures it names. It recognises the console output of `rustc` / `cargo build`, `cargo test`, `cargo nextest`, `vitest`, `tsc`, Playwright, `pytest`, and lint tools. The verdict is made over those named failures, not over exit codes.

- **Failures named, none new** → the PR lands.
- **New failures** → the PR bounces, with the failing output in the report.
- **The step failed but its output names nothing arc can read** → the round ends as *cannot say*, and a person has to look. Prefer test runners arc reads, and let their normal output reach the console.
- **The machine could not run the step** (it would not start, ran past `[tenant.gate] timeout_secs`, or ran out of disk or memory) → no PR is charged; the queue waits for the machine.

Main must be green on the merge machine before you start. If a step fails on the base for a reason that is not a test — a missing tool, a missing credential — every PR's round fails the same way at the same step. A PR that repairs the gate itself is judged by its own gate once approved, and lands if that gate is green.

## What arc runs in a workflow file

arc implements part of the GitHub Actions format, and it says so when it meets the rest. The same rules apply to the merge gate, to deploy jobs and to `arc workflow`.

**Read and honoured:**

| Key | Where | What arc does |
|---|---|---|
| `jobs.<id>.steps` | job | the steps, in order |
| `run:` | step | the command; run with `sh -c` at the repo root |
| `name:` | step | how reports name the step (unnamed: `step 3`) |
| `env:` | workflow, job, step | exported before the command; step overrides job overrides workflow |
| `working-directory:` | step | `cd` into it first |
| `defaults.run.working-directory` | workflow, job | the directory for steps that set none |
| `if:` | step | evaluated before the run (below) |
| `strategy.matrix.include` | job | the job's steps run once per entry |
| `uses:` | step | only the few actions listed below |
| `phase:` | step | arc's own key: `build`, `test`, `lint` or `deploy`. Only decides how a failure is filed in a deploy's or release's record. Any other word refuses the file. |

Other keys (`runs-on`, `permissions`, `timeout-minutes`, `needs`, `shell`, `continue-on-error`, …) are ignored.

**Every step's command** is your `run:` text preceded by `set -e`, the `env:` exports, and the `cd`. `set -e` means a multi-line `run:` stops at its first failing line, as it does on GitHub. One difference: `pipefail` is not set, so in `npx vitest run | tee log` the step's status is `tee`'s. And the shell is `sh`, not `bash`.

**`if:`** is evaluated before any step runs. It can read `runner.os` (`Linux`, `macOS`, `Windows`), `runner.arch` (`X64`, `ARM64`, …), `env.*` (the workflow and job `env:`), and `matrix.*`. Operators and the functions `contains`, `startsWith`, `endsWith`, `format`, `join`, `toJSON`, `fromJSON`, `case` work as on GitHub. A step whose condition is false is not run, and `arc workflow --list` shows it as `not run`. A condition that needs anything else — `secrets`, `github`, `steps`, `hashFiles()`, `success()`, `always()`, `failure()`, `cancelled()` — cannot be decided, and the step is refused.

**`uses:`** — arc runs no actions. A few are read as statements about the machine instead:

| Action | What arc does |
|---|---|
| `actions/checkout` | nothing: the code is already checked out |
| `actions/setup-node` + `node-version` | checks that `node --version` on the machine matches |
| `actions/setup-python` + `python-version` | same, with `python3 --version` |
| `actions/setup-go` + `go-version` | same, with `go version` |
| `dtolnay/rust-toolchain@<ref>` | same, with `rustc --version` |

These are checked before the first step. If the machine does not match, the round stops as the machine's problem, naming the tool. Install the toolchain on the machine and put it on `[machine] path`. Any other `uses:` is refused.

**`${{ … }}`** anywhere in a `run:`, an `env:` value or a step name is refused, even `${{ matrix.os }}`. Use shell variables instead: `env:` values arrive as ordinary environment variables, so write `$NODE_ENV`, not `${{ env.NODE_ENV }}`.

**A step with neither `run:` nor `uses:`** is refused.

**What "refused" means for the merge gate:** one refused step anywhere in the file, and every PR's round ends as *cannot say*, naming the step and the reason. A merge gate that ran less than the file says would pass changes it never checked.

## Variables a step is given

| Variable | When | What |
|---|---|---|
| `PATH` | always | `[machine] path` from the machine's `~/.arc/machine.toml` |
| `CARGO_NET_GIT_FETCH_WITH_CLI=true` | `[tenant.gate] fetch_private_deps_over_ssh = true` | cargo fetches private git dependencies with the machine user's git credentials |
| `ARC_GATE_OUT` | the repo has test history (TAP) enabled | a directory: copy JUnit XML and build reports there for arc to collect after the gate. Unset otherwise — guard with `if [ -n "$ARC_GATE_OUT" ]`. |
| `ARC_GATE_BASE` | with `ARC_GATE_OUT` | the base commit, for `arc affected --base "$ARC_GATE_BASE"` |

Every step also gets what a GitHub runner gives one. The merge gate, `arc workflow` and a deploy give the same set:

| Variable | What |
|---|---|
| `RUNNER_TEMP` | a directory only this run uses, outside the clone; it is removed when the run ends. Write intermediate files here, never into the tree — an untracked file left in the clone fails the next round. |
| `GITHUB_WORKSPACE` | the root of the tree the steps run in |
| `GITHUB_ENV` | a file: a line `NAME=value`, or `NAME<<DELIM`, the value's lines, then `DELIM` alone, sets `NAME` for every later step, the post steps included. A line that is neither form, or a `NAME<<DELIM` whose `DELIM` never comes, fails the step that wrote it with GitHub's words (`Unable to process file command 'env' successfully`) and sets nothing from that file. `GITHUB_*` and `RUNNER_*` cannot be overwritten, and neither can arc's own variables (`ARC_GATE_OUT` and the rest) |
| `GITHUB_PATH` | a file: each line is a directory put at the front of `PATH` for every later step, the latest first |
| `GITHUB_STEP_SUMMARY` | a file: Markdown that goes into the run's report under the step's output (for the merge gate, the round's report). The first 1 MiB is kept and the report says how many bytes past it were dropped; a summary never fails its step |
| `GITHUB_OUTPUT` | a file a step may write to so it does not fail; nothing reads it, because `${{ steps.<id>.outputs.<name> }}` is refused (above) |

Each step gets fresh `GITHUB_ENV`, `GITHUB_PATH`, `GITHUB_OUTPUT` and `GITHUB_STEP_SUMMARY` files, as on GitHub.

### What arc reads from `$ARC_GATE_OUT`

> **Temporary:** these names are fixed until artifacts can be declared in the workflow file, the way GitHub does it.

arc reads files by **name**, and the name is what says which runner wrote the report — JUnit XML itself names no language. Every step of the gate shares the one directory, so two runs of a runner need two names.

| File name | Runner | Rows are |
|---|---|---|
| `junit-nextest.xml` | `cargo nextest run` | `rust` |
| `junit-vitest-web.xml`, `junit-vitest-vscode.xml`, `junit-playwright.xml` | arc's own front-end suites (their paths are read relative to arc's own directories) | `js/ts` |
| `junit-pytest-<suite>.xml` | `pytest --junitxml`, one file per pytest run; `<suite>` is yours (letters, digits, `-`, `_`), e.g. `default`, `fi`, `bench` | `python` |
| `cargo-timing.html` | `cargo build --timings` | build timings |
| `cargo-messages.json` | `cargo build --message-format=json` | compile diagnostics |
| `plan.json` | `arc affected --emit-plan` | shadow test selection |

Any other name is not read, and the run's line in arc-server's log says so by name (`` `junit-pytest.xml` not read (arc reads no file by that name) ``) — check that line after wiring a new runner. A pytest case's id is pytest's own `classname::name` (`tests.test_x::test_f[tpc]`). pytest writes each case's file only under `-o junit_family=xunit1`, relative to its rootdir (keep that the repository root); without it the file is left blank, and `arc affected` cannot tie the case to a changed file.

A Python gate with two pytest runs, each over its own build of the extension:

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

pytest writes the report straight into the directory, so there is no previous round's copy to delete first. The `mktemp -d` fallback is for a run without test history (`arc workflow` here), so the report never lands in the work tree.

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

`--all-targets` matters: a plain `cargo build` does not compile tests, so a signature change whose only stale callers are in tests would pass the build step.

## A real one

arc's own `merge.yml` gates a Rust workspace, a web UI and a VS Code extension. Shortened, with its paths and names made generic, it has this shape:

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

Things worth copying from it:

- **Check the machine first.** A missing credential fails the base and the merge the same way, so the verdict sees nothing new and would land the change unchecked. A first step that fails loudly turns that into a visible stop.
- **Capture the test exit code, then exit with it.** `rc=0; … || rc=$?; …; exit "$rc"` lets the copy to `$ARC_GATE_OUT` happen even when tests fail, which is when the results matter most. Delete the old report first, or a run that writes none hands over the previous one.
- **One job per language** reads well, and all of them run.

## Check it before you commit it

```bash
arc workflow .github/workflows/merge.yml --job rust --list
```

`--list` prints which steps would run, which are turned off by their `if:`, and stops at the first step arc refuses, naming it. Without `--list`, `arc workflow` runs that one job here, with the same step runner the merge machine uses. Its `PATH` is `[machine] path` when this machine has a `~/.arc/machine.toml` that sets one, and your own otherwise. It runs **one job**; the merge machine runs all of them, so check each job.

## Common pitfalls

| What you see | Why | What to do |
|---|---|---|
| every PR comes back *cannot say*, naming a step | that step has a `uses:` arc does not know, a `${{ … }}`, or an `if:` it cannot decide | rewrite it as plain shell; run `arc workflow … --list` to find each one |
| every PR stops on a toolchain | a `setup-*` / `rust-toolchain` version the machine does not have | install that version on the merge machine and add it to `[machine] path` |
| a step passes here but fails on the merge machine | the machine's `PATH` is `[machine] path`, not your shell's | list every tool directory there |
| a red test reported green | a pipe: `vitest run \| tee log` returns `tee`'s status | drop the pipe, or capture the runner's code yourself |
| a bash-only line fails | steps run under `sh` | write POSIX shell, or run `bash -c '…'` inside the step |
| your edit to `merge.yml` did not apply to its own PR | the base's copy judges every PR | expected: it applies from the next PR |
| failing step, *cannot say* instead of a bounce | its output names no failure arc can read | use a runner arc reads (cargo, nextest, vitest, tsc, pytest, Playwright) and keep its output on the console |
| every PR fails at the same step | main is red on the merge machine for a non-test reason | fix it on main outside the queue, then register |
| a matrix job runs only once | arc expands only `strategy.matrix.include` lists | write the combinations under `include:` |
| `needs:` ordering ignored | jobs run in the order the file lists them | order the jobs in the file |

---

*Next: [Releases and deploys](release.md) · [Configuration](configuration.md) · [Onboarding](onboarding.md).*
