# Configuration

arc's settings live in several files. Each file holds one kind of setting, belongs to one party, and no setting appears in two files.

| File | Belongs to | What it holds | Commit it? |
|---|---|---|---|
| `~/.tars/config.toml` | you, on each machine | the LLM providers: type, model, credentials | **never** |
| `<repo>/.arc/config.toml` | this clone of the repo | which provider plays which role (`[roles]`), what review skips and how long a local review goes on (`[review]`), where test results are (`[test]`), which job deploys (`[release]`) | no |
| `<repo>/presubmit.toml` | the project | the checks `arc submit` runs on your machine before it pushes; `arc fix` tells the Fixer to run them too | **yes** |
| `<repo>/.github/workflows/merge.yml` | the project | the merge gate: what the pipeline runs before it lands a PR ([Merge](merge-gate.md)) | **yes** |
| `<repo>/.arc/delivery.toml` | the project | how the project ships: `[builds.*]`, `[targets.*]` ([Releases and deploys](release.md#delivery-toml)) | **yes** |
| `~/.arc/client.toml` | each machine that talks to the pipeline | the address of the pipeline's board | no |
| `~/.arc/machine.toml` | the pipeline machine | the repos it serves (each one is called a **tenant**) and how: gate, reviewers, release | no |

Which files you need where:

- **On a machine where you write code:** `~/.tars/config.toml`, the repo's `.arc/config.toml` (written by `arc init`) and `~/.arc/client.toml`.
- **Committed in the repo:** `presubmit.toml` (optional), `merge.yml`, and `delivery.toml` once you ship.
- **On the pipeline machine:** `~/.arc/machine.toml`, its own `~/.tars/config.toml`, and the `.arc/config.toml` of each repo's clone there.

Each file is explained below. [Set up the pipeline](onboarding.md) writes them with you, in order.

`arc` takes its runtime inputs as command-line flags, not environment variables. The one environment variable it reads for you is the API key a tars provider names (below).

## `~/.tars/config.toml` — providers and keys

This is the only place where a model name or a credential is written. arc reads providers from nowhere else, so one file serves every repo on the machine.

Each provider is a table, named by an id you choose. `[roles]` in `.arc/config.toml` refers to that id. An unknown key in a provider table is refused, and the error names the key.

To use another file, pass `--tars-config <file>` to any arc command, or `--tars_home <dir>` for a whole tars home (arc reads its `config.toml`). With neither, arc reads `$TARS_HOME/config.toml`, and if that is not set, `~/.tars/config.toml`. Pass the same flag to every arc call.

### No API key: use the Claude Code you are signed in to

If `claude` works in your terminal, arc can review and fix through it. The `claude_cli` type uses your own `claude login`; there is no key to create or export.

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

Both CLI types also take `executable` (default `claude`, `codex`) when the binary is not on `PATH` under that name.

- arc's own tests run `claude_cli` as a Fixer from start to finish. `codex_cli` is accepted and run the same way, but has not been tested as a Fixer from start to finish.
- With either one, the Critic and the Fixer come from the same model family. A Critic from another family (next section) keeps the review more independent.

More on each agent: [Connecting your coding agent](coding-agents.md).

### With an API key

```toml ignore: ~/.tars/config.toml, tars's file, not arc's
# ~/.tars/config.toml
[providers.gemini_flash]
type = "gemini"
default_model = "flash@latest"
auth = { kind = "secret", secret = { source = "env", var = "GEMINI_API_KEY" } }
```

Export the variable the provider names (`export GEMINI_API_KEY=…`) in the shell you run arc from.

- **`type`** — one of `openai`, `openai_compat`, `anthropic`, `gemini`, `bedrock`, `vllm`, `mlx`, `llamacpp`, `claude_cli`, `claude_sdk`, `codex_cli`, `opencode`, `antigravity`.
- **`default_model`** — a model id to pin one model, or `<series>@latest` (for example `flash@latest`) to always take the newest model of a series. Only some providers define series; for the others, write a model id. Run records always name the model that actually ran, never `@latest`.
- **`auth`** — `{ kind = "secret", secret = { source = "env", var = "NAME" } }` reads the key from an environment variable; `secret = { source = "file", path = "…" }` reads it from a file. `{ kind = "none" }` is for local servers. The CLI types (`claude_cli`, `codex_cli`) use your own login and take no `auth`.

To use a different model for a role, add a second provider entry with its own `default_model`.

## `<repo>/.arc/config.toml` — this clone's routing

This file says how *this clone* is set up. It differs from machine to machine, so it is not committed. `arc init` writes `.arc/.gitignore`, which ignores everything under `.arc/` (itself included) except `config.toml.example`, `delivery.toml`, `archcheck.toml` and `arch_waivers.txt`. To share a template, commit `config.toml.example`.

### What `arc init` writes

- **In a terminal:** it reads your tars providers, asks which one reviews (the critic) and which one fixes (the fixer), and writes `.arc/config.toml` with:
  - `[roles]`: `default`, `critic`, `critic_l4`, `critic_l5` set to the critic's provider, `fixer` set to the fixer's;
  - `[review] exclude`: a starter list of directories that are not source (tests, docs, vendor, build output, …);
  - `[test]`: commented out, for you to fill in.
- **Not in a terminal** (CI, a script): it writes `.arc/config.toml.example` instead and exits non-zero, telling you to copy it to `.arc/config.toml`.
- **If `.arc/config.toml` already exists:** it refuses. `arc init --force` overwrites it.
- **If tars has no providers:** it stops and asks you to define one first.

### `[roles]` — which provider plays which part

```toml config.toml
[roles]
default   = "gemini_flash"   # any role not listed below
critic    = "gemini_flash"
critic_l4 = "gemini_flash"   # per-file review
critic_l5 = "gemini_flash"   # whole-repo rot review
fixer     = "claude_fixer"   # must be written out: `default` does not cover it
```

Each value is a provider id from `~/.tars/config.toml`. A role you leave out uses `default`, except `fixer`, which you must always name. Choosing a critic and a fixer from different model families keeps the review independent.

There is no `[providers]` section here. If the file still has one, arc refuses it and names each `[providers.<id>]` block: move those definitions to `~/.tars/config.toml` and keep `[roles]`.

### `[review]` — what review skips, and how long a local review goes on

```toml config.toml
[review]
exclude = ["**/tests/**", "**/docs/**", "**/vendor/**", "**/node_modules/**"]
# max_rounds  = 5    # reviewer replies without an LGTM before arc fix lets the head through
# react_turns = 24   # model calls the reviewer may take on one review
```

- `exclude` is the full list of paths that review and `arc rot` skip; arc has no built-in list. Each entry is a glob matched against the file's path from the repo root: `*` stays inside one directory, `**` crosses any number of them. To skip a directory, write `dir/**`. `"tests/**"` skips only the top-level `tests/`; `"**/tests/**"` skips every `tests/`. A malformed glob is an error when the file is read.
- `max_rounds` (default 5) and `react_turns` (default 24) limit a **local** review: `arc local-review` and `arc fix` in this clone. The pipeline's review has its own limits in `machine.toml` (`review.max_rounds`, `review.react_turns`, [below](#arcmachinetoml--the-pipeline-machine)).
- The keys `enable`, `disable`, `experimental` and `confidence_floor` are still accepted, but nothing reads them: a local review runs only the stable rules.

### `[test]` — where your test results are

```toml config.toml
[test]
junit = "target/nextest/arc-tap/junit.xml"
```

arc never runs your tests; it reads the JUnit XML your test runner writes. `arc tap init` sets up your runner and prints the value to put in `junit`. The path is relative to the repo root.

By default `arc fix` writes tests for its fixes. `generate = false` turns that off.

### `[release]` — which job is your deploy

```toml config.toml
[release]
workflow = ".github/workflows/deploy.yml"
job      = "deploy"
```

You write this in the repo's clone on the pipeline machine, where deploys run. See [Releases and deploys](release.md).

### A complete small example

```toml config.toml
[roles]
default = "claude_critic"
fixer   = "claude_fixer"

[review]
exclude = ["**/tests/**", "**/docs/**", "**/node_modules/**", "**/dist/**"]
```

## `<repo>/presubmit.toml` — the checks before submit

This file lists the checks a change must pass. It is committed at the repo root, because the checks are the same in every clone.

- `arc submit` runs the checks before it pushes anything, and pushes the results along with the branch.
- `arc presubmit` runs the checks alone: it pushes nothing and records nothing.
- `arc fix` gives the Fixer the same checks, to run before it calls a finding fixed. Placeholders are filled in for the pull request: `{target}` is the PR's target branch on `origin`, `{base}` is the commit where HEAD forks from it, and `{affected}` is the packages the change reaches. In a repo without this file, the Fixer is told to find the build and test commands itself.

```toml presubmit.toml
timeout_seconds = 1800   # per check; a check past it is killed with its whole process group

[[checks]]
name = "merge-check"
command = "git merge-tree --write-tree HEAD {target}"

[[checks]]
name = "clippy"
command = "cargo clippy --all-targets -- -D warnings"
```

### How the checks run

- `arc submit` runs the commands in the current branch's `presubmit.toml`, as you.
- The checks run in order, through `sh -c`, at the repo root. Every check runs; one that fails does not stop the ones after it.
- Each check runs in its own process group. When it ends, passed or not, arc kills the whole group. Ctrl-C (or a SIGTERM to arc) kills the check that is running.
- No environment variable is set for a check.
- A check's output goes to a temporary file, not a pipe, so a background job that keeps the output open does not keep the run waiting. `timeout_seconds` limits the wait.

### Passes are remembered

- A check that already passed on this commit is skipped. arc remembers each pass under `.arc/cache/presubmit/<commit>/`, one file per command, named by the hash of the command text with the placeholders filled in. So `arc presubmit` followed by `arc submit` of the same HEAD with the same flags runs nothing twice, and a rerun after a failure runs only what has not passed yet. If a pass cannot be written down, the run stops.
- A check that does run needs a clean working tree (no uncommitted changes, untracked files included), because its pass is recorded for HEAD. If the tree changes or HEAD moves while it runs, no pass is recorded. When every check already passed on HEAD, nothing runs, and a dirty tree does not matter, since HEAD is what gets pushed.
- The record is the author's own: presubmit is not a security boundary. The merge gate is.

### Placeholders: `{base}`, `{target}`, `{affected}`

- A command may use `{base}`, `{target}` and `{affected}`. Each value is quoted for `sh`; `{affected}` becomes one quoted word per package.
- `{base}` and `{target}` come from the run's `--base <sha>` and `--target <ref>`. arc fetches nothing, so usually you run `git fetch origin`, then pass `--base "$(git merge-base HEAD origin/main)"` and `--target origin/main`.
- arc works out `{affected}` itself: the packages that the change from `--base` to the checked commit reaches, computed the same way as `arc affected --base <base>` (none when the change is in no package). `--affected <package>...` overrides it; `--affected` alone says the change reaches no package.
- If the packages cannot be worked out, arc uses every package in the workspace and prints the error. If even the workspace cannot be listed, no check runs. The output, and the `affected` field of `--json`, says which packages were used and where the list came from: `given`, `computed` or `full`.
- If a check uses a placeholder that has no value (its flag was not given; for `{affected}`, neither `--affected` nor `--base`), the run stops before any check runs, with exit 2, naming the check and the missing flag.
- arc replaces only those three spellings. Every other brace (`${HOME}`, `{ cmd; }`, awk's `'{print}'`) reaches the shell as written.

### When a check fails

- A check that ran and did not pass makes arc exit 11. arc prints, for that check:
  - its name;
  - how it ended: `it exited with code N`, `signal N killed it`, or `it ran past its Ns timeout and was killed`;
  - the command as it ran;
  - the failures arc's test reader finds in the output (tests, compile errors, denied lints), each in its own words;
  - the output itself: the start and the end, with the number of bytes cut stated where they were cut.
  When no line names a failure, only the output is shown. A check that could not start says why. The run still runs every check before it exits 11.
- Under `--json`, `checks` lists every check in order. Each is an object with `name`, `command`, `result` (`passed`, `passed_before`, `failed`, `timed_out`, `not_started`) and `duration_ms`. A failed check adds `exit_code`, `signal`, `failures` (`[{unit, excerpt}]`, or `null` when none is named) and `output` (`null` when it printed nothing). A timed-out check adds `timeout_seconds`, `failures` and `output`. A check that did not start adds `why`. `passed` says whether all of them passed.

### What `arc submit` does with the results

- A failed check does not stop `arc submit`: it still pushes the branch and sends the PR to review, then exits 11 after naming the checks that did not pass.
- Before it sends the PR to review, `arc submit` writes the results on the pushed commit as a git note under `refs/notes/arc-presubmit`, and pushes it to origin on top of the notes already there. The note is JSON: `{"checks": [{"name", "kind": "passed"|"passed_before"|"failed"|"not_run", "took_ms", "reason"}]}`. `not_run` is a check that ran past its timeout or could not start, and `reason` is what the terminal said. The PR's page and the review board show the note; a commit without one shows "no record".
- If origin does not accept the note, arc says so in one line, and `--json`'s `presubmit_note` says `not_pushed` with git's words. Nothing fails because of it. `arc presubmit` and `--dry-run` write no note.
- After the checks, `arc submit` pushes the branch itself. It never pushes over commits the remote branch has and HEAD does not: such a push is refused, never forced. arc checks for this before any check runs, along with these other refusals: a PR already open when you did not pass `--pr`; a `--pr` that is not the branch's open PR; a PR aimed at another branch; an origin with no default branch.

### The file itself

- No `presubmit.toml` means no checks: `arc submit` just submits.
- A misspelt key, no `[[checks]]`, a zero limit, or a `timeout_seconds` over 86400 is refused when the file is read.
- `.arc/config.toml` no longer has a `[gate]` section. A file that still has one is not refused (each part of arc reads only its own section), so the leftover is just ignored. Delete it.

## `<repo>/.arc/delivery.toml` — how the project ships

This file **is committed**, because how the project builds and where the output goes is the same in every clone. It holds `[builds.<id>]` (how to build something you ship) and `[targets.<id>]` (where it goes). The release page is drawn from it. Both are explained, with an example, in [Releases and deploys](release.md#delivery-toml).

A build or target id may be declared here or in `.arc/config.toml`, not in both. The same id in both files is an error; one does not override the other.

## `~/.arc/client.toml` — where the pipeline is

Every machine that talks to the pipeline (your laptop, each agent's machine) has this file with one line: the address of the pipeline's board (the `arc-web` service).

```toml client.toml
# ~/.arc/client.toml
web = "http://<board-host>:<port>"
```

- The file has exactly this one key. A misspelt key is refused, not ignored.
- Clients ask the board for every other address (where the chat server is, where this repo's test history goes), so those are written only once, on the pipeline machine.
- Without `client.toml`, the bridge hooks let every stop through, and `arc tap` writes to the repo's own `.arc/tap.db`.
- On the pipeline machine, `arc-server tenant url web` prints the address to put here ([Set up the pipeline](onboarding.md#32-clients-and-agent-machines)).

## `~/.arc/machine.toml` — the pipeline machine

Only the machine that runs the server suite has this file. Every service reads its settings from this file and nowhere else:

- a systemd unit carries no settings;
- a service started with an `ARC_*` environment variable that is not on its short allow-list refuses to start, and says what replaced the variable;
- `--config FILE` points a service at another file.

The file lists the repos the machine serves. Each repo is a **tenant**: a `[[tenant]]` table saying how the machine serves it. You do not write a tenant's first lines by hand: `arc-server install <clone>` (or `arc-server tenant add <clone>`) registers the repo and writes `id`, `name` and `home`. After that, use these commands:

```bash
arc-server tenant show [owner/name]                    # every value, and whether it came from machine.toml or the default
arc-server tenant set owner/name gate.rerun=never      # change tenant keys; several key=value at once
arc-server tenant unset owner/name gate.rerun          # back to the default; `tap` or `release` drops that whole table
arc-server tenant check [owner/name]                   # paths exist, the clone is clean, the stores are in place
arc-server tenant url web                              # the board's address, for client.toml
arc-server tenant list                                 # every tenant, one per line
```

`tenant set` changes only `[[tenant]]` keys. Edit `[machine]` and the `[[tenant.review.route]]` rules in the file. Every table refuses keys it does not know. A mistake in `[machine]` stops every service. A mistake in one `[[tenant]]` stops only that tenant, with an error naming the table, the key and the reason; the other tenants keep running.

### A complete file

One repo, `acme/widgets`, reviewed by a real reviewer, plus a label that lets a PR through on the dummy reviewer:

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

For a repo nobody else reviews, use one rule that sends every PR to the dummy reviewer. Every PR still goes through review, and lands on the dummy's LGTM:

```toml machine.toml#tenant
[[tenant.review.route]]
reviewer = "dummy"
name     = "dummy"
```

### `[machine]` — once per machine

| Key | Default | What it does |
|---|---|---|
| `address` | none | this machine's IP address (not a host name); the addresses of the board, the chat server and the test-history store are built from it |
| `expose` | `false` | `true`: listen on `address`, so other machines can reach the board and the chat server; `false`: listen on loopback only. `true` without `address` is refused |
| `path` | the service manager's | the `PATH` for every gate step and deploy step. Put the toolchains your `merge.yml` needs here |
| `[machine.web] port` | `8787` | the board's port; `client.toml` names `http://<address>:<port>` |
| `[machine.bridge] port` | `8790` | the chat server's port; clients learn it from the board |
| `[[machine.disk]]` | none | `mount`, `min_free_gib` (and optionally `min_free_inodes`): while a mount has less free space than this, the merge server starts no round, and the nightly release and deploys refuse to run |

### `[[tenant]]` — once per repo

| Key (name for `tenant set`) | Default | What it does |
|---|---|---|
| `target` | `main` | the branch PRs land on |
| `queue.admit` | `pr` | `pr`: an open PR enters the queue only when its pass matches its current head. `any`: everything pushed, for a remote without PRs |
| `gate.timeout_secs` | `3600` | time limit for one gate step; the step is killed with its process group |
| `gate.round_timeout_secs` | 4 × `gate.timeout_secs` | time limit for a whole merge round (fetch, merge, every gate run, push) |
| `gate.rerun` | `once` | `once`: a new failure must show up twice on the same commit before the PR is sent back. `never`: the first failing run decides |
| `gate.too_divergent` | `100` | the number of conflicting paths at which a round stops as "too divergent" without running the gate |
| `gate.fetch_private_deps_over_ssh` | `false` | `true` gives every step `CARGO_NET_GIT_FETCH_WITH_CLI=true`, so cargo fetches private git dependencies with the service user's own git credentials |
| `gate.read_key` | none | a read-only deploy key; only `tenant check` uses it, to prove the key cannot push |
| `[[tenant.review.route]]` | none | who reviews which PR (below). **With no rule, nobody reviews and nothing lands** |
| `review.gate` | `all_lgtm` | which LGTMs grant the pass: `all_lgtm`, every reviewer of the current head; `one_lgtm`, any one of them |
| `review.max_rounds` | `5` | how many replies a reviewer may give without an LGTM; at the limit it counts as an LGTM and the reviewer stops |
| `review.react_turns` | `24` | how many model calls the `react` reviewer may make on one review |
| `review.reviewer_timeout_secs` | `3600` | how long a reviewer may run before it is killed and called again |
| `review.reviewer_attempts` | `3` | how many calls in a row may end without a reply before the review stops and says so in the PR's chat channel |
| `review.fixer_client` | `author` | who answers the findings: `author` (they are sent to the author's agent session over the chat server), `claude` (`claude -p` fixes them in a worktree of the PR's head), `tars` (arc's own fixer), `nothing` (the author runs `arc submit` again) |
| `review.model_config` | the clone's `.arc/config.toml` | another file whose `[roles]` the real reviewers use |
| `bridge.enabled` | `false` | `true`: the merge server posts each round's result into the PR's chat channel, as `merger@<owner>:<name>` |
| `github.mirror` | `true` | `false`: reviews are not posted on the PR and the issue board is not copied to GitHub issues; both stay in arc |
| `[tenant.tap]` | absent | the central test-history store; set `tap.port`, `tap.gate_token` and `tap.tokens` in one `tenant set` |
| `[tenant.release]` | absent | the nightly release; set `release.clone`, `release.build` and `release.artifact` in one `tenant set` ([Releases and deploys](release.md#the-nightly-release)) |

**Review routes.** `[[tenant.review.route]]` is an ordered list of rules. Each rule has:

- `reviewer`: which reviewer runs, `dummy`, `basic` or `react`;
- `name`: the name its replies are signed with; the gate counts LGTMs by this name;
- `label` (optional): the PR label the rule applies to.

When a new version of a PR enters review, every rule whose label the PR has adds its reviewer. A rule without `label` applies only when no labelled rule does. The set of reviewers is then fixed for that version. Every label a rule names must exist on GitHub (`gh label create arc-bypass`). `dummy` runs no model and says LGTM. `basic` and `react` use the `[roles]` from the `.arc/config.toml` in the tenant's clone (at least `critic_l4`, or `default`) and the providers in that machine's `~/.tars/config.toml`.

**Changing a value.** The merge server reads `machine.toml` again every round, but the review service and the board read it only when they start. So run `arc-server tenant check`, then restart them (`systemctl --user restart arc-review@<owner>-<name> arc-web`).

---

*Next: [Set up the pipeline](onboarding.md) · [The commands](commands.md) · [Troubleshooting](troubleshooting.md).*
