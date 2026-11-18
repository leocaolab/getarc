# arc preflight (shared)

Run before any arc action. It fails closed: when something is missing, stop and route
the person to the right skill — never fabricate a review or a fix.

## Checks

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/arc-setup/scripts/probe.py --stage prereq --stage binary --stage roles --stage smoke
```

Pass `--tars-home DIR` when the person's tars home is not `~/.tars` (and give arc the
same `--tars_home DIR`).

| Probe result | Means | Do |
|---|---|---|
| `prereq` / `binary` / `roles` not `done` | arc is not installed or not configured here | **`arc-skills:arc-setup`**; stop |
| `smoke.review_service_here` false | no review service serves this repo from this machine: `arc submit` puts a PR on a queue nobody here takes. `arc local-review` and `arc fix` do not need one — they run on the clone's own `.arc/review.db` | say so before `arc submit`; local-review / fix run |
| the branch holds no open local PR | `arc fix` stops with `this checkout's branch holds no open local PR — run \`arc local-review\` first` | run `arc local-review` first (local only, nothing pushed) |

## Exit codes (an agent API — `crates/review/cli/src/error.rs`)

| Code | Class | What to do |
|---|---|---|
| 0 | the command did what it says | a review exits 0 with findings too: read the count from `--json`, never infer "clean" from 0 |
| 1 | internal — likely a bug, or a review with a unit that failed | report the raw output |
| 2 | config / setup (config, role, missing tool, clap flags) | fix the setup; do not retry |
| 3 | git / repository state | fix the tree |
| 4 | provider (not transient) | provider / policy; report |
| 5 | filesystem / storage | environment |
| 6 | transient (rate limit, network, a request not yet taken) | may retry later |
| 7 | a gate said "no" (`post-commit-gate`) | not an error |
| 8 | `arc submit`: an issue the PR title names did not list it | re-run `arc submit` |

With `--json`, also read the envelope: `"success": false` is a failure even on exit 0,
and its `"error"` is the reason, word for word.

For any failure, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/arc-setup/scripts/diagnose.py --from -`
(the output on stdin) matches it against the known issues.
