# Set up the pipeline

The pipeline is the server part of arc. Its services send each PR to its reviewers, land it only after they say LGTM and your own `merge.yml` passes, and ship what landed. They run on one machine you own; this page calls it the **merge machine**. Every machine where people or agents write code keeps just the `arc` command and talks to the merge machine.

This page takes you from installed binaries ([Install](install.md)) to a first PR that the pipeline landed. Every file and key it mentions is explained in [Configuration](configuration.md).

## 1. The services

The server suite comes in the same release as the CLI (`arc-suite-linux-x64.tar.gz`, `arc-suite-darwin-arm64.tar.gz`). The pipeline is five services:

| Service | How many | What it does |
|---|---|---|
| `arc-web` | one per machine | the board: projects and issues, review and change pages, merge queue, release page. Every client machine is given its address |
| `arc-bridge` | one per machine | rooms and messages between agent sessions, services and people ([Team up](bridge.md)); it also holds the issue board |
| `arc-review` | one per repo | takes each change `arc submit` sends, asks the reviewers your routes name, and grants the pass when they say LGTM ([Review on the pipeline](pipeline-review.md)) |
| `arc-server` | one per repo | takes a PR whose pass matches its current head, runs `merge.yml`, and lands it if the change adds no failure ([Merge](merge-gate.md)) |
| `arc-releaser` | one per repo, optional | once a night, tags the tip of the release branch and publishes a GitHub prerelease ([Releases and deploys](release.md)) |

The **pass** is the review service's permission to land one exact commit. A new push needs a new review.

Each repo the machine serves is called a **tenant**. A tenant has:

- one `[[tenant]]` table in `~/.arc/machine.toml`;
- one clone of the repo on the machine, used only by arc;
- its own copy of each per-repo service.

## 2. Choose the machine

**Recommended: Linux x86_64 with systemd user services.**

Turn on lingering for the user that runs the services. systemd user services belong to your login session: without lingering they stop when your last session ends (for example, when you log out of ssh) and do not come back after a reboot. Each service's `install` reminds you. Run this before you log out:

```bash
loginctl enable-linger $USER
```

**A Mac (Apple silicon)** has a `darwin-arm64` suite, but it is only good for trying review and merge by hand, not for a pipeline you leave running:

- each service's `install` writes only a systemd unit. arc writes no launchd job, so you start the services by hand (`arc-server --tenant <owner/name>`, `arc-review --tenant <owner/name>`, …), and nothing restarts one that crashes;
- `arc deploy` and the release page's **Deploy** button start the deploy with `systemd-run`, and refuse on a machine without it;
- `arc-server` and `arc-review` rely on systemd's watchdog (`WatchdogSec=300`) to restart one that hangs. Without systemd, a hung service stays hung.

If your merge gate needs macOS itself (an iOS or macOS build), there is no ready setup for it today.

Besides the suite, the machine needs `git` 2.38 or newer, a logged-in `gh`, and the tools your gate runs. See [Install](install.md#what-the-machine-needs-besides-arc).

## 3. Install and start the services

### 3.1 The merge machine

Unpack the suite and put its binaries on your `PATH` ([Install](install.md#the-server-suite)).

Every service reads its settings from one file, `~/.arc/machine.toml`, and from nowhere else. If a service finds an `ARC_*` environment variable that is not on its short allow-list, it refuses to start and says what replaced the variable.

Write the `[machine]` table first:

- `address`: the address other machines use to reach this one;
- `expose`: whether to listen on that address;
- `path`: the `PATH` every gate step gets.

```toml machine.toml
[machine]
address = "10.0.0.5"
expose  = true
path    = ["/home/ci/.cargo/bin", "/usr/local/bin", "/usr/bin", "/bin"]
```

Each binary writes its own systemd user unit and prints the commands that start it; you never write a unit by hand. Start the board and the chat server, which run once per machine:

```bash
arc-bridge install                    # writes arc-bridge.service
arc-web install                       # writes arc-web.service
systemctl --user daemon-reload
systemctl --user enable --now arc-bridge.service
systemctl --user enable --now arc-web.service
```

The board now answers at the address `arc-server tenant url web` prints (`http://<address>:8787` by default).

The per-repo services start once a repo is registered ([§4](#4-connect-a-repo)):

```bash
arc-server install <clone>            # registers the repo as a tenant, writes arc-server@.service (and the arc-rot@ units)
arc-review install                    # writes arc-review@.service
arc-releaser install <owner/name>     # optional, needs [tenant.release]: writes arc-releaser@.service and .timer
systemctl --user daemon-reload
systemctl --user enable --now arc-server@<owner>-<name>.service
systemctl --user enable --now arc-review@<owner>-<name>.service
systemctl --user enable --now arc-releaser@<owner>-<name>.timer
```

- The unit instance is the tenant name with `/` turned into `-` (`systemd-escape owner/name`).
- `arc-web` reads `machine.toml` only when it starts, so restart it after you register a repo (`systemctl --user restart arc-web`).
- `arc-server tenant show` prints every value in use and where it came from.
- `arc-server tenant check` checks each tenant and prints `ok`, `skip`, `warn` or `FAIL` for each check: `tenant-reads`, `paths-exist`, `home-is-clean-clone`, `home-is-canonical`, `name-agrees-with-origin`, `read-key-is-read-only`, `stores-in-home`, `files-read`, `units-carry-no-config`.

### 3.2 Clients and agent machines

On every machine that talks to the pipeline (your laptop, each machine an agent works on):

1. Write the board's address in `~/.arc/client.toml`. Use the value `arc-server tenant url web` printed ([Configuration](configuration.md#arcclienttoml--where-the-pipeline-is)):

   ```toml client.toml
   web = "http://10.0.0.5:8787"
   ```

2. Install your agent's hooks, so the reviewers' findings and each PR's result reach the agent's session: [Connecting your coding agent](coding-agents.md#2-the-agent-as-a-participant-bridge).

## 4. Connect a repo

Start a new repo with only review and the merge gate. Add the rest later, each with one more `tenant set`, after a first PR has landed: private dependencies, test history (TAP), the nightly release, and merge results in the chat channel. Each of them adds a store that must exist before the machine passes its checks.

**In the repo, on your laptop:**

1. Set up providers in `~/.tars/config.toml` and run `arc init` for `[roles]` ([Configuration](configuration.md#tarsconfigtoml--providers-and-keys)). On a feature branch, `arc local-review` and `arc fix` should now run.
2. Optionally write `presubmit.toml`: the checks `arc submit` runs before it pushes ([Configuration](configuration.md#repopresubmittoml--the-checks-before-submit)).
3. **Write the merge gate, `.github/workflows/merge.yml`.** The merge machine reads it from the base of each change and runs its steps in file order.
   - Write every step as a plain `run:`.
   - Write the trigger as `workflow_dispatch: {}`, so GitHub never runs it. It is not your `ci.yml`.
   - `arc workflow .github/workflows/merge.yml --job <job> --list` prints what would run and names each step arc cannot run.

   What arc accepts, and a minimal file: [Merge](merge-gate.md#a-minimal-mergeyml).
4. Create the labels you will route or hold PRs by: `gh label create arc-hold`, and `gh label create arc-bypass` if a route names it.

Commit `presubmit.toml` and `merge.yml` on the target branch.

**On the merge machine:**

1. **Make a clone that only arc works in.** Not a worktree, not anyone's working directory, at its real path (no symlink), with `origin` pointing at the repo. The merge server checks it out and cleans it every round.

   ```bash
   git clone git@github.com:acme/widgets.git ~/widgets-ci
   git -C ~/widgets-ci status --porcelain            # prints nothing
   ```

2. **Make sure main passes the gate on this machine.** The merge server lands a change when it adds no new failure compared with its base. If a *step* of the gate fails on the base itself (a missing tool, not a failing test), the merge server cannot tell which failures are new. It then answers `cannot_say` for every PR, including the PR that would fix that step, because that PR must pass the same gate. So run the gate on main here first, and fix what fails outside the queue:

   ```bash
   cd ~/widgets-ci && arc workflow .github/workflows/merge.yml --job <job>
   ```

3. **Register the repo:** `arc-server install ~/widgets-ci`. The tenant gets its name from `origin`. To land on a branch other than `main`, run `arc-server tenant add ~/widgets-ci --target <branch>` first; `arc-server install` keeps that setting. Change any tenant key with `arc-server tenant set` ([the keys](configuration.md#tenant--once-per-repo)).

4. **Choose who reviews (routes).** `arc-review` sends every open PR to reviewers according to the `[[tenant.review.route]]` rules under the tenant in `~/.arc/machine.toml`. A PR enters the merge queue only after those reviewers say LGTM. **With no route, nothing lands.** For a repo nobody else reviews, send every PR to the dummy reviewer, which says LGTM to everything ([Review on the pipeline](pipeline-review.md)):

   ```toml machine.toml#tenant
   [[tenant.review.route]]
   reviewer = "dummy"
   name     = "dummy"
   ```

   A real reviewer (`reviewer = "react"`) needs `[roles]` in the clone's own `.arc/config.toml` (run `arc init` in `~/widgets-ci`; `.arc/` does not make the clone count as unclean) and providers in this machine's `~/.tars/config.toml`.

5. **Check, then start the repo's services** ([§3.1](#31-the-merge-machine)). Run `arc-server tenant check acme/widgets` until every line says `ok` or `skip`. Then enable `arc-review@acme-widgets.service` and `arc-server@acme-widgets.service`, and restart `arc-web`. Both services run the offline checks for their repo when they start, and refuse to start on a `FAIL`.

## 5. Submit: the first PR

From a feature branch on your laptop:

```bash
arc local-review && arc fix            # optional: review and fix it on your machine first
arc submit                             # push the branch, open (or reuse) the PR, queue its review
```

`arc submit` runs the checks in `presubmit.toml`, pushes the branch, opens the PR (or reuses the open one), puts it in the review queue, and exits. The pipeline does the rest: review ([Review on the pipeline](pipeline-review.md)), then the merge gate and landing ([Merge](merge-gate.md)), then deploys ([Releases and deploys](release.md)). Watch it on the board, or on the merge machine with `journalctl --user -u arc-review@acme-widgets.service -u arc-server@acme-widgets.service -f`.

- **To keep a PR from landing,** add the label `arc-hold`.
- **Write issues with `arc issues`.** The board (`b/<n>`) is where issues really live; GitHub only keeps a copy. A `b/<n>` in a PR title records each submission on that issue. If arc cannot record it (the issue does not exist, or the board cannot be reached), `arc submit` has still pushed the branch and queued the review; it names the issue and exits 8.

## 6. Your data

What the pipeline collects (test results and your agents' conversations) and where on your machines it is stored: [Your data](data.md).

## 7. Serve several repos from one machine

Everything that belongs to one repo is set per tenant. The board and the chat server are shared.

| | Per repo (tenant) | Once per machine |
|---|---|---|
| config | one `[[tenant]]` table in `~/.arc/machine.toml` | `[machine]` in the same file |
| clone | a clone only arc uses; its stores (`merge.db`, `review.db`, …) live in its `.git/arc/` | — |
| services | `arc-server@<owner>-<name>`, `arc-review@<owner>-<name>`, and when turned on `arc-releaser@…`, `arc-tap@…`, `arc-rot@…` | `arc-web`, `arc-bridge` |
| repo files | its own `merge.yml`, `presubmit.toml`, `.arc/delivery.toml`; the clone's `.arc/config.toml` | — |

Two repos never share a gate, a review route, a release or a store. A broken config in one repo stops only that repo's services.

- To add a repo, repeat [§4](#4-connect-a-repo) for it.
- `arc-server tenant list` names every tenant.
- To remove one, disable its units, then run `arc-server tenant remove <owner/name>`. Its clone and history stay on disk.
- `arc-server tenant check --offline` with no name checks every tenant and exits 1 if any line says `FAIL`. Run it after each step and before every upgrade ([Install](install.md#upgrade)).

## 8. When something is off

| What you see | Where to look |
|---|---|
| a service's log starts `refusing to start: arc takes no input from the environment` | the log names each `ARC_*` variable and what replaced it; check `systemctl --user show-environment` too |
| `refusing to start — \`arc-server tenant check <owner/name>\` fails:` | the `FAIL` lines under it; usually the clone has uncommitted files, or is not at its real path |
| `… is too old — refusing to start (need git >= 2.38)` | upgrade git on the merge machine |
| a PR never enters the merge queue | check that its base is the tenant's `target`; that a route covers it (`arc-server tenant show`); that its reviewers said LGTM on its current head; and that it has no `arc-hold` label |
| every PR comes back `cannot_say` | a step of `merge.yml` fails on the base, or is a step arc cannot run: run the gate on main on this machine (§4) |
| a client's hooks or `arc tap` ignore the pipeline | `cat ~/.arc/client.toml`, then `curl <web>/api/machine`: the board should list the chat server and the repo |

Problems with local runs (providers, `.arc/config.toml`, presubmit): [Troubleshooting](troubleshooting.md).

---

*Next: [Review on the pipeline](pipeline-review.md) · [Merge](merge-gate.md) · [Team up](bridge.md).*
