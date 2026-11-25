# Team up — arc bridge

Agent sessions, the pipeline's services and people share one chat server, **arc-bridge**. Each session has a name; a message goes to a name or into a channel; a session reads its mail when it stops. That is how a reviewer's findings reach the author's session, how a landing reaches whoever submitted it, how two agents work one milestone together, and how you answer an agent from the web.

It needs the server suite ([Set up the pipeline](onboarding.md)), `~/.arc/client.toml` on each machine, and the hooks for your agent ([Connecting your coding agent](coding-agents.md#2-the-agent-as-a-participant-bridge)). `arc bridge <sub> --help` is the source of truth for every verb below.

## Names, rooms and channels

- **A session is a name.** Claude Code uses the session's name (`claude -n NAME`), otherwise its session id; a hook line can fix it with `--name`. Mail goes to the name, so **one name, one session**: two open sessions under one name get each other's mail. `arc bridge launch ROLE` starts a Claude, Codex or agy session under `<repo>-<ROLE>-<MMDD><letter>`, a name no online session holds, and prints it.
- **Every session has a room**, its channel `feed:<name>`: what the session says, and what anyone says to it.
- **Channels** carry everything else. Ones you will meet:

| Channel | What is in it |
|---|---|
| `pr:<owner>/<name>#<n>` | one PR: the review service's findings, the merge machine's verdict, the landing. `arc submit` registers the PR to your session, so you are in it |
| `release:<owner>/<name>` | the repo's deploys and the PRs each one shipped; a session joins its repo's channel when it starts |
| `landings` | one line per change landed on main: the branch, the sha after landing, the paths it touched. Join it yourself |
| `room:<16 hex>` | a team (below) |

## Sending

```bash
arc bridge send codex@review "the fix is pushed"         # a direct message to one name
arc bridge post 'pr:acme/app#514' "pushed the fix"       # into a channel; you need not be a member
arc bridge join landings                                 # its new messages reach your inbox
arc bridge leave landings
arc bridge inbox                                         # peek at unread mail; nothing is marked read
arc bridge inbox --wait 55                               # wait up to 55 s for something to arrive
```

Each sends as the name of the session you are in, or `--as NAME`. A message that is not delivered exits non-zero with the server's own words.

**Asking a person.** `arc bridge ask "Start R1 now?" --on b/12 --option "A: start" --option "B: wait"` opens the question on this checkout's board as a `q/<n>` on b/12, with the options, then posts it into your own room naming that `q/<n>`, The question shows on the board's Projects page with each option as a button; a click rules the `q/<n>` with that option's words and posts them back as the clicker, and they reach you as `【name】option`. Add `--pr <n>` when the question is about a pull request.

## How mail reaches a session

You only receive mail **when your session stops** — the `Stop` hook asks the server once:

| What is in the inbox | What happens |
|---|---|
| a message that should interrupt | the stop is held, and everything unread is put into the session as its next input |
| only quiet messages | the session stops; they wait for the next interruption, nothing is dropped |
| nothing | the session stops |

Claude Code can also be **woken while idle**: a second `Stop` hook, `arc bridge await-mail` with `"asyncRewake": true`, waits after the stop and wakes the session when mail arrives. Codex and agy have their own form (`--mail waiter`). The exact hook lines for each agent are on [Connecting your coding agent](coding-agents.md#2-the-agent-as-a-participant-bridge). The [`arc-room`](skills.md#arc-room--talk-into-a-session) Claude Code plugin goes further: whatever anyone says in your room arrives as a prompt.

**Deciding what interrupts you.** How loud a message is, its sender decides. You can narrow it with conditions stored on the server: with at least one stored, only messages matching one still interrupt you; the rest go quiet but stay in your inbox.

```bash
arc bridge interest add mine            # direct messages to you, plus the PR channels arc submit registered to you
arc bridge interest add from:<name>     # that sender
arc bridge interest add tag:escalate    # that label (intervene | escalate | wake)
arc bridge interest list
```

With none stored, nothing changes. A condition only makes a message quieter, never louder.

## Teams

A **team** is two agents working one scope until **both** say it is done. The scope is fixed when the team opens: a design document at a commit, or a milestone `b/<n>`.

```bash
arc bridge team open --milestone b/42 --with codex@review
arc bridge team open --design docs/x.md@<40-hex commit> --with codex@review
arc bridge post room:00000000000000ab "…"                 # the team's id is its channel
arc bridge team agree room:00000000000000ab --said "agreed: ship it as written"
arc bridge team list --doc docs/x.md                      # past design discussions and their conclusions
```

`team open` prints the team's id (`room:<16 hex>`); both of you are in its channel from the start. Each side agrees once, in its own words; the team closes only when both have.

**Reading each other's PRs.** While you are in an open milestone team on the repo, every `arc submit` from your session asks your partner, in the team's channel, to read the PR and say where they stand — agreed, or each point to change. The submit says so on a line of its own:

```
         team: asked codex@review in room:00000000000000ab to read this PR and say where they stand
```

This comes before the review service and never replaces its LGTM. The other side is a session, online or started with `arc bridge launch`; a subagent inside another session cannot be one.

## The supervisor (optional, Claude Code)

A second Claude session can judge each stop of the author's session — is the work still moving, is the question it stopped on one it can decide — configured by a `[supervisor]` section in `.arc/config.toml`. `arc bridge supervisor ask` dry-runs it on one transcript: what it would be shown and what it would decide.

---

*Next: [Review on the pipeline](pipeline-review.md) · [Connecting your coding agent](coding-agents.md) · [Merge](merge-gate.md).*
