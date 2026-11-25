# The commands — review your change, fix it, submit it

The loop on your machine: your agent writes a change, arc reviews it here (`arc local-review`), the Fixer answers until the reviewer says LGTM (`arc fix`), and `arc submit` hands it to the pipeline, which reviews it again, lands it and ships it ([Review on the pipeline](pipeline-review.md)). The first two are the check you run before you submit; they need no server.

| Command | What it does |
|---|---|
| `arc init` | write `.arc/config.toml` from your tars registry (interactive; non-TTY writes an example) |
| `arc local-review` | review this branch's change on your machine as a local PR; prints a report, never edits |
| `arc rot` | whole-repo L5 structural-rot review |
| `arc fix [id\|path]` | the Fixer answers what the local PR owes, one commit per fix on your branch, and the change is reviewed again — round after round until LGTM or `[review] max_rounds` turns |
| `arc presubmit` | run `presubmit.toml`'s checks on HEAD, as `arc submit` runs them before it pushes; pushes nothing |
| `arc submit` | push the branch, open (or reuse) its PR and hand it to the review service |
| `arc hook install` | after each commit, a background `arc local-review` of it and a record of its diff for test history (`arc tap record`); `arc hook uninstall` removes it |

## The local path: `arc local-review`, then `arc fix`

**`arc local-review`** reviews the branch's change against the remote's default branch, the working tree as it is, as one round of review on this clone's own `.arc/review.db`. It only looks: it never edits a file. When it finishes it prints a report — each open finding with its place, its rule, the reviewer's own words and the code around it — which you can paste straight into your own Claude to fix, or open in VS Code. A report from arc's test fixture:

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

- `--since HEAD` reviews only what is not committed yet; `--since HEAD~1` the last commit and what is not committed yet.
- `--show` reviews nothing: it reads back the branch's last local PR and where each finding on it stands.
- When the review lets the head through, the local PR is recorded as passed (landed). The run says why: `LGTM from <reviewer>: <its words>`, or, when the reviewer's turns ran out, `no LGTM: the reviewer's turns ran out ([review] max_rounds), so the head went through with N finding(s) open`.

**`arc fix`** has the Fixer answer each finding the local PR owes — fixed or won't fix — one commit per fix on your current branch, in your working tree. The answers go on the new head, which is reviewed again; while that review leaves findings, it fixes again, until the reviewer says LGTM or has taken its `[review] max_rounds` turns. Each round prints what it answered and what the review said, and the run ends on one line saying why it stopped (`[A.R.C.] fix: stopped — the reviewer said LGTM on the head`, or `… took its N turns ([review] max_rounds) without an LGTM, so the head is let through with what it left open`).

- The working tree must be HEAD's: no tracked change and no untracked file (ignored ones are fine). Commit or stash first.
- No local PR yet → run `arc local-review` first.
- `git reset --hard refs/arc/before-fix/<branch>` undoes the whole run.
- `arc fix <path>` or `arc fix <id>` narrows it to a file, a folder or one finding; `arc fix --dry-run` only assesses and changes nothing.

## Submit it

`arc local-review` and `arc fix` never push. When the local PR is clean, `arc submit` runs `presubmit.toml`'s checks, pushes the branch, opens (or reuses) its PR and puts it on the review queue; the pipeline's review service takes it from there ([Review on the pipeline](pipeline-review.md)). To run the same checks without pushing anything, `arc presubmit` ([Configuration](configuration.md#repopresubmittoml--the-checks-before-submit)).

## The other tools

All of them run on your machine:

- **`arc rot`** — whole-repo structural review; suggestions only, acted on through a branch ([Rot](rot.md)).
- **`arc hook install`** — reviews each commit in the background (`arc local-review`), logged to `.arc/critic.log`; it skips commits in a linked worktree, during a rebase or cherry-pick, on an amend, and commits already reviewed. It never edits; it also records each commit's diff for test history (`arc tap record`, logged to `.arc/tap.log`). `arc hook uninstall` removes it.
- **`arc tap`** / **`arc affected`** — test history from your runner's JUnit XML, and which tests a change can reach. arc never runs your tests: `arc tap init` makes JUnit a side effect of your normal run, `arc tap test` ingests it, `arc tap signal` shows slow and flaky tests. It writes the pipeline's central test-history store when this machine's board names one for the repo (or `--tap-server` does), else the repo's own `.arc/tap.db`.
- **`arc reset --yes`** — wipes this repo's local arc history; keeps the config.


## Every command

`arc --help` lists fifteen commands. Grouped by what you are doing:

| You want to | Command |
|---|---|
| set arc up in a repo | `arc init`, `arc hook install` / `arc hook uninstall`, `arc reset --yes` |
| review and fix a change on your machine | `arc local-review`, `arc fix`, `arc rot` |
| hand a change to the pipeline | `arc presubmit`, `arc submit`; `arc archcheck` is a step of the merge gate ([Merge](merge-gate.md#architecture-rules-a-step-of-the-gate)) |
| ship | `arc deploy` (in the repo's clone on the deploy machine: starts its declared deploy of origin/main's tip now) |
| check the tree | `arc affected`, `arc tap` |
| track work | `arc issues` (the issue board, `b/<n>`) |
| talk to the other agents | `arc bridge` ([Team up](bridge.md)) |
| ask the log: who changed a file, who worked on a repo, what one session did, who said these words | `arc intent history` |

Each one's subcommands are in `arc <cmd> --help`. A few are left out of `--help` because a hook, a service or another program runs them, never a person at work; they still run when typed: `arc intent collect` (every hook starts one), `arc intent floor reindex` (rebuilds the index from the floor), `arc bridge supervisor` (the Stop hook starts it), `arc workflow` (runs one job of a workflow file here), `arc post-commit-gate` (the post-commit hook's), `arc review-task` (the reviewer `arc local-review`'s engine starts) and `arc fix-task` (the fixer the review service starts with `fixer_client = "tars"`).

Some names are gone. Typing one is a usage error, and for the ones below arc says what to type instead:

| You typed | Type |
|---|---|
| `install-hook` / `uninstall-hook` (top level) | `arc hook install` / `arc hook uninstall` |
| `arc issues create` / `new` | `arc issues open` |
| `arc issues search` | `arc issues list` |
| `arc issues close` | `arc issues fixed`, `wont-fix` or `duplicate` — the status says how it ended |
| `arc issues view` | `arc issues show` |

`arc issues verify` / `set-verifier` and `arc bridge revive` are removed with nothing in their place: no issue was ever verified, and no timer ever ran revive.

`arc <cmd> --help` is the source of truth for flags. `--json` makes any command emit one machine-readable envelope (the agent control bus).

---

*Next: Finding model · [Rot (L5)](rot.md) · full flag reference in `../usage.md`.*
