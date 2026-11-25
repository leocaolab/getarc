# Working on the board

The web board (`arc-web`) is where people look and decide. The agents do the work. A plan goes onto the board as milestones and issues, an agent works through a milestone, and a person answers its questions with one click. Every PR's review, merge and release show up on the same pages.

The board's address is the one line in `~/.arc/client.toml` (`arc-server tenant url web` prints it on the pipeline machine). Open it in a browser and pick the repo.

## The pages

| Page | What it shows | What you do there |
|---|---|---|
| **Projects** | Every milestone (active, idle, done) and the questions waiting on you | Answer a question: one button per option, or write your own answer |
| A milestone | Its issues by status or as a tree. A blocked issue shows the question it is stuck on | Read; open an issue |
| **Issues** | The whole board, filtered and grouped, beside the open issue | Open an issue; comment (an `@agent` you name gets it) |
| Report | Open, overdue, due soon, how old, and the week's flow, by priority, kind, assignee or milestone | Pick the axis and the milestone |
| **Review** | What needs you, what agents are working through, and history: who holds each change, its size, wait and rounds | Open a change |
| A change (PR) | Overview, files, activity, why it waits, each reviewer's findings | **LGTM** or **Fix again** when it waits on a person; answer a finding "fixed" or "won't fix" |
| **Merge** | The queue (who waits, when their turn comes, who is held) and every change's attempts, failures in red | Read |
| **Release** | The nightly, versions, deploy targets, and what landed since the last release | **Deploy**, when this machine can deploy |
| Rot, Usage | The structural-rot trend; agent usage and cost | Filter; download CSV |

A page updates by itself. You never reload to see a change land.

To ask the board where one piece of work stands, use the progress address. It takes an issue, a PR number or a branch and answers with one stage per PR (in review, waiting on the author, queued, held, gate red, landed…) and where to look next:

```bash
curl "$(sed -n 's/^web *= *"\(.*\)"/\1/p' ~/.arc/client.toml)/api/r/<owner>/<name>/progress/b/<n>"
```

## From a plan to landed work

1. **Write the plan as a document.** A roadmap in Markdown: milestones in order, each small, each with what proves it done.
2. **Put it on the board.** `arc issues candidates --doc roadmap.md` lists the document's blocks with an id each. Write a proposal that cites them, then `arc issues plan proposal.json --doc roadmap.md` shows what filing it would do and refuses anything the document does not say or anything it leaves out. `arc issues apply proposal.json --doc roadmap.md --role reporter` files it: all of it or nothing. One issue at a time: `arc issues open --kind task --parent b/<milestone> "<title>"`.
3. **Start a loop.** In the agent's session: `arc issues loop start b/<milestone> --until drained --role assignee` (or `--until fixed:<n>`). Each time the session stops, the loop hands it the next issue. `arc issues loop stop b/<milestone>` ends it; `arc issues show b/<milestone>` shows how far it got.
4. **The agent works each issue.** It branches, writes, and submits with the handle in the PR title (`b/<n>: …`), so the submission is recorded on the issue. It marks the issue `fixed` once the PR has landed, not before.
5. **When it needs a person, it asks on the board.** `arc issues block b/<n> --said "<question, with the background>" --option "A: …" --option "B: …"` opens a question (`q/<n>`). It shows on Projects with a button per option. A click answers it and the answer reaches the agent's session. Only a person rules: `arc issues rule` refuses an agent.
6. **Follow a PR.** The PR's page on Review; the queue on Merge. When a PR lands, a landing letter reaches the session that submitted it.
7. **Trim.** Report shows what is old and overdue. End issues with `fixed`, `wont-fix` (with the reason) or `duplicate --of b/<n>`. There is no plain "close".

A second Claude session can supervise the agent's session: it judges each stop and decides the small questions itself ([the supervisor](bridge.md#the-supervisor-optional-claude-code)).

## What works well

- **Keep the queue full, and don't wait on yourself.** Agents submit as soon as a change is ready. A person checks in when they can, not on every PR.
- **Ask once, completely.** A question carries its background, the options with their pros and cons, and a recommendation, so one click settles it. A question asked only in chat is lost: put it on the board.
- **Small issues.** Each issue is one agent's work in an hour or so. A bigger one is split before anyone starts it.
- **People decide, agents act.** The board has buttons for decisions (answer, LGTM, deploy), not for running tools. If something has to be done, an agent does it.
- **Don't watch a PR.** The landing letter or a bounce arrives in the session by itself. Polling the PR only spends tokens.
- **The board is the record.** Write issues with `arc issues`. GitHub's issues are a mirror; edits there are not read back.
- **A deploy is a person's call.** Deploy from Release when you mean to.

## Keeping a PR from landing: `arc-hold`

Label the PR `arc-hold` and the merge queue skips it:

```bash
gh pr edit <n> --add-label arc-hold      # hold it
gh pr edit <n> --remove-label arc-hold   # let it go
```

- **What it stops:** landing, and only landing. The PR is still reviewed and can still get its reviewers' LGTM. The merge machine reads the label again just before it pushes, so a hold put on at the last moment still counts.
- **Taking it off:** the PR goes back into the queue. If its LGTM is for its current head, it lands without another review.
- **On the board:** Merge shows the PR as "held by its author". You set and clear the label on GitHub; the board does not change labels.
- **Once per repo:** `gh label create arc-hold`.

When to hold:

- You doubt the change and want to look again before it lands.
- The PR has a known problem and the fix is still on its way. The queue can be faster than your next push.
- A person must see it first.

When not to hold:

- It only waits for another PR to land. Submit it with `--after <N>` instead, and it lands after that one.
- Documentation. Let it go through review and land.

Not to be confused with:

- **"Held" on the Review page.** That is a change waiting for a person's decision (LGTM or fix again), not this label.
- **`arc-bypass`.** `arc submit --bypass-review` adds it, and your routes hand such a PR to the dummy reviewer, which says LGTM to it. That skips the real review; use it only when you mean to.
