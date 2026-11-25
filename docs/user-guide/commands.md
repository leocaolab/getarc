# The commands — review your change, fix it, submit it

Check a change on your own machine before anyone else sees it, then hand it to the pipeline:

```text
your agent writes a change ──▶ arc local-review ──▶ arc fix ──▶ arc submit
```

`arc local-review` and `arc fix` run on your machine and need no server. `arc submit` pushes the change; from there the pipeline reviews it again, merges it and ships it ([Review on the pipeline](pipeline-review.md)).

| Goal | Command |
|---|---|
| Set arc up in this repo | `arc init` — writes `.arc/config.toml` from your tars providers (asks you questions in a terminal; outside a terminal it writes an example file) |
| Review my change | `arc local-review` — reviews this branch's change and prints a report; never edits a file |
| Fix what the review found | `arc fix [id\|path]` — fixes each finding with one commit on your branch, then reviews again, until the reviewer says LGTM or `[review] max_rounds` is used up |
| Look for structural problems across the repo | `arc rot` — whole-repo L5 review |
| Run the pre-submit checks only | `arc presubmit` — runs `presubmit.toml`'s checks on HEAD, the same ones `arc submit` runs; pushes nothing |
| Send the change for review | `arc submit` — pushes the branch, opens (or reuses) its PR and puts it on the review queue |
| Review every commit automatically | `arc hook install` — after each commit, runs `arc local-review` in the background and records the commit's diff for test history (`arc tap record`); `arc hook uninstall` removes it |

## The local path: `arc local-review`, then `arc fix`

**`arc local-review`** reviews everything on your branch that differs from the remote's default branch, including uncommitted changes in the working tree. It stores the result as a "local PR" in this clone's `.arc/review.db` — one round of review, the same kind the pipeline runs. It only reads; it never edits a file.

When it finishes it prints a report. Each open finding comes with its file and line, the rule it broke, the reviewer's own words and the code around it. Paste the report into your own Claude to fix, or open it in VS Code. A report from arc's test fixture:

```
[A.R.C.] local-review: local PR acme/app#1 at <sha>

- finding F-1 — lib.rs:3 [free_review::ad-hoc]
  reviewer: x is never read
  code:
    1 | // one
    2 | fn f() {
  > 3 |     let x = 1;
    4 | }

[A.R.C.] 1 finding(s) open — fix them in this working tree and run `arc local-review` again, or run `arc fix`
```

- `--since HEAD` reviews only what is not committed yet. `--since HEAD~1` reviews the last commit plus what is not committed yet.
- `--show` reviews nothing. It prints the branch's last local PR and the state of each finding on it.
- How a run ends: if the reviewer approves, the local PR is marked passed (landed) and arc prints `LGTM from <reviewer>: <its words>`. If the reviewer used up its turns without approving, arc prints `no LGTM: the reviewer's turns ran out ([review] max_rounds), so the head went through with N finding(s) open`.

**`arc fix`** works through every open finding on the local PR. For each one the Fixer either fixes it or says why it won't, and each fix is one commit on your current branch, in your working tree. Then the new tip is reviewed again. If that review still leaves findings, `arc fix` fixes again — until the reviewer says LGTM or has used its `[review] max_rounds` turns. Each round prints what was answered and what the review said. The last line says why it stopped: `[A.R.C.] fix: stopped — the reviewer said LGTM on the head`, or `… took its N turns ([review] max_rounds) without an LGTM, so the head is let through with what it left open`.

- **Clean tree first.** The working tree must match HEAD: no changes to tracked files, no untracked files (ignored files are fine). Commit or stash first.
- **Review first.** If the branch has no local PR yet, run `arc local-review` first.
- **Undo.** `git reset --hard refs/arc/before-fix/<branch>` removes every commit the run made.
- **Narrow it down.** `arc fix <path>` fixes one file or folder; `arc fix <id>` fixes one finding. `arc fix --dry-run` only assesses and changes nothing.

## Submit it

`arc local-review` and `arc fix` never push. When the local PR is clean, run `arc submit`. It runs `presubmit.toml`'s checks, pushes the branch, opens (or reuses) its PR and puts it on the review queue. The pipeline's review service takes it from there ([Review on the pipeline](pipeline-review.md)). To run the same checks without pushing anything, run `arc presubmit` ([Configuration](configuration.md#repopresubmittoml--the-checks-before-submit)).

## The other tools

All of these run on your machine:

- **`arc rot`** — reviews the whole repo for structural problems. It only prints suggestions; to act on one, make the change on a branch ([Rot](rot.md)).
- **`arc hook install`** — reviews each commit in the background with `arc local-review` and logs to `.arc/critic.log`. It skips commits made in a linked worktree, commits replayed by a rebase, cherry-pick, revert or amend, and commits already reviewed. It never edits. It also records each commit's diff for test history (`arc tap record`, logged to `.arc/tap.log`). `arc hook uninstall` removes it.
- **`arc tap`** / **`arc affected`** — test history from your test runner's JUnit XML, and which tests a change can reach. arc never runs your tests: `arc tap init` makes your normal test run write JUnit XML, `arc tap test` reads it in, and `arc tap signal` shows slow and flaky tests. The history goes to the pipeline's test-history server (arc-tap): the one you name with `--tap-server`, or else the one your board names for this repo (the board is the `web = "http://…"` address in `~/.arc/client.toml`). With neither, the command stops and says so; there is no local fallback.
- **`arc reset --yes`** — deletes this repo's local arc history and keeps the config.


## Every command

`arc --help` lists fifteen commands. Grouped by what you want to do:

| You want to | Command |
|---|---|
| set arc up in a repo | `arc init`, `arc hook install` / `arc hook uninstall`, `arc reset --yes` |
| review and fix a change on your machine | `arc local-review`, `arc fix`, `arc rot` |
| hand a change to the pipeline | `arc presubmit`, `arc submit`; `arc archcheck` runs as a step of the merge check ([Merge](merge-gate.md#architecture-rules-a-step-of-the-gate)) |
| ship | `arc deploy` — run it in the repo's clone on the deploy machine; it starts the repo's declared deploy of origin/main's tip right away |
| check the tree | `arc affected`, `arc tap` |
| track work | `arc issues` (the issue board, `b/<n>`) |
| talk to the other agents | `arc bridge` ([Team up](bridge.md)) |
| search the log: who changed a file, who worked on a repo, what one session did, who said these words | `arc intent history` |

Each command's subcommands and flags are in `arc <cmd> --help`, which is the source of truth. Add `--json` to any command to get one machine-readable JSON result, for agents and scripts.

Some commands are hidden from `--help` because a hook, a service or another program runs them, not a person. They still run if you type them:

| Hidden command | Who runs it, or what it is for |
|---|---|
| `arc intent collect` | every hook starts one |
| `arc intent floor reindex` | you, if `intent.db` is lost: rebuilds its file index from the archived files |
| `arc bridge supervisor` | the Stop hook |
| `arc workflow` | runs one job of a workflow file on this machine |
| `arc post-commit-gate` | the post-commit hook, to decide whether a commit needs a review |
| `arc review-task` | `arc local-review` starts it as the reviewer |
| `arc fix-task` | the review service starts it as the fixer when `fixer_client = "tars"` |
| `arc errpaths` | an internal tool: lists every error-handling site in the Rust tree as JSON lines |

Some old names are gone. Typing one is a usage error, and for these arc tells you what to type instead:

| You typed | Type instead |
|---|---|
| `install-hook` / `uninstall-hook` (top level) | `arc hook install` / `arc hook uninstall` |
| `arc issues create` / `new` | `arc issues open` |
| `arc issues search` | `arc issues list` |
| `arc issues close` | `arc issues fixed`, `wont-fix` or `duplicate` — the status says how it ended |
| `arc issues view` | `arc issues show` |

`arc issues verify` / `set-verifier` and `arc bridge revive` were removed with nothing in their place: no issue was ever verified, and no timer ever ran revive.

---

*Next: [Rot (L5)](rot.md) · full flag reference in `../usage.md`.*
