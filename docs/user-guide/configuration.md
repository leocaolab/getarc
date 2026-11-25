# Configuration

arc's settings are split by whose fact they are: each file holds one kind of fact, owned by one party, and a fact lives in exactly one of them.

| File | Whose fact | What it holds | Commit it? |
|---|---|---|---|
| `~/.tars/config.toml` | yours, on each machine | LLM providers: type, model, credentials | **never** |
| `<repo>/.arc/config.toml` | this clone | which provider plays which role (`[roles]`), what review skips and how long a local review goes on (`[review]`), test results (`[test]`), the deploy job (`[release]`) | no |
| `<repo>/presubmit.toml` | the project | the checks `arc submit` runs on your machine before it pushes, and `arc fix` tells the fixer to run | **yes** |
| `<repo>/.github/workflows/merge.yml` | the project | the merge gate the pipeline runs before it lands a PR ([Merge](merge-gate.md)) | **yes** |
| `<repo>/.arc/delivery.toml` | the project | how the project ships: `[builds.*]`, `[targets.*]` ([Releases and deploys](release.md#delivery-toml)) | **yes** |
| `~/.arc/client.toml` | each machine that talks to the pipeline | the one address of the pipeline's board | no |
| `~/.arc/machine.toml` | the pipeline machine | the repos it serves (each a **tenant**) and how: gate, review routes, release | no |

On a machine where you write code: `~/.tars/config.toml`, the repo's `.arc/config.toml` (from `arc init`) and `~/.arc/client.toml`. In the repo, committed: `presubmit.toml` (optional), `merge.yml`, and `delivery.toml` once you ship. On the pipeline machine: `~/.arc/machine.toml`, its own `~/.tars/config.toml`, and the `.arc/config.toml` of each repo's clone there. Each file is explained below; [Set up the pipeline](onboarding.md) walks through writing them in order.

`arc` itself takes its runtime inputs as command-line flags, not environment variables. The one environment variable it reads on your behalf is the API key a tars provider names (below).

## `~/.tars/config.toml` — providers and keys

This is the only place a model name or a credential is written. arc never reads a provider from anywhere else, so the same file serves every repo on the machine.

Each provider is a table named by an id you choose. `[roles]` in `.arc/config.toml` refers to that id. Unknown keys in a provider table are refused, naming the key.

To use another file, give any arc command `--tars-config <file>`, or `--tars_home <dir>` for a whole tars home (its `config.toml`); with neither, arc reads `$TARS_HOME/config.toml`, else `~/.tars/config.toml`. Pass the same flag to every arc call.

### No API key: use the Claude Code you are signed in to

If `claude` works in your terminal, arc can review and fix through it. The `claude_cli` type signs in with your own `claude login`; there is no key to create or export.

```toml ignore: ~/.tars/config.toml, tars's file, not arc's
# ~/.tars/config.toml
[providers.claude_critic]
type = "claude_cli"
default_model = "opus"

[providers.claude_fixer]
type = "claude_cli"
default_model = "sonnet"
tools = "default"        # a Fixer edits files; the default "disabled" cannot
timeout_secs = 900       # the default is 300
```

`arc init` then puts the critic roles on `claude_critic` and the fixer on `claude_fixer`. The [arc-setup skill](skills.md) writes exactly this when it finds `claude` on your PATH.

### No API key: use the Codex CLI you are signed in to

The same two blocks with `type = "codex_cli"` run through your `codex login`:

```toml ignore: ~/.tars/config.toml, tars's file, not arc's
# ~/.tars/config.toml
[providers.codex_critic]
type = "codex_cli"
default_model = "<a Codex model id>"

[providers.codex_fixer]
type = "codex_cli"
default_model = "<a Codex model id>"
sandbox = "workspace-write"   # a Fixer edits files; the default "read-only" cannot
timeout_secs = 900            # the default is 600
```

Every CLI type also takes `executable` (default `claude`, `codex`) when the binary is not on `PATH` under that name. arc's own tests run `claude_cli` as a Fixer end to end; `codex_cli` is accepted and run the same way, but not tested as a Fixer end to end. With either, both roles come from one model family; a critic from another family (next section) keeps the review more independent. More on each agent: [Connecting your coding agent](coding-agents.md).

### With an API key

```toml ignore: ~/.tars/config.toml, tars's file, not arc's
# ~/.tars/config.toml
[providers.gemini_flash]
type = "gemini"
default_model = "flash@latest"
auth = { kind = "secret", secret = { source = "env", var = "GEMINI_API_KEY" } }
```

Export the variable the provider names (`export GEMINI_API_KEY=…`) in the shell arc runs from.

- **`type`** — one of `openai`, `openai_compat`, `anthropic`, `gemini`, `bedrock`, `vllm`, `mlx`, `llamacpp`, `claude_cli`, `claude_sdk`, `codex_cli`, `opencode`, `antigravity`.
- **`default_model`** — a concrete model id to pin one, or `<series>@latest` (for example `flash@latest`) to take the newest model of a series. A series is known only for providers that define them; elsewhere write a concrete id. Run records name the concrete model that ran, never `@latest`.
- **`auth`** — `{ kind = "secret", secret = { source = "env", var = "NAME" } }` reads the key from an environment variable; `secret = { source = "file", path = "…" }` reads it from a file. `{ kind = "none" }` is for local servers. The CLI types (`claude_cli`, `codex_cli`) use your own login and take no `auth`.

A different model per role is a second provider entry with its own `default_model`.

## `<repo>/.arc/config.toml` — this clone's routing

This file says how *this clone* is wired. It differs between machines, so it is not committed: `arc init` writes `.arc/.gitignore`, which ignores everything under `.arc/` (itself included) except `config.toml.example`, `delivery.toml`, `archcheck.toml` and `arch_waivers.txt`. Commit `config.toml.example` if you want to share a template.

### What `arc init` writes

- **In a terminal:** it reads your tars providers, asks for the critic and the fixer, and writes `.arc/config.toml` with:
  - `[roles]` — `default`, `critic`, `critic_l4`, `critic_l5` on the critic's provider, `fixer` on the fixer's;
  - `[review] exclude` — a starter list of non-source directories (tests, docs, vendor, build output, …);
  - `[test]` — commented out, for you to fill in.
- **Not in a terminal** (CI, a script): it writes `.arc/config.toml.example` instead and exits non-zero, telling you to copy it to `.arc/config.toml`.
- **When `.arc/config.toml` already exists:** it refuses. `arc init --force` overwrites it.
- **When tars has no providers:** it stops and asks you to define one first.

### `[roles]` — which provider plays which part

```toml config.toml
[roles]
default   = "gemini_flash"   # any role not listed below
critic    = "gemini_flash"
critic_l4 = "gemini_flash"   # per-file review
critic_l5 = "gemini_flash"   # whole-repo rot review
fixer     = "claude_fixer"   # must be written out: `default` does not cover it
```

Each value is a provider id from `~/.tars/config.toml`. A role you leave out falls back to `default`, except `fixer`, which must be named. Picking a critic and a fixer from different model families keeps the review independent.

There is no `[providers]` section here. A file that still has one is refused, with each `[providers.<id>]` block named: move the definitions to `~/.tars/config.toml` and keep `[roles]`.

### `[review]` — what review skips, and how long a local review goes on

```toml config.toml
[review]
exclude = ["**/tests/**", "**/docs/**", "**/vendor/**", "**/node_modules/**"]
# max_rounds  = 5    # reviewer replies without an LGTM before arc fix lets the head through
# react_turns = 24   # model calls the reviewer may take on one review
```

- `exclude` is the whole list of paths review and `arc rot` skip — arc has no built-in list. Each entry is a glob over the repo-relative file path: `*` stays inside one directory, `**` crosses any number. To skip a directory, write `dir/**`; `"tests/**"` is only the top-level `tests/`, `"**/tests/**"` is any `tests/`. A malformed glob is an error when the file is read.
- `max_rounds` (default 5) and `react_turns` (default 24) bound a **local** round — `arc local-review` and `arc fix` on this clone. The pipeline's review has its own, in `machine.toml` (`review.max_rounds`, `review.react_turns`, [below](#arcmachinetoml--the-pipeline-machine)).
- The keys `enable`, `disable`, `experimental` and `confidence_floor` still parse, but nothing reads them: a local review runs the stable rules only.

### `[test]` — where your test results are

```toml config.toml
[test]
junit = "target/nextest/arc-tap/junit.xml"
```

arc never runs your tests; it reads the JUnit XML your runner writes. `arc tap init` sets your runner up and prints the value for `junit`. The path is relative to the repo root.

`generate = false` stops `arc fix` from writing tests for its fixes (it does by default).

### `[release]` — which job is your deploy

```toml config.toml
[release]
workflow = ".github/workflows/deploy.yml"
job      = "deploy"
```

Written in the repo's clone on the pipeline machine, where deploys run; covered in [Releases and deploys](release.md).

### A complete small example

```toml config.toml
[roles]
default = "claude_critic"
fixer   = "claude_fixer"

[review]
exclude = ["**/tests/**", "**/docs/**", "**/node_modules/**", "**/dist/**"]
```

## `<repo>/presubmit.toml` — the checks before submit

Committed, at the repo root: what a change must pass is the same in every clone. `arc submit` runs it before it pushes anything, and pushes how each check came out beside the head; `arc presubmit` runs it alone, pushes nothing and records nothing. `arc fix` hands the fixer the same checks, filled for the pull request (`{target}` is its target on `origin`, `{base}` where HEAD forks from it, `{affected}` the packages reached since), as what to run before it calls a finding fixed; a repo without the file gets a fixer told to find its own build and test commands.

```toml presubmit.toml
timeout_seconds = 1800   # per check; a check past it is killed with its whole process group

[[checks]]
name = "merge-check"
command = "git merge-tree --write-tree HEAD {target}"

[[checks]]
name = "clippy"
command = "cargo clippy --all-targets -- -D warnings"
```

- `arc submit` runs the commands in the current branch's `presubmit.toml`, as you. Each check runs in a process group of its own; when it ends, passed or not, the whole group is killed, and Ctrl-C (or a SIGTERM to arc) kills the check that is running.
- The checks run in order through `sh -c` at the repo root; every check runs, and one that fails stops none after it. A command that passed on this commit is skipped. A check that does run needs a working tree without uncommitted changes (untracked files included), because its pass counts for HEAD; a tree that changes while it runs, or a HEAD that moves, remembers no pass. When every check passed on HEAD already, nothing runs and a dirty tree does not matter, since HEAD is what is pushed.
- A command may use `{base}`, `{target}` and `{affected}`, each value quoted for `sh` (`{affected}` becomes one quoted word per package). `{base}` and `{target}` come from the run's `--base <sha>` and `--target <ref>`; arc fetches nothing, so usually `git fetch origin`, then `--base "$(git merge-base HEAD origin/main)"` and `--target origin/main`. `{affected}` arc works out itself: the packages the change from `--base` to the checked commit reaches, the same computation as `arc affected --base <base>` (none when the change is in no package). `--affected <package>...` only overrides it (`--affected` alone says the change reaches none). When the packages cannot be worked out, every package of the workspace is used and the output says so with the error; when even the workspace cannot be listed, no check runs. The output, and `--json`'s `affected`, says which packages were used and where they came from: `given`, `computed` or `full`. A check whose placeholder has no value (its flag not given; for `{affected}`, neither `--affected` nor `--base`) stops the run before any check runs, exit 2, naming the check and the flag. arc replaces only those three spellings; every other brace (`${HOME}`, `{ cmd; }`, awk's `'{print}'`) reaches the shell as written.
- No environment variable is set for a check.
- Each pass is remembered on its own under `.arc/cache/presubmit/<commit>/`, one file per command named by the hash of its text with the placeholders filled in, so `arc presubmit` then `arc submit` of the same HEAD with the same flags runs nothing twice, and a rerun after a failure runs only what has not passed. A pass that cannot be written down stops the run. The record is the author's own: presubmit is no security boundary, the merge gate is.
- A check's output goes to a temporary file, not a pipe, so a background job holding the output does not hold the run; `timeout_seconds` bounds the wait.
- A check that ran and did not pass exits 11 and prints its name, how it ended (`it exited with code N`, `signal N killed it`, or `it ran past its Ns timeout and was killed`), its command as it ran, the failures arc's test reader names in its output (tests, compile errors, denied lints), each in its own words, and then the output itself: its start and its end, with how many bytes were cut between them stated where they were cut. When no line names a failure, only the output is shown. A check that could not start says why. The run still exits 11 once every check has run. Under `--json`, `checks` holds every check in order, each an object with `name`, `command` and `result` (`passed`, `passed_before`, `failed`, `timed_out`, `not_started`), plus `duration_ms`; a failed one adds `exit_code`, `signal`, `failures` (`[{unit, excerpt}]`, or `null` when none is named) and `output` (`null` when it printed nothing), a timed-out one `timeout_seconds`, `failures` and `output`, one that did not start `why`; `passed` says whether all did.
- A failed check does not stop `arc submit`: the head is pushed, the PR goes to review, and arc exits 11 after naming the checks that did not pass. Before the request is sent, the run is written on the head as a git note under `refs/notes/arc-presubmit` and pushed to origin on top of the notes already there: JSON `{"checks": [{"name", "kind": "passed"|"passed_before"|"failed"|"not_run", "took_ms", "reason"}]}`, where `not_run` is a check past its timeout or one that could not start and `reason` is the terminal's words. The PR's page and the review board show it; a head without a note says no record. A note origin does not take is said in one line, and `--json`'s `presubmit_note` says `not_pushed` with git's words; it fails nothing. `arc presubmit` and `--dry-run` write no note.
- Once the checks have run, `arc submit` pushes the branch itself, never over commits the remote branch has and HEAD lacks: such a branch is refused, never overwritten. That refusal, a PR already open without `--pr`, a `--pr` that is not the branch's open PR, a PR aimed at another branch, and an origin with no default branch all come before any check runs.
- No `presubmit.toml` means no checks: `arc submit` submits as before.
- A misspelt key, no `[[checks]]`, a zero limit, or a `timeout_seconds` over 86400 is refused when the file is read.
- `.arc/config.toml` has no `[gate]` any more. A file that still holds one is not refused — each section's reader reads only its own section — so the leftover is ignored. Delete it.

## `<repo>/.arc/delivery.toml` — how the project ships

This one **is committed**: how the project builds and where its output goes is the same in every clone. It holds `[builds.<id>]` (how a shippable thing is made) and `[targets.<id>]` (where it ends up), and the release page is drawn from it. Both are explained, with an example, in [Releases and deploys](release.md#delivery-toml).

A build or target id may be declared here or in `.arc/config.toml`, not in both — the same id in both files is an error, not an override.

## `~/.arc/client.toml` — where the pipeline is

Every machine that talks to the pipeline — your laptop, each agent's machine — writes one line, the address of the pipeline's board (the `arc-web` service):

```toml client.toml
# ~/.arc/client.toml
web = "http://<board-host>:<port>"
```

The file has exactly this one key; a misspelled key is refused, not ignored. Clients ask the board for everything else — where the chat server is, where this repo's test history goes — so an address is written once, on the pipeline machine. With no `client.toml`, the bridge hooks let every stop through and `arc tap` writes the repo's own `.arc/tap.db`. On the pipeline machine, `arc-server tenant url web` prints the address to write here ([Set up the pipeline](onboarding.md#32-clients-and-agent-machines)).

## `~/.arc/machine.toml` — the pipeline machine

Only the machine that runs the server suite has this file. Every service reads it and nothing else: a unit carries no settings, and a service started with an `ARC_*` environment variable that is not on its short allow-list refuses to start and says what replaced it. `--config FILE` points a service at another file.

It lists the repos the machine serves — each one is a **tenant**, a `[[tenant]]` table — and how it serves them. You do not write the tenant's head by hand: `arc-server install <clone>` (or `arc-server tenant add <clone>`) registers the repo and writes `id`, `name` and `home`. After that:

```bash
arc-server tenant show [owner/name]                    # every value, and whether it came from machine.toml or the default
arc-server tenant set owner/name gate.rerun=never      # change tenant keys; several key=value at once
arc-server tenant unset owner/name gate.rerun          # back to the default; `tap` or `release` drops that whole table
arc-server tenant check [owner/name]                   # paths exist, the clone is clean, the stores are in place
arc-server tenant url web                              # the board's address, for client.toml
arc-server tenant list                                 # every tenant, one per line
```

`tenant set` writes only `[[tenant]]` keys; `[machine]` and the `[[tenant.review.route]]` rules are edited in the file. Every table refuses keys it does not know. A mistake in `[machine]` stops every service; a mistake in one `[[tenant]]` refuses only that tenant, naming which table, which key and why, and the other tenants run on.

### A complete file

One repo, `acme/widgets`, reviewed by a real reviewer, with a label that lets a PR through on the dummy reviewer:

```toml machine.toml
[machine]
address = "10.0.0.5"     # this machine's IP, as the other machines reach it
expose  = true           # listen on that address; without it, the board and the chat server listen on 127.0.0.1 only
path    = ["/home/ci/.cargo/bin", "/usr/local/bin", "/usr/bin", "/bin"]   # PATH for every gate step and deploy step

[[tenant]]
id   = "0199f2c4-7b1e-7a3d-9c55-2f0e8b1d4a60"   # written by `arc-server install`; never edit it
name = "acme/widgets"                           # owner/name on GitHub, as the clone's origin says
home = "/home/ci/widgets-ci"                    # a clone only arc works in; its stores live in <home>/.git/arc/

[[tenant.review.route]]   # PRs labelled arc-bypass: the dummy reviewer, which says LGTM
label    = "arc-bypass"
reviewer = "dummy"
name     = "dummy"

[[tenant.review.route]]   # every other PR: a real reviewer
reviewer = "react"
name     = "react"
```

For a repo nobody else reviews, the one rule is the fallback to the dummy reviewer, and every PR goes through review on its LGTM:

```toml machine.toml#tenant
[[tenant.review.route]]
reviewer = "dummy"
name     = "dummy"
```

### `[machine]` — once per machine

| Key | Default | What it does |
|---|---|---|
| `address` | none | this machine's IP address (not a host name); the board, chat server and test-history addresses are derived from it |
| `expose` | `false` | `true`: listen on `address`, so other machines reach the board and the chat server; `false`: loopback only. `true` without `address` is refused |
| `path` | the service manager's | `PATH` for every gate step and deploy step. Put the toolchains your `merge.yml` needs here |
| `[machine.web] port` | `8787` | the board's port; `client.toml` names `http://<address>:<port>` |
| `[machine.bridge] port` | `8790` | the chat server's port; clients learn it from the board |
| `[[machine.disk]]` | none | `mount`, `min_free_gib` (and optionally `min_free_inodes`): the merge server starts no round, and the nightly and deploys refuse, while a mount is below its floor |

### `[[tenant]]` — once per repo

| Key (`tenant set` name) | Default | What it does |
|---|---|---|
| `target` | `main` | the branch PRs land on |
| `queue.admit` | `pr` | `pr`: an open PR is taken only when its pass matches its head. `any`: everything pushed, for a remote without PRs |
| `gate.timeout_secs` | `3600` | deadline for one gate step; the step is killed with its process group |
| `gate.round_timeout_secs` | 4 × `gate.timeout_secs` | deadline for a whole merge round (fetch, merge, every gate run, push) |
| `gate.rerun` | `once` | `once`: a new failure must show up twice on the same sha before the PR bounces. `never`: the first red reading stands |
| `gate.too_divergent` | `100` | conflicting paths at which a round ends as too divergent without running the gate |
| `gate.fetch_private_deps_over_ssh` | `false` | `true` gives every step `CARGO_NET_GIT_FETCH_WITH_CLI=true`, so cargo fetches private git dependencies with the service user's own git credentials |
| `gate.read_key` | none | a read-only deploy key; only `tenant check` uses it, to prove the key cannot push |
| `[[tenant.review.route]]` | none | who reviews which PR, below. **With no rule, nobody reviews and nothing lands** |
| `review.gate` | `all_lgtm` | which LGTMs grant the head its pass: `all_lgtm`, every reviewer of the head; `one_lgtm`, any one |
| `review.max_rounds` | `5` | replies a reviewer may give without an LGTM; at the limit it counts as an LGTM and stops reviewing |
| `review.react_turns` | `24` | model calls the `react` reviewer may take on one review |
| `review.reviewer_timeout_secs` | `3600` | how long a reviewer may run before it is killed and called again |
| `review.reviewer_attempts` | `3` | calls in a row that end without a reply before the review stops and says so on the PR's chat channel |
| `review.fixer_client` | `author` | who answers the findings: `author` (sent to the author's agent session over the chat server), `claude` (`claude -p` fixes in a worktree of the head), `tars` (arc's own fixer), `nothing` (the author runs `arc submit` again) |
| `review.model_config` | the clone's `.arc/config.toml` | another file whose `[roles]` the real reviewers use |
| `bridge.enabled` | `false` | `true`: the merge server posts each round's verdict into the PR's chat channel, as `merger@<owner>:<name>` |
| `github.mirror` | `true` | `false`: reviews are not posted on the PR and the issue board is not mirrored to GitHub issues; both stay in arc |
| `[tenant.tap]` | absent | the central test-history store; `tap.port`, `tap.gate_token` and `tap.tokens` are set in one `tenant set` |
| `[tenant.release]` | absent | the nightly release; `release.clone`, `release.build` and `release.artifact` are set in one `tenant set` ([Releases and deploys](release.md#the-nightly-release)) |

**Review routes.** `[[tenant.review.route]]` is an ordered list of rules; each has `reviewer` (which reviewer runs: `dummy`, `basic` or `react`), `name` (whose name its replies carry, which the gate counts LGTMs by), and optionally `label`. When a PR version enters review, every rule whose label the PR wears adds its reviewer; a rule without `label` counts only when no labelled rule holds. The set is fixed for that version. Labels a rule names must exist on GitHub (`gh label create arc-bypass`). `dummy` runs no model and says LGTM; `basic` and `react` use the `[roles]` of the tenant clone's `.arc/config.toml` (at least `critic_l4`, or `default`) and the providers in that machine's `~/.tars/config.toml`.

Changing a value: the merge server reads `machine.toml` again each round, but the review service and the board read it when they start, so run `arc-server tenant check`, then restart them (`systemctl --user restart arc-review@<owner>-<name> arc-web`).

---

*Next: [Set up the pipeline](onboarding.md) · [The commands](commands.md) · [Troubleshooting](troubleshooting.md).*
