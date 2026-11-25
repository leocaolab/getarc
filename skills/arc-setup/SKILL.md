---
name: arc-setup
description: >-
  Install and set up A.R.C. (arc) in the current repo, stage by stage: the arc
  binary from getarc, LLM providers in ~/.tars/config.toml, `arc init` roles,
  optional merge gate / deploy / coding-agent hooks, then a smoke test. Probes
  what is already configured, does only what is missing, verifies each stage
  with one command, and stops with the real error if a step fails. Use when
  the user says "install arc", "set up arc", "装 arc", "配 arc", or when
  another arc skill reports arc is missing or unconfigured.
allowed-tools: "Bash Read Edit Write"
---

# Set up arc

You are the installer. Follow the stages in `roadmap.json` in order; the helper scripts inspect the environment and report status, while you decide, ask the user, and apply changes. `$S` is the directory containing this `SKILL.md` (note that when installed via `npx skills add` outside a Claude Code plugin, `CLAUDE_PLUGIN_ROOT` is not set).

## Tools available

| Tool | What it does | Writes |
|---|---|---|
| `python3 $S/scripts/probe.py [--stage ID] [--tars-home DIR] [--repo DIR]` | Checks every stage's criteria: `ok` (`true`/`false`/`null`), observed facts, and `next` (first incomplete required stage) | Nothing user-owned; the smoke check lets `arc` create `.arc/.gitignore` and `.arc/tars/` |
| `python3 $S/scripts/diagnose.py -- <cmd…>` or `--from FILE\|-` | Runs (or reads) a failed command and matches stdout/stderr against `known_issues.json` (cause + fix) | Nothing |
| `python3 $S/scripts/fetch_arc.py --stage-dir DIR [--install-to DIR] [--version vX.Y.Z \| --from URL]` | Downloads this platform's binary from `getarc` (or `URL/<asset>`) into `DIR`, reports its version and any `missing_verbs`; `--install-to` moves it into place | `DIR`; install dir only with `--install-to` |
| `$S/reference.md` | Reference for provider fields, `[roles]`, `merge.yml` rules, deploy config, and bridge hooks | — |
| `arc <verb> --help` | Source of truth for CLI flags | — |

The scripts require `python3` (3.11+ for TOML checks; older versions report `ok: null`).

## Rules

1. **Probe first, every time.** Run `probe.py` at the start and after each stage. If a previous install stopped halfway, resume from `next`. Never redo a stage that already passes.
2. **Ask before anything outward or global:** `git push`, `arc submit` (which pushes the branch and opens a PR), creating a remote repo/branch, installing into a directory on `PATH`, or writing `~/.tars/config.toml`, `~/.arc/*`, `~/.claude/settings.json`, or `~/.codex/*`. Files inside this repo's `.arc/` and `.github/` may be written after telling the user what goes into them.
3. **Never handle API keys directly.** Ask which environment variable or key file holds the credential; let the user set it. Never print, echo, or write a key value. Provider definitions and credentials belong only in `~/.tars/config.toml` — never in `.arc/config.toml` (where `[providers]` is rejected).
4. **Keep `--tars-home` consistent.** If the user keeps their provider config outside `~/.tars`, pass `--tars_home DIR` to `arc` and `--tars-home DIR` to `probe.py` on every call.
5. **When the probe and the user disagree, show the fact and ask.** For example, if they say they have no bridge server but `~/.arc/client.toml` configures one, show what the file contains and let them decide. Never silently override either side.
6. **Keep questions minimal and batched.** Only ask when the probe cannot determine the answer and the stage requires user input. Batch all questions for a stage into one message.
7. **Stop on failure.** Go to *Troubleshooting*; never skip ahead or paper over a failure with a different command.
8. **Be clear about what is not public.** The team edition's review server, merge server, release page, and `arc bridge` server are not publicly released. Any stage requiring them needs an operator — never act as if the user can install them from `getarc`.

## Stages

Follow `next` from `probe.py`. For each stage: probe → ask (if needed) → apply only missing items → run its `verify` command → probe again.

**1. `prereq`**
- If not inside a git repository, ask the user to `cd` into their project (or confirm running `git init`).
- If there is no prebuilt binary for this OS/arch (`getarc` ships macOS arm64 and Linux x86_64), stop and tell the user.

**2. `binary`**
- If `arc` is missing or lacks required subcommands, run `fetch_arc.py --stage-dir <scratch>` first (downloads without installing) and show the user the version and `missing_verbs`.
- **Release selection:** `getarc`'s latest release (default) is what this skill targets. Only pass `--version <tag>` if the user asks for a specific release, or `--from URL` if they provide a mirror or local directory (`file:///…`); these two flags are mutually exclusive. Note that releases also include `arc-suite-<platform>.tar.gz` (the operator-hosted server suite — not installed by this skill) and `arc-skills.tar.gz` (this plugin).
- **If `missing_verbs` is empty:** ask where to install. Suggest `~/.local/bin` (no `sudo` needed). If that directory isn't on `PATH`, show the shell profile line needed to add it and let the user approve editing it. Then run `--install-to` and re-probe.
- **If `missing_verbs` is non-empty:** the latest public release predates this skill. Stop and report the release tag, missing verbs, and release URL. Do not install it or substitute old commands.

**3. `tars` (model provider config)**
- `probe.py --stage tars` lists configured providers and whether their env vars are set / CLIs are on `PATH`.
- If no config or providers exist and `claude` is on `PATH`, default to Claude Code: propose the two `claude_cli` blocks in `$S/reference.md` § No API key (`claude_critic` on `opus`, `claude_fixer` on `sonnet` with `tools = "default"`). These use the user's `claude login`, so no API key is needed; mention that using a different model family for the fixer keeps reviews more independent, and move on.
- If `claude` is absent but `codex` is on `PATH`, do the same with `codex_cli`.
- If neither is present, ask which model provider the user has access to, then propose `[providers.<id>]` blocks using `$S/reference.md` § Every type (supported types: `openai`, `openai_compat`, `anthropic`, `gemini`, `bedrock`, `vllm`, `mlx`, `llamacpp`, `claude_cli`, `claude_sdk`, `codex_cli`, `opencode`, `antigravity`).
- Show the exact TOML block and ask before writing `~/.tars/config.toml`. API-key providers use `auth = { kind = "secret", secret = { source = "env", var = "NAME" } }`; `claude_cli` uses `claude login` and takes no `auth`.
- `tars_loads_in_arc` verifies that `arc` can actually parse the config (by running `arc init` in a temporary repo), catching any invalid keys before stage 4.

**4. `roles`**
- Run `arc init`. Non-interactively it writes `.arc/config.toml.example`, prints `arc init needs an interactive terminal…`, and exits `1` (expected); it also creates `.arc/.gitignore` and `.arc/tars/`.
- The example assigns the first configured provider to every critic role and the second to `fixer` purely by order. Ask the user which provider should be critic and which should be fixer, copy the example to `.arc/config.toml`, and set `[roles]`: `default`, `critic`, `critic_l4`, and `critic_l5` to the critic, and `fixer` explicitly to the fixer (it never falls back to `default`).
- A fixer from a different model family than the critic keeps reviews independent; if `probe.py` reports `fixer_family_differs` as `null`, ask the user which model family that provider serves.
- Ensure the fixer provider has edit permissions in `~/.tars/config.toml`: `tools = "default"` for `claude_cli`, or `sandbox = "workspace-write"` for `codex_cli`.
- Checks run by `arc fix` before claiming a fix come from the repo's committed `presubmit.toml` (not `.arc/config.toml`).

**5. Optional: `merge_gate`, `release`**
Ask whether a self-hosted merge machine will land/deploy this repo; skip if not.
- **Merge gate:** Draft `.github/workflows/merge.yml` from the repo's existing CI — `run:` steps only, `on: workflow_dispatch: {}` only, no `${{ … }}` expressions, and `uses:` restricted to `actions/checkout`, `actions/setup-node|python|go`, and `dtolnay/rust-toolchain`. Compiled languages must also compile tests; keep supported test runner output (`cargo`, `nextest`, `vitest`, `tsc`, `pytest`, `Playwright`) on stdout. Validate each job with `arc workflow .github/workflows/merge.yml --job <job> --list`.
- The merge machine reads `merge.yml` from the target branch, so it only takes effect once committed and merged. Leave it uncommitted unless the user asks you to commit.
- **Release:** Configure `[release]` in `.arc/config.toml`, a deploy job with a `concurrency:` group, and one `[builds.*]` entry in `.arc/delivery.toml` referencing the same workflow and job (`$S/reference.md` § Deploy). Validate with `arc workflow <file> --job <job> --list`. Never run a deploy job without `--list`, and never run `arc deploy`.
- Registering the repo on a merge machine is an operator task; note that clearly.

**6. Optional: `agents`**
- As Fixer: already covered in stage 4 (`claude_cli` / `codex_cli` / `antigravity`).
- As Bridge participant: requires an operator's `arc-bridge` server URL. Without one, skip and explain why. With one, show the hook snippet from `$S/reference.md` § Bridge and the `~/.arc/client.toml` line (`web = "http://<host>:<port>"`); write them only after user approval. Verify with `arc bridge inbox`.

**7. `smoke`**
Run read-only checks first — `arc rot --no-judge` must exit `0`. Then summarize what works right now:
- **Personal edition** needs no server: `arc local-review` and `arc fix` work locally using `.arc/review.db`. Both require an `origin` remote (to diff against its default branch) and an identity — either running inside a coding agent session or having `gh auth login` configured (otherwise they fail with `cannot tell who is submitting`). If `gh_authed` is `false`, explain the impact: inside an agent session, local commands still work; from a plain terminal, `local-review` and `fix` will refuse, and `arc submit` cannot run. To fix it, the user should install `gh` (https://cli.github.com) and run `gh auth login` themselves (it's interactive, so never run it for them).
- If `review_service_here` is `false` (normal for personal setups), note plainly that no team review service is watching this repo from this machine, though the personal edition works fine.
- Note which providers haven't made a live LLM call yet (arc has no standalone ping command, and `arc rot` only calls `critic_l5` if it finds structural suspects).
- `arc submit` pushes the branch, opens a PR, and queues it for a team review service. It is an outward action — always ask before running it, and warn the user if no review service is watching the repo.

## Troubleshooting

When a command fails:
1. Run `diagnose.py -- <the same command>` (or `diagnose.py --from -` with existing output for outward commands that shouldn't run twice).
2. If it matches a known issue, show the cause and fix; apply local fixes if appropriate, otherwise ask.
3. If there is no match, stop and show the command, exit code, raw output (trimmed, never paraphrased), and what you checked. Do not guess a cause.
4. Re-run the stage's `verify` command, then re-run `probe.py`.

## Hand-off

End with a summary table covering every stage:

| Stage | Result | Evidence |
|---|---|---|
| `prereq` … `smoke` | `done` / `already there` / `skipped (<why>)` / `failed` / `needs an operator` | Verify command & output, or raw error |

Then give the next useful command:
- **Personal edition:** on a feature branch, run `arc local-review`, then `arc fix`, then `git push` (and `arc rot` for a whole-repo structural check).
- **Team edition** (once an operator's review service is watching the repo): `arc submit`.
