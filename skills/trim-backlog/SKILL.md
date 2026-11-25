---
name: trim-backlog
description: Reconcile the issue board against main — take a milestone (or a pasted stretch of the board), check every open issue's premise in the code and history, sort each into done / premise gone / owned elsewhere / really open with evidence, show the maintainer one table, write ONLY what they named, then read the board back. The reverse of `arc-skills:sync-roadmap` (document → board); this is board → main. Use when asked 看看还有什么没完成, 核一遍还有没有必要留着, 清 backlog, 关掉做完的, 这个 milestone 还剩什么, or when a board paste shows long-idle issues ("nobody on it", "5d").
version: 0.1.0
---

# trim-backlog

An open issue is a claim that some work is still owed. Over weeks the claim goes
stale three ways: the work landed under another name, the thing it talks about was
deleted, or a later ruling made it moot. This skill re-checks each claim against
main and closes what no longer holds — with evidence a later reader can re-check,
so nobody investigates it twice.

| | What | Who |
|---|---|---|
| 1 | take the issues, bodies included | command |
| 2 | check every premise against main; sort into four | you |
| 3 | measure what reading cannot settle | an agent |
| 4 | one table; the maintainer names what to do | maintainer |
| 5 | write exactly what was named, then read back | command, then you |

## 1. Take

```
arc issues list --under b/<milestone> --json     # bodies, status, labels, parent
arc issues show b/<n> --json                     # one issue with its timeline
arc issues list --label milestone                # sibling milestones: is the work owned elsewhere?
```

A board paste from the maintainer names the milestone; map it to its handle with
`arc issues list | grep`. Read the WHOLE body — the file paths, endpoints, design
docs and verbs it names are the premises you are about to check.

## 2. Check against main (you)

`git fetch` first, then check on `origin/main`, never the shared working tree
(another session's uncommitted deletions show up there).

For every premise the body names:

- a file / doc: `git ls-tree -r --name-only origin/main | grep`; gone ⇒ find who
  removed it and why: `git log origin/main --diff-filter=D -1 -- <path>`
- a symbol / endpoint / table: `git grep -n <it> origin/main`
- a verb: `arc <verb> --help` (the source of truth for what exists)
- a capability under another name: `git log origin/main --grep=<b/n or #n or keyword>`
  and `-S'<string>'`

Then put each issue in exactly one bucket:

| Bucket | Means | Board verb |
|---|---|---|
| **done** | main does what the issue asked, maybe in another shape | `fixed` |
| **mostly done** | the core landed; a leftover is deferred | `fixed` + `open` a P3 leftover |
| **premise gone** | what it would change no longer exists, or a later ruling voids it | `wont-fix --why obsolete` |
| **owned elsewhere** | another open issue carries the same work | `duplicate --of b/<n>` |
| **really open** | nothing on main does it | keep (or P3 = backlog) |

Rules that make the sort honest:

1. **A later ruling overrides the issue's text.** Memory, CLAUDE.md, a design doc's
   decision line, a maintainer quote in a commit — if the ruling came after the
   issue, the issue is judged by it.
2. **Mostly done ⇒ close the original, the rest goes to backlog.** Don't keep an
   issue open for its leftover, and don't close it as if the leftover never existed:
   `fixed` the original (evidence for the half that landed), and `open` a new P3
   issue for exactly the leftover, naming the original in its body. A leftover that
   was *measured* not to work is not backlog — it is the `wont-fix --why infeasible`
   reason, with the numbers.
3. **Say what you did NOT verify.** "A page exists" is not "the page shows Codex
   sessions". Unverified goes in the table as unverified, never as done.
4. **Evidence is a sha or a `file:line` on origin/main**, not "I believe it landed".
5. **A milestone whose children all close is itself closable** — propose it; its
   done/wont-fix follows the children.

## 3. Measure what reading cannot settle (an agent)

When the question is "does this idea even work" (a heuristic, a compression, a
precision claim), do not close or keep it on intuition. Dispatch a read-only
agent with: the exact rule from the issue's source doc, the real corpus, a sample
size, a manual spot-check of false positives, a dumb baseline to compare against,
and "every number says what it covers". Its numbers go into the close reason.

## 4. One table (maintainer)

One row per issue: handle · title · what main has (evidence) · bucket · proposed
verb. Put the calls only they can make (keep vs drop a half, which of two
rulings) as explicit questions under the table.

**Write only what they named.** "都关掉" after a table covers that table; "87, 59
关掉" covers 87 and 59 and nothing else — ask about the rest. Never apply your own
recommendation to an item they did not mention.

## 5. Write, then read back

```
arc issues fixed      b/<n> --role reporter --said "<their words> <evidence>"
arc issues wont-fix   b/<n> --why obsolete|infeasible|intended_behavior|not_reproducible --role reporter --said "…"
arc issues duplicate  b/<n> --of b/<m> --role reporter --said "…"
arc issues unlabel b/<n> P2 --role reporter && arc issues label b/<n> P3 --role reporter   # backlog = P3
arc issues open --kind task --priority P3 --role reporter "<title>" --body "leftover of b/<n>: …"
```

- `--role reporter`: you write on their instruction; `human` would be a false claim
  (the writer identity is resolved by arc from the session anyway).
- `--said` = **their verbatim words + your evidence** (sha, `file:line`, measured
  numbers). This is the negative result the next reader relies on.
- Then `arc issues list --under b/<milestone>` and compare with the table.
  A write GitHub did not take: `arc issues mirror`.

## Handoff

- Write issues only with `arc issues`, never `gh issue …`.
- Report per issue: the verb written and the one-line reason; then what is still
  open on the milestones you touched.
- Do not edit the design docs you found stale (a "status: Y0 在建" header, a
  deleted doc still linked) in the same pass — list them for the maintainer.
