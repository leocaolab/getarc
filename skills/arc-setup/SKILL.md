---
name: arc-setup
description: >-
  Install and set up A.R.C. (arc) in the current repo, stage by stage: the arc
  binary from getarc, LLM providers in tars, `arc init` roles, optional merge gate /
  deploy / coding-agent hooks, then a smoke test. Probes what is already there,
  does only what is missing, verifies each stage with one command, and stops with
  the real error when one fails. Use when the user says "install arc", "set up
  arc", "装 arc", "配 arc", or another arc skill found arc missing or unconfigured.
allowed-tools: "Bash Read Edit Write"
---

# Set up arc

You are the installer. The route is `roadmap.json` (stages in order, each with its
completion criteria); the scripts read the world and report; you judge, ask the
person, and act. `$S` is the directory this SKILL.md is in: the skill is also
installed outside a Claude Code plugin (`npx skills add`), where no plugin root is set.

## What you have

| Tool | What it does | Writes |
|---|---|---|
| `python3 $S/scripts/probe.py [--stage ID] [--tars-home DIR] [--repo DIR]` | every stage's criteria judged now: `ok` true/false/null, the facts seen, and `next` (the first required stage not done) | nothing of the person's; the smoke check lets arc create its own `.arc/.gitignore` and `.arc/tars/` |
| `python3 $S/scripts/diagnose.py -- <cmd…>` or `--from FILE\|-` | runs (or reads) a failed step, returns the raw stdout/stderr plus every row of `known_issues.json` it matches (cause, fix, source in arc's code) | nothing |
| `python3 $S/scripts/fetch_arc.py --stage-dir DIR [--install-to DIR] [--tag T]` | downloads this platform's binary from getarc into DIR, reports its version and which route verbs it lacks; `--install-to` moves it into place | DIR; the install dir only with `--install-to` |
| `$S/reference.md` | the facts the stages need — provider fields, `[roles]`, merge.yml rules, deploy, bridge hooks — since the person has no arc docs | — |
| `arc <verb> --help` | the source of truth for every flag | — |

The scripts need only `python3` (3.11+ for the TOML checks; older reports `ok: null`).

## Rules

1. **Probe first, every time.** Run `probe.py` at the start and after each stage. An
   install that stopped half-way resumes from its `next`. Never redo a stage whose
   criteria hold.
2. **Ask before anything outward or global**: `git push`, `arc review` (it pushes the
   branch and opens a PR), creating a remote repo or branch, installing into a
   directory on PATH, writing `~/.tars/config.toml`, `~/.arc/*`, `~/.claude/settings.json`,
   `~/.codex/*`. Files inside this repo's `.arc/` and `.github/` you may write after
   telling the person what goes in them.
3. **Keys never pass through you.** Ask which env var or file holds a credential; the
   person sets it. Never print, echo or write a key's value. Provider definitions and
   credentials live only in the tars config — never in `.arc/config.toml`
   (`[providers]` there is refused: `crates/infra/types/src/config/parse.rs:27`).
4. **One tars home.** If the person uses a tars home other than `~/.tars`, pass it to
   every call: `arc <verb> --tars_home DIR` and `probe.py --tars-home DIR`.
5. **When the probe and the person disagree, show the fact and ask.** E.g. they say
   they have no bridge server but `~/.arc/client.toml` names one: tell them what the
   file says, then let them decide. Never silently pick one side; when you cannot
   ask, change nothing on either side and report the disagreement.
6. **Few, precise questions.** Ask only when the probe cannot decide and the stage's
   `asks` needs an answer. Batch the questions for one stage into one message.
7. **A failure stops the stage.** Go to *Troubleshooting*; never skip to the next stage
   and never paper over a failure with a different command.
8. **Say what is not public.** arc's review service, merge machine, release page and
   chat bridge are not publicly released. A stage that needs one is reported as needing
   an operator — never set up as if the person could install it.

## The stages

Walk `next` from the probe. For each stage: probe it → ask (if needed) → do only the
missing criteria → run its `verify` → probe again.

**1 `prereq`.** Not in a git repo → ask the person to `cd` into the project (or agree to
`git init`). No binary for this platform (getarc ships macOS arm64 and Linux x86_64) →
stop; say so.

**2 `binary`.** `arc` missing or lacking route verbs → `fetch_arc.py --stage-dir <scratch>`
first (installs nothing), show the person the version and `missing_verbs`.
- Which release: getarc's *latest* (the default) is the one this route is written for.
  Pass `--tag` only when the person names another release. The release also carries `arc-suite-<platform>.tar.gz` (the server suite, an
  operator's — this skill does not install it) and `arc-skills.tar.gz` (this plugin).
- `missing_verbs` empty → ask where to install. Suggest `~/.local/bin` (no sudo); if
  that directory is not on their PATH, say which shell profile line adds it — editing
  the profile is theirs to approve. Then `--install-to` it and re-probe. Updating later
  is the same fetch with the newer tag.
- `missing_verbs` not empty → the newest public release predates this route. Stop and
  report the tag, the missing verbs, and the release page. Do not install it as if it
  worked; do not substitute old verbs.

**3 `tars`.** `probe.py --stage tars` lists the providers and, per provider, whether its
env var is set / its CLI is on PATH. If there is no tars config or no provider, ask
which model access the person has, then propose one `[providers.<id>]` block per
provider (format and fields: `$S/reference.md` § tars providers; types: `openai`, `openai_compat`,
`anthropic`, `gemini`, `bedrock`, `vllm`, `mlx`, `llamacpp`, `claude_cli`, `claude_sdk`,
`codex_cli`, `opencode`, `antigravity`). Writing the tars config is global: show the
block and ask. An API-key provider uses
`auth = { kind = "secret", secret = { source = "env", var = "NAME" } }`; `claude_cli`
uses the person's `claude login` and takes no `auth`.
`tars_loads_in_arc` has arc read the file itself (`arc init` in a throwaway repo), so
a field tars refuses fails here, in tars's words, before stage 4.

**4 `roles`.** Run `arc init`. Off a terminal (you) it writes
`.arc/config.toml.example`, prints `arc init needs an interactive terminal…` and exits 1
— expected; it also creates `.arc/.gitignore` and `.arc/tars/` (arc's own state). The
example puts the first tars id arc listed on every critic role and the second on
`fixer` — an order, not a choice: ask for the critic and the fixer, copy the example to
`.arc/config.toml`, and overwrite every `[roles]` line: `default`/`critic`/`critic_l4`/`critic_l5` to
the critic, `fixer` to the fixer. `fixer` must be written out
(`crates/infra/llm/src/roles/mod.rs:96`). A fixer of a different model family than the
critic keeps the review independent; when the probe's `fixer_family_differs` is `null`,
ask which family the provider serves. A `claude_cli` fixer needs `tools = "default"`, a
`codex_cli` fixer `sandbox = "workspace-write"`, on the tars provider
(`$S/reference.md`). `[gate]` (what `arc fix` hands the fixer as the
build/test to run) is optional: offer it with the repo's real commands, and run each
one here first — a command that fails on this machine (a missing tool) fails every fix.
If one fails, do not install the tool for them: say what is missing and leave `[gate]`
out until they have it.
For a language with no compile step, `command` is the typecheck or lint if the repo has
one, else leave it out and set only `final_command` (the tests).

**5 optional: `merge_gate`, `release`.** Ask whether a merge machine will land / deploy
this repo; skip when no.
- *Merge gate*: draft `.github/workflows/merge.yml` from the repo's existing CI — only
  `run:` steps, `on: workflow_dispatch: {}` only, no `${{ … }}`, `uses:` only
  `actions/checkout`, `actions/setup-node|python|go`, `dtolnay/rust-toolchain`; a
  compiled language's build must compile tests too; keep test runners arc reads (cargo, nextest, vitest, tsc,
  pytest, Playwright) on the console. Rules: `$S/reference.md` § Merge gate. Verify
  each job with `arc workflow .github/workflows/merge.yml --job <job> --list` (it prints
  how many steps run and names the first step it refuses).
- The merge machine reads `merge.yml` from the target branch, so it only takes effect
  once committed and landed there. Committing and pushing it are the person's call:
  say so, and leave it uncommitted unless they ask.
- *Release*: `[release]` in `.arc/config.toml`, a deploy job with a `concurrency:` group,
  and exactly one `[builds.*]` in `.arc/delivery.toml` naming the same workflow and job
  (`$S/reference.md` § Deploy). Verify with `arc workflow <file> --job <job> --list`.
  Never run a deploy job without `--list`, and never `arc deploy` (it asks this
  machine to deploy).
- Registering the repo on a merge machine (`~/.arc/machine.toml`, `arc-server tenant add`)
  is the operator's; say so.

**6 optional: `agents`.** As the Fixer: covered by stage 4 (`claude_cli` / `codex_cli` /
`antigravity`). As a participant: the bridge needs an operator's arc-bridge server
address. Without one, skip and say why. With one, show the person the hook block for
their agent from `$S/reference.md` § Bridge and the `~/.arc/client.toml` line
(`web = "http://<host>:<port>"`); write them only on their yes. Verify:
`arc bridge inbox`.

**7 `smoke`.** Read-only checks first — they are the probe's `smoke` stage:
`arc rot --no-judge` must exit 0. Then report the facts that decide what works next:
- `review_service_here` false (the usual case) → `arc local-review` and `arc fix` are
  refused here (`… is not a tenant in ~/.arc/machine.toml`): they work through a review
  service that serves this repo. Say so plainly.
- No LLM call has been proven yet: arc has no stand-alone provider check, and
  `arc rot` (with its judge, `critic_l5`) calls the model only when it finds suspects.
  Say which provider calls are still unproven.
- `arc review` pushes the branch and opens a PR (needs `origin` and `gh auth`). It is an
  outward action: ask, and run it only on a yes. Without a review service watching the
  repo, nothing will review the PR it opens — say that before asking.

## Troubleshooting

When a command fails:
1. `diagnose.py -- <the same command>` — or, for a command that must not run twice
   (anything outward), `diagnose.py --from -` with the output you already have.
2. A match → tell the person the cause and the fix in that row, with its `source`; do
   the fix only if it is local, else ask.
3. No match → stop. Show the command, the exit code and the raw output (trimmed, never
   reworded), and what you checked. Do not guess a cause.
4. Re-run the stage's `verify`, then the probe.

## Hand-off

End with one table, every stage on its own row:

| Stage | Result | Evidence |
|---|---|---|
| prereq … smoke | done / already there / skipped (why) / failed / needs an operator | the verify command and its result, or the raw error |

Then the next useful step: `arc rot` (whole-repo structural review, uses `critic_l5`),
and — once an operator serves the repo — `arc review` → `arc local-review` / `arc fix`.
