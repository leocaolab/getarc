---
name: loop-scheduler
description: >-
  Work through a milestone under arc's loop scheduler, as the coordinating session. Start one with
  `arc issues loop start b/<milestone> --until fixed:N|drained --role assignee`; from then on, each time you stop, the
  scheduler (inside arc-bridge) tells you what to do next — the next issue it assigned you, a
  stalled issue, an interrupted turn to carry on, a drained milestone to check against its source,
  or the loop's end. Teaches what to do with each of those messages, how to hand every issue to a
  sub-agent in its own warm worktree, why only a landed `fixed` counts, and that every question
  for a person goes on the board with `arc issues block`, never into chat. Use when asked to "loop"
  a milestone, when your own goal is milestone-sized (start the loop yourself), when reminded that
  you work a milestone with no loop open / 把 b/N 下面修 N 个 / 一直做到 milestone 做完, or when a Stop-hook message starts
  with "loop b/<n>:".
---

# loop-scheduler — work a milestone until it is really done

The loop fixes two pains, and they are yours:

- **Really done, not 80% done.** The loop's count is the server's, from the board: an issue
  counts only when it is `fixed` **and** its PR has `landed`. Saying "done" counts for nothing.
- **No drift.** You work only on issues under the milestone. Anything new you find goes on the
  board under the milestone first (citing the milestone's source), and is worked when the
  scheduler hands it out.

You do not drive the loop. There is no `next`, `claim`, `complete` or `sign-off` verb — the
scheduler assigns, and it is atomic; you just answer what it says. A loop is not a thing of its
own: it is two events on the milestone's timeline (`loop_started` / `loop_ended`), so your verbs
are all the issue board's — `arc issues loop start | stop`, `arc issues show` for progress, and
the rest of `arc issues …`. There is no top-level `loop` command.

## 1. Start

You start a loop yourself — no one starts it for you. Three ways in:

- **The person asks** ("把 b/2500 下面修 10 个", "loop b/2500", "drain b/2500").
- **You decide.** Your goal is milestone-sized: finish a milestone, or several issues under one
  milestone, or you just split a piece of work into a milestone and its issues on the board.
  Start the loop yourself; do not ask whether to. No milestone yet → put one on the board first
  (`arc issues open --kind milestone --role assignee …`, the work as issues under it), then start — a loop
  only runs over a milestone.
- **You are reminded.** A Stop-hook message saying you are working b/N under b/M with no loop
  open: if you mean to see b/M through, start one now; otherwise carry on. It is said once.


```
arc issues loop start b/2500 --until fixed:10 --role assignee   # n issues fixed and landed
arc issues loop start b/2500 --until drained --role assignee    # until nothing under it is left to take
```

- It writes on this checkout's board, like every `arc issues` verb; a milestone on another
  board is started from that repo's checkout (or the global `--repo <path>`). The thresholds
  (`--wip`, `--stall-after`, `--brake-after`, `--retry-after`, `--offline-after`) keep the
  scheduler's usual values unless the person named others.
- It prints the first issue it assigned you — treat it as P1 below. "Nothing to take" means
  the milestone has nothing open and unassigned: go to P4.
- One loop per session: starting again stops your other one. Another session's loop on the
  same milestone stands beside yours (§7, two in a team); the scheduler never hands one issue
  to both — an issue somebody already holds is refused as `taken`, naming the holder.
- `arc issues show b/<milestone>` answers "how far along": it prints one loop line per open
  loop on it (landed, in hand, to take, remaining). Use it instead of reconstructing progress
  from chat. `arc issues loop stop b/<milestone> --role assignee` only when the person says
  stop — it stops your own loop there; your partner's keeps running.

## 2. What the scheduler says, and what you do

Each message starts with `loop b/<milestone>:`. It arrives when you stop (the Stop hook
injects it), or later through your inbox if you stopped idle.

| | It says | You do |
|---|---|---|
| **P1 Next** | `progress k/n; next b/N <title> (assigned to you)` | Do b/N (§3). It is already yours — do not `assign` or `start` it again. |
| **P2 Stalled** | `b/N is in your hands and nothing about it has moved for T minutes` | Pick one, now: carry on (and say what is moving); `arc issues block` it (§4); or `arc issues reject b/N --role assignee --said "<why you will not take it>"` to put it back. |
| **P3 Retry** | `the last turn was interrupted by: <error>; carry on` | Carry on from where the turn died. Re-check what the sub-agent or command was doing; do not restart finished work. |
| **P4 Drained** | `nothing left to take, progress k/n; find what is missing against the source named in b/<m>'s body` | §5. |
| **P5 Done** | `loop b/<m> closed: done …; landed …` | Report (§6) and stop. |
| **P6 Braked** | `loop b/<m> braked: …` | Three wake-ups in a row with no progress; a person has been told. Report (§6) and stop. Do not restart the loop yourself. |

A message from the loop is not a person's go-ahead for anything outside the issue it names.

## 3. Doing an issue: you coordinate, a sub-agent does the work

One long session doing every issue itself costs an order of magnitude more context than a
fresh agent per issue. So you are the **coordinator**:

1. Read b/N (`arc issues show b/N`) and its parent milestone's source, so the brief you write
   is complete. The brief is the sub-agent's whole context.
2. Hand b/N to a **sub-agent** (general-purpose, not a fork). Its prompt carries: the issue
   handle and what "done" means for it; the repo's `CLAUDE.md` rules it must follow and the
   skills to load; that it works in **its own worktree** (reuse an idle one — HEAD detached
   and `git status --porcelain` empty — else a new one beside the repo, never the main
   checkout or a scratchpad); and that it opens the PR with `arc submit`, with
   **`b/N` in the PR title** — the merger records `landed` only on the issues a PR title names.
3. While it works, you are free: stop. With wip 1 the scheduler holds you until something
   happens; the landing letter wakes you.
4. When the sub-agent hands back, read its diff before relaying anything. Not right → send it
   back (or a fresh agent) with the specific gap.
5. When the PR **lands** (the landing letter), mark it:
   `arc issues fixed b/N --role assignee --said "<PR #, what landed>"`. Not before: a fix that
   has not landed is not counted, and marking it early makes the count lie.

Then stop. The scheduler hands you the next one.

## 4. Asking a person: on the board, never in chat — then keep going

**In a milestone team, your partner first** (§7): `arc issues block` on an issue under the
team's milestone is refused until you have asked your partner about it in the team's channel —
a message of yours there naming the issue's handle:

```
arc bridge post room:<hex> "b/N: <the question, with the options you see>"
```

Block it only when your partner cannot decide either; say so in `--said`.

Any question for a person (a ruling, a choice, a permission) goes on the board:

```
arc issues block b/N --role assignee --said "<the question, readable without this chat>" \
  --option "A: … (pros, cons, cost)" --option "B: … (pros, cons, cost)"
```

- A `blocked` issue no longer counts against wip, so the scheduler hands you the next issue at
  your next stop. **Do not wait in chat for the answer.** Asking only in chat is invisible to the
  scheduler; that issue ends up stalled (P2) and the session idles until someone returns.
- You may say the question in chat too, but the board copy is the one that counts.
- When a person rules, the issue goes back to `in_progress` with you; pick it up when it comes
  back to you.
- **A person who answers you in this session** (「同意」, 「选 A」): you cannot `rule` — a session
  is refused there, and so is a `!` command typed into the session. Write their answer down
  yourself, then close the question; the refusal and `block`'s output print both lines with the
  real `q/<n>`:

  ```
  arc issues question answer q/<n> --role assignee --said "<the question> — <their exact words>"
  arc issues question close q/<n> --role assignee --said "<what was decided>"
  ```

  Copy their words verbatim, and the question they answered with them — a bare 「同意」 does not
  say which question it agrees to. Ask them to rule somewhere else only when this is refused.
- **Not your question?** `answer` and `close` are refused, naming who asked. Send that session
  the person's words (`arc bridge send <asker> "q/<n>: <their exact words>"`) and it writes them
  down. If the asker is gone, a person rules on the web board's issue page.

## 5. Drained (P4): check against the source

The milestone has nothing left to take but the goal is not met. Do not declare victory:

1. Read the milestone's body; it names its source (a design doc, a roadmap, a conversation).
2. Compare the source item by item against what landed and what is open under the milestone.
3. For each item missing, open an issue **under the milestone**, citing the source:
   `arc issues open "<title>" --kind task --parent b/<m> --role assignee --body "<what, and: source <doc>§<section>, '<quoted words>'>"`.
   An item you cannot cite is not in scope — it is drift; leave it.
4. If nothing is missing, say why it is complete: `arc issues comment b/<m> --role assignee
   --said "<each source item → the issue that covered it>"`.

Then stop. New issues are handed out by the next P1; if there are none, the loop closes (P5).

## 6. Closing report

At P5 or P6, tell the person in a few lines: what landed (issues and PRs), what is `blocked` and
on which question (`q/<n>`), what was rejected or left, and anything in P4 you judged complete
and why. Facts only, from `arc issues show b/<m>` and the board — not from memory.

## 7. Two of you on one milestone (a team)

A team scoped to a milestone (`arc bridge team open --with <them> --milestone b/<m>`) works it
as two loops, one per party:

- **Each party starts its own loop** on the milestone: `arc issues loop start b/<m> --until drained
  --role assignee`. The two stand side by side; the scheduler hands each of you different
  issues. Do not split the issues by hand and do not `assign` your partner's.
- **Your PR is read by your partner before the review service.** `arc submit` posts the PR number
  and title into every open milestone team you are in, asking your partner to read it and say
  where they stand. When your partner's PR arrives in the channel, read the diff and answer in
  the channel — agreed, or each point to change. This does not replace the review service's
  LGTM, and it does not hold the merge: an objection is for the author to act on.
- **Questions go to your partner first** (§4); only what neither of you can decide goes on the
  board with `arc issues block`.
- **Done is both of you.** When the milestone is drained and landed, each writes `arc bridge team
  agree <room:hex> --said "<your conclusion>"`; the team closes when both have.

## Do not

- Do not call verbs that do not exist (a top-level `loop`, `arc issues loop next / claim / complete
  / status`); do not
  `arc issues assign` issues to yourself to get ahead of the scheduler.
- Do not count an issue done before its PR landed, and do not mark one `fixed` that you did not
  land.
- Do not work an issue that is not under the milestone, however related.
- Do not ask a person anything only in chat while the loop runs.
- In a milestone team, do not block before asking your partner, and do not approve a partner's PR
  in the team as if it were the review service's LGTM.
