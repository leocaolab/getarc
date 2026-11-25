# Best practices: how we build arc with arc

arc is built with arc. This page walks through how we actually work, with real examples from arc's own board: what we said to the agent at each step, what came out, and what went wrong when we skipped a step. Do it the same way in your repo.

You never need to type a slash command. Every step below started with one plain sentence to a coding agent; the agent loaded the right skill by itself.

## 1. Day one: let every PR through, then turn on real review

Start with every PR routed to the **dummy reviewer**: it runs no model and says LGTM to everything. Only your merge check (`merge.yml`) can send a PR back. This gets the whole pipeline working end to end (submit, queue, merge, release) before you spend tokens on review.

```toml machine.toml#tenant
[[tenant.review.route]]
reviewer = "dummy"
name     = "dummy"
```

Then switch to a real reviewer when the pipeline runs smoothly and you can afford the tokens:

```toml machine.toml#tenant
[[tenant.review.route]]
reviewer = "react"
name     = "react"
```

**What we did.** On Oct 10 we turned the model reviewer off to save tokens and ran on the dummy alone; the merge check was the only thing that could send a PR back. On Nov 11 we said "we skipped review because of tokens; now there are enough, so go through review", and on Nov 12 we moved the reviewer's model to Sonnet. From then on the reviewer's findings started real follow-up PRs. Keep `arc-bypass` (a label that routes one PR to the dummy) for the rare PR that truly needs no review. More: [Review on the pipeline](pipeline-review.md).

## 2. Check the whole repo once, then let agents fix it

Before building new things on an existing codebase, find what is already wrong, put it on the board, and let agents fix it in parallel.

> Run `arc rot` on the whole repo and put what it finds on the board, one issue per problem.

The agent runs `arc rot` (structural rot across files) and `arc local-review` (each file against its contracts), groups what they find, and opens issues. Then one agent per group of issues fixes them, one PR per fix.

**What we did.** On Nov 9 we had every crate group of arc checked at once: one read-only agent per group, each against the same rules. They found 15 blocking problems and about 600 smaller ones, all written to one ledger with file and line. The 15 became issues b/2956–b/2970 under milestone b/2955, and were all fixed the same day, by agents on three machines; the ledger shows 371 findings closed by 30 PRs. What is left stays as open issues, not as a to-do in someone's head.

## 3. From an idea to issues on the board

Big work goes through five stations. Each one leaves a file in the repo or issues on the board, so nothing depends on a chat that will be forgotten.

| Station | What you say (our real words) | Skill | What comes out |
|---|---|---|---|
| Brainstorm | "Look at our bridge design. What does it lack compared to a mature chat server?" (with the problems pasted) | `brainstorm` | a record of the discussion: directions, pros and cons, the decision |
| Design | "Start the design, then find another agent to attack it. Data first, then auth, then channels." | `design` | `gateway-design.md` |
| Implementation plan | "Don't ask me, I know nothing about this. Borrow from how the big chat services are designed." | `impl-design` | `gateway-impl.md`: each step mapped to files and functions, audited |
| Roadmap | "Build it as two projects: data schema first, then the features, auth last. Then split it across many agents." | `impl-roadmap` | `gateway-roadmap.md`: milestones, 79 tasks, each one agent, under an hour |
| Board | (same sentence) | `sync-roadmap` | milestones b/3179 and b/3180 with their issues, each issue citing the line of the roadmap it came from |

**What we did.** This is the bridge gateway, Nov 15–18. The design was written on Nov 16 at 17:31 and on the board by 20:23 the same evening. Agents started on the first issues at 20:31.

Two things we learned on the way:

- **A prototype still goes through every station.** On Nov 15 we tried to skip straight to a demo; the result had to be rewritten twice ("Go back and look at why we are doing this"). The gate can be light for a prototype; the stations cannot be skipped.
- **When you don't know, say so and let the agent borrow.** "I know nothing about this; borrow from the big chat services" settled most technical questions without a meeting.

## 4. One agent designs, another attacks

The agent that wrote something never reviews it. Ask for a second agent whose only job is to find what is wrong.

> Start the design, then find another agent to attack it.

**What we did.** The gateway design got two rounds of attack: 9 blocking problems in the first, 4 in the second, all answered in the design itself; then we stopped. The implementation plan got two independent audits before any code. After the code was written, every report came from an agent that had not written that code, and each fix batch was checked again by a fresh agent that saw only the diff and the rules.

Stop after two rounds. More rounds stop finding real problems and start finding taste.

## 5. Work a milestone in a loop, and supervise it

Agents are good at doing one issue. Left alone on a big job, they chase rabbits: they widen the scope, re-check things that are already fine, or stop halfway. Two tools keep them on the board's issues.

**The loop.** In the agent's session:

```bash
arc issues loop start b/<milestone> --until drained --role assignee
```

Each time the session stops, the loop hands it the next issue of the milestone, until none is left. Our cleanest run: milestone b/2573 (nine issues for `arc archcheck`). Once the loop started, nobody said a word to that session, and all nine issues had landed, in 21 PRs, less than five hours later.

**The supervisor.** A second session reads each stop of the working session and decides: still moving, let it go; stuck on a small question, answer it; a real decision, ask a person on the board. Load the `supervisor` skill in that second session. [How to set it up](bridge.md#the-supervisor-optional-claude-code).

**Where agents went off track, and the rule that came out of it:**

| What happened | What we said | The rule now |
|---|---|---|
| Four agents spent two hours polling GitHub for merge results | "Why poll? These hours burn tokens." | An agent's job ends at `arc submit`. The result comes to the session that sent it. |
| An agent acted on the supervisor's summary of a conversation and built the wrong thing (58 files thrown away) | "Just paste the conversation and it won't go wrong." | Briefs carry the original words, not a summary. |
| A review kept spawning more re-checks that never converged | "Are you drifting?" | After two rounds, the rest becomes issues on the board. |
| The opposite: review started before everything was built | "Don't rush to review; finish every missing feature first." | Check the build against the original list of problems before review. |
| A flow was patched again and again around one failing agent | "Let the agent fit the flow, not a pile of patches." | Fix the participant, not the flow. |

## 6. Talk through the bridge, not through a person

Agents, services and people talk over arc's chat server. What you see in a session:

- **The reviewer, when findings are waiting:** `review of 7d807b0: 6 open findings have no answer from you on #4566. Answer every one from this session with one arc submit --fix-answers …`
- **The merge server, when a PR lands:** `fix/b1947-nextest-timeout landed as ad82e56b79bd`
- **The loop, with the next issue:** `loop b/1680: progress 0/1; next b/1877 … (assigned to you)`
- **One session to another, before taking over its work:** `taking over #4461 (b/3069): … please stop the agent you sent on #4461`
- **An agent that needs a person** opens a question on the board (`arc issues block b/<n> --said "…" --option "A: …" --option "B: …"`); a person clicks an answer, and it arrives in the agent's session.

Nobody has to watch a PR or relay a message. More: [Team up](bridge.md).

---

*Next: [Skills and plugins](skills.md) · [Working on the board](working-on-the-board.md) · [Team up](bridge.md).*
