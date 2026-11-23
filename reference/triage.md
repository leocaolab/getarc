# Triage heuristic — CORE vs noise (shared)

A review can return dozens of findings, and most of any model's raw output is soft
smells, duplicates, or non-actionable. Never dump the raw list. Triage first.

## Read the findings

Where a finding's full text lives depends on whose PR it is on:

- **A local PR** (`arc local-review`): it has no review page. The run prints each open
  finding as one line — `<id>  <path>:<line>  [<rule>] <message>` — and `--json` prints one
  object whose `open` lists them, each with `id`, `rule`, `message`, `path`, `line`. The whole
  record, the debate included, is in the clone's `.arc/review.db` (tables `findings` and
  `finding_events`); open it read-only (`sqlite3 -readonly`).
- **A PR in review** (`arc submit`): its review page holds each finding's rule, reasoning
  and debate.

`arc fix --json` ends with the envelope of the PR the branch is: `metrics` (`open`,
`closed`, `total`), `open_issues` (each `id`, `file`, `severity`), and `action_required`.
Use the finding's number (`id`) as the handle; never invent one.

## Bucket each finding

**CORE** (show these, ranked by severity) — all of:
- grounded in a named rule (not an ungrounded `free_review::*`);
- severity `critical` / `error` / `warning` (drop `info` unless asked);
- not a duplicate of another finding (same file, same rule, adjacent line).

**NOISE** (fold into one line "+N low-signal") — any of: ungrounded, a duplicate,
`info` with no correctness or security angle, or the message itself says it is not
actionable (a build script, a test helper, an intentional pattern).

## Present

```
N core findings (M folded as low-signal — say "show all" to expand):

  ① <severity> <file>  ·  #<id>
     <one-line why>  ·  fix: arc fix <id>
```

If everything is noise, say "nothing clearly actionable — N low-signal findings if you
want them."
