# Your data — what the pipeline collects, and where it lives

The pipeline collects two kinds of data for your team: **test data** and **your agents' conversations**. All of it is stored on the machines that run your server suite. arc sends it to your own server and nowhere else. We do not receive it, read it or use it.

What `arc local-review` and `arc fix` write on your own machine stays in your repo's `.arc/` directory and goes nowhere.

## Test data (TAP)

| What | Who sends it | When |
|---|---|---|
| Each commit's diff (the changed regions) | `arc tap record`, run by the post-commit hook | every commit, in clones where `arc hook install` ran |
| The JUnit XML your test runner writes | the merge gate, through `ARC_GATE_OUT` ([Merge](merge-gate.md)) | every gate run that has test history enabled |
| Build timings and failed-build logs | `arc tap build` / `arc tap build-log` | only when you or your agent run them |

arc never runs your tests. It records what your runner already wrote.

Where it lands, per repo (tenant), under the tenant's `home` clone named in `~/.arc/machine.toml`:

- `<home>/.git/arc/tap.db` — the test-history store;
- `<home>/.git/arc/logs/<table>/date=YYYY-MM-DD/` — the raw test rows, as Parquet files by day.

What it is used for: slow and flaky tests (`arc tap signal`), which tests a change can reach (`arc affected`), coverage as mutant survival (`arc tap coverage`, `arc tap gaps`), and writes the store lost (`arc tap absence`).

## Conversation data (arc bridge)

| What | Who sends it | When |
|---|---|---|
| Claude Code transcripts (sub-agents too), their meta files, the tool outputs they name, `~/.claude/history.jsonl` | `arc intent collect`, which every hook starts in the background | after each hook, sending only what the server does not have yet |
| Which repo each directory a session ran in belongs to | the same `arc intent collect` | same |
| Messages sent with `arc bridge send` / `post` | the sender | when sent |

Codex CLI transcripts are not uploaded yet.

On each machine with the hooks installed:

- `~/.arc/bridge-archive/` keeps a copy of transcript bytes, because Claude Code deletes transcripts after about 30 days;
- `~/.arc/logs/bridge-collect.log` lists what each run sent, and what it could not send and why.

On the server, next to the `machine.toml` that `arc-bridge` reads (by default `~/.arc/`):

- `bridge.db` — sessions, messages, rooms and the index;
- `raw/` — every received record exactly as it came, as Parquet; the index can be rebuilt from it;
- `intentdb/` and `log/` — what is derived from the transcripts;
- `bridge-archive/` — the transcripts' side files.

What it is used for: each room's feed, searching past conversations (`arc intent history`), the supervisor session, and landing letters.

---

*See also: [Set up the pipeline](onboarding.md) · [Team up — arc bridge](bridge.md) · [Merge](merge-gate.md).*
