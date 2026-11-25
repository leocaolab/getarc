# arc preflight (shared)

Run before any `arc` action. Fail closed: if something is missing, stop and route the user to the right skill — never fabricate a review or a fix.

## Checks

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/arc-setup/scripts/probe.py --stage prereq --stage binary --stage roles --stage smoke
```

Pass `--tars-home DIR` if the user's provider config lives outside `~/.tars` (and pass `--tars_home DIR` to `arc`).

| Probe result | Meaning | Action |
|---|---|---|
| `prereq`, `binary`, or `roles` is not `done` | `arc` is not installed or configured here | Route to **`arc-skills:arc-setup`** and stop |
| `smoke.review_service_here` is `false` | No team review service is watching this repo from this machine, so `arc submit` would queue a PR nobody picks up. `arc local-review` and `arc fix` still work locally using `.arc/review.db` | Mention this before running `arc submit`; `local-review` and `fix` can proceed |
| Branch has no open local PR | `arc fix` fails with `this checkout's branch holds no open local PR — run \`arc local-review\` first` | Run `arc local-review` first (local only, nothing pushed) |

## Exit codes

| Code | Meaning | Action |
|---|---|---|
| 0 | Command succeeded | `arc local-review` also exits 0 when it finds issues — check the finding count in `--json`, never assume exit 0 means clean |
| 1 | Internal error (bug, or a review unit failed) | Report the raw output |
| 2 | Config or setup error (bad config, missing role/tool, invalid flags) | Fix the setup; do not retry |
| 3 | Git or repository state error | Fix the working tree or branch state |
| 4 | Provider error (non-transient) | Report the provider/policy error |
| 5 | Filesystem or storage error | Check disk/permissions |
| 6 | Transient error (rate limit, network, queued request) | Safe to retry later |
| 7 | A gate rejected the change (`post-commit-gate`) | Expected gate rejection, not a crash |
| 8 | `arc submit`: an issue named in the PR title did not list it | Re-run `arc submit` |

With `--json`, always check the response envelope: `"success": false` indicates a failure even if the exit code is 0, and `"error"` holds the exact reason.

For any failure, pipe the output into `python3 ${CLAUDE_PLUGIN_ROOT}/skills/arc-setup/scripts/diagnose.py --from -` to match it against known issues.
