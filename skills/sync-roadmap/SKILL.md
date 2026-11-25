---
name: sync-roadmap
description: Put a roadmap document (or a stretch of conversation) onto the issue board as milestones and issues that each carry a criterion (判据) and a verbatim source (出处) — cite the document's blocks by id so nothing can be made up, let `arc issues plan` refuse what is made up or missed, check the rest yourself, `apply`, then read the board back and compare. Use when asked to 把 roadmap / 讨论变成 issues, 铺路线上板, 同步路线到板子, 开一批 issue, 排 milestone 的活, 对账板子, 检查有没有漏 / 有没有跑偏, or when a roadmap changed and the board must follow.
version: 0.3.0
---

# sync-roadmap

The board holds what the work IS. This skill puts a roadmap on it with the two
facts that let anyone check it later — **判据** (how you know an item is done) and
**出处** (who said so, in their words) — and then checks that the board holds what
you meant it to.

Four steps. The CLI verbs are its parts; **you** are the reading and the checking.

| | What | Who |
|---|---|---|
| 1 | get the roadmap: `arc issues candidates --doc`, write a proposal that cites blocks by id | you |
| 2 | `arc issues plan <proposal> --doc <md>` — dry run: made up? missed? | command |
| 3 | check and complete what the command cannot see | you, then the maintainer |
| 4 | `arc issues apply`, then read the board back and compare | command, then you |

## What this guarantees, and what it does not

**Guaranteed by construction (step 2, mechanically):**

- **Nothing is made up.** A source, a criterion, a north star is a list of block
  ids; the tool fills the words in from the document. There is no field to type a
  quote into, so a criterion that is not in the source cannot be written.
- **Nothing is skipped at block level.** Every heading, list item and table row is
  cited exactly once — as a source, a criterion, a north star, or an `unclaimed`
  entry with a reason — or the whole proposal is refused.

**Not guaranteed — steps 3 and 4 are for these:**

- real work waved into `unclaimed` with one sentence of reason;
- a criterion cited under the wrong item;
- one block that holds two pieces of work;
- work stated in a paragraph (prose is never owed a citation — `plan` prints the
  uncited ones);
- whether any of it is written well: a criterion too soft to mean anything, a
  north star that names a mechanism instead of the pain.

**"Every block cited" means you skipped nothing. It does NOT mean you read anything
right.** Never report an empty refusal list as "extracted correctly".

## 1. Get the roadmap (you)

```
arc issues candidates --doc <roadmap.md> --json
```

Every block, with its `id` (`b1`, `b2`, … in document order — the same every run on
the same text), `kind` (`heading` · `list_item` · `table_row` · `paragraph` ·
`code`), `line`, byte `span`, `text`, and `candidate`:

- **candidate = true** (headings, list items, table rows): each must be cited
  **exactly once** somewhere in the proposal, or named in `unclaimed` with a reason.
- **candidate = false** (prose, code): cite them when they hold a criterion or a
  north star — often they do — but you never have to.

Then write ONE JSON file for the whole document — every milestone in it,
optionally all under one `parent`:

```json
{
  "parent": "b/1755",
  "milestones": [
    {
      "milestone": {
        "name": "M2 合并前测试和 CI 读同一份定义",
        "north_star": {"doc": "docs/design.md", "from": ["b7"]},
        "goal": "releaser 不再自己解析一遍 workflow",
        "acceptance": {"from": ["b31"], "run": "just gate-parity"},
        "sources": {"from": ["b12"]}
      },
      "items": [
        {
          "title": "releaser 走 workflow runner",
          "kind": "task",
          "priority": "P1",
          "acceptance": {"from": ["b15"], "run": "cargo test -p arc_build releaser_reads_the_workflow"},
          "sources": {"from": ["b14"]}
        },
        {
          "title": "门的定义只留一份",
          "kind": "task",
          "acceptance": {"from": [{"block": "b17", "text": "门的定义只留一份"}]}
        }
      ]
    }
  ],
  "unclaimed": [
    {"block": "b1", "why": "文档标题"},
    {"block": "b13", "why": "表头"},
    {"block": "b40", "why": "已在 b/1622"}
  ]
}
```

- `{"from": [ids]}` — the blocks whose words are this field's. Several ids = their
  words one per line. `"doc"` = a block of another document (typically the
  design's north star); run `candidates --doc` on that one too. Only the `--doc`
  document is held to coverage; another document is only quoted.
- A **part** of a block: `{"block": "b17", "text": "<words copied verbatim from
  the block's text>"}`. The tool finds them in that block; words not in it, or
  in it more than once, are refused — quote a longer stretch then. The block
  still counts as cited once. There is no byte form.
- `acceptance` with `"run"` is a command; its `from` is the block you read it out
  of — **required**: a command with no block behind it is refused at the file.
  Without `run`, it is a claim in the cited words.
- Every cited block becomes a source of what cites it — a row that states the work
  AND its criterion is cited once, in `acceptance`, and needs no separate `sources`.
- What you still write in your own words is only what LABELS the work: `name`,
  `title`, `body`, `goal`.
- `kind`: `bug` · `test` · `design` · `question` · `feature` · `task`;
  `priority`: `P0`…`P4`, or omit.
- `parent`: a board handle every milestone is filed under; a milestone already on
  the board elsewhere is moved under it. Without one, nothing is moved.

The rules that make this worth doing:

1. **宁可漏,不可编.** No criterion in the source → `"acceptance": null`; no north
   star → `"north_star": null`. `plan` refuses it and says so; the maintainer
   supplies it. **Zero refusals on a real document is a reason to suspect
   yourself.**
2. **`command` over `claim`.** If the source names something runnable, write
   `run` — an exit code cannot be argued with.
3. **The north star names the PAIN, not the mechanism.** 「合并前测试和 CI 是同一份
   定义」is one; 「实现 workflow 解析器」is not — it can be finished while the goal
   is still far away.
4. **`unclaimed` is for what is truly not work** — a title, a table header, a
   non-goal, background, work already on the board (`b/<n>`). Every entry a true
   one-sentence reason. Dumping leftovers there to clear the refusals is exactly
   the silent drop this exists to expose.

**From a conversation** there is no document and so no ids: the maintainer gives
the range ("从今天早上那段起", a session id) or tells you to find it, and the file
holds quotes — `"sources": [{"cite": "session 07c00677 14:29", "quote": "…"}]`,
`"charter": {"north_star": "…", "goal": "…", "acceptance": {"kind": "claim",
"says": "…"}}`, `"acceptance": {"kind": "command", "run": "…"}` — and no
`unclaimed`. Use `--from-conversation` instead of `--doc` in steps 2 and 4.
Nothing is filled in or counted there, and `plan` says coverage was not checked.

## 2. Dry run (command)

```
arc issues plan <proposal.json> --doc <roadmap.md>
```

Writes nothing. Run it in the checkout whose board it is (`--repo <path>` for
another). It prints what would be opened and changed, and **every refusal with the
words behind it and, for the document, the block id and line**:

- filling and coverage: an id the document has not got · a span outside its block
  · a block cited in two places (both named) · a candidate cited nowhere (verbatim);
- the plan's own: no criterion · no source · a milestone with no charter (north
  star, goal or criterion missing) · two items citing the same evidence · an item
  matching more than one issue already on the board · two milestones of one name;
- then the prose / code blocks nothing cited, verbatim.

One refusal anywhere ⇒ `apply` would write nothing, in any milestone.

## 3. Check and complete (you)

The command has told you what is made up or missed. Now do what it cannot:

1. **Every refusal.** A missed block: cite it as work, or name it in `unclaimed`
   with a true reason. A block cited twice: decide which one field it belongs to.
   A missing criterion / north star: if the source has it, cite it; if not, it
   goes to the maintainer — **never soften or invent one to get past the gate**.
2. **Read `unclaimed` again, entry by entry**: is any of it real work dismissed
   with a sentence?
3. **Every criterion**: is it cited under the item it actually judges?
4. **Every block you cited as one item**: does it hold two pieces of work? Split
   with spans, or file both and say so.
5. **The uncited prose `plan` printed**: is work stated there?
6. **Soft criteria, mechanism north stars**: say so.

Fix what you can and re-run step 2 until it is clean. What only the maintainer can
decide — a criterion the source does not state, a north star it does not name, a
judgement call from 2–6 — list for them in a short table (block id, the words, the
question), and change the proposal by their answer.

## 4. Apply, then read back (command, then you)

```
arc issues apply <proposal.json> --doc <roadmap.md> --role reporter
```

The same judgement as `plan`, performed, then pushed to GitHub. Idempotent: the
same file again writes nothing. An item is recognised by what it cites, so a
reworded title updates the issue rather than opening a second one; an issue the
new read no longer cites is **commented, not closed** — "renamed" and "dropped"
look the same from here, and that call is the maintainer's. Who is writing is this
run (resolved by arc), not a flag.

**Do not trust `apply`'s own report.** Read the board back and compare it with the
proposal:

```
arc issues list --under b/<parent> --json     # every milestone and item, its parent, its criterion
                                              # (no parent: --kind milestone, then --under each)
arc issues show b/<n> --json                  # one issue: criterion / charter, and its sources verbatim
```

Check, for every milestone and item of the proposal:

- it is on the board, and a milestone is under the `parent`, an item under its milestone;
- its criterion (`declares`) and every source (`sources[].quote`) are word for word
  what `plan` filled in from the cited blocks;
- the milestone's north star and goal are there;
- `apply` reported nothing owed to GitHub (else run `arc issues mirror`).

Any mismatch → report it to the maintainer as it is (the proposal's words beside
the board's) and **do not say it is done**.

## Handoff

- The board is the source of truth; GitHub is its mirror. Write issues with
  `arc issues`, never `gh issue …`.
- **Do not rewrite the roadmap** to link the issues and commit that. The board
  holds the words; revising the document is a person's call.
- Keep the proposal file beside the milestone's docs if it should be re-runnable,
  or in the scratchpad if it was one-off. When the roadmap changes, re-run
  `candidates` first — ids follow the text, so an edited document numbers its
  blocks anew.
