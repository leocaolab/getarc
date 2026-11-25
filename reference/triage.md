# Triage heuristic — CORE vs. noise (shared)

A code review can return dozens of findings, and most raw LLM output consists of low-priority smells, duplicates, or non-actionable items. Never dump the raw list — triage it first.

## Read the findings

Where full finding details live depends on the review mode:

- **Local review** (`arc local-review`): There is no web review page. The command prints one line per open finding (`<id>  <path>:<line>  [<rule>] <message>`), and `--json` returns an `open` array where each item has `id`, `rule`, `message`, `path`, and `line`. The full record (including any reviewer–fixer debate) is stored in `.arc/review.db` (tables `findings` and `finding_events`); inspect it read-only with `sqlite3 -readonly`.
- **Team PR review** (`arc submit`): The PR's review page holds each finding's rule, reasoning, and debate.

`arc fix --json` ends with the PR envelope: `metrics` (`open`, `closed`, `total`), `open_issues` (`id`, `file`, `severity`), and `action_required`. Always reference findings by their numeric `id`; never invent IDs.

## Bucket each finding

**CORE** (show these first, ranked by severity) — must meet all of:
- Grounded in a named rule (not an ungrounded `free_review::*` note)
- Severity is `critical`, `error`, or `warning` (omit `info` unless requested)
- Not a duplicate of another finding (same file, same rule, adjacent lines)

**NOISE** (collapse into `+N low-signal`) — any of:
- Ungrounded `free_review::*` notes
- Duplicates
- `info` findings with no correctness or security impact
- Findings whose own message admits they aren't actionable (e.g., build scripts, test helpers, or documented intentional patterns)

## Present the summary

```
N core findings (M folded as low-signal — say "show all" to expand):

  ① <severity> <file>  ·  #<id>
     <one-line summary>  ·  fix: arc fix <id>
```

If every finding is noise, say: `"Nothing clearly actionable — N low-signal findings if you want to see them."`
