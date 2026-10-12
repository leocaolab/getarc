# Install reference — the facts each stage needs

The person installing arc does not have arc's source or its docs, so the facts the
stages rely on are here. Each section names the document it is taken from (in arc's
repo) so it can be re-checked when arc changes.

## tars providers (`<tars home>/config.toml`)
*From `docs/user-guide/configuration.md`, `docs/user-guide/coding-agents.md`; schema in
tars-config `providers.rs`.*

One table per provider, named by an id the person chooses. Unknown keys are refused,
naming the key and the ones allowed.

Where arc looks: `--tars_home DIR` reads `DIR/config.toml`; `--tars-config FILE` names
the file directly; with neither, `$TARS_HOME/config.toml`, else `~/.tars/config.toml`.
Pass the same flag to every arc call.

```toml
[providers.gemini_flash]            # an API-key provider
type = "gemini"
default_model = "flash@latest"      # a concrete id, or <series>@latest where the provider defines series
auth = { kind = "secret", secret = { source = "env", var = "GEMINI_API_KEY" } }
# or: secret = { source = "file", path = "~/.keys/gemini" };  auth = { kind = "none" } for a local server

[providers.claude_fixer]            # Claude Code as the Fixer — uses `claude login`, no auth
type = "claude_cli"
default_model = "sonnet"
tools = "default"                   # REQUIRED for a Fixer; the default "disabled" cannot edit
timeout_secs = 900                  # default 300

[providers.codex_fixer]             # Codex CLI
type = "codex_cli"
default_model = "<a Codex model id>"
sandbox = "workspace-write"         # REQUIRED for a Fixer; the default is "read-only"
timeout_secs = 900                  # default 600 (the key is timeout_secs, not timeout)

[providers.agy]                     # agy (Antigravity CLI)
type = "antigravity"
default_model = "<model>"
effort = "high"                     # "low" | "high"
```

Every CLI type also takes `executable` (default `claude`, `codex`, `agy`). Types:
`openai`, `openai_compat`, `anthropic`, `gemini`, `bedrock`, `vllm`, `mlx`, `llamacpp`,
`claude_cli`, `claude_sdk`, `codex_cli`, `opencode`, `antigravity`. arc's own tests run
`claude_cli` as a Fixer end to end; `codex_cli` and `antigravity` are accepted but not
tested as Fixers end to end.

## `.arc/config.toml`
*From `docs/user-guide/configuration.md`.* Not committed (`arc init` writes
`.arc/.gitignore`). No `[providers]` — refused.

```toml
[roles]
default   = "<critic id>"
critic    = "<critic id>"
critic_l4 = "<critic id>"     # per-file review
critic_l5 = "<critic id>"     # arc rot's judge
fixer     = "<fixer id>"      # must be written out; never falls back to default

[gate]                         # optional: what arc fix hands the Fixer to run
command       = "<build, compiling tests too>"
final_command = "<tests>"
# or: workflow = ".github/workflows/ci.yml"  job = ["build"]   — never both forms
```

## Merge gate (`.github/workflows/merge.yml`)
*From `docs/user-guide/merge-gate.md`.* A merge machine runs it — not GitHub — on the
base and on the merged tree; a PR lands when the second run adds no failure. It is read
from the target branch, so a PR editing it is judged by the old copy.

- Path fixed: `.github/workflows/merge.yml`. Trigger: `on: workflow_dispatch: {}` only.
- All jobs run, in file order, as one gate; `needs:`, `runs-on:` are not read. Steps run
  under `sh -c` with `set -e`, no `pipefail` (a `| tee` hides the runner's status).
- Honoured: `run:`, `name:`, `env:` (workflow / job / step), `working-directory:`,
  `defaults.run.working-directory`, `strategy.matrix.include`, `if:` on `runner.os`,
  `runner.arch`, `env.*`, `matrix.*`; arc's own `phase:` (`build`/`test`/`lint`/`deploy`).
- `uses:` only `actions/checkout` (nothing), `actions/setup-node|python|go` with
  `with: node-version|python-version|go-version` and `dtolnay/rust-toolchain@<ref>` —
  each checks the merge machine's installed version before the first step; it installs
  nothing. Any other `uses:` is refused. A matrix expands only `strategy.matrix.include`:
  a one-value list (`python: ["3.12"]`) becomes the literal; for several, write each
  combination under `include:`. A `run:` cannot read a matrix value (`${{ matrix.x }}`
  is refused); only `if:` reads `matrix.*`.
- `${{ … }}` anywhere is refused — use shell variables (`$NODE_ENV`).
- One refused step anywhere and every PR comes back *cannot say*.
- For a compiled language the build must compile tests (`cargo build --all-targets`,
  `tsc -b`); with no compile step, the test run is the check. Keep runner
  output arc reads on the console: rustc/cargo, cargo test, nextest, vitest, tsc,
  Playwright, pytest.
- Main must be green on the merge machine before the repo is registered.

```yaml
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

Check every job: `arc workflow .github/workflows/merge.yml --job <job> --list`.

## Deploy (`[release]` + `.arc/delivery.toml`)
*From `docs/user-guide/release.md`.* Runs on the merge machine, in its clone of the repo.
- A deploy job (any workflow file) with a `concurrency:` group; it builds in
  `$RUNNER_TEMP`, deploys `${ARC_DEPLOY_REF:-main}`, writes the shipped sha to
  `$ARC_SHIPPED_SHA`, and marks going-live steps `phase: deploy`.
- `.arc/config.toml`: `[release] workflow = "<file>"`, `job = "<job>"`.
- `.arc/delivery.toml` (committed): exactly one `[builds.<id>]` with the same `workflow`
  and `job` (`from = "main"`, `on = "merge"` to deploy after each landing), and
  `[targets.<id>]` (`kind = "service"|"binary"`, `promote = "auto"|"manual"`, `from = <build id>`).
- Check with `arc workflow <file> --job <job> --list`. Never run the job without `--list`.

## Bridge (participant)
*From `docs/user-guide/coding-agents.md`.* Needs an operator's arc-bridge server.
- `~/.arc/client.toml`, exactly one key: `web = "http://<board-host>:<port>"`.
- Claude Code hooks (in `~/.claude/settings.json` or the repo's `.claude/settings.json`;
  arc does not install them):

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

- Codex CLI: `~/.codex/config.toml` with `[features] hooks = true` and
  `[[hooks.<Event>]]` / `[[hooks.<Event>.hooks]]` tables running
  `/abs/path/arc bridge hook <Event> --agent codex --name <name>` for SessionStart,
  PreToolUse, Stop (`--mail waiter`), SessionEnd; then trust them in `/hooks`.
- agy: `~/.gemini/config/hooks.json` or `.agents/hooks.json`:
  `{"arc-bridge": {"Stop": [{"type": "command", "command": "<arc> bridge hook Stop --agent agy --name <name>", "timeout": 30}]}}` — `Stop` only, once.
- Verify: `arc bridge inbox` answers without `no arc-bridge server is configured`.
