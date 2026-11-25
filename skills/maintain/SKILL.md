---
name: maintain
description: >-
  Diagnose and maintain A.R.C. (arc) in an existing repo — troubleshoot failing
  commands, refused reviews, stale local state after a refactor, or swapping
  provider roles. Use when arc behaves unexpectedly or the user asks to reset,
  clean up, or reconfigure arc.
allowed-tools: "Bash Read Edit"
---

# arc maintenance

## Diagnose failures — don't guess
1. Re-run the install probe:
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/arc-setup/scripts/probe.py`
   (pass `--tars-home DIR` if provider config is not in `~/.tars`). If any required stage is not `done`, resume with **`arc-skills:arc-setup`**.
2. Run the failing command through `diagnose.py`:
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/arc-setup/scripts/diagnose.py -- <command>`
   (or `--from -` with existing output for commands that shouldn't run twice). If it matches a known issue, show the cause and fix; otherwise report the raw output as-is.
3. Add `-v` or `-vv` to any `arc` command for verbose diagnostic logs on stderr.

Common errors and fixes:
- `"cannot tell who is submitting — not in an agent session and no gh login"` → run from inside a coding agent session, or run `gh auth login`.
- `"this checkout's branch holds no open local PR — run arc local-review first"` → run `arc local-review` on the branch first.
- `"missing credential: env var X is not set"` → export the provider's API key in the current shell.
- `"No provider for role …"` → `[roles]` in `.arc/config.toml` is missing that role and has no `default`.

See `known_issues.json` in `skills/arc-setup/` for the full list.

## Reset local state (destructive — confirm first)
Use this after a major refactor if local review state is stale:
```bash
arc reset          # dry-run: lists what would be removed
arc reset --yes    # wipes local arc state in this repo; preserves .arc/config.toml and .arc/delivery.toml
```
Always show the user the `arc reset` listing before running `--yes`.

## Swap provider roles
Edit `[roles]` in `.arc/config.toml` (`critic_l4`, `critic_l5`, `critic`, `default`, `fixer` — each mapped to a provider ID in `~/.tars/config.toml`), or run `arc init --force` in an interactive terminal. Keep the fixer on a different model family from the critic when possible, and always specify `fixer` explicitly. Re-run `probe.py --stage roles` afterward.

## Check run progress
- **Personal edition:** `arc local-review --show` prints the branch's local PR and the status of every finding.
- **Team edition:**
  ```bash
  curl <web>/api/r/<owner>/<name>/progress/<b/N|PR|branch>   # check PR progress (`web` is in ~/.arc/client.toml)
  ```
  Full findings and review rounds are visible on the PR's review page.
