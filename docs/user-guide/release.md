# Releases and deploys

arc can ship what lands: build it and install it on a machine (a **deploy**), or tag it and publish a GitHub prerelease every night (the **nightly release**). Both are steps you write in a workflow file, both are recorded, and the release page of arc's web board shows each run.

This is the last stage of the pipeline, after [Merge](merge-gate.md). In short:

- **Nightly.** Once a night, `arc-releaser` builds the release branch's tip and publishes it as a GitHub prerelease tagged `nightly-<UTC date>` ([below](#the-nightly-release)).
- **Deploy.** From the **Deploy** button on the board's **Release** page, or with `arc deploy` on the deploy machine, arc starts the deploy job your `[release]` names on the spot ([below](#deploys)); arc never deploys on its own after a landing. The run is recorded; whoever asked gets a message when it ends, and so does everyone whose PR it shipped.
- **Where to look.** The board's **Release** page: the lanes and targets `.arc/delivery.toml` declares, the current deploy and its steps, and the nightlies.
- **Versioned releases.** `arc-releaser promote --tenant <owner/name> nightly-YYYYMMDD` promotes a nightly to a versioned release (`v<X.Y.Z>`) published on getarc, with `install.sh` and `SHA256SUMS` beside it; it refuses while any lane's declared assets are missing.

arc does not look for a file called `release.yml`. A deploy runs the job that `[release]` in `.arc/config.toml` names, in whatever file it names; the nightly runs `.github/workflows/nightly-release.yml`.

## Deploys

### The pieces

| Piece | Where | Committed? | Says |
|---|---|---|---|
| the deploy job | a workflow file, e.g. `.github/workflows/deploy.yml` | yes | the steps |
| `[release]` | `.arc/config.toml` of the clone on the deploy machine | no | which job *is* the deploy |
| `[builds.<id>]` | `.arc/delivery.toml` | yes | the lane the deploy is filed under |
| `[targets.<id>]` | `.arc/delivery.toml` | yes | where the output ends up — a card on the release page |

The deploy runs on the merge machine, in the repo's clone there (the tenant's `home`), so that clone is where `[release]` must be written.

### 1. Write the deploy job

The job follows the rules in [What arc runs in a workflow file](merge-gate.md#what-arc-runs-in-a-workflow-file), with one difference: **one step arc cannot run refuses the whole deploy** before anything is touched, so no machine is left half-upgraded.

Beyond that, a deploy job needs:

- **A `concurrency:` group.** It keeps two deploys from running at once. Without one, neither the Deploy button nor `arc deploy` will start the job. Both spellings work: `concurrency: deploy-app` or `concurrency: { group: deploy-app, cancel-in-progress: false }`. A second run waits for the group up to 30 minutes (`arc-deployer --lock-wait`, default 1800 seconds), then gives up, naming who holds it.
- **Build somewhere of its own.** The clone the deploy starts in is the merge gate's working copy, which moves to a different commit every round. Fetch the commit to deploy into `$RUNNER_TEMP` — a fresh directory per run, removed when the job ends — and build there.
- **Deploy the commit it was given.** `$ARC_DEPLOY_REF` holds the commit arc decided to deploy. Read it as `${ARC_DEPLOY_REF:-main}`, so a run by hand gets the branch.
- **Say what it shipped.** Write the full commit sha to the file named by `$ARC_SHIPPED_SHA`: `git rev-parse HEAD > "$ARC_SHIPPED_SHA"`. Do it right after checking out, so a run that stops later still names its commit. Without it, the record names no commit.
- **Mark the going-live steps `phase: deploy`.** When a run fails, the failing step's phase decides how it is recorded: `test` / `lint` → *verify failed*, `build` → *build failed*, `deploy` → *deploy failed*. A step without `phase:` is guessed from its name (lint words → `lint`; `test`, `check`, `verify` → `test`; anything else → `build`) and is never guessed as `deploy`.

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

- The `[builds.*]` entry must name the same `workflow` and `job` as `[release]`, written the same way. Exactly one build may do so: with none, or two, a deploy has no lane to be recorded under and is refused.
- A deploy run that `[release]` does not name is refused: a deploy that leaves no record would be invisible on the release page.

### 3. Two ways a deploy starts

When a deploy runs is your call: arc never deploys on its own after a landing, and the merge machine never waits for or yields to a deploy. Both ways below start one `arc-deployer` for `origin/main`'s tip on the spot, in a systemd scope of its own (a deploy restarts what started it), and use the same check first: `[release]` names a job, exactly one `[builds.*]` runs it, and the job has a `concurrency:` group. When the check fails, or the machine has no `systemd-run`, nothing starts and you get the reason.

1. **The Deploy button** on the release page. When the check fails, the button is disabled and the page says what is missing.
2. **`arc deploy`**, run in the tenant's clone on the deploy machine. It names who asked, prints the unit the deploy runs in and its log, and exits; progress and the result are on the release page. When the check fails it exits non-zero with the reason.

To deploy after every landing, call `arc deploy` from your own post-landing job. Two deploys started close together run one at a time under the job's `concurrency:` group, and one whose lane already deployed that commit records *skipped*.

To try the job's steps without recording a deploy, run `arc workflow .github/workflows/deploy.yml --job deploy --list` (prints the plan) or without `--list` (runs it and records nothing).

### What gets recorded

Each deploy is one row in the repo's release record, opened before the first step and closed after the last: the commit from `$ARC_SHIPPED_SHA`, each step's result and output, who asked, and how it ended — *published*, *verify failed*, *build failed*, *deploy failed*, or *machine* when the machine itself was the problem. The release page's "current deploy" reads it.

<a id="delivery-toml"></a>
## `.arc/delivery.toml` reference

It declares builds (how a shippable thing is made) and targets (where it ends up). The release page is drawn from it; there are no built-in stage names.

What actually **runs** today: the build whose `workflow` + `job` is the declared deploy (started by the button or `arc deploy`, as above), and `builtin = "nightly"` (started by the nightly timer, below). Everything else in this file is parsed and drawn on the page but starts nothing — the table marks those keys *not implemented*.

**`[builds.<id>]`**

| Key | Default | Meaning |
|---|---|---|
| `from` | `"main"` | branch it is built from |
| `on` | — | `"merge"`: the release page draws the Deploy button on this lane's targets; a landing starts nothing — call `arc deploy` from your own post-landing job for that. Anything else is read as a tag pattern (`"v*"`, `"tag v*"`) — *not implemented*: shown on the page, and pushing a tag starts nothing. |
| `cron` | — | a schedule, shown as written — the machine's timer is what actually fires (only the nightly has one). Not together with `on`. |
| `workflow` + `job` | — | the steps live in that workflow job |
| `builtin` | — | `"nightly"`: arc's nightly release (below) |
| `steps` | `[]` | step names listed in place, for a repo with no workflow file |
| `artifacts` | `[]` | what it produces, shown on the page |
| `confirm` | `false` | *not implemented*: parsed, but nothing asks anyone to confirm |

A build has at most one of `on` / `cron` (neither = only by hand), and its steps in exactly one place: `workflow`, `builtin` or `steps`. `job` without `workflow` is refused.

**`[targets.<id>]`** — every key is drawn on the release page; arc does not move anything to a target by itself (*not implemented*), so `promote`, `soak` and `rollback` describe intent only.

| Key | Default | Meaning |
|---|---|---|
| `from` | required | a build id, or another target's id (`production` ← `staging` ← `app`) |
| `kind` | `"service"` | `"service"` or `"binary"` |
| `promote` | `"manual"` | `"auto"` or `"manual"`, as you mean it to happen |
| `channel` | — | for a binary: where it is published (`internal`, `prerelease`, …) |
| `audience` | — | who can get it, shown as written |
| `soak` | — | how long it sits upstream first, shown as written (`3d`) |
| `rollback` | — | where to roll back to |

A `from` that names nothing, or a chain of `from`s that loops, is refused when the file is read.

<a id="the-nightly-release"></a>
## The nightly release

Once a night, `arc-releaser` takes the tip of the release branch (`[tenant.release] branch`, default `main`), runs the steps in `.github/workflows/nightly-release.yml` from that tip, and — when every step passed — pushes the tag `nightly-<UTC date>` and, with `publish` on, creates a GitHub prerelease with the assets the lane declares attached. A tip already released is not released again.

It is configured per repo on the merge machine, in `~/.arc/machine.toml`:

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

and installed with `arc-releaser install <owner/name>`, which writes a systemd timer.

`nightly-release.yml` must hold exactly one job. Its steps get these variables:

| Variable | Value |
|---|---|
| `ARC_RELEASE_BUILD` | `[tenant.release] build` |
| `ARC_RELEASE_ARTIFACT` | `[tenant.release] artifact` |
| `ARC_RELEASE_ASSETS` | the directory, outside the clone, to leave every asset in |
| `ARC_RELEASE_ASSET_NAMES` | the names `artifacts` declares, one per line |
| `ARC_RELEASE_TARBALL` | where to leave the one tarball a tip without fixed `artifacts` attaches (outside the clone); going away |
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

With `publish` on, the release attaches exactly the files `delivery.toml` declares as the nightly lane's `artifacts`, taken from `$ARC_RELEASE_ASSETS`; before the tag is pushed, `arc-releaser` checks each is there, and a missing one stops the night as a build failure naming it. Use names of `A-Z a-z 0-9 . _ -` only, not starting with `.`, and free of versions, so `releases/download/<tag>/<name>` keeps its shape. A tip that declares nothing, or only `<...>` templates such as `widgets-<version>.tar.gz`, still gets the old behaviour for now: the release attaches the one tarball left at `$ARC_RELEASE_TARBALL`. Any other name that breaks those rules, alone or beside good ones, stops the night as a declaration failure naming it.

The release body ends with a trailer: `Build: <version>-bNN`, the build the night produced as its binaries' `--version` names it (only when the tree names a version), then `Attached:` and the file names. A lane that adds files to the night's release later, from another machine, reads its ordinal from the `Build:` line, so its binaries name the same build.

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
