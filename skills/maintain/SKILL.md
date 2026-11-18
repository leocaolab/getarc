---
name: maintain
description: >-
  Diagnose and maintain A.R.C. (arc) in a repo that already has it — a command that
  fails, a review that is refused, stale local state after a refactor, or a provider
  role to swap. Use when arc behaves unexpectedly or the user asks to reset / clean up
  / re-configure arc.
allowed-tools: "Bash Read Edit"
---

# arc maintenance

## Something fails — diagnose, don't guess
1. Re-probe the install: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/arc-setup/scripts/probe.py`
   (add `--tars-home DIR` if the person's tars home is not `~/.tars`). A stage that is
   not `done` → **`arc-skills:arc-setup`** resumes from it.
2. Run the failing command through
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/arc-setup/scripts/diagnose.py -- <command>`
   (or `--from -` with output you already have, for anything outward). A match gives
   the cause, the fix and where arc says it; no match → report the raw output as is.
3. Add `-v` / `-vv` to the arc command for its diagnostic log on stderr.

The usual causes, in arc's own words:
- "cannot tell who is submitting — not in an agent session and no `gh` login" — run it from the coding agent, or log in to `gh`;
- "this checkout's branch holds no open local PR — run `arc local-review` first" — the branch has no local PR;
- "missing credential: env var X is not set" — the provider's key is not in this shell;
- "No provider for role …" — `[roles]` lacks that role and `default`.

`known_issues.json` in the install skill has the rest, each with its source.

## Reset local state (after a big refactor — destructive, confirm first)
```bash
arc reset          # lists what would be removed
arc reset --yes    # wipes this repo's local arc state; keeps .arc/config.toml and .arc/delivery.toml
```
Show the person the listing before `--yes`.

## Swap provider roles
Edit `[roles]` in `.arc/config.toml` (`critic_l4` / `critic_l5` / `critic` / `default` /
`fixer`, each a tars provider id), or `arc init --force` in a terminal. Keep the fixer a
different model family from the critic, and explicit. Then re-probe the `roles` stage.

## Watch a run
Personal edition: `arc local-review --show` reads back the branch's local PR and where each
finding stands. Team edition, with an operator's server:
```bash
curl <web>/api/r/<owner>/<name>/progress/<b/N|PR|branch>   # how far a PR has got (`web`: ~/.arc/client.toml)
```
Findings and rounds are on the PR's review page.
