# Releases and deploys

arc can ship what lands, in two ways:

- **Deploy:** build it and install it on a machine.
- **Nightly release:** tag it and publish a GitHub prerelease every night.

Both are steps you write in a workflow file, both are recorded, and the **Release** page of arc's web board shows every run. This is the last stage of the pipeline, after [Merge](merge-gate.md).

| You want to | Do this |
|---|---|
| Deploy now | Click **Deploy** on the board's **Release** page, or run `arc deploy` on the deploy machine ([Deploys](#deploys)). arc never deploys on its own after a landing |
| Publish a build every night | Set up `arc-releaser`; it builds the release branch's latest commit and publishes it as a GitHub prerelease tagged `nightly-<UTC date>` ([below](#the-nightly-release)) |
| Turn a nightly into a versioned release | `arc-releaser promote --tenant <owner/name> nightly-YYYYMMDD` (below) |
| See what is happening | The board's **Release** page: the lanes and targets `.arc/delivery.toml` declares, the current deploy and its steps, and the nightlies |

When a deploy ends, whoever asked for it gets a message, and so does everyone whose PR it shipped.

**Promoting a nightly.** `arc-releaser promote --tenant <owner/name> nightly-YYYYMMDD` publishes a nightly, unchanged, as a versioned release (`v<X.Y.Z>`) on the repository that the tree's manual binary target names, with `install.sh` and `SHA256SUMS` attached. It builds nothing. It refuses while any lane's declared assets are missing.

arc does not look for a file called `release.yml`. A deploy runs the job that `[release]` in `.arc/config.toml` names, in whatever file it names; the nightly runs `.github/workflows/nightly-release.yml`.

## Deploys

### The pieces

| Piece | Where | Committed? | What it says |
|---|---|---|---|
| the deploy job | a workflow file, e.g. `.github/workflows/deploy.yml` | yes | the steps |
| `[release]` | `.arc/config.toml` of the clone on the deploy machine | no | which job *is* the deploy |
| `[builds.<id>]` | `.arc/delivery.toml` | yes | the lane the deploy is recorded under |
| `[targets.<id>]` | `.arc/delivery.toml` | yes | where the output ends up — a card on the Release page |

The deploy runs on the merge machine, in the clone arc keeps of the repo there (the `home` path in `~/.arc/machine.toml`). That clone is where you write `[release]`.

### 1. Write the deploy job

The job follows the rules in [What arc runs in a workflow file](merge-gate.md#what-arc-runs-in-a-workflow-file), with one difference: **if arc cannot run even one step, it refuses the whole deploy** before touching anything, so no machine is left half-upgraded.

A deploy job also needs:

- **A `concurrency:` group,** so two deploys never run at once. Without one, neither the Deploy button nor `arc deploy` starts the job. Both forms work: `concurrency: deploy-app` or `concurrency: { group: deploy-app, cancel-in-progress: false }`. A second run waits for the group for up to 30 minutes (`arc-deployer --lock-wait`, default 1800 seconds), then gives up and says who holds it.
- **Its own build directory.** The clone the deploy starts in is the merge gate's working copy, which moves to a different commit every round. Fetch the commit to deploy into `$RUNNER_TEMP` — a fresh directory for each run, removed when the job ends — and build there.
- **The commit arc chose.** `$ARC_DEPLOY_REF` holds the commit arc decided to deploy. Read it as `${ARC_DEPLOY_REF:-main}`, so a run by hand gets the branch.
- **A note of what it shipped.** Write the full commit sha to the file `$ARC_SHIPPED_SHA` names: `git rev-parse HEAD > "$ARC_SHIPPED_SHA"`. Do it right after checkout, so a run that fails later still names its commit. Without it, the record names no commit.
- **`phase: deploy` on the steps that go live.** When a run fails, the failing step's phase decides how the failure is recorded: `test` / `lint` → *verify failed*, `build` → *build failed*, `deploy` → *deploy failed*. A step without `phase:` is guessed from its name (lint words → `lint`; `test`, `check`, `verify` → `test`; anything else → `build`) and is never guessed as `deploy`.

Every step runs with `PATH` set to `[machine] path` from `~/.arc/machine.toml`.

A minimal deploy job for a service:

```yaml workflow.yml
name: Deploy
on:
  workflow_dispatch: {}

jobs:
  deploy:
    concurrency:
      group: deploy-widgets
      cancel-in-progress: false
    steps:
      - name: Fetch the commit into a scratch clone
        run: |
          src="$RUNNER_TEMP/src"
          git init --quiet "$src"
          git -C "$src" fetch --quiet --depth 1 git@github.com:acme/widgets.git "${ARC_DEPLOY_REF:-main}"
          git -C "$src" checkout --quiet --detach FETCH_HEAD
          if [ -n "${ARC_SHIPPED_SHA:-}" ]; then git -C "$src" rev-parse HEAD > "$ARC_SHIPPED_SHA"; fi

      - name: Build
        run: |
          cd "$RUNNER_TEMP/src"
          cargo build --release --locked

      - name: Install and restart
        phase: deploy
        run: |
          install -m 755 "$RUNNER_TEMP/src/target/release/widgets" "$HOME/.local/bin/widgets"
          systemctl --user restart widgets.service
```

arc's own deploy job, `deploy.yml` (`ci-server`), is a full example: it builds several binaries with a cache kept outside the scratch clone, checks the machine before overwriting anything, and restarts each service in its own `phase: deploy` step.

### 2. Declare it

In `.arc/config.toml` of the clone on the deploy machine:

```toml config.toml
[release]
workflow = ".github/workflows/deploy.yml"
job      = "deploy"     # omit only if the file has a single job
```

In `.arc/delivery.toml`, committed:

```toml delivery.toml
[builds.app]
from     = "main"                          # the branch it is built from
on       = "merge"                         # the lane the Deploy button sits under; it starts nothing on its own
workflow = ".github/workflows/deploy.yml"  # the same file and job as [release]
job      = "deploy"

[targets.production]
kind    = "service"   # or "binary"
promote = "auto"      # shown on the release page; see the table below
from    = "app"       # a build id, or another target's id
```

- The `[builds.*]` entry must name the same `workflow` and `job` as `[release]`, written the same way. Exactly one build may do so. With none, or with two, the deploy has no lane to be recorded under and is refused.
- A deploy run that `[release]` does not name is refused, because a deploy that leaves no record would be invisible on the Release page.

### 3. Start a deploy

You decide when to deploy. arc never deploys on its own after a landing, and the merge machine never waits for a deploy or makes way for one. There are two ways to start one; both start one `arc-deployer` for the latest commit of `origin/main`, right away, in its own systemd scope (a deploy restarts the services that started it).

Both check the same things first: `[release]` names a job, exactly one `[builds.*]` runs that job, and the job has a `concurrency:` group. If a check fails, or the machine has no `systemd-run`, nothing starts and you are told why.

1. **The Deploy button** on the Release page. When a check fails, the button is disabled and the page says what is missing.
2. **`arc deploy`**, run in the repo's clone on the deploy machine. It records who asked, prints the systemd unit the deploy runs in and its log, and exits; progress and the result are on the Release page. When a check fails it exits non-zero with the reason.

To deploy after every landing, call `arc deploy` from your own post-landing job. Two deploys started close together run one at a time under the job's `concurrency:` group, and one whose lane already deployed that commit is recorded as *skipped*.

To try the job's steps without recording a deploy, run `arc workflow .github/workflows/deploy.yml --job deploy --list` (prints the plan) or the same without `--list` (runs it and records nothing).

### What gets recorded

Each deploy is one row in the repo's release record, opened before the first step and closed after the last. It holds the commit from `$ARC_SHIPPED_SHA`, each step's result and output, who asked, and how it ended: *published*, *verify failed*, *build failed*, *deploy failed*, or *machine* when the machine itself was the problem. The Release page's "current deploy" is read from it.

<a id="delivery-toml"></a>
## `.arc/delivery.toml` reference

This file declares builds (how a shippable thing is made) and targets (where it ends up). The Release page is drawn from it; there are no built-in stage names.

What actually **runs** today:

- the build whose `workflow` + `job` is the declared deploy (started by the button or `arc deploy`, as above);
- `builtin = "nightly"` (started by the nightly timer, below).

Everything else in this file is read and shown on the page but starts nothing; the tables mark those keys *not implemented*.

**`[builds.<id>]`**

| Key | Default | Meaning |
|---|---|---|
| `from` | `"main"` | the branch it is built from |
| `on` | — | `"merge"`: the Release page shows the Deploy button on this lane's targets. A landing starts nothing — call `arc deploy` from your own post-landing job for that. Any other value is read as a tag pattern (`"v*"`, `"tag v*"`) — *not implemented*: shown on the page, but pushing a tag starts nothing. |
| `cron` | — | a schedule, shown as written. The machine's timer is what actually starts a run (only the nightly has one). Cannot be combined with `on`. |
| `workflow` + `job` | — | the steps are in that workflow job |
| `builtin` | — | `"nightly"`: arc's nightly release (below) |
| `steps` | `[]` | step names listed here, for a repo with no workflow file |
| `artifacts` | `[]` | what it produces, shown on the page |
| `confirm` | `false` | *not implemented*: read, but nothing asks anyone to confirm |

A build has at most one of `on` / `cron` (neither means it only runs by hand), and its steps in exactly one place: `workflow`, `builtin` or `steps`. `job` without `workflow` is refused.

**`[targets.<id>]`** — every key is shown on the Release page. arc does not move anything to a target by itself (*not implemented*), so `promote`, `soak` and `rollback` only describe what you intend.

| Key | Default | Meaning |
|---|---|---|
| `from` | required | a build id, or another target's id (`production` ← `staging` ← `app`) |
| `kind` | `"service"` | `"service"` or `"binary"` |
| `promote` | `"manual"` | `"auto"` or `"manual"`, as you intend it to happen |
| `channel` | — | for a binary: where it is published (`internal`, `prerelease`, …) |
| `audience` | — | who can get it, shown as written |
| `soak` | — | how long it stays at the previous target first, shown as written (`3d`) |
| `rollback` | — | where to roll back to |

A `from` that names nothing, or a chain of `from`s that loops, is refused when the file is read.

<a id="the-nightly-release"></a>
## The nightly release

Once a night, `arc-releaser`:

1. takes the latest commit of the release branch (`[tenant.release] branch`, default `main`) — and skips the night if that commit was already released;
2. runs the steps in `.github/workflows/nightly-release.yml` from that commit;
3. if every step passed, pushes the tag `nightly-<UTC date>`;
4. with `publish` on, creates a GitHub prerelease with the assets the lane declares attached.

Set it up per repo on the merge machine, in `~/.arc/machine.toml`:

```toml machine.toml#tenant
[tenant.release]
clone    = "/home/ci/widgets-release"          # its own clone, not the tenant's home
build    = "cargo build --release --locked"    # required
artifact = "target/release/widgets"            # required, relative to clone
# branch       = "main"
# verify       = "…"     # replaces the verify step (normally left out)
# publish      = true    # false: tag only, no GitHub release
# timeout_secs = 3600
```

Then install it with `arc-releaser install <owner/name>`, which writes a systemd timer.

`nightly-release.yml` must contain exactly one job. Its steps get these variables:

| Variable | Value |
|---|---|
| `ARC_RELEASE_BUILD` | `[tenant.release] build` |
| `ARC_RELEASE_ARTIFACT` | `[tenant.release] artifact` |
| `ARC_RELEASE_ASSETS` | a directory outside the clone; put every asset here |
| `ARC_RELEASE_ASSET_NAMES` | the names `artifacts` declares, one per line |
| `ARC_RELEASE_TARBALL` | where to put the single tarball, for a commit that declares no fixed `artifacts` (outside the clone); being phased out |
| `ARC_RELEASE_VERIFY` | `[tenant.release] verify`, empty when not set |

A minimal one: check the tree, build, package.

```yaml workflow.yml
name: Nightly release
on:
  workflow_dispatch: {}

jobs:
  nightly:
    steps:
      - name: verify
        run: |
          if [ -n "${ARC_RELEASE_VERIFY:-}" ]; then eval "$ARC_RELEASE_VERIFY"; exit $?; fi
          arc workflow .github/workflows/merge.yml --job rust

      - name: build
        run: |
          eval "$ARC_RELEASE_BUILD"
          [ -f "$ARC_RELEASE_ARTIFACT" ] || { echo "$ARC_RELEASE_ARTIFACT was not built"; exit 1; }
          tar -C "$(dirname "$ARC_RELEASE_ARTIFACT")" -czf "$ARC_RELEASE_ASSETS/widgets-linux-x64.tar.gz" "$(basename "$ARC_RELEASE_ARTIFACT")"
```

**Which files are attached.** With `publish` on, the release attaches exactly the files `delivery.toml` declares as the nightly lane's `artifacts`, taken from `$ARC_RELEASE_ASSETS`. Before the tag is pushed, `arc-releaser` checks that each one is there; a missing one stops the night as a build failure and names the file.

- Use names made of `A-Z a-z 0-9 . _ -` only, not starting with `.`, and without versions in them, so the download URL `releases/download/<tag>/<name>` stays the same from night to night.
- A commit that declares nothing, or only `<...>` templates such as `widgets-<version>.tar.gz`, still gets the old behaviour for now: the release attaches the one tarball left at `$ARC_RELEASE_TARBALL`.
- Any other name that breaks these rules, alone or next to valid ones, stops the night as a declaration failure and names it.

**The release notes** end with `Build: <version>-bNN` — the build number the night's binaries report in `--version` (only when the tree names a version) — then `Attached:` and the file names. A lane that adds files to the same night's release later, from another machine, reads its build number from the `Build:` line, so its binaries report the same build.

```toml delivery.toml
[builds.nightly]
from      = "main"
cron      = "03:00 UTC"
builtin   = "nightly"
artifacts = ["widgets-linux-x64.tar.gz"]

[targets.prerelease]
kind    = "binary"
promote = "auto"
from    = "nightly"
channel = "prerelease"
```

---

*Next: [The merge gate](merge-gate.md) · [Configuration](configuration.md) · [Troubleshooting](troubleshooting.md).*
