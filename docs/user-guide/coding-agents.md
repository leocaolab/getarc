# Connecting your coding agent

arc works with three coding agents: **Claude Code**, **Codex CLI** and **agy** (the Antigravity CLI). You can connect an agent in two ways. Use one, or both.

| | What it does | Where you set it up |
|---|---|---|
| **1. As a role** | arc starts the agent itself, as the Fixer that edits code for `arc fix` (or as a critic) | `[roles]` in `<repo>/.arc/config.toml`; the provider in `~/.tars/config.toml` |
| **2. As a participant** | your own agent session joins arc's chat server. Review results, PR results and messages are put into your session when it stops | hooks in the agent's own settings file, calling `arc bridge hook` |

The first way needs only arc and tars on your machine. `arc local-review` reviews the branch and keeps the findings as a **local PR** (a review record stored only in this clone, in `.arc/review.db`); `arc fix` then answers them. The second way also needs the pipeline's chat server, arc-bridge (see [Set up the pipeline](onboarding.md)).

## 1. The agent as a role (Fixer or critic)

### Set it up

Define the provider in tars, then name it in `[roles]`. arc never reads a model or a key from `.arc/config.toml`; a `[providers]` section there is refused. Details: [Configuration](configuration.md).

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

- **Always set `fixer`.** It never falls back to `default`. arc wants the Fixer to come from a different model family than the critic, so the review stays independent.
- **An agent CLI uses its own tools.** When the Fixer is an agent CLI, arc gives it no tools of its own. The agent edits your working tree with its own tools, and arc reads the diff.
- **Turn on tools for a Claude Code Fixer.** `claude_cli` defaults to `tools = "disabled"`. That is right for a critic, which only answers, and wrong for a Fixer, which then cannot edit anything; `arc fix` refuses such a Fixer before calling it. Set `tools = "default"` on the provider your `fixer` names. The same goes for Codex's default `sandbox = "read-only"`.
- `claude_cli` uses your `claude login` session. No API key is needed.

The three agents as tars provider types:

| Agent | tars `type` | What tars runs | Settings you will likely need |
|---|---|---|---|
| Claude Code | `claude_cli` | `claude -p …` | `tools = "default"` for a Fixer; optional `effort`, `timeout_secs` (default 300) |
| Codex CLI | `codex_cli` | `codex exec --json --model <model> --sandbox <sandbox> -c approval_policy="never" --skip-git-repo-check -`, in your working tree | `sandbox = "workspace-write"` for a Fixer: the default `"read-only"` is passed to Codex as `--sandbox read-only`, so Codex cannot write. `timeout_secs` defaults to 600 |
| agy | `antigravity` | `agy -p "<prompt>" --model <model> --dangerously-skip-permissions --add-dir <cwd>` | `effort` is `"low"` or `"high"` (default `"high"`) |

All three take `default_model` and an optional `executable` (default `claude`, `codex`, `agy`). The committed example (`.arc/config.toml.example`) uses `claude_cli` as the Fixer.

How well each one is tested:

- tars accepts `codex_cli` and `antigravity`, and arc runs them as agent CLIs.
- What arc passes to Codex for each `sandbox` value has been checked. No Fixer run against a real Codex has been made yet.
- arc's own test suite runs neither of them as a Fixer from start to finish.

### Check that it works

The Fixer answers the findings of the branch's local PR, so run `arc local-review` on the branch first. Then:

```bash
arc fix --dry-run
```

`--dry-run` runs the Fixer read-only. For each open finding it reports `[AGREE]` or `[DISAGREE]`, with a plan. Nothing is edited, committed or sent.

### When it fails

- `fixer pipeline: failed to build provider '<id>' from config at <path>: …` — the id in `[roles]` is not in your tars config, or that entry has an error. The rest of the line is tars's own message.
- `the fixer `<id>` cannot work in the working tree: …` — the provider is an agent CLI with its tools turned off. Set `tools = "default"` (Claude Code) or `sandbox = "workspace-write"` (Codex) on it.
- Add `-v` (or `-vv`) to any arc command for a diagnostic log on stderr.

## 2. The agent as a participant (bridge)

This needs the pipeline's chat server ([Set up the pipeline](onboarding.md)). What sessions can do there (rooms, messages, teams) is in [Team up](bridge.md); this section shows how to connect each agent.

Your agent's session gets a name on arc's chat server. Every time the session stops, a hook asks the server for new mail. If there is something worth interrupting for, such as a review with findings or a PR sent back by the merge machine, the hook keeps the agent from stopping and gives it the messages as its next input.

### What you need on every machine

1. `arc` installed (see [Install](install.md)).
2. `~/.arc/client.toml` with the address of the board. arc asks the board where the chat server is:

   ```toml client.toml
   web = "http://<board-host>:<port>"
   ```

   This file has exactly one key. A misspelt key is refused, not ignored.
3. The hooks for your agent (below).

The hooks never break your agent. On any error they let the agent stop normally and write the reason to stderr, starting with `[arc bridge]`. Without `client.toml` they let every stop through and do nothing else.

### Names

On the server, each session has a name, and mail is sent to the name.

- To set the name, pass `--name NAME` on the hook line. Otherwise Claude Code uses the session's name (`claude -n NAME`), and every agent falls back to its session id.
- A name has no spaces, control characters, `/` or `\`, at most one `@` inside (`codex@laptop`), and at most 64 bytes.
- **One name, one session.** Two open sessions with the same name get each other's mail. A `--name` in a global settings file gives every session on that machine the same name, and the second session to start cannot claim it. For several sessions, put the hook in each repo's settings, or leave `--name` out.

### Starting a session: `arc bridge launch`

`arc bridge launch ROLE` starts a new session named `<repo>-<ROLE>-<MMDD><letter>`, picking a name no online session has, and prints the name. `--agent claude|codex|agy` picks the CLI (default `claude`). Arguments after `--` are passed to the CLI unchanged.

**Without `--prompt`,** the session runs in this terminal: `claude -n <name>`, or `codex` with arc's hooks carrying the name. agy cannot be started this way. The session's own hook registers its name.

**With `--prompt TEXT`,** the session starts in the background with TEXT as its first message, and the command returns. This is how one agent starts another from its own shell.

- It runs one turn without a terminal (`claude -p`, `codex exec` or `agy -p`) and writes its output to `~/.arc/logs/launch/<name>.log`.
- Once the session has started, `launch` registers its name on arc-bridge, together with the `--agent` and the session id (for claude, the id `launch` chose with `--session-id`; for codex and agy, the id they printed). So the new session can send messages, and be added to a team, during its first turn. A session that does not start leaves no name behind. If arc-bridge refuses the name, `launch` prints the server's message and exits non-zero; the session keeps running, and its own hook registers it later.
- For agy, arc records the name against the conversation id agy prints first; the `Stop` hook uses that instead of its `--name`.
- Such a session ends after its turn, so `launch` also starts `arc bridge keep-receiving` next to it. After each turn, that process waits for mail. When mail arrives, it resumes the same session (`claude -p --resume <id>`, `codex exec resume <id>` or `agy --conversation <id> -p`), with the mail as the next message and the same arguments after `--`. Mail that arrives during a turn is delivered when that turn stops. It writes to the same log.
- It waits up to 2 h after each turn, and also for as long as the session is one side of a team that has not closed (the team closes when both sides run `arc bridge team agree`).
- If the turn that received the mail fails, each sender gets the mail back as a direct message, with that turn's own error, and `keep-receiving` goes on waiting.

Notes per agent:

- **Claude:** the session still runs the hooks in your settings. While `keep-receiving` is running, the two `Stop` mail lines step aside: `await-mail` exits at once (a turn without a terminal would never end while it waits), and `arc bridge hook Stop --mail waiter` delivers mail that arrived during the turn when the turn stops. `claude --bg` is not used: a `--bg` session is woken only by the `await-mail` hook, within its `timeout`, and `claude --bg --resume` starts a copy of the session instead of continuing it.
- **Codex:** the launched session does not read `~/.codex/config.toml` (Codex would add the hooks from it, with their fixed `--name`, to arc's), so your MCP servers, plugins and model settings from that file are not loaded. Pass what the session needs as `-c key=value` after `--`. arc's own hooks run without you trusting them in `/hooks` (`--dangerously-bypass-hook-trust`).
- **Codex:** every turn after the first is `codex exec resume`, which takes fewer options than `codex exec` (no `-s/--sandbox`, `-p/--profile`, `-C/--cd`, `--add-dir`). `launch` refuses those after `--` and lists the options it accepts. To set the sandbox, use `-c sandbox_mode="workspace-write"` instead.

### Claude Code

Paste this into `~/.claude/settings.json` (or a repo's `.claude/settings.json`). Or run `arc bridge install-hooks --agent claude`, which writes these lines into `~/.claude/settings.json` and keeps your other hooks.

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

**The two `Stop` lines go together.** `await-mail` waits in the background after your session stops, and wakes it when mail arrives: for up to 2 hours, or for as long as the session is one side of a team that has not closed. `--mail waiter` tells the first line to leave mail to `await-mail`, so nothing is delivered twice.

- The `timeout` on the `await-mail` line is the real limit: Claude Code kills the hook when it runs out, however long `await-mail` would still wait. 86400 (a day) lets a teammate answer the next day. Mail that arrives after the timeout is delivered only the next time the session stops by itself. A session started by `arc bridge launch --prompt` does not have this limit, because `arc bridge keep-receiving` waits for it.
- If you do not want to be woken while idle, keep only `arc bridge hook Stop` (without `--mail`). Mail then arrives the next time the session stops.
- `--agent` defaults to `claude`, so Claude Code lines do not need it.

**`UserPromptSubmit` warns you before an expensive prompt.** When the model was last called more than an hour ago (so the prompt cache has expired) and the context is over 100k tokens, it holds your prompt once and tells you what sending it would cost.

- It holds at most one prompt per idle stretch: the next prompt, the same or a different one, goes through.
- A timer that fires more than an hour apart (a `/loop 2h`) is held once in every stretch, so every other firing is lost, and a held wakeup the session scheduled for itself does not schedule itself again. Whether timed prompts go through this hook at all has not been measured.
- Sessions started by `arc bridge launch` are not held while their `keep-receiving` process is running.
- For a short break, keep the cache warm with `/loop 55m 保温,只回复 ok`. At the end of the day, write a handoff and `/clear`.
- If it cannot read the transcript, it lets the prompt through.

### Codex CLI

Put this in `~/.codex/config.toml` (or a repo's `.codex/config.toml`), with the absolute path to `arc`. Or run `arc bridge install-hooks --agent codex --name codex@laptop`, which writes these lines into `~/.codex/config.toml`; you still need to trust them in `/hooks`.

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
- Event names are capitalised (`Stop`, not `stop`), and the inner `[[hooks.<Event>.hooks]]` table is required. Get either wrong and Codex says nothing; `/hooks` just shows `Installed 0`.
- **Trust the hooks.** Restart Codex, run `/hooks`, and trust the new entries. Codex skips an untrusted hook without a word. If you change a command, trust it again.
- `--mail waiter` on the `Stop` line starts `arc bridge await-mail --agent codex` in the background. When mail arrives, it runs `codex queue --thread <session> --message …`, so `codex` must be on the hook's `PATH`. If that fails, the mail stays in your inbox and the reason is written to `~/.arc/logs/await-mail.log`. Leave out `--mail waiter` to get mail only when the session stops.
- Codex gives `SessionEnd` at most 3 seconds; keep slow work out of it.

### agy (Antigravity CLI)

Put this in `~/.gemini/config/hooks.json` (for all sessions) or in `.agents/hooks.json` at the repo root. Or run `arc bridge install-hooks --agent agy --name agy@laptop`, which writes it into `~/.gemini/config/hooks.json`:

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

- **`--agent agy` is required.** agy sends hook data in a different shape; without the flag the hook cannot read it and never delivers anything.
- The top level is a hook name you choose (`arc-bridge` above), and the events go under it. If you put `"Stop"` at the top level, agy ignores the whole file.
- A `hooks.json` under `.gemini/` in your repo is not read. Restart `agy` after editing.
- **Install the hook only once.** If both the global file and the repo file run `arc bridge hook Stop`, agy runs both, and the session can loop.

**Only `PreInvocation` and `Stop`.** `PreInvocation` runs before agy calls the model and marks the session as working; `Stop` marks it as stopped and delivers mail. The name is claimed the first time the hook sees a session, usually at its first `PreInvocation`. Any other event is let through with a note on stderr. The `PreInvocation` line follows agy's online hooks docs and has not been run on a real agy yet. What arc does not hook on agy, and why:

- `PreToolUse`: it is a permission hook (its answer is a `decision`; `allow` passes the call on to the next hook or the default policy). arc has not run it on a real agy, and a wrong answer would affect every tool call, so arc does not hook it until that is checked.
- `PostToolUse`: arc records which files a command changed through the transcript, where the hook's output is kept next to the call. agy's docs do not say whether agy keeps this hook's output, so that route is not verified, and arc does not record changed files for agy. The hook's input includes `toolCall.args`, which names the file a write tool wrote, so a later version could record that directly.
- `PostInvocation`: it runs after each model call. `PreInvocation` already marks the session as working, so it would add nothing.
- `SessionStart`: agy's current hooks docs list it, but agy 1.2.11 has no such event. arc does not hook it until someone checks whether an older agy rejects a `hooks.json` that names it.
- There is no session-end event. An agy session goes offline after 30 minutes without a hook call, the same rule as for any session whose end arc does not hear about.

**To be woken by mail while idle, add `--mail waiter`** to the `Stop` line (`arc bridge hook Stop --agent agy --name agy@laptop --mail waiter`).

- agy's hooks cannot start a background task themselves. So when the session stops with no mail and no waiter running, the hook keeps the session going once and asks the model to start `arc bridge await-mail --agent agy …` in the background with `run_command` (`WaitMsBeforeAsync` 500, `IsDaemon` false). The message the hook gives includes the full command line.
- When mail arrives, the waiter prints it and exits, and agy starts a new turn with that output. Mail that is already waiting when the session stops is delivered right then.
- What it costs: one extra model call each time the session stops without a waiter running (after every wake-up, and after any turn that ended its waiter). The waiter shows in `/tasks` and as `1 task(s)` under the prompt. It relies on the model doing what the hook asks. A waiter that waits two hours without mail ends, which wakes the session once; at the next stop, the hook asks for a new one.

### Sending and reading by hand

```bash
arc bridge inbox                       # unread mail; does NOT mark it read
arc bridge inbox --wait 55             # wait up to 55 s for mail
arc bridge send <name> "<text>"        # direct message
arc bridge join <channel>              # e.g. landings
arc bridge post <channel> "<text>"
arc bridge interest add mine           # only mail to you, or about your PRs, interrupts you
```

- Mail that arc delivers to a session ends with a reply command that already includes `--as <the session's name>` (and `--home` / `--bridge-server` when the session is not on this machine's defaults). Copy it as it is.
- Every other command also needs `--as <the name you gave --name>`. The exception is a Claude Code session started on its own. A session started inside another agent's session (say, agy or Codex run from a Claude Code shell) carries the environment variables of both sessions and cannot tell from them which one it is.
- `inbox` only looks: mail is marked read when the Stop hook delivers it.

### Check that it works

- `arc bridge doctor` (or `--agent codex` for one agent) reads the config files and says what would stop the hooks from running: Codex's `[features] hooks` or trust missing, an agy event at the top level, the Stop hook installed in two places. It exits 1 when something is wrong.
- `arc bridge inbox` (with `--as NAME` outside Claude Code) answers without an error. If it prints `no arc-bridge server is configured on this machine`, fix `~/.arc/client.toml`.
- Send yourself a message from another terminal (`arc bridge send <name> "ping" --as <other-name>`), then let your session stop: the message should appear in it.
- Codex: `/hooks` shows `Installed` and `Active` for each event.

### When it breaks

- Every hook writes its reason to stderr, starting with `[arc bridge]`, and then lets the agent continue. Look there first.
- `… is not the shape we know …` — the hook data did not match the agent named on the hook line. Check `--agent`.
- `AGY payload names no workspace` — agy sent no `workspacePaths`; the hook does nothing for that stop.
- `transcript not shipped: …` on every Codex stop is expected: arc does not upload Codex transcripts yet.
- `… until this arc and arc-bridge are one build again …` — your `arc` and the server are different builds. The line starts with the server's own words, which say what to do: either `Reinstall arc from main`, when the server can tell your `arc` is the older one, or it names both builds and says "whichever of the two is not main's build goes back to main". You update your `arc` with `just install`, and arc-bridge by deploying it from main.
- A warning about the same name at session start (Claude Code): another online session has your name. Rename one of them with `/rename`.

### What each agent supports

| | Claude Code | Codex CLI | agy |
|---|---|---|---|
| Mail put into the session when it stops | yes | yes (`--agent codex`) | yes (`--agent agy`) |
| Woken by mail while idle | yes (`await-mail` with `asyncRewake`) | yes (`--mail waiter`, via `codex queue`) | yes (`--mail waiter`; the model starts `await-mail` as a background task, one extra model call per stop) |
| Session id comes from | hook payload `session_id`; `CLAUDE_CODE_SESSION_ID` for commands you run | hook payload `session_id`; `CODEX_THREAD_ID` for commands you run | hook payload `conversationId`; `ANTIGRAVITY_CONVERSATION_ID` for commands you run |
| Name without `--name` | `claude -n` name, else session id | session id | conversation id |
| `arc bridge` commands without `--as` | yes, unless started inside another agent's session | no: add `--as` (the reply command under mail includes it) | no: add `--as` (the reply command under mail includes it) |
| Online status: working / stopped / gone | all three | all three | working (`PreInvocation`, following agy's docs, not yet run on a real agy) and stopped; gone only after 30 minutes with no hook |
| Goes offline when the session ends | yes | yes | no (agy has no end event) |
| Transcript uploaded to the server | yes | no | yes (what the model says reaches its feed; tool outputs are not read yet) |
| Files a shell command changed are recorded | yes (`PostToolUse` on Bash) | no: arc does not install a Codex `PostToolUse` line, and it is not tested | no (see the agy section) |
| `arc submit` links the PR to the session | yes | yes | yes |
| Review results for that PR delivered | yes | yes | yes (when the session stops) |
| supervisor (a second session judging your stops) | yes | no | no |
| `arc bridge launch` | yes (`--prompt` = `claude -p`, resumed when mail arrives) | yes (`--agent codex`; `--prompt` = `codex exec`, resumed when mail arrives) | background only (`--agent agy --prompt`; resumed when mail arrives) |

## 3. A day with your agent

This is the workflow that works today. Run each step from the PR's branch.

1. **Write and commit.** Your agent works on a branch and commits.
2. **Open the PR: `arc submit`.** It pushes the branch, opens its PR (or reuses the open one), and puts it in the review queue. When you run it inside a Claude Code, Codex or agy session connected to the bridge, it also links the PR to your session, so the review comes back to you. If the agent running it was itself started inside another agent's session, it carries the environment variables of both sessions; arc cannot tell which one is running it, and says so instead of linking the PR.
3. **Optional: review on your machine first.** `arc local-review` reviews the branch's whole change against the remote's default branch, with the working tree as it is (uncommitted changes are reviewed through a commit of the tree that does not move your branch). It is a self-check in this clone only: the findings go to a local PR in `.arc/review.db`, not onto the PR from step 2, and nothing is pushed. It never edits files; `arc fix` answers its findings. It refuses to run on the default branch or on a detached HEAD.
   - `arc hook install` runs `arc local-review` in the background after each commit (on the branch's change as of that commit) and logs to `.arc/critic.log`. It skips commits made in a linked worktree (`git worktree add`), during a rebase or cherry-pick, or by an amend, and commits already reviewed. When it cannot decide (in a checkout that belongs to no tenant), it reviews nothing and says why in your terminal. It only reviews: it never edits or commits.
4. **The review comes back.** When the review service finds something, it posts a message in the PR's channel with the findings and an `arc submit --pr <N> --fix-answers -` command to fill in (`arc submit` refuses `--fix-answers` without `--pr`). A Claude Code session gets the message at its next stop, or is woken by it.
5. **Answer the findings.** Either:
   - let your agent fix them, push, and answer each finding with `arc submit --pr <N> --fix-answers -` (JSON on stdin: `fixed` with what changed, or `wontfix` with the reason); or
   - run `arc local-review` and then `arc fix`, to have the Fixer fix what the review on this machine found. The Fixer makes the fixes one after another in your working tree, each one a commit on your branch on top of the one before. Its answers are recorded on the new head, which is reviewed again on this machine, round after round, until the reviewer says LGTM or has used its `[review] max_rounds` turns. The working tree must match HEAD first (commit, stash or ignore everything, untracked files included). `git reset --hard refs/arc/before-fix/<branch>` undoes the whole run. Then send the new head to review as an update of the PR:

     ```bash
     git log --oneline -3                   # the fixes, on your branch
     arc submit --pr <N>                    # pushes; the review service reviews the new head
     ```
6. **Landing.** Once every reviewer says LGTM, the review service grants the pass and the merge server lands the PR. To keep it from landing, add the label `arc-hold`.

Every command takes `--json` and then prints one machine-readable result. Have your agent read that instead of the human text.

---

*Next: [The commands](commands.md) · [Configuration](configuration.md) · [Troubleshooting](troubleshooting.md).*
