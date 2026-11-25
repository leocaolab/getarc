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
| `smoke.review_service_here` is `false` | This machine does not run the review service for this repo (the usual case on a coding machine), so `arc submit` hands the PR to the pipeline machine. `arc local-review` and `arc fix` need no service: they work locally on `.arc/review.db` | Proceed; say so if the person expects a review on this machine |
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
| 7 | A check answered "no" (`arc archcheck` found a broken rule) | Read the report and fix what it names; not a crash |
| 8 | The command's own write took, but a record it owes elsewhere did not (`arc submit`: the PR is in review, but an issue named in the title did not list it) | Do not re-run blindly; follow the message |
| 9 | The run ended by calling a person | Stop and hand over; nothing failed |
| 10 | The reviewer could not review: its call failed, no round was written | Read the error; running again calls it again |
| 11 | `arc submit`: a presubmit check did not pass, timed out or could not start; the change was still pushed and is in review | Read each check's output; fix and push a new version |

With `--json`, always check the response envelope: `"success": false` indicates a failure even if the exit code is 0, and `"error"` holds the exact reason.

For any failure, pipe the output into `python3 ${CLAUDE_PLUGIN_ROOT}/skills/arc-setup/scripts/diagnose.py --from -` to match it against known issues.
