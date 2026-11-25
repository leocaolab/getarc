# arc for coding agents

This page is for you, the coding agent (Claude Code, Codex CLI, agy) that has to use arc. Read it once; it says what arc does, which command to run at each step, what comes back, and what you must never do. Every flag is in `arc <command> --help`, which is the source of truth when this page and the binary disagree.

## Quick start

You were asked to set up arc, or to use it. In order:

1. **Is arc here?** `arc --version`. If not, or if the repo has no `.arc/config.toml` or no pipeline yet, run the install route below with the arc-setup skill (`claude plugin install arc@getarc`, or `npx skills add leocaolab/getarc --skill arc-setup`).
2. **Before you submit a change:** on a feature branch, `arc --json local-review`; then `arc --json fix` until the review is closed (section 2).
3. **Submit:** `arc --json submit --target origin/main --base "$(git merge-base HEAD origin/main)"`, after asking the person — it pushes.
4. **Answer what comes back:** findings arrive in your session; fix, push, `arc submit --pr <N> --fix-answers -`. The merge machine lands the PR after every reviewer's LGTM.
5. **Working through a milestone:** `arc issues loop start b/<milestone> --until drained --role assignee`; ask a person with `arc issues block b/<n> --said … --option … --option …` and wait for the ruling in your session. The board side of this: [Working on the board](working-on-the-board.md).

## The install route

arc-setup walks these stages in order. At each one it probes what is already there (`probe.py --machine coding|pipeline|both --stage <id>`), asks the person only what the probe cannot tell, does only what is missing, and verifies the stage with one command before the next. A failed verify stops the route with the real error. Each stage follows a page of this guide.

| # | Stage | Machine | Verify | Guide |
|---|---|---|---|---|
| 1 | `prereq` | coding | `git rev-parse --show-toplevel` | [Install](install.md) |
| 2 | `binary` | coding | `arc --version` | [Install](install.md) |
| 3 | `tars` | coding | `probe.py --stage tars` | [Configuration](configuration.md) |
| 4 | `roles` | coding | `probe.py --stage roles` | [Configuration](configuration.md) |
| 5 | `smoke` | coding | `arc rot --no-judge` | |
| 6 | `presubmit` (optional) | coding | `arc presubmit --target origin/<target> --base "$(git merge-base HEAD origin/<target>)"` | [Configuration](configuration.md) |
| 7 | `merge_gate` | coding | `arc workflow .github/workflows/merge.yml --job <job> --list` | [Merge](merge-gate.md) |
| 8 | `labels` | coding | `gh label list --search arc-hold` | [Set up the pipeline](onboarding.md) |
| 9 | `suite` | pipeline | `probe.py --machine pipeline --stage suite` | [Set up the pipeline](onboarding.md) |
| 10 | `machine` | pipeline | `arc-server tenant url web` | [Set up the pipeline](onboarding.md) |
| 11 | `board` | pipeline | `curl -fsS "$(arc-server tenant url web)/api/machine"` | [Set up the pipeline](onboarding.md) |
| 12 | `tenant` | pipeline | `arc-server tenant check <owner/name>` | [Set up the pipeline](onboarding.md) |
| 13 | `tenant_services` | pipeline | `probe.py --machine pipeline --stage tenant_services` | [Set up the pipeline](onboarding.md) |
| 14 | `client` | coding | `arc bridge inbox` | [Connecting your coding agent](coding-agents.md) |
| 15 | `first_pr` | coding | `curl -fsS <web>/api/r/<owner>/<name>/merger` | [Set up the pipeline](onboarding.md) |
| 16 | `release` (optional) | pipeline | `arc workflow <deploy workflow> --job <job> --list` | [Releases and deploys](release.md) |

When the pipeline machine is not one you can run commands on, give the person each stage's commands, one stage at a time, judge the output they paste back, and verify from the coding machine what the board shows (stage `client` asks it whether it serves this repo).

## 1. What arc is, and the one loop

- arc reviews code changes. A reviewer model files **findings** on your change; you (or arc's Fixer) answer each one **fixed** or **won't fix**; the reviewer reads the new head again.
- It runs in two places: on your machine (`arc local-review`, `arc fix`), and on the pipeline, a server suite that reviews every PR, grants a **pass** on LGTM, and lands the PR.
- Only the review service grants a pass (`refs/arc/pass/<pr>`), and only for the exact head it reviewed. Only the merge machine lands. Nobody merges by hand.
- Findings, rounds and answers are recorded; you never edit them, you answer them.
- arc is a detector. A finding is the reviewer's opinion; a reasoned won't-fix is a valid answer.

The loop, and whose move each step is:

| Step | What happens | Whose move |
|---|---|---|
| 1 | `arc local-review` — review the branch's change here, as a local PR | you |
| 2 | `arc fix` — the Fixer answers the open findings, one commit per fix, and the change is reviewed again until LGTM or the reviewer's turns run out | you |
| 3 | `arc submit` — push, open the PR, hand it to the review service | you |
| 4 | The reviewers file findings; the letter arrives in your session (section 4) | the review service |
| 5 | Fix, push, then `arc submit --pr <N> --fix-answers -` | you |
| 6 | Every reviewer the routes asked says LGTM, the service grants the pass | the review service |
| 7 | The merge machine runs the repo's `merge.yml` and lands the PR, or bounces it with the failing output | the merge machine |
| 8 | A landing letter arrives: how the PR ended and which worktree on this machine still holds the branch | you decide about the worktree |

A person steps in when: a run exits 9 (a finding escalated to a person), you ask a question (section 4), or someone labels the PR `arc-hold` (the merge machine then does not take it; the review still runs and a pass is still granted). A reviewer has `[review] max_rounds` turns (default 5) of replies without an LGTM; when it has used them, it lets that head through.

## 2. The commands you run

Add the global `--json` to any of them: stdout then carries exactly one JSON line and no human text; diagnostics (`-v`) go to stderr. Decide success by the **exit code** (section 3), then read the line. On a failure stdout is usually empty and stderr has one line `[A.R.C.] <verb>: <the real error>`; quote that line, do not paraphrase it.

| Command | When | Notes |
|---|---|---|
| `arc local-review` | before you submit | `--since <rev>` reviews only what changed since that commit. Never edits code. |
| `arc local-review --show` | to read where each finding stands | no model call, no write |
| `arc fix` / `arc fix <F-id>` / `arc fix <path>` | to let the Fixer answer the findings | needs a clean tree and a local PR; each fix is a commit; undo with `git reset --hard refs/arc/before-fix/<branch>`. `--dry-run` only assesses. |
| `arc presubmit --base <sha> --target origin/main` | to run `presubmit.toml`'s checks without pushing | exits 11 when a check did not pass |
| `arc submit --target origin/main --base <sha>` | to open the PR and hand it to review | runs presubmit first; `--branch <name>` refuses if HEAD moved; `--after <N>` lands only after PR N |
| `arc submit --pr <N>` | to hand a new head of PR N to review | refused without `--pr` when the branch already has an open PR |
| `arc submit --pr <N> --fix-answers -` | to answer PR N's findings | reads a JSON array on stdin (below); push the fix first |
| `arc submit --abandon "<why>"` | to end a PR without landing it | the only way to close a PR; your reason is kept verbatim |
| `arc issues ...` | to read or write the issue board | every write states `--role` (reporter, assignee, verifier, human); judging verbs need `--said` |
| `arc bridge inbox` / `send` / `post` / `ask` | to talk to sessions and people | section 4 |

Fill `--base` with the merge base after a fetch: `git fetch origin && arc submit --target origin/main --base "$(git merge-base HEAD origin/main)"`.

Answers for `--fix-answers`, one item per finding, `finding` being its number as the review gave it:

```json
[{"finding": 3, "kind": "fixed", "text": "carried the error typed"},
 {"finding": 5, "kind": "wontfix", "text": "the empty string is the wire format the client expects"}]
```

One bad item refuses them all and nothing is sent.

### The `--json` lines

Every envelope starts with `command`. The shapes below are read from the code; values are illustrative.

`arc local-review --json` — `reviewed: false` with nothing beside it means the change changes nothing:

```json
{"command": "local-review", "reviewed": true, "pr": "7", "head": "<40-hex>", "closed": false,
 "open": [{"id": "F-12", "rule": "<rule id>", "message": "<reviewer's words>", "path": "src/a.rs", "line": 42}]}
```

`closed: true` means the review ended on this head (an LGTM, or the turns ran out). `open` empty and `closed: true`: ready to submit.

`arc local-review --show --json` — `pr` is `null` when the branch has no local PR:

```json
{"command": "local-review --show", "pr": {"id": "7", "head": "<40-hex>", "closed": false, "findings": [
  {"id": "F-12", "status": "open", "rule": "<rule id>", "message": "...", "path": "src/a.rs", "line": 42,
   "severity": "...", "confidence": "...", "snippet": "...", "events": [{"kind": "...", "by": "<name>", "words": "...", "at": 0, "sha": "<40-hex>"}]}]}}
```

`status` is one of `open`, `fixed`, `wontfix`, `escalated`, `resolved`, `dismissed`.

`arc fix --json`:

```json
{"command": "fix", "run_id": "<request id>", "metrics": {"open": 1, "closed": 4, "total": 5},
 "open_issues": [{"id": "F-12", "file": "src/a.rs", "severity": "..."}],
 "transitions": [{"id": "F-9", "file": "src/b.rs", "previous_state": "open", "new_state": "fixed"}],
 "fix_rounds": [{"handed": ["F-9", "F-12"], "answered": ["F-9"], "inferred": [], "unanswered": ["F-12"]}],
 "action_required": true, "success": true}
```

`success: false` comes with `error` (the real error text) and nothing else beside `command`, `run_id` and `action_required: false`: the record was not read, so do not read it as "nothing to fix".

`arc submit --json` — `outcome` says which of three:

```json
{"command": "submit", "outcome": "submitted", "branch": "<branch>", "sha": "<40-hex>", "pr": 514, "pr_url": "https://...",
 "size": {"base": "origin/main", "files": 3, "added": 40, "removed": 12, "net": 28},
 "review": "by_routes", "answered": [3, 5],
 "cl_list": {"named": [], "listed": [], "unlisted": []},
 "presubmit": {"outcome": "ran", "passed": true, "affected": {"source": "computed", "packages": ["<pkg>"]}, "checks": []},
 "presubmit_note": {"kind": "pushed"}}
{"command": "submit", "outcome": "already_in", "sha": "<40-hex>"}
{"command": "submit", "outcome": "abandoned", "pr": 514, "sha": "<40-hex>", "abandoned": "<why>", "request": "<request id>"}
```

`size` is `null` with `size_unknown` (the error) beside it when the change could not be measured. `review` is `bypassed` only when `--bypass-review` was given. `cl_list` is `null` when the PR has no page; `cl_list.unlisted` holds each board issue the title names that did not get this submission, with its error. `presubmit` is `{"outcome": "no_presubmit"}` when the repo has no `presubmit.toml`. `presubmit_note` is `{"kind": "not_pushed", "error": "..."}` when the checks' record did not reach origin.

`arc presubmit --json` is the `presubmit` object above with `command` and the head's `sha`. Each check is `{"name", "command", "result", ...}` where `result` is:

| `result` | Fields beside it |
|---|---|
| `passed` | `duration_ms` |
| `passed_before` | none: it passed on this commit before and was skipped |
| `failed` | `exit_code`, `signal`, `duration_ms`, `failures` (`[{"unit", "excerpt"}]` or `null`), `output` |
| `timed_out` | `timeout_seconds`, `failures`, `output` |
| `not_started` | `why` |

Other commands with `--json` print their own one-line report; read their fields, and still decide by the exit code.

## 3. Exit codes

| Code | Meaning | What you do | Source |
|---|---|---|---|
| 0 | done; also a run that found rot, or that left findings open | read the output; open findings are your next step | `crates/review/cli/src/error.rs:149` |
| 1 | internal failure, likely a bug; also a run refused before it started (not a git repo, an `ARC_*` variable set, a judge call failed in `arc rot`) | stop; report the stderr line verbatim | `crates/review/cli/src/error.rs:151` |
| 2 | configuration or setup error, a refused submit, or a command line that did not parse | fix the setup or the arguments; do not retry as is | `crates/review/cli/src/error.rs:153`, `crates/apps/cli/src/main.rs:70` |
| 3 | git or repository state | fix the tree (conflict, missing merge base, diverged branch), then rerun | `crates/review/cli/src/error.rs:155` |
| 4 | provider or review-engine error that is not transient (also a GitHub refusal) | report the error; a person fixes the provider | `crates/review/cli/src/error.rs:157` |
| 5 | filesystem or storage error | report the error | `crates/review/cli/src/error.rs:159` |
| 6 | transient: rate limit, timeout, outage | retry later | `crates/review/cli/src/error.rs:161` |
| 7 | a check answered "no": `arc archcheck` found a broken rule | read the report and fix what it names | `crates/review/cli/src/error.rs:164` |
| 8 | your write took, a record owed elsewhere did not: `arc submit` could not list the PR on a board issue its title names; `arc issues` could not mirror a write to GitHub | do **not** rerun the same command (it would write twice); follow the stderr line (for issues: `arc issues mirror`) | `crates/review/cli/src/error.rs:167` |
| 9 | the reviewer escalated a finding to a person | stop and hand over; tell the person what is escalated | `crates/review/cli/src/error.rs:170` |
| 10 | the reviewer's call failed; no round was written | read the error; rerunning calls the reviewer again | `crates/review/cli/src/error.rs:173` |
| 11 | a presubmit check did not pass, timed out or did not start. `arc submit` still pushed and handed the PR to review | fix the check's failure, push, `arc submit --pr <N>` | `crates/review/cli/src/error.rs:178` |
| 130 | arc was stopped by SIGINT or SIGTERM; its child processes were killed | rerun if the stop was not meant | `crates/apps/cli/src/main.rs:49` |

## 4. Messages: how they reach you, how you ask a person

You are on the chat server (arc-bridge) under your session's name (`claude -n NAME`; an unnamed session goes by its session id). The hook lines that put you there are in [Connecting your coding agent](coding-agents.md#2-the-agent-as-a-participant-bridge); `arc bridge install-hooks --agent <claude|codex|agy>` writes them and `arc bridge doctor` says why they would not run.

**Mail arrives when your session stops.** The Stop hook asks the server once:

| In your inbox | What happens |
|---|---|
| a message that should interrupt | the stop is held, and the unread mail becomes your next input |
| only quiet messages | you stop; they stay in the inbox |
| nothing | you stop |

Review letters for a PR you submitted, bounces from the merge machine (with the failing tests' output) and landing letters all come this way. Act on them: a review letter carries the findings and the `arc submit --pr <N> --fix-answers -` command to fill in.

| Command | What it does |
|---|---|
| `arc bridge inbox` | print unread mail without marking it read; `--wait <seconds>` waits for some |
| `arc bridge send <name> "<text>"` | a direct message to one session |
| `arc bridge post <channel> "<text>"` | a message into a public channel, such as the PR's `pr:<owner>/<repo>#<n>` |
| `arc bridge ask "<question>" --on b/<n> --option "A: ..." --option "B: ..."` | ask a person; at least two options |
| `arc issues block b/<n> --role assignee --said "<question>" --option "..."` | mark an issue blocked on a person's ruling |

**Asking a person.** `arc bridge ask` opens the question as a `q/<n>` on that board issue and posts it into your own room. A person answers it with one click on the board's Projects page; the answer comes back into your room, and so into your session, as `【name】option`. Ask in the checkout whose board holds the issue. Ask when the decision is a person's (scope, a design fork, loosening a rule, deleting something that may be used); decide yourself what the code, the docs or `--help` already settle. A question carries its background, the options with their pros and cons, and your recommendation.

A message that is not delivered exits non-zero with the server's own words; report those words.

## 5. Rules

| Never | Do instead |
|---|---|
| `arc submit --bypass-review` on your own | submit normally; only a person decides to bypass review |
| close a PR by hand (`gh pr close`, the GitHub button) | `arc submit --abandon "<why>"` |
| merge a PR, or push to the target branch | the merge machine lands it after the pass |
| force-push, or push over commits the remote has | `arc submit` pushes the branch under its own name and refuses a diverged branch; rebase or merge, then submit |
| write issues with `gh issue` or `gh api .../issues` | `arc issues` (GitHub is only its mirror) |
| invent a default for a missing config value, or edit config to make an error go away | report what is missing; a person decides the value |
| remove or add the `arc-hold` label unless a person asked | leave it; it is a person's hold |
| rerun after exit 8 | follow the stderr line; the write already took |
| summarize a failure ("it failed", "parse error") | quote the real error text, exit code and command |
| `git reset` away a fix run you do not understand | read `arc local-review --show` first; undo only on purpose, with `refs/arc/before-fix/<branch>` |

On any failure, report: the command you ran, the exit code, and the stderr line or the `error` field as printed. A short excerpt of real output beats a description of it.

## 6. Config: where it lives, what you may touch

| File | Holds | You may edit it? |
|---|---|---|
| `~/.tars/config.toml` | LLM providers, models, credentials | **no**, never without a person asking; never commit it |
| `<repo>/.arc/config.toml` | this clone's routing: `[roles]`, `[review]`, `[test]`, `[release]`; no providers | only when a person asks; not committed |
| `<repo>/presubmit.toml` | the checks `arc submit` runs before it pushes | yes, as a code change that goes through review |
| `<repo>/.github/workflows/merge.yml` | the merge gate the merge machine runs | only when the task is the gate itself; it goes through review like code |
| `<repo>/.arc/delivery.toml`, `.arc/archcheck.toml`, `.arc/arch_waivers.txt` | how the project ships; its architecture rules and waivers | only as a reviewed change; loosening a rule or adding a waiver is a person's decision |
| `~/.arc/client.toml`, `~/.arc/machine.toml` | the pipeline's address; the pipeline machine's tenants | no |

arc takes its runtime inputs as flags, not environment variables: an `ARC_*` variable it does not know stops it (exit 1). To use another provider file, pass `--tars-config <file>` to every call. [Configuration](configuration.md) explains each file.

---

*See also: [The commands](commands.md) · [Review on the pipeline](pipeline-review.md) · [Team up](bridge.md) · [Merge](merge-gate.md) · [Connecting your coding agent](coding-agents.md).*
