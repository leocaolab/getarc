# Working on the board

The web board (`arc-web`) is where people look at the work and make decisions. Agents do the work itself. You put a plan on the board as milestones and issues, an agent works through one milestone, and when it needs a decision you answer with one click. Every PR's review, merge and release show up on the same board.

To open it, take the address in `~/.arc/client.toml` (on the pipeline machine, `arc-server tenant url web` prints it), open it in a browser and pick the repo.

## The pages

| Page | What it shows | What you do there |
|---|---|---|
| **Projects** | Every milestone (active, idle, done) and the questions waiting for you | Answer a question: click one of its options, or write your own answer |
| A milestone | Its issues, by status or as a tree. A blocked issue shows the question it is waiting on | Read; open an issue |
| **Issues** | The whole board, filtered and grouped, with the open issue beside it | Open an issue; comment (an `@agent` you name gets the comment) |
| Report | Open, overdue, due soon, age, and this week's flow, by priority, kind, assignee or milestone | Pick what to group by and which milestone |
| **Review** | Changes that need you, changes agents are working on, and history: who has each change, its size, how long it waited, how many rounds | Open a change |
| A change (PR) | Overview, files, activity, why it is waiting, each reviewer's findings | Click **LGTM** or **Fix again** when it waits for a person; answer a finding "fixed" or "won't fix" |
| **Merge** | The queue (who is waiting, when each turn comes, who is held) and every attempt to land each change, failures in red | Read |
| **Release** | The nightly, versions, deploy targets, and what landed since the last release | Click **Deploy**, when this machine can deploy |
| Rot, Usage | How structural rot is trending; what agents used and what it cost | Filter; download CSV |

Pages update by themselves. You do not need to reload to see a change land.

To find out where one piece of work stands, ask the progress address. Give it an issue, a PR number or a branch. For each PR it answers with a stage (in review, waiting on the author, queued, held, gate red, landed…) and where to look next:

```bash
curl "$(sed -n 's/^web *= *"\(.*\)"/\1/p' ~/.arc/client.toml)/api/r/<owner>/<name>/progress/b/<n>"
```

## From a plan to landed work

1. **Write the plan as a document.** A Markdown roadmap: milestones in order, each one small, each with what proves it is done.
2. **Put it on the board.** `arc issues candidates --doc roadmap.md` lists the document's blocks, each with an id. Write a proposal that cites those ids. `arc issues plan proposal.json --doc roadmap.md` shows what filing it would do, and refuses anything the document does not say and anything the proposal leaves out. `arc issues apply proposal.json --doc roadmap.md --role reporter` files it — all of it, or nothing. To open a single issue: `arc issues open --kind task --parent b/<milestone> "<title>"`.
3. **Start a loop.** In the agent's session, run `arc issues loop start b/<milestone> --until drained --role assignee` (or `--until fixed:<n>`). Each time the session stops, the loop gives it the next issue. `arc issues loop stop b/<milestone>` ends the loop; `arc issues show b/<milestone>` shows how far it got.
4. **The agent works each issue.** It makes a branch, writes the change and submits it with the issue number in the PR title (`b/<n>: …`), so the submission is recorded on the issue. It marks the issue `fixed` after the PR has landed, not before.
5. **When it needs a person, it asks on the board.** `arc issues block b/<n> --said "<question, with the background>" --option "A: …" --option "B: …"` opens a question (`q/<n>`). The question shows on Projects with one button per option. A click answers it, and the answer is sent to the agent's session. Only a person can rule: `arc issues rule` refuses an agent.
6. **Follow a PR.** Its page is on Review; its place in the queue is on Merge. When the PR lands, the session that submitted it gets a message saying so.
7. **Clean up.** Report shows what is old and overdue. End an issue with `fixed`, `wont-fix` (with the reason) or `duplicate --of b/<n>`. There is no plain "close".

A second Claude session can supervise the agent's session: it looks at each stop and decides the small questions itself ([the supervisor](bridge.md#the-supervisor-optional-claude-code)).

## What works well

- **Keep the queue full; don't wait on yourself.** Agents submit as soon as a change is ready. A person checks in when they have time, not on every PR.
- **Ask once, and ask completely.** A question carries its background, the options with their pros and cons, and a recommendation, so one click settles it. A question asked only in chat gets lost: put it on the board.
- **Keep issues small.** One issue is about an hour of one agent's work. Split a bigger one before anyone starts on it.
- **People decide, agents act.** The board's buttons are for decisions (answer, LGTM, deploy), not for running tools. If something has to be done, an agent does it.
- **Don't watch a PR.** The message that it landed, or that it was sent back, arrives in the session by itself. Polling the PR only spends tokens.
- **The board is the record.** Write issues with `arc issues`. GitHub's issues are a copy; edits made there are not read back.
- **Deploying is a person's call.** Deploy from Release when you mean to.

## Keeping a PR from landing: `arc-hold`

Add the label `arc-hold` to a PR and the merge queue skips it:

```bash
gh pr edit <n> --add-label arc-hold      # hold it
gh pr edit <n> --remove-label arc-hold   # let it go
```

- **What it stops:** landing, and nothing else. The PR is still reviewed and can still get its reviewers' LGTM. The merge machine checks the label again just before it pushes, so a hold added at the last moment still counts.
- **Removing it:** the PR goes back into the queue. If its LGTM is for its current head commit, it lands without another review.
- **On the board:** Merge shows the PR as "held by its author". You add and remove the label on GitHub; the board does not change labels.
- **Once per repo:** create the label with `gh label create arc-hold`.

Hold a PR when:

- you have doubts about the change and want to look again before it lands;
- the PR has a known problem and the fix is still coming — the queue can be faster than your next push;
- a person must see it first.

Don't hold a PR when:

- it only needs another PR to land first. Submit it with `--after <N>` instead, and it lands after that one;
- it is documentation. Let it go through review and land.

Don't confuse it with:

- **"Held" on the Review page.** That is a change waiting for a person to decide (LGTM or fix again), not this label.
- **`arc-bypass`.** `arc submit --bypass-review` adds this label, and your review routes send such a PR to the dummy reviewer, which approves everything. That skips the real review; use it only when you mean to.
