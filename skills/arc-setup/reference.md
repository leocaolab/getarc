# Install reference — configuration & syntax

Reference details for each setup stage (`arc-setup`).

## Model providers (`<tars home>/config.toml`)
*See `docs/user-guide/configuration.md` and `docs/user-guide/coding-agents.md`.*

Each provider is defined as a `[providers.<id>]` table with an ID of your choice. Unknown keys are rejected with a list of valid fields.

Config lookup order: `--tars_home DIR` (`DIR/config.toml`) → `--tars-config FILE` → `$TARS_HOME/config.toml` → `~/.tars/config.toml`. Pass the same flag to every `arc` call if you use a custom location.

### No API key: default when `claude` is on `PATH`

Both roles run via Claude Code using your existing `claude login`:

```toml ignore: ~/.tars/config.toml
[providers.claude_critic]
type = "claude_cli"
default_model = "opus"

[providers.claude_fixer]
type = "claude_cli"
default_model = "sonnet"
tools = "default"                   # REQUIRED for a Fixer; default "disabled" cannot edit files
timeout_secs = 900                  # default 300
```

In `.arc/config.toml` `[roles]`: set `default`, `critic`, `critic_l4`, `critic_l5` to `claude_critic`, and `fixer` to `claude_fixer`.
For `codex` instead, use `type = "codex_cli"`, a Codex model ID as `default_model`, and `sandbox = "workspace-write"` on the fixer instead of `tools`.

### All provider types

```toml ignore: ~/.tars/config.toml
[providers.gemini_flash]            # API-key provider
type = "gemini"
default_model = "flash@latest"      # concrete model ID, or <series>@latest
auth = { kind = "secret", secret = { source = "env", var = "GEMINI_API_KEY" } }
# alternatives: secret = { source = "file", path = "~/.keys/gemini" }; or auth = { kind = "none" } for local servers

[providers.claude_fixer]            # Claude Code Fixer — uses `claude login`, no auth needed
type = "claude_cli"
default_model = "sonnet"
tools = "default"                   # REQUIRED for a Fixer; default "disabled" cannot edit files
timeout_secs = 900                  # default 300

[providers.codex_fixer]             # Codex CLI
type = "codex_cli"
default_model = "<a Codex model id>"
sandbox = "workspace-write"         # REQUIRED for a Fixer; default is "read-only"
timeout_secs = 900                  # default 600 (note: key is timeout_secs, not timeout)

[providers.agy]                     # agy (Antigravity CLI)
type = "antigravity"
default_model = "<model>"
effort = "high"                     # "low" | "high"
```

All CLI providers also accept `executable` (defaults: `claude`, `codex`, `agy`).
Supported types: `openai`, `openai_compat`, `anthropic`, `gemini`, `bedrock`, `vllm`, `mlx`, `llamacpp`, `claude_cli`, `claude_sdk`, `codex_cli`, `opencode`, `antigravity`. (`claude_cli` is end-to-end tested as a Fixer; `codex_cli` and `antigravity` are supported but not end-to-end tested as Fixers.)

## `.arc/config.toml`
*See `docs/user-guide/configuration.md`.* Not committed (`arc init` adds it to `.arc/.gitignore`). `[providers]` is not allowed here.

```toml config.toml
[roles]
default   = "<critic id>"
critic    = "<critic id>"
critic_l4 = "<critic id>"     # per-file review
critic_l5 = "<critic id>"     # `arc rot` structural judge
fixer     = "<fixer id>"      # must be set explicitly; never falls back to default
```

Checks run by the Fixer before committing a fix come from the repo's committed `presubmit.toml`.

## Merge gate (`.github/workflows/merge.yml`)
*See `docs/user-guide/merge-gate.md`.* Executed by a self-hosted merge runner (not GitHub Actions) on both the base branch and the merged tree; a PR lands only if the merged run adds no new failures. Because it is read from the target branch, a PR modifying `merge.yml` is judged by the existing copy on `main`.

- **Path & trigger:** `.github/workflows/merge.yml`, `on: workflow_dispatch: {}` only.
- **Execution:** All jobs run in file order as one gate (`needs:` and `runs-on:` are ignored). Steps run under `sh -c` with `set -e` and no `pipefail` (avoid `| tee`, which hides exit codes).
- **Supported keys:** `run:`, `name:`, `env:` (workflow/job/step), `working-directory:`, `defaults.run.working-directory`, `strategy.matrix.include`, `if:` on `runner.os` / `runner.arch` / `env.*` / `matrix.*`, and arc's `phase:` (`build` / `test` / `lint` / `deploy`).
- **Supported `uses:`:** Only `actions/checkout`, `actions/setup-node|python|go` (with `node-version` / `python-version` / `go-version`), and `dtolnay/rust-toolchain@<ref>`. These verify the version already installed on the merge machine without downloading anything. Any other `uses:` is rejected.
- **Matrices:** Only `strategy.matrix.include` is expanded (single-value lists like `python: ["3.12"]` become literals). `${{ … }}` expressions anywhere are rejected — use shell variables (`$NODE_ENV`) instead.
- **Strict validation:** One unsupported step causes every PR to fail validation.
- **Build & test output:** Compiled languages must also compile tests (`cargo build --all-targets`, `tsc -b`). Keep test runner output on stdout (`rustc`/`cargo`, `cargo test`, `nextest`, `vitest`, `tsc`, `Playwright`, `pytest`).
- `main` must pass on the merge machine before registering the repo.

```yaml workflow.yml
name: Merge gate
on:
  workflow_dispatch: {}
jobs:
  test:
    steps:
      - name: Install
        run: python3 -m pip install -r requirements.txt
      - name: Test
        run: python3 -m pytest -q
```

Validate each job with: `arc workflow .github/workflows/merge.yml --job <job> --list`.

## Deploy (`[release]` + `.arc/delivery.toml`)
*See `docs/user-guide/release.md`.* Runs on the merge machine in its clone of the repo.
- Define a deploy job (in any workflow file) with a `concurrency:` group that builds in `$RUNNER_TEMP`, deploys `${ARC_DEPLOY_REF:-main}`, writes the shipped commit SHA to `$ARC_SHIPPED_SHA`, and marks live rollout steps with `phase: deploy`.
- In `.arc/config.toml`: `[release] workflow = "<file>"`, `job = "<job>"`.
- In `.arc/delivery.toml` (committed): one `[builds.<id>]` referencing the same `workflow` and `job` (`from = "main"`, `on = "merge"` to deploy after each merge), plus `[targets.<id>]` (`kind = "service"|"binary"`, `promote = "auto"|"manual"`, `from = "<build id>"`).
- Validate with `arc workflow <file> --job <job> --list`. Never run the deploy job without `--list`.

## Bridge (agent participant)
*See `docs/user-guide/coding-agents.md`.* Requires an operator-hosted `arc-bridge` server.
- `~/.arc/client.toml`, one key: `web = "http://<board-host>:<port>"`.
- **Claude Code hooks** (in `~/.claude/settings.json` or `.claude/settings.json`; `arc` does not install these automatically):

```json
{
  "hooks": {
    "SessionStart": [{ "hooks": [{ "type": "command", "command": "arc bridge hook SessionStart", "timeout": 10 }] }],
    "PreToolUse":   [{ "hooks": [{ "type": "command", "command": "arc bridge hook PreToolUse", "timeout": 5 }] }],
    "PostToolUse":  [{ "matcher": "Bash", "hooks": [{ "type": "command", "command": "arc bridge hook PostToolUse", "timeout": 5 }] }],
    "PostToolUseFailure": [{ "matcher": "Bash", "hooks": [{ "type": "command", "command": "arc bridge hook PostToolUseFailure", "timeout": 5 }] }],
    "Stop": [{ "hooks": [
      { "type": "command", "command": "arc bridge hook Stop --mail waiter", "timeout": 600 },
      { "type": "command", "command": "arc bridge await-mail", "timeout": 7200, "asyncRewake": true }
    ] }],
    "SessionEnd":   [{ "hooks": [{ "type": "command", "command": "arc bridge hook SessionEnd", "timeout": 10 }] }]
  }
}
```

- **Codex CLI:** `~/.codex/config.toml` with `[features] hooks = true` and `[[hooks.<Event>]]` / `[[hooks.<Event>.hooks]]` running `/abs/path/arc bridge hook <Event> --agent codex --name <name>` for `SessionStart`, `PreToolUse`, `Stop` (`--mail waiter`), and `SessionEnd`; then trust them in `/hooks`.
- **agy:** `~/.gemini/config/hooks.json` or `.agents/hooks.json`:
  `{"arc-bridge": {"Stop": [{"type": "command", "command": "<arc> bridge hook Stop --agent agy --name <name>", "timeout": 30}]}}` — `Stop` only.
- **Verify:** `arc bridge inbox` should succeed without `no arc-bridge server is configured`.
