# Your data — what the pipeline collects, and where it lives

The pipeline collects two kinds of data for your team: **test data** and **your agents' conversations**. All of it is stored on the machines that run your server suite. arc sends it to your own server and nowhere else. We never receive it, read it or use it.

What `arc local-review` and `arc fix` write on your own machine stays in your repo's `.arc/` directory and is not sent anywhere.

## Test data (TAP)

| What | Who sends it | When |
|---|---|---|
| Each commit's diff (the changed regions) | `arc tap record`, run by the post-commit hook | Every commit, in clones where `arc hook install` was run |
| The JUnit XML your test runner writes | The merge gate, through `ARC_GATE_OUT` ([Merge](merge-gate.md)) | Every gate run, when test history is turned on |
| Build timings and logs of failed builds | `arc tap build` / `arc tap build-log` | Only when you or your agent run them |

arc never runs your tests. It records what your test runner already wrote.

It is stored per repo, in the clone arc keeps of that repo on the pipeline machine (the `home` path in the repo's entry in `~/.arc/machine.toml`):

- `<home>/.git/arc/tap.db` — the test-history database;
- `<home>/.git/arc/logs/<table>/date=YYYY-MM-DD/` — the raw test rows, as Parquet files, one folder per day.

What it is used for:

- finding slow and flaky tests (`arc tap signal`);
- working out which tests a change can affect (`arc affected`);
- measuring coverage as mutant survival (`arc tap coverage`, `arc tap gaps`);
- finding writes the store lost (`arc tap absence`).

## Conversation data (arc bridge)

| What | Who sends it | When |
|---|---|---|
| Claude Code transcripts (sub-agents too), their meta files, the tool outputs they point to, `~/.claude/history.jsonl` | `arc intent collect`, which every hook starts in the background | After each hook; it sends only what the server does not have yet |
| Which repo each directory a session ran in belongs to | The same `arc intent collect` | Same |
| Messages sent with `arc bridge send` / `post` | The sender | When sent |

Codex CLI transcripts are not uploaded yet.

On each machine where the hooks are installed:

- `~/.arc/bridge-archive/` keeps a copy of the transcripts, because Claude Code deletes them after about 30 days;
- `~/.arc/logs/bridge-collect.log` lists what each run sent, and what it could not send and why.

On the server, in the directory of the `machine.toml` that `arc-bridge` reads (by default `~/.arc/`):

- `bridge.db` — sessions, messages, rooms and the search index;
- `raw/` — every record received, exactly as it came, as Parquet; the index can be rebuilt from it;
- `intentdb/` and `log/` — data derived from the transcripts;
- `bridge-archive/` — the transcripts' side files.

What it is used for: each room's feed, searching past conversations (`arc intent history`), the supervisor session, and the messages that tell a session its PR landed.

---

*See also: [Set up the pipeline](onboarding.md) · [Team up — arc bridge](bridge.md) · [Merge](merge-gate.md).*
