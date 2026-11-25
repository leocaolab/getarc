# Review on the pipeline

On the pipeline, your change is reviewed by the **review service** (`arc-review`), not on your machine. The steps:

1. You run `arc submit`. It pushes the branch and puts the PR on the review queue.
2. Reviewer agents read the PR and write findings.
3. You answer each finding and push a fix. The new head commit is reviewed again.
4. When every reviewer says LGTM, the review service writes a **pass** for that exact commit: a git ref, `refs/arc/pass/<pr>`, pointing at the commit they approved.
5. The merge machine only takes a PR whose pass points at its current head ([Merge](merge-gate.md)). Push again and you need a new LGTM.

## 1. Send a change to review: `arc submit`

```bash
arc submit                      # a new PR: push, open it, queue its review
arc submit --pr 514             # send this head to PR 514 as an update
```

What `arc submit` does, in order:

1. **Runs your checks.** Before pushing, it runs the checks in `presubmit.toml` on HEAD ([Configuration](configuration.md#repopresubmittoml--the-checks-before-submit)). Every check runs, and a failed one stops nothing: the head is still pushed, each check's result is pushed with it as a git note (shown on the PR's page and on the board), and the PR still goes to review. At the end arc names the failed checks and exits 11.
2. **Pushes the branch** under its own name. It never overwrites commits the remote has and HEAD does not.
3. **Opens the PR**, or reuses the open one, puts it on the review queue, and exits:

```
[A.R.C.] submit: PR #514 · handed to review (<sha>)
         <url>
         branch <branch> — the review service asks the reviewers the tenant's routes name; their LGTM grants the pass and the merger lands it. A new push is a new version and is reviewed again
```

Options and side effects:

- **Inside an agent session with the bridge on,** `arc submit` also links the PR to that session (`bridge: verdicts for this PR go to <name> in channel pr:…`), so the review results come back to you ([Team up](bridge.md)).
- `--branch <name>` checks that HEAD is on that branch and refuses if it is not. Use it when something else may move HEAD (another agent in the same working tree, a long command before this one).
- `--after <N>` lands this change only after PR N has landed. Repeat it to wait for several PRs.
- A `b/<n>` in the PR title records this submission on that board issue. If `b/<n>` does not exist, arc exits 8.

## 2. Choose who reviews

Who reviews a repo's PRs is set by its routes, in `~/.arc/machine.toml` on the pipeline machine ([Configuration](configuration.md#arcmachinetoml--the-pipeline-machine)):

```toml machine.toml#tenant
[[tenant.review.route]]          # PRs labelled arc-bypass: the dummy reviewer, which says LGTM
label    = "arc-bypass"
reviewer = "dummy"
name     = "dummy"

[[tenant.review.route]]          # every other PR: a real reviewer
reviewer = "react"
name     = "react"
```

- `reviewer` is `dummy` (approves everything), `basic` or `react`. Real reviewers use the `[roles]` in `.arc/config.toml` of the repo's clone on the pipeline machine. `name` is the name the reviewer signs its replies with.
- **With no route, nobody reviews and nothing lands.** For a repo nobody else reviews, route every PR to `dummy`.
- `[tenant.review] gate` says whose LGTM writes the pass: `all_lgtm` (the default: every reviewer of the head) or `one_lgtm` (any one).
- `[tenant.review] max_rounds` (default 5) is how many rounds a reviewer may go without saying LGTM. After that, it lets the head through and stops reviewing it.
- `arc submit --bypass-review` labels the PR `arc-bypass`, and the route above sends it to the dummy reviewer. Even a skipped review goes through the review service and is recorded.

## 3. Read the findings

Each review round's report is written to the git ref `refs/arc/reports/<cl>`. With the bridge on, a review that has findings is sent to the PR's channel and put into your session when it stops (or wakes it up if it is idle). The message lists the findings and a ready-to-fill `arc submit --pr <N> --fix-answers -` command.

## 4. Answer each finding

Answer every finding with **fixed** (and what you changed) or **won't fix** (and why). Push the fix first, then send the answers:

```bash
arc submit --pr 514 --fix-answers - <<'EOF'
[{"finding": 3, "kind": "fixed", "text": "carried the error typed: #[from] GitError"},
 {"finding": 5, "kind": "wontfix", "text": "the empty string is the wire format the client expects"}]
EOF
```

- The answers are sent with the new head as one update, in the order of the array.
- If one item is wrong, all of them are refused and nothing is sent. `--fix-answers` without `--pr` is refused.
- Or let the Fixer do it on your machine: `arc local-review`, then `arc fix` ([The commands](commands.md)). Then send the new head with `arc submit --pr <N>`.

The reviewer then reads the new head. It closes each answered finding or reopens it, and it may raise new ones. Every push is a new version and is reviewed again.

## 5. LGTM, landing, holding and giving up

When the reviewers your routes asked for have all said LGTM on the head, the review service writes the pass, `refs/arc/pass/<pr>`, on that commit. The merge machine only takes a PR whose pass is its current head.

- **To keep a PR from landing, label it `arc-hold`.** The merge machine skips a held PR even when it has a pass. Remove the label and it is picked up again.
- **To drop a PR without landing it,** run `arc submit --abandon "<why>"` on its branch, with no other flag. arc records the close and your reason, word for word, on the review queue, then closes the PR on GitHub. It pushes nothing and opens nothing. Do not close the PR by hand.

## 6. Review on the board

The board (arc-web) has a **Review** tab: changes that need you and why, what agents are working on, and history.

- **The change page** shows what the change is (title, status, author, size), why it is waiting, each reviewer's opinion and findings, the head's files, the revision history, its risk and how much of the code it reaches, and the head's presubmit results. Its buttons: *Open on GitHub*, *Fix again* (send it back to its author) and *LGTM*.
- **Files · comments** is the editor page. It shows one version's code next to its findings, and diffs any version against any later one. Select lines and comment on them from the right-click menu; each comment becomes a finding in your review round. Decide on each existing finding (close it, or send it back), then click *Send review* to send your whole round at once. Nobody lands a change from this page — only the merge machine lands changes.

---

*Next: [Merge](merge-gate.md) · [Team up](bridge.md) · [Releases and deploys](release.md).*
