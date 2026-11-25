---
name: arc-setup
description: >-
  Install and set up all of A.R.C. (arc), stage by stage: the arc CLI on this
  machine (binary from getarc, LLM providers in ~/.tars/config.toml, `arc init`
  roles, presubmit.toml, the merge gate, the arc-hold label), then the pipeline
  machine (the server suite, machine.toml, arc-web and arc-bridge, the repo
  registered with its review routes, its services), this machine pointed at the
  pipeline, and a first PR the pipeline reviewed and landed. Probes what is
  already there, does only what is missing, verifies each stage with one
  command, and stops with the real error if a step fails. Use when the user says
  "install arc", "set up arc", "装 arc", "配 arc", "set up the pipeline", or when
  another arc skill reports arc is missing or unconfigured.
allowed-tools: "Bash Read Edit Write"
---

# Set up arc

You are the installer. arc is two halves: the `arc` CLI on every machine where people or agents write code (the **coding machine**), and the server suite on one machine the person owns (the **pipeline machine**), which reviews, lands and ships. Installing arc means both, ending with a first PR the pipeline landed.

Follow the stages in `roadmap.json` in order; the scripts inspect and report, while you decide, ask the person, and apply changes. `$S` is the directory containing this `SKILL.md` (`CLAUDE_PLUGIN_ROOT` is not set when the skill came from `npx skills add`).

The user guide is the one source of the install steps: `$S/../../docs/user-guide/` when the plugin is installed (`install.md` → `configuration.md` → `onboarding.md`; Chinese: `$S/../../docs/user-guide.zh-CN.md` §0–§2), else https://github.com/leocaolab/getarc/tree/main/docs/user-guide. Each stage below names its section; read it before you act on that stage.

## Tools available

| Tool | What it does | Writes |
|---|---|---|
| `python3 $S/scripts/probe.py [--machine coding\|pipeline\|both] [--stage ID] [--repo DIR] [--tenant owner/name] [--tars-home DIR]` | Checks the criteria of every stage of this machine: `ok` (`true`: read and holds; `false`: read and the answer is no; `null`: could not be read, and `facts.raw` says why), observed facts, and `next` (the first required stage here that is not done). Stages of the other machine come back `judged_here: false` | Nothing user-owned; the smoke check lets `arc` create `.arc/.gitignore` and `.arc/tars/` |
| `python3 $S/scripts/diagnose.py -- <cmd…>` or `--from FILE\|-` | Runs (or reads) a failed command and matches stdout/stderr against `known_issues.json` (cause + fix) | Nothing |
| `python3 $S/scripts/fetch_arc.py --stage-dir DIR [--install-to DIR] [--version vX.Y.Z \| --from URL]` | Downloads this platform's CLI from `getarc` (or `URL/<asset>`) into `DIR`, reports its version and any `missing_verbs`; `--install-to` moves it into place | `DIR`; install dir only with `--install-to` |
| `$S/reference.md` | Provider fields, `[roles]`, `merge.yml` rules, presubmit, the pipeline's files and units, deploy config, bridge hooks | — |
| `arc <verb> --help`, `arc-server tenant` (no args prints its usage) | Source of truth for flags | — |

The scripts require `python3` (3.11+ for TOML checks; older versions report `ok: null`).

## Rules

1. **Probe first, every time.** Run `probe.py` at the start and after each stage. If a previous install stopped halfway, resume from `next`. Never redo a stage that already passes.
2. **Ask before anything outward or global:** `git push`, `arc submit` (pushes the branch and opens a PR), `gh label create`, creating a remote repo or branch, installing into a directory on `PATH`, writing `~/.tars/config.toml`, `~/.arc/*`, `~/.claude/settings.json` or `~/.codex/*`, `systemctl --user enable`/`restart`, and `loginctl enable-linger`. Files inside this repo's `.arc/` and `.github/` and `presubmit.toml` may be written after telling the person what goes into them.
3. **Never handle API keys directly.** Ask which environment variable or key file holds the credential; let the person set it. Never print, echo, or write a key value. Provider definitions and credentials belong only in `~/.tars/config.toml` — never in `.arc/config.toml` (where `[providers]` is rejected).
4. **Keep `--tars-home` consistent.** If the person keeps their provider config outside `~/.tars`, pass `--tars_home DIR` to `arc` and `--tars-home DIR` to `probe.py` on every call.
5. **Know which machine you are on.** Ask once, in stage `suite`, whether the pipeline machine is this machine or another, and whether you can run commands there. Probe with `--machine coding` on the coding machine, `--machine pipeline` on the pipeline machine (with `--repo <the tenant clone>` once it exists, else `--tenant owner/name`), and `--machine both` when one machine is both.
6. **When you cannot reach the pipeline machine,** give the person each stage's commands from the guide, one stage at a time, ask them to paste the output (or the output of `probe.py --machine pipeline` there), and judge it as you would your own. Then verify from the coding machine what can be seen from there: stage `client` asks the board whether it serves this repo.
7. **When the probe and the person disagree, show the fact and ask.** For example, if they say there is no pipeline yet but `~/.arc/client.toml` names a board that answers, show both and let them decide. Never silently override either side.
8. **Keep questions minimal and batched.** Only ask when the probe cannot determine the answer and the stage needs the person's input. Batch a stage's questions into one message.
9. **Stop on failure.** Go to *Troubleshooting*; never skip ahead or paper over a failure with a different command.

## Stages

Follow `next` from `probe.py`. For each stage: probe → ask (if needed) → apply only missing items → run its `verify` command → probe again.

### The CLI on this machine — guide: `install.md`, `configuration.md`

**1. `prereq`**
- If not inside a git repository, ask the person to `cd` into their project (or confirm running `git init`).
- If there is no prebuilt binary for this OS/arch (`getarc` ships macOS arm64 and Linux x86_64), stop and tell the person.

**2. `binary`**
- If `arc` is missing or lacks required subcommands, run `fetch_arc.py --stage-dir <scratch>` first (downloads without installing) and show the person the version and `missing_verbs`.
- **Release selection:** `getarc`'s latest release (default) is what this skill targets. Only pass `--version <tag>` if the person asks for a specific release, or `--from URL` if they provide a mirror or local directory (`file:///…`); the two are mutually exclusive.
- **If `missing_verbs` is empty:** ask where to install. Suggest `~/.local/bin` (no `sudo` needed). If that directory isn't on `PATH`, show the shell profile line that adds it and let the person approve editing it. Then run `--install-to` and re-probe.
- **If `missing_verbs` is non-empty:** the latest public release predates this skill. Stop and report the release tag, the missing verbs and the release URL. Do not install it or substitute old commands.

**3. `tars` (model providers)**
- `probe.py --stage tars` lists the configured providers and whether their env vars are set / CLIs are on `PATH`.
- No config or providers, and `claude` on `PATH`: propose the two `claude_cli` blocks in `$S/reference.md` § No API key (`claude_critic` on `opus`, `claude_fixer` on `sonnet` with `tools = "default"`). They use the person's `claude login`, so no API key is needed; mention that a fixer from a different model family keeps reviews more independent, and move on.
- `claude` absent but `codex` on `PATH`: the same with `codex_cli`.
- Neither: ask which model provider the person has access to, then propose `[providers.<id>]` blocks from `$S/reference.md` § All provider types.
- Show the exact TOML and ask before writing `~/.tars/config.toml`. API-key providers use `auth = { kind = "secret", secret = { source = "env", var = "NAME" } }`; `claude_cli` uses `claude login` and takes no `auth`.
- `tars_loads_in_arc` runs `arc init` in a throwaway repo, so a key tars refuses shows up here rather than in stage 4.

**4. `roles`**
- Run `arc init`. Not in a terminal it writes `.arc/config.toml.example`, prints `arc init needs an interactive terminal…`, and exits `1` (expected); it also creates `.arc/.gitignore` and `.arc/tars/`.
- The example puts the first provider on every critic role and the second on `fixer`, by order only. Ask which provider is critic and which is fixer, copy the example to `.arc/config.toml`, and set `[roles]`: `default`, `critic`, `critic_l4`, `critic_l5` to the critic and `fixer` to the fixer (it never falls back to `default`).
- If `fixer_family_differs` is `null`, ask which model family that provider serves. The fixer needs edit rights in `~/.tars/config.toml`: `tools = "default"` for `claude_cli`, `sandbox = "workspace-write"` for `codex_cli`.

**5. `smoke`**
- `arc rot --no-judge` must exit `0`. `arc local-review` and `arc fix` now work on a feature branch with no server, on the clone's own `.arc/review.db`.
- Both need an identity: the coding agent's session, or a `gh auth login`. If `gh_authed` is `false`, say what it costs: from inside an agent session the local commands still work; from a plain terminal `local-review` and `fix` refuse, and `arc submit` (stage `first_pr`) cannot open a PR without `gh`. The person installs `gh` (https://cli.github.com) and runs `gh auth login` themselves (interactive, never run it for them).
- arc has no standalone ping, and `arc rot` calls `critic_l5` only when it finds structural suspects: tell the person which providers have not made a live call yet.

### The repo's committed files — guide: `onboarding.md` §4 "In the repo, on your laptop"

**6. Optional: `presubmit`**
- Ask which commands must pass before a push. Write `presubmit.toml` at the repo root (`$S/reference.md` § presubmit.toml); `arc submit` runs it before it pushes, and `arc fix` hands the same checks to the fixer.
- Verify with `arc presubmit` (pass `--target origin/<target> --base "$(git merge-base HEAD origin/<target>)"` when a check spells `{target}`, `{base}` or `{affected}`). It needs a clean tree, so commit first.
- Skip when the person wants no checks; say that `arc fix` then tells the fixer to find the build and test commands itself.

**7. `merge_gate`**
- Draft `.github/workflows/merge.yml` from the repo's existing CI: `run:` steps only, `on: workflow_dispatch: {}` only, no `${{ … }}`, `uses:` only `actions/checkout`, `actions/setup-node|python|go`, `dtolnay/rust-toolchain` ($S/reference.md § Merge gate). Compiled languages also compile their tests. Validate every job with `arc workflow .github/workflows/merge.yml --job <job> --list`.
- The merge machine reads `merge.yml` from the base of every change, so `merge_yml_on_target` (and `presubmit_on_target`) want both files on the target branch. Committing and pushing them there is outward: ask, and let the person choose how (a direct push, or a PR they merge on GitHub before the pipeline exists). The probe reads `origin/HEAD` as of the last fetch; run `git fetch origin` after they land.

**8. `labels`**
- `gh label create arc-hold` (and `gh label create arc-bypass` if a review route will name it), after asking. A PR labelled `arc-hold` never lands.

### The pipeline machine — guide: `install.md` § The pipeline machine, `onboarding.md` §2–§4

From here the stages are `machine: pipeline`. Ask the stage-`suite` question first (rule 5), then work there yourself or through the person (rule 6). A Linux x86_64 machine with systemd user services is the one to leave running; on a Mac the services have no units and are started by hand (`onboarding.md` §2), which is fit for trying the pipeline only — say so if they pick one.

**9. `suite`**
- Install the server suite: `arc-suite-<platform>.tar.gz` and `SHA256SUMS` from the same release, check, unpack, `install -m 755 arc-suite-<platform>/arc* ~/.local/bin/` (ask: it is a `PATH` directory). The units run the binaries from the path they were installed at, so they stay there.
- The machine also needs git 2.38 or newer, `gh auth login` as the user the services run as (the merge server pushes what it lands), and every tool `merge.yml` runs. arc installs none of them; name what is missing and let the person install it.
- `linger_on` false on Linux: propose `loginctl enable-linger $USER` (ask). Without it the services stop at logout and do not come back after a reboot.

**10. `machine`**
- Ask for the address the coding machines reach this one at, then write `[machine]` in `~/.arc/machine.toml` (ask — global file): `address`, `expose = true` when the coding machines are other machines, `path` = the directories holding the toolchains `merge.yml` runs. `$S/reference.md` § machine.toml.
- No `ARC_*` variable may be set for the services; a service that finds one refuses to start and names it.
- Verify: `arc-server tenant url web` prints `http://<address>:8787` — the board's address, which stage `client` writes on the coding machine.

**11. `board`**
- `arc-bridge install`, `arc-web install`, then `systemctl --user daemon-reload` and `systemctl --user enable --now arc-bridge.service arc-web.service` (ask). On a Mac, start `arc-bridge` and `arc-web` by hand instead.
- Verify: `curl -fsS "$(arc-server tenant url web)/api/machine"` answers JSON.

**12. `tenant`** (`onboarding.md` §4 "On the merge machine", steps 1–4)
- **A clone only arc works in**: `git clone <origin> ~/<name>-ci` — not a worktree, not anyone's working directory, at its real path; `git -C ~/<name>-ci status --porcelain` prints nothing. Probe from now on with `--repo ~/<name>-ci`.
- **Main green on this machine**: `cd ~/<name>-ci && arc workflow .github/workflows/merge.yml --job <job>` for each job. A step that fails on main here (a missing tool) makes the merge server answer `cannot_say` for every PR; fix it before registering. This runs the person's build and tests: say how long it may take before you start it.
- **Register**: `arc-server install ~/<name>-ci` (add `--target <branch>` when PRs land on a branch other than `main`). It writes the `[[tenant]]` and the units, and prints the commands that start them.
- **Routes**: append the `[[tenant.review.route]]` rules under the tenant in `~/.arc/machine.toml` (ask — global file; `$S/reference.md` § machine.toml). With no route, nobody reviews and nothing lands. The dummy reviewer says LGTM to everything and needs no model; a model reviewer (`react`) needs `arc init` in the clone (its `.arc/` does not count against a clean clone) and providers in this machine's `~/.tars/config.toml` — the coding-machine stages 3 and 4, run here.
- Verify: `arc-server tenant check <owner/name>` until every line says `ok` or `skip`.

**13. `tenant_services`** (§4 step 5)
- `arc-review install`, `systemctl --user daemon-reload`, `systemctl --user enable --now arc-server@<owner>-<name>.service arc-review@<owner>-<name>.service`, then `systemctl --user restart arc-web` — arc-web reads `machine.toml` only when it starts (ask before each). The instance is the tenant name with `/` turned into `-`. Both services run the offline checks at start and refuse on a `FAIL`; their log is `journalctl --user -u arc-server@<owner>-<name>.service -u arc-review@<owner>-<name>.service`.
- Verify: `tenant_served_here` — the board lists the tenant with its merge and review stores open.

### Back on this machine — guide: `onboarding.md` §3.2, §5

**14. `client`**
- Write `~/.arc/client.toml` with the one key `web = "<what arc-server tenant url web printed>"` (ask — global file).
- Install the coding agent's hooks so the reviewers' findings and each PR's outcome reach its session: `$S/reference.md` § Bridge (Claude Code, Codex CLI, agy). Write them only after the person approves.
- `board_reachable` false: the machine cannot reach the board — on the pipeline machine, `[machine] expose = true` with the right `address`, and a firewall that lets the port through. `board_serves_repo` false: stages 12–13 are not done for this repo, or arc-web was not restarted after them.
- Verify: `arc bridge inbox` runs without `no arc-bridge server is configured`.

**15. `first_pr`**
- On a feature branch with a small change: `arc local-review && arc fix` (optional), then `arc submit` — ask first; it runs `presubmit.toml`, pushes the branch, opens the PR and queues its review. To keep a PR from landing, label it `arc-hold`.
- Watch it on the board, or on the pipeline machine with the `journalctl` line of stage 13. Re-probe until `pr_landed` holds; its facts carry the last merge rounds. If one says `cannot_say`, a step of `merge.yml` fails on main on the pipeline machine (stage 12's main-green step).

**16. Optional: `release`** (after a first PR has landed — `release.md`)
- `machine: pipeline`: `[release]` is written in the tenant clone's `.arc/config.toml`, where the deploy runs. A deploy job with a `concurrency:` group, and one `[builds.*]` in `.arc/delivery.toml` (committed) naming the same workflow and job ($S/reference.md § Deploy). Validate with `arc workflow <file> --job <job> --list`. Never run a deploy job without `--list`, and never run `arc deploy`.

## Troubleshooting

When a command fails:
1. Run `diagnose.py -- <the same command>` (or `diagnose.py --from -` with existing output for outward commands that must not run twice).
2. If it matches a known issue, show the cause and fix; apply local fixes if appropriate, otherwise ask.
3. If there is no match, stop and show the command, exit code, raw output (trimmed, never paraphrased), and what you checked. Do not guess a cause. `onboarding.md` §8 lists where to look on the pipeline machine.
4. Re-run the stage's `verify` command, then re-run `probe.py`.

## Hand-off

End with a summary table covering every stage:

| Stage | Machine | Result | Evidence |
|---|---|---|---|
| `prereq` … `release` | coding / pipeline | `done` / `already there` / `skipped (<why>)` / `failed` / `done by the person (pasted output)` | Verify command & output, or raw error |

Then give the next useful command: on a feature branch, `arc local-review`, then `arc fix`, then `arc submit` (and `arc rot` for a whole-repo structural check).
