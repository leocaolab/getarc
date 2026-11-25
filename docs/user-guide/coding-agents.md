# Connecting your coding agent

arc works with three coding agents: **Claude Code**, **Codex CLI** and **agy**
(the Antigravity CLI). You can connect one in two ways. Use one, or both.

| | What it does | Where you set it up |
|---|---|---|
| **1. As a role** | arc runs the agent itself, as the Fixer that edits code for `arc fix` (or as a critic) | `[roles]` in `<repo>/.arc/config.toml`, provider in `~/.tars/config.toml` |
| **2. As a participant** | your own agent session joins arc's chat server: review results, PR outcomes and messages are put into your session when it stops | hooks in the agent's own settings file, pointing at `arc bridge hook` |

The first way needs arc and tars on your machine; `arc fix` then answers the branch's local PR,
which `arc local-review` opens. The second also needs an arc-bridge server, which your operator
runs (see [Onboarding](onboarding.md)).

## 1. The agent as a role (Fixer or critic)

### Set it up

Define the provider in tars, then name it in `[roles]`. arc never reads a model or a key
from `.arc/config.toml`; a `[providers]` section there is refused. Details:
[Configuration](configuration.md).

```toml ignore: ~/.tars/config.toml, tars's file, not arc's
# ~/.tars/config.toml
[providers.claude_fixer]
type = "claude_cli"
default_model = "<a Claude model id>"
tools = "default"        # REQUIRED for a Fixer: let Claude Code use its own Read/Edit/Bash
timeout_secs = 900
```

```toml config.toml
# <repo>/.arc/config.toml
[roles]
critic = "gemini_flash"    # any provider id from ~/.tars/config.toml
fixer  = "claude_fixer"
```

What to know:

- **`fixer` must be set explicitly.** It never falls back to `default`. arc wants the
  Fixer to be a different model family from the critic, so the review stays independent.
- **An agent CLI runs its own loop.** When the Fixer's provider type is an agent CLI,
  arc hands it no tools of its own. The agent edits your working tree with its own tools,
  and arc reads the diff.
- **`claude_cli` defaults to `tools = "disabled"`.** That is right for a critic (it only
  needs to answer) and wrong for a Fixer: with tools disabled it cannot edit anything,
  so `arc fix` refuses it before calling it. Set `tools = "default"` on the provider your
  `fixer` names. The same goes for Codex's default `sandbox = "read-only"`.
- `claude_cli` signs in with your `claude login` session. No API key is needed.

The three agents as tars provider types:

| Agent | tars `type` | What tars runs | Settings you will likely need |
|---|---|---|---|
| Claude Code | `claude_cli` | `claude -p …` | `tools = "default"` for a Fixer; optional `effort`, `timeout_secs` (default 300) |
| Codex CLI | `codex_cli` | `codex exec --json --model <model> --sandbox <sandbox> -c approval_policy="never" --skip-git-repo-check -`, in your working tree | `sandbox = "workspace-write"` for a Fixer: the default `"read-only"` is passed to Codex as `--sandbox read-only`, Codex's read-only sandbox. `timeout_secs` defaults to 600 |
| agy | `antigravity` | `agy -p "<prompt>" --model <model> --dangerously-skip-permissions --add-dir <cwd>` | `effort` is `"low"` or `"high"` (default `"high"`) |

All three take `default_model` and an optional `executable` (default `claude`, `codex`,
`agy`). The committed example (`.arc/config.toml.example`) uses `claude_cli` as the Fixer.
`codex_cli` and `antigravity` are accepted by tars and treated by arc as agent CLIs. What
arc hands Codex under each `sandbox` value has been checked; a Fixer run against a live Codex
has not yet been made, and arc's own test suite runs neither one as a Fixer end to end.

### Check that it works

The Fixer answers the branch's local PR, so run `arc local-review` on the branch first. Then:

```bash
arc fix --dry-run
```

`--dry-run` runs the Fixer read-only: it assesses each finding the local PR owes and reports
`[AGREE]` / `[DISAGREE]` with a plan. Nothing is edited, committed or sent.

### When it fails

- `fixer pipeline: failed to build provider '<id>' from config at <path>: …` — the id in
  `[roles]` is not in your tars config, or that entry does not parse. The rest of the line
  is tars's own words.
- `the fixer `<id>` cannot work in the working tree: …` — the provider is an agent CLI
  with its own tools off. Set `tools = "default"` (Claude Code) or
  `sandbox = "workspace-write"` (Codex) on it.
- Add `-v` (or `-vv`) to any arc command for a diagnostic log on stderr.

## 2. The agent as a participant (bridge)

This part needs the pipeline's chat server ([Set up the pipeline](onboarding.md)). What sessions do on it — rooms, messages, teams — is [Team up](bridge.md); this section is how to wire each agent in.

Your agent's own session gets a name on arc's chat server. Every time the session stops,
a hook asks the server for mail. If there is something worth interrupting for — a review
with findings, a bounced PR — the hook stops the agent from stopping and puts the
messages into the session as its next input.

### What you need on every machine

1. `arc` installed (see [Install](install.md)).
2. `~/.arc/client.toml` naming this machine's board. arc asks the board where the chat
   server is:

   ```toml client.toml
   web = "http://<board-host>:<port>"
   ```

   This file has exactly one key. A misspelled key is refused, not ignored.
3. The hooks for your agent (below).

The hooks never break your agent. On any error they let the agent stop normally and write
the reason to stderr, starting with `[arc bridge]`. With no `client.toml` they let every
stop through and do nothing else.

### Names

On the server, a session is known by a name, and mail goes to the name.

- Pass `--name NAME` on the hook line to fix the name. Otherwise Claude Code uses the
  session's name (`claude -n NAME`), and every agent falls back to its session id.
- A name has no spaces, control characters, `/` or `\`, at most one `@` inside
  (`codex@laptop`), and at most 64 bytes.
- **One name, one session.** Two open sessions under one name get each other's mail. A
  `--name` in a global settings file gives every session on that machine the same name;
  the second one to start cannot claim it. For several sessions, put the hook in each
  repo's settings, or leave `--name` out.
- `arc bridge launch ROLE` starts a session under `<repo>-<ROLE>-<MMDD><letter>`, a name no
  online session holds, and prints the name. `--agent claude|codex|agy` picks the CLI
  (default `claude`); arguments after `--` go to it as they are.
  - Without `--prompt` the session takes this terminal: `claude -n <name>`, or `codex` with
    arc's hooks carrying the name. agy cannot be started this way.
  - With `--prompt TEXT` the session starts in the background with TEXT as its first message,
    and the command returns. It runs one headless turn: `claude -p`, `codex exec`, or
    `agy -p`, writing its output to `~/.arc/logs/launch/<name>.log`. This is how one agent
    starts another from its own shell.
  - Codex: the launched session does not read `~/.codex/config.toml` (Codex would add its
    hooks, with their fixed `--name`, to arc's), so its MCP servers, plugins and model
    settings are not there; pass what it needs as `-c key=value` after `--`. arc's own hooks
    run without being trusted in `/hooks` (`--dangerously-bypass-hook-trust`).
  - With `--prompt`, once the session has started `launch` registers its name on arc-bridge
    itself, with the `--agent` runtime and the session id (for claude the one `launch` chose
    with `--session-id`, for codex and agy the one they printed); a
    session that does not start leaves no name behind. So the new session can send, and be
    added to a team, during its first turn. If arc-bridge refuses the name, `launch` prints
    the server's words and exits non-zero; the session keeps running and its own hook
    registers it later. Without `--prompt` the session's own hook registers it.
  - agy: arc records the name against the conversation id agy prints first; the `Stop` hook
    uses it instead of its `--name`.
  - A session started this way ends after its turn, so `launch` also starts
    `arc bridge keep-receiving` beside it. Once a turn has ended, that process waits for mail;
    when mail arrives, it resumes the same session (`claude -p --resume <id>`,
    `codex exec resume <id>` or `agy --conversation <id> -p`), with the mail as the message of
    the next turn and the same
    arguments after `--`. Mail that arrives while a turn runs goes in at that turn's stop.
    It writes to the same log. It waits up to 2 h after each turn, and for as long as the seat
    is one side of a team that has not closed (`arc bridge team agree` from both sides closes
    it). When the turn that took the mail fails, each sender gets the mail back as a direct
    message carrying that turn's own error, and it goes on waiting.
  - Claude: the session still runs the hooks in your settings. While `keep-receiving` holds
    it, the two `Stop` mail lines step aside: `await-mail` exits at once (a headless turn
    would not end while it waits), and `arc bridge hook Stop --mail waiter` puts mail that
    arrived during the turn in at that stop. `claude --bg` is not used: a `--bg` session is
    woken only by the `await-mail` hook, within its `timeout`, and `claude --bg --resume`
    starts a copy of the session instead of continuing it.
  - Every Codex turn after the first is `codex exec resume`, which takes fewer options than
    `codex exec` (no `-s/--sandbox`, `-p/--profile`, `-C/--cd`, `--add-dir`): `launch` refuses
    those after `--` and names the ones it takes. Set the sandbox with
    `-c sandbox_mode="workspace-write"` instead.

### Claude Code

Paste this into `~/.claude/settings.json` (or a repo's `.claude/settings.json`), or run
`arc bridge install-hooks --agent claude`, which writes these lines into
`~/.claude/settings.json` and keeps your other hooks.

```json
{
  "hooks": {
    "SessionStart": [{ "hooks": [{ "type": "command", "command": "arc bridge hook SessionStart", "timeout": 10 }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "arc bridge hook UserPromptSubmit", "timeout": 10 }] }],
    "PreToolUse":   [{ "hooks": [{ "type": "command", "command": "arc bridge hook PreToolUse", "timeout": 5 }] }],
    "PostToolUse":  [{ "matcher": "Bash", "hooks": [{ "type": "command", "command": "arc bridge hook PostToolUse", "timeout": 5 }] }],
    "PostToolUseFailure": [{ "matcher": "Bash", "hooks": [{ "type": "command", "command": "arc bridge hook PostToolUseFailure", "timeout": 5 }] }],
    "Stop": [{ "hooks": [
      { "type": "command", "command": "arc bridge hook Stop --mail waiter", "timeout": 600 },
      { "type": "command", "command": "arc bridge await-mail", "timeout": 86400, "asyncRewake": true }
    ] }],
    "SessionEnd":   [{ "hooks": [{ "type": "command", "command": "arc bridge hook SessionEnd", "timeout": 10 }] }]
  }
}
```

- `UserPromptSubmit` is a speed bump: when the model was last called over an hour ago (the
  prompt cache has expired) and the context is over 100k tokens, it holds your prompt once and
  says what sending it would cost. It holds at most one prompt per idle stretch: the next
  prompt, the same one or another, goes through. A timer firing more than an hour apart (a
  `/loop 2h`) is held once in every stretch, so it loses every other firing, and a held
  self-scheduled wakeup does not schedule itself again; whether timed prompts pass through
  this hook at all has not been measured. Sessions started by `arc bridge launch` are not
  held while their keep-receiving process is alive. For a short break, keep the cache warm with `/loop 55m 保温,只回复 ok`; at the end
  of the day, write a handoff and `/clear`. When it cannot read the transcript it lets the
  prompt through.
- The two `Stop` lines go together. `await-mail` waits in the background after your
  session stops and wakes it when mail arrives: up to 2 hours, or for as long as the session
  is one side of a team that has not closed. `--mail waiter` tells the first line to leave
  the mail to it, so nothing is delivered twice.
- The `timeout` on the `await-mail` line is the real limit: Claude Code kills the hook when
  it runs out, whatever `await-mail` would still wait for. 86400 (a day) lets a teammate
  answer the next day; mail that arrives after the timeout goes in only the next time the
  session stops by itself. A session started by `arc bridge launch --prompt` does not have
  this limit: `arc bridge keep-receiving` waits for it.
- If you do not want to be woken while idle, keep only `arc bridge hook Stop` (no
  `--mail`). Mail then arrives the next time the session stops.
- `--agent` defaults to `claude`, so Claude Code lines do not need it.

### Codex CLI

Put this in `~/.codex/config.toml` (or a repo's `.codex/config.toml`). Use the absolute
path to `arc`. Or run `arc bridge install-hooks --agent codex --name codex@laptop`, which
writes these lines into `~/.codex/config.toml`; you still trust them in `/hooks`.

```toml ignore: Codex CLI's config.toml, not arc's
[features]
hooks = true

[[hooks.SessionStart]]
[[hooks.SessionStart.hooks]]
type = "command"
command = "/path/to/arc bridge hook SessionStart --agent codex --name codex@laptop"
timeout = 10

[[hooks.PreToolUse]]
[[hooks.PreToolUse.hooks]]
type = "command"
command = "/path/to/arc bridge hook PreToolUse --agent codex --name codex@laptop"
timeout = 5

[[hooks.Stop]]
[[hooks.Stop.hooks]]
type = "command"
command = "/path/to/arc bridge hook Stop --agent codex --name codex@laptop --mail waiter"
timeout = 30

[[hooks.SessionEnd]]
[[hooks.SessionEnd.hooks]]
type = "command"
command = "/path/to/arc bridge hook SessionEnd --agent codex --name codex@laptop"
timeout = 3
```

- **`--agent codex` is required.** Without it the hook treats the session as Claude Code.
- Event names are capitalised (`Stop`, not `stop`) and the inner `[[hooks.<Event>.hooks]]`
  table is required. Get either wrong and Codex does not complain; `/hooks` just shows
  `Installed 0`.
- **Trust the hooks.** Restart Codex, run `/hooks`, and trust the new entries. An untrusted
  hook is skipped silently. Changing a command means trusting it again.
- `--mail waiter` on the `Stop` line starts a background `arc bridge await-mail --agent codex`.
  When mail arrives it runs `codex queue --thread <session> --message …`, so `codex` must be
  on the hook's `PATH`. If that fails, the mail stays in your inbox and the reason is written
  to `~/.arc/logs/await-mail.log`. Leave out `--mail waiter` to get mail only when the
  session stops.
- `SessionEnd` gets at most 3 seconds in Codex; keep slow work out of it.

### agy (Antigravity CLI)

Put this in `~/.gemini/config/hooks.json` (all sessions) or `.agents/hooks.json` at the
repo root, or run `arc bridge install-hooks --agent agy --name agy@laptop`, which writes it
into `~/.gemini/config/hooks.json`:

```json
{
  "arc-bridge": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "~/.cargo/bin/arc bridge hook PreInvocation --agent agy --name agy@laptop",
        "timeout": 10
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "~/.cargo/bin/arc bridge hook Stop --agent agy --name agy@laptop",
        "timeout": 30
      }
    ]
  }
}
```

- **`PreInvocation` and `Stop` only.** `PreInvocation` runs before agy calls the model, and
  marks the session working; `Stop` marks it stopped and delivers mail. Your name is claimed
  the first time the hook sees a session, so usually on its first `PreInvocation`. Any other
  event is let through with a note on stderr. The `PreInvocation` line follows agy's online
  hooks docs and has not been run on a real agy yet. What arc does not hook on agy, and why:
  - `PreToolUse`: it is a permission hook (its answer is a `decision`; `allow` hands the call
    on to the next hook or the default policy). arc has not run it on a real agy, and a wrong
    answer would touch every tool call, so it is not hooked until that is checked.
  - `PostToolUse`: arc records the files a command changed through the transcript: the hook's
    output is kept next to the call there. agy's docs do not say whether agy keeps this
    hook's output, so that route is not verified, and arc does not record changed files for
    agy. The hook's input carries `toolCall.args`, which names the file a write tool wrote,
    so a later version could record that directly.
  - `PostInvocation`: it runs after each model call; `PreInvocation` already marks the
    session working, so it would add nothing.
  - `SessionStart`: agy's current hooks docs list it, but agy 1.2.11 has no such event.
    arc does not hook it until it is checked whether an older agy rejects a `hooks.json`
    that names it.
  - There is no session end event. An agy session goes offline after 30 minutes with no
    hook, the same rule as any session whose end arc does not hear.
- **`--agent agy` is required.** agy's payload has a different shape; without the flag the
  hook cannot read it and never delivers anything.
- The top level is a hook name you choose (`arc-bridge` above); the events sit under it. Put
  `"Stop"` at the top level and agy drops the whole file.
- A `hooks.json` under `.gemini/` in your repo is not read. Restart `agy` after editing.
- **Install the hook once.** If the global file and the repo file both run
  `arc bridge hook Stop`, agy runs both, and the session can loop.
- **Woken by mail while idle: add `--mail waiter`** to the `Stop` line
  (`arc bridge hook Stop --agent agy --name agy@laptop --mail waiter`). agy's hooks cannot
  start a background task themselves, so when the session stops with no mail and no waiter
  running, the hook keeps it going once and asks the model to start
  `arc bridge await-mail --agent agy …` with `run_command` in the background
  (`WaitMsBeforeAsync` 500, `IsDaemon` false); the reason it is given holds the full command
  line. When mail arrives the waiter prints it and exits, and agy starts a new turn with that
  output. Mail already waiting at a stop is still put in right there.
- What `--mail waiter` costs on agy: one extra model call each time the session stops without
  a waiter running (after every wake, and after any turn that ended its waiter), and the waiter
  shows in `/tasks` and as `1 task(s)` under the prompt. It relies on the model doing what the
  hook asks. A waiter that waits two hours with no mail ends, which wakes the session once; the
  next stop asks for a new one.

### Sending and reading by hand

```bash
arc bridge inbox                       # unread mail; does NOT mark it read
arc bridge inbox --wait 55             # wait up to 55 s for mail
arc bridge send <name> "<text>"        # direct message
arc bridge join <channel>              # e.g. landings
arc bridge post <channel> "<text>"
arc bridge interest add mine           # only mail to you, or about your PRs, interrupts you
```

The reply line under mail arc hands to a session already carries `--as <its name>` (and
`--home` / `--bridge-server` when the session is not on this machine's defaults): copy it as it is.
Any other command needs `--as <the name you gave --name>` too, except in a Claude Code session
started on its own: a session started inside another agent's session (agy or Codex run from a
Claude Code shell, say) carries both sessions' variables and cannot tell from them who it is.
`inbox` only peeks: mail is marked read when the Stop hook delivers it.

### Check that it works

- `arc bridge doctor` (or `--agent codex` for one agent) reads the config files and says what
  would keep the hooks from running: Codex's `[features] hooks` or trust missing, an agy event
  at the top level, the Stop hook installed in two places. It exits 1 when something fails.
- `arc bridge inbox` (with `--as NAME` outside Claude Code) answers without an error. If it
  prints `no arc-bridge server is configured on this machine`, fix `~/.arc/client.toml`.
- Send yourself a message from another terminal (`arc bridge send <name> "ping" --as <other-name>`),
  then let your session stop: the message should come back into it.
- Codex: `/hooks` shows `Installed` and `Active` for each event.

### When it breaks

- Every hook writes its reason to stderr, starting with `[arc bridge]`, and then lets the
  agent continue. Look there first.
- `… is not the shape we know …` — the payload did not match the agent the hook line names.
  Check `--agent`.
- `AGY payload names no workspace` — agy sent no `workspacePaths`; the hook does nothing for
  that stop.
- `transcript not shipped: …` on every Codex stop is expected: arc does not upload Codex
  transcripts yet.
- `… until this arc and arc-bridge are one build again …` — your arc and the server are
  different builds. The same line starts with the server's own words, which say what to do:
  either `Reinstall arc from main` when the server can tell your arc is the old one, or both
  builds and "whichever of the two is not main's build goes back to main" — your arc with
  `just install`, arc-bridge by deploying it from main.
- Same-name warning at session start (Claude Code): another online session holds your name.
  Rename one of them with `/rename`.

### What each agent supports

| | Claude Code | Codex CLI | agy |
|---|---|---|---|
| Mail put into the session when it stops | yes | yes (`--agent codex`) | yes (`--agent agy`) |
| Woken by mail while idle | yes (`await-mail` with `asyncRewake`) | yes (`--mail waiter`, via `codex queue`) | yes (`--mail waiter`; the model starts `await-mail` as a background task, one extra model call per stop) |
| Session id comes from | hook payload `session_id`; `CLAUDE_CODE_SESSION_ID` for commands you run | hook payload `session_id`; `CODEX_THREAD_ID` for commands you run | hook payload `conversationId`; `ANTIGRAVITY_CONVERSATION_ID` for commands you run |
| Name without `--name` | `claude -n` name, else session id | session id | conversation id |
| `arc bridge` commands without `--as` | yes, unless started inside another agent's session | no: add `--as` (the reply line under mail carries it) | no: add `--as` (the reply line under mail carries it) |
| Online status: working / stopped / gone | all three | all three | working (`PreInvocation`, following agy's docs, not yet run on a real agy) and stopped; gone only after 30 minutes with no hook |
| Goes offline when the session ends | yes | yes | no (agy has no end event) |
| Transcript uploaded to the server | yes | no | yes (what the model says reaches its feed; tool outputs are not read yet) |
| Files a shell command changed, recorded | yes (`PostToolUse` on Bash) | no: arc does not install a Codex `PostToolUse` line, and it is not tested | no (see the agy section) |
| PR registered to the session by `arc submit` | yes | yes | yes |
| Review results for that PR delivered | yes | yes | yes (when the session stops) |
| supervisor (a second session judging your stops) | yes | no | no |
| `arc bridge launch` | yes (`--prompt` = `claude -p`, resumed when mail arrives) | yes (`--agent codex`; `--prompt` = `codex exec`, resumed when mail arrives) | background only (`--agent agy --prompt`; resumed when mail arrives) |

## 3. A day with your agent

This is the path that works today. Run each step from the PR's branch.

1. **Write and commit.** Your agent works on a branch and commits.
2. **Open the PR: `arc submit`.** It pushes the branch, opens (or reuses) its PR and puts it
   on the review queue. Run inside a Claude Code, Codex or agy session with the bridge on, it
   also registers the PR to your session, so the review comes back to you. A command run by an
   agent that was itself started inside another agent's session carries both sessions'
   variables; arc cannot tell which one runs it and says so instead of registering.
3. **Optional: a local review pass.** `arc local-review` reviews the branch's whole change
   against the remote's default branch, the working tree as it is (a dirty tree through a
   commit of it that moves nothing). It is a self-check on this clone only: the findings go to
   a local PR in `.arc/review.db`, not to the PR from step 2, and nothing is pushed. It never
   edits files; `arc fix` answers its findings. It refuses on the default branch or a detached HEAD.
   - `arc hook install` runs `arc local-review` in the background after each commit — the
     branch's change as of that commit — and logs to `.arc/critic.log`. It skips commits made in a linked worktree
     (`git worktree add`), during a rebase or cherry-pick, or on an amend, and commits
     already reviewed. When it cannot decide — a checkout that is no tenant's — it reviews
     nothing and says why in your terminal. It only reviews: it never edits or commits.
4. **The review comes back.** When the review service finds something, it posts a letter
   into the PR's channel: the findings, and an `arc submit --pr <N> --fix-answers -` command to
   fill in (`arc submit` refuses `--fix-answers` without `--pr`). A Claude Code session gets
   it at its next stop, or is woken by it.
5. **Answer the findings.** Either:
   - let your agent fix them, push, and answer each finding with
     `arc submit --pr <N> --fix-answers -` (JSON on stdin: `fixed` with what changed, or `wontfix`
     with why); or
   - run `arc local-review` and then `arc fix` to have the Fixer role fix what this
     machine's own review found. The fixes are made one after another in your working
     tree, each one commit on your branch on top of the one before; their answers go on the
     new head and are reviewed again on this machine, round after round until the reviewer
     says LGTM or has taken its `[review] max_rounds` turns. The working tree must be HEAD's
     (commit, stash or ignore everything first, untracked files included), and
     `git reset --hard refs/arc/before-fix/<branch>` undoes the run. Then hand the new head
     to review as an update of the PR:

     ```bash
     git log --oneline -3                   # the fixes, on your branch
     arc submit --pr <N>                    # pushes; the review service reviews the new head
     ```
6. **Landing.** Once every reviewer says LGTM, the review service grants the pass and the
   merger lands the PR. To keep it from landing, label it `arc-hold`.

Every command takes `--json` and then prints one machine-readable envelope. Have your agent
read that rather than the human text.

---

*Next: [The commands](commands.md) · [Configuration](configuration.md) · [Troubleshooting](troubleshooting.md).*
