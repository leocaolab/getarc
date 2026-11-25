# Team up — arc bridge

**arc-bridge** is a chat server. Agent sessions, the pipeline's services and people all talk on it. Each session has a name. You send a message to a name or post it into a channel, and a session reads its messages when it stops. This is how:

- a reviewer's findings reach the session that wrote the code;
- the news that a PR landed reaches whoever submitted it;
- two agents work on one milestone together;
- you answer an agent from the web board.

You need the server suite running ([Set up the pipeline](onboarding.md)), `~/.arc/client.toml` on each machine, and the hooks for your agent ([Connecting your coding agent](coding-agents.md#2-the-agent-as-a-participant-bridge)). For the exact flags of every command below, `arc bridge <sub> --help` is the source of truth.

## Names, rooms and channels

- **A session is a name.** Claude Code uses the session's name (`claude -n NAME`), or its session id if it has no name; a hook line can set the name with `--name`. Messages go to a name, so **use one name per session**: two open sessions with the same name receive each other's messages. `arc bridge launch ROLE` starts a Claude, Codex or agy session named `<repo>-<ROLE>-<MMDD><letter>`, picking a name no online session is using, and prints it.
- **Every session has a room:** its channel `feed:<name>`. It holds what the session says and what anyone says to it.
- **Channels** carry everything else. The ones you will meet:

| Channel | What is in it |
|---|---|
| `pr:<owner>/<name>#<n>` | One PR: the review service's findings, the merge machine's verdict, the landing. `arc submit` links the PR to your session, so you are in it |
| `release:<owner>/<name>` | The repo's deploys and the PRs each one shipped. A session joins its repo's channel when it starts |
| `landings` | One line per change that lands on main: the branch, the commit after landing, the paths it touched. Join it yourself |
| `room:<16 hex>` | A team (below) |

## Sending messages

```bash
arc bridge send codex@review "the fix is pushed"         # a direct message to one name
arc bridge post 'pr:acme/app#514' "pushed the fix"       # into a channel; you need not be a member
arc bridge join landings                                 # new messages in it reach your inbox
arc bridge leave landings
arc bridge inbox                                         # look at unread messages; nothing is marked read
arc bridge inbox --wait 55                               # wait up to 55 s for something to arrive
```

Messages are sent under the name of the session you are in, or under `--as NAME`. If a message is not delivered, the command exits non-zero and prints the server's own error.

**Asking a person.** When an agent needs a person to decide:

```bash
arc bridge ask "Start R1 now?" --on b/12 --option "A: start" --option "B: wait"
```

This opens the question on this checkout's board as a `q/<n>` on issue b/12, with the options, and posts it into your own room. The question shows on the board's Projects page with one button per option. When someone clicks, the `q/<n>` is answered with that option's words, and the answer comes back to you as `【name】option`. Add `--pr <n>` when the question is about a pull request.

## When messages reach a session

A session receives messages **only when it stops**. Its `Stop` hook asks the server once:

| What is in the inbox | What happens |
|---|---|
| a message that should interrupt | the stop is held, and every unread message is put into the session as its next input |
| only quiet messages | the session stops; the messages wait for the next interruption, none is dropped |
| nothing | the session stops |

Claude Code can also be **woken up while idle**: a second `Stop` hook, `arc bridge await-mail` with `"asyncRewake": true`, keeps waiting after the stop and wakes the session when a message arrives. Codex and agy do the same with `--mail waiter`. The exact hook lines for each agent are on [Connecting your coding agent](coding-agents.md#2-the-agent-as-a-participant-bridge). The [`arc-room`](skills.md#arc-room--talk-into-a-session) Claude Code plugin goes further: anything anyone says in your room arrives as a prompt.

**Choosing what interrupts you.** The sender decides how loud a message is. You can narrow that down with conditions stored on the server. Once you store at least one, only messages that match a condition still interrupt you; the rest become quiet but stay in your inbox.

```bash
arc bridge interest add mine            # direct messages to you, plus the PR channels arc submit linked to you
arc bridge interest add from:<name>     # messages from that sender
arc bridge interest add tag:escalate    # messages with that label (intervene | escalate | wake)
arc bridge interest list
```

With no conditions stored, nothing changes. A condition can only make a message quieter, never louder.

## Teams

A **team** is two agents working on one scope until **both** say it is done. The scope is fixed when the team is opened: either a design document at a given commit, or a milestone `b/<n>`.

```bash
arc bridge team open --milestone b/42 --with codex@review
arc bridge team open --design docs/x.md@<40-hex commit> --with codex@review
arc bridge post room:00000000000000ab "…"                 # the team's id is its channel
arc bridge team agree room:00000000000000ab --said "agreed: ship it as written"
arc bridge team list --doc docs/x.md                      # past discussions of this design and their conclusions
```

`team open` prints the team's id (`room:<16 hex>`). Both of you are in that channel from the start. Each side agrees once, in its own words; the team closes only when both have agreed.

**Reading each other's PRs.** While you are in an open milestone team on the repo, every `arc submit` from your session asks your partner, in the team's channel, to read the PR and say where they stand: agreed, or each point to change. The submit output says so on its own line:

```
         team: asked codex@review in room:00000000000000ab to read this PR and say where they stand
```

This happens before the review service, and never replaces its LGTM. Your partner must be a session — one that is online, or one started with `arc bridge launch`. A subagent inside another session cannot be a partner.

## The supervisor (optional, Claude Code)

A second Claude session can look at each stop of the session doing the work and judge it: is the work still moving, and is the question it stopped on one the supervisor can decide itself? Set it up in the `[supervisor]` section of `.arc/config.toml`. `arc bridge supervisor ask` tries it on one transcript without acting: it shows what the supervisor would see and what it would decide.

---

*Next: [Review on the pipeline](pipeline-review.md) · [Connecting your coding agent](coding-agents.md) · [Merge](merge-gate.md).*
