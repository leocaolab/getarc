# Set up the pipeline

The pipeline is the server half of arc: services that route each PR to its reviewers, land it only on their LGTM and your own `merge.yml`, and ship what landed. They run on one machine you own (below, the **merge machine**); every machine where people or agents write code keeps the plain `arc` CLI and talks to it. This page goes from installed binaries ([Install](install.md)) to a first PR the pipeline landed; every file and key it writes is in [Configuration](configuration.md).

## 1. The services

The server suite ships on the same release as the CLI (`arc-suite-linux-x64.tar.gz`, `arc-suite-darwin-arm64.tar.gz`). The pipeline is five services:

| Service | How many | What it does |
|---|---|---|
| `arc-web` | one per machine | the board: projects and issues, review and change pages, merge queue, release page; and the one address every client is given |
| `arc-bridge` | one per machine | rooms and messages between agent sessions, services and people ([Team up](bridge.md)); also the issue board |
| `arc-review` | one per repo | takes each update `arc submit` queues, asks the reviewers your routes name, grants the pass on their LGTM ([Review on the pipeline](pipeline-review.md)) |
| `arc-server` | one per repo | takes a PR whose pass matches its head, runs `merge.yml`, lands it when the change adds no failure ([Merge](merge-gate.md)) |
| `arc-releaser` | one per repo, optional | once a night, tags the release branch's tip and publishes a GitHub prerelease ([Releases and deploys](release.md)) |

Each repo the machine serves is a **tenant**: one `[[tenant]]` table in `~/.arc/machine.toml`, one clone on the machine that only arc works in, and its own instances of the per-repo services.

## 2. Choose the machine

**Recommended: Linux x86_64 with systemd user services.** For the services to stay up, turn lingering on for the user that runs them: systemd user services follow the login session, so without it they stop when your last session ends (an ssh logout) and do not come back after a reboot. Each service's `install` reminds you of this line; run it before you log out:

```bash
loginctl enable-linger $USER
```

**A Mac (Apple silicon)** has a `darwin-arm64` suite, but it is fit only for trying review and merge by hand, not for a pipeline you leave running:

- each service's `install` writes only a systemd unit; arc writes no launchd job, so you start the services by hand (`arc-server --tenant <owner/name>`, `arc-review --tenant <owner/name>`, …) and nothing restarts one that crashes;
- `arc deploy` and the release page's **Deploy** button start the deploy with `systemd-run`, and refuse on a machine that has none;
- `arc-server` and `arc-review` rely on systemd's watchdog (`WatchdogSec=300`) to restart one that hangs; with no systemd, a hung service stays hung.

A project whose merge gate needs macOS itself (an iOS or macOS build) has no ready path today.

What the machine needs besides the suite — `git` 2.38 or newer, a logged-in `gh`, the tools your gate runs — is in [Install](install.md#what-the-machine-needs-besides-arc).

## 3. Install and start the services

### 3.1 The merge machine

Unpack the suite and put its binaries on `PATH` ([Install](install.md#the-server-suite)). Every service reads one file, `~/.arc/machine.toml`. They take no settings from the environment: a service that finds an `ARC_*` variable outside its short allow-list refuses to start and says what replaced it.

Write `[machine]` first — the address other machines reach this one at, whether to listen on it, and the `PATH` every gate step gets:

```toml machine.toml
[machine]
address = "10.0.0.5"
expose  = true
path    = ["/home/ci/.cargo/bin", "/usr/local/bin", "/usr/bin", "/bin"]
```

Each binary writes its own systemd user unit and prints the lines that start it; nobody writes a unit by hand. The board and the chat server are one per machine:

```bash
arc-bridge install                    # writes arc-bridge.service
arc-web install                       # writes arc-web.service
systemctl --user daemon-reload
systemctl --user enable --now arc-bridge.service
systemctl --user enable --now arc-web.service
```

The board now answers at the address `arc-server tenant url web` prints (`http://<address>:8787` by default). The per-repo services start once a repo is registered ([§4](#4-connect-a-repo)):

```bash
arc-server install <clone>            # registers the repo as a tenant, writes arc-server@.service (and the arc-rot@ units)
arc-review install                    # writes arc-review@.service
arc-releaser install <owner/name>     # optional, needs [tenant.release]: writes arc-releaser@.service and .timer
systemctl --user daemon-reload
systemctl --user enable --now arc-server@<owner>-<name>.service
systemctl --user enable --now arc-review@<owner>-<name>.service
systemctl --user enable --now arc-releaser@<owner>-<name>.timer
```

The unit instance is the tenant name with `/` turned into `-` (`systemd-escape owner/name`). `arc-web` reads `machine.toml` once, when it starts: restart it after registering a repo (`systemctl --user restart arc-web`). `arc-server tenant show` prints every value in effect and where it came from; `arc-server tenant check` checks each tenant — `tenant-reads`, `paths-exist`, `home-is-clean-clone`, `home-is-canonical`, `name-agrees-with-origin`, `read-key-is-read-only`, `stores-in-home`, `files-read`, `units-carry-no-config` — and prints `ok`, `skip`, `warn` or `FAIL` for each.

### 3.2 Clients and agent machines

On every machine that talks to the pipeline — your laptop, each machine an agent works on:

1. Write the board's address in `~/.arc/client.toml`, the value `arc-server tenant url web` printed ([Configuration](configuration.md#arcclienttoml--where-the-pipeline-is)):

   ```toml client.toml
   web = "http://10.0.0.5:8787"
   ```

2. Install your agent's hooks, so the reviewers' findings and each PR's outcome reach its session: [Connecting your coding agent](coding-agents.md#2-the-agent-as-a-participant-bridge).

## 4. Connect a repo

Start a new repo with only the review and the merge gate. Private dependencies, test history (TAP), the nightly release and chat-channel verdicts are each one more `tenant set` after a first PR has landed: each adds a store that must exist before the machine passes its checks.

**In the repo, on your laptop:**

1. Providers in `~/.tars/config.toml` and `arc init` for `[roles]` ([Configuration](configuration.md#tarsconfigtoml--providers-and-keys)); on a feature branch, `arc local-review` and `arc fix` should run.
2. `presubmit.toml` (optional): the checks `arc submit` runs before it pushes ([Configuration](configuration.md#repopresubmittoml--the-checks-before-submit)).
3. **The merge gate, `.github/workflows/merge.yml`.** The merge machine reads it from the base of every change and runs its steps in file order. Write every step as a plain `run:` and the trigger as `workflow_dispatch: {}`, so GitHub never runs it; it is not your `ci.yml`. `arc workflow .github/workflows/merge.yml --job <job> --list` prints what would run and names each step arc cannot run. What is accepted, and a minimal file: [Merge](merge-gate.md#a-minimal-mergeyml).
4. The labels you will route or hold by: `gh label create arc-hold`, and `gh label create arc-bypass` if a route names it.

Commit `presubmit.toml` and `merge.yml` on the target branch.

**On the merge machine:**

1. **A clone only arc works in** — not a worktree, not anyone's working directory, at its real path (no symlink), its `origin` the repo. The merge server checks it out and cleans it every round.

   ```bash
   git clone git@github.com:acme/widgets.git ~/widgets-ci
   git -C ~/widgets-ci status --porcelain            # prints nothing
   ```

2. **Main must be green on this machine.** The merge server lands a change when it adds no new failure against its base. If a *step* of the gate fails on the base (a missing tool, not a failing test), it cannot tell which failures are new and answers `cannot_say` for every PR — the one that would fix that step included, because it must pass the same gate. So run the gate on main here first, and fix what is red outside the queue:

   ```bash
   cd ~/widgets-ci && arc workflow .github/workflows/merge.yml --job <job>
   ```

3. **Register it:** `arc-server install ~/widgets-ci`. The tenant's name is the one `origin` gives. To land on a branch other than `main`, run `arc-server tenant add ~/widgets-ci --target <branch>` first; `arc-server install` keeps it. Change any tenant key with `arc-server tenant set` ([the keys](configuration.md#tenant--once-per-repo)).

4. **Routes: who reviews.** `arc-review` routes every open PR by the `[[tenant.review.route]]` rules under the tenant in `~/.arc/machine.toml`, and only the reviewers' LGTM lets a PR into the merge queue. **With no route, nothing lands.** A repo nobody else reviews routes every PR to the dummy reviewer, which says LGTM to everything ([Review on the pipeline](pipeline-review.md)):

   ```toml machine.toml#tenant
   [[tenant.review.route]]
   reviewer = "dummy"
   name     = "dummy"
   ```

   A real reviewer (`reviewer = "react"`) needs `[roles]` in the clone's own `.arc/config.toml` — run `arc init` in `~/widgets-ci`; `.arc/` does not count against a clean clone — and providers in this machine's `~/.tars/config.toml`.

5. **Check, then start its services** ([§3.1](#31-the-merge-machine)): `arc-server tenant check acme/widgets` until every line says `ok` or `skip`; then enable `arc-review@acme-widgets.service` and `arc-server@acme-widgets.service`, and restart `arc-web`. Both services run the offline checks for their repo when they start and refuse to start on a `FAIL`.

## 5. Submit: the first PR

From a feature branch on your laptop:

```bash
arc local-review && arc fix            # optional: review and fix it on your machine first
arc submit                             # push the branch, open (or reuse) the PR, queue its review
```

`arc submit` runs `presubmit.toml`'s checks, pushes the branch, opens or reuses its PR, puts the update on the review queue, and exits. The pipeline takes it from there: review ([Review on the pipeline](pipeline-review.md)) → the merge gate and landing ([Merge](merge-gate.md)) → deploys ([Releases and deploys](release.md)). Watch it on the board, or on the machine with `journalctl --user -u arc-review@acme-widgets.service -u arc-server@acme-widgets.service -f`.

- **To keep a PR from landing,** label it `arc-hold`.
- **Issues go through `arc issues`.** The board (`b/<n>`) is the source of truth and GitHub is its mirror. A `b/<n>` in a PR title records each submission on that issue. When it cannot record one — the issue does not exist, or the board cannot be reached — `arc submit` has still pushed the branch and queued the review; it names the issue and exits 8.

## 6. Your data

What the pipeline collects — test results and your agents' conversations — and where on your machines it is stored: [Your data](data.md).

## 7. Serve several repos from one machine

Everything that belongs to one repo is per tenant; the board and the chat server are shared.

| | Per repo (tenant) | Once per machine |
|---|---|---|
| config | one `[[tenant]]` table in `~/.arc/machine.toml` | `[machine]` in the same file |
| clone | a dedicated clone; its stores (`merge.db`, `review.db`, …) live in its `.git/arc/` | — |
| services | `arc-server@<owner>-<name>`, `arc-review@<owner>-<name>`, and when enabled `arc-releaser@…`, `arc-tap@…`, `arc-rot@…` | `arc-web`, `arc-bridge` |
| repo files | its own `merge.yml`, `presubmit.toml`, `.arc/delivery.toml`; the clone's `.arc/config.toml` | — |

Two repos never share a gate, a review route, a release or a store, and one repo's broken config stops only that repo's services. To add a repo, repeat [§4](#4-connect-a-repo) for it. `arc-server tenant list` names every tenant; `arc-server tenant remove <owner/name>` takes one off the list (its clone and history stay), after its units are disabled. `arc-server tenant check --offline` with no name checks every tenant and exits 1 when any line says `FAIL`: run it after each step and before every upgrade ([Install](install.md#upgrade)).

## 8. When something is off

| What you see | Where to look |
|---|---|
| a service's log starts `refusing to start: arc takes no input from the environment` | it names each `ARC_*` variable and what replaced it; check `systemctl --user show-environment` too |
| `refusing to start — \`arc-server tenant check <owner/name>\` fails:` | the `FAIL` lines under it; usually the clone has uncommitted paths, or is not written at its real path |
| `… is too old — refusing to start (need git >= 2.38)` | upgrade git on the merge machine |
| a PR never enters the merge queue | its base is the tenant's `target`; a route covers it (`arc-server tenant show`); its reviewers said LGTM on its current head; it has no `arc-hold` label |
| every PR comes back `cannot_say` | a step of `merge.yml` fails on the base, or is one arc cannot run: run the gate on main on this machine (§4) |
| a client's hooks or `arc tap` ignore the pipeline | `cat ~/.arc/client.toml`, then `curl <web>/api/machine`: the board should list the chat server and the repo |

Local runs — providers, `.arc/config.toml`, presubmit: [Troubleshooting](troubleshooting.md).

---

*Next: [Review on the pipeline](pipeline-review.md) · [Merge](merge-gate.md) · [Team up](bridge.md).*
