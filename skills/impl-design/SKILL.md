---
name: impl-design
description: Three steps between a design doc and code — (1) freely write each CUJ's implementation as readable prose, (2) map every step onto files/functions with evidence-producing actions, (3) gate through a fresh adversarial rubric audit whose findings drive amendments — at most 2 rounds; blocking findings still open after round 2 go to the maintainer as open questions. Discipline lives in the gate, not in writer compliance.
---

# Impl Design (实现设计 — 三步)

Baked-in lesson (measured by A/B experiment): **methods that command actions get followed; methods that command
virtues get skipped; the only reliable discipline is the gate.** So: two action steps,
one gate. No virtue clauses.

## 第一步 — 自由写每个 CUJ 的实现

For each CUJ in the design doc (derive them first if the doc doesn't name them, and say
so): write, freely, how the journey runs — trigger → what happens, step by step → outcome.
Narrative prose a maintainer can read in one pass. No tables, no citation duty yet — this
is the creative pass; get the mechanism right and legible.

## 第二步 — 映射到文件/函数

For every step of every CUJ walkthrough, one mapping row: `CUJ 步骤 → 文件/函数`.

- **EXISTING**: cite `file:line` — and the action behind it: Read the cited lines AND the
  surrounding function before citing. (Both A/B audits' failures clustered in claims that
  needed reading *past* the cited line.)
- **NEW**: name + exact signature + home (crate/module), plus two actions before NEW may
  stand:
  1. run the search for an existing equivalent and **paste what you searched** into the
     row (the grep/glob, not a promise);
  2. sweep the design corpus — a COMMAND, not a virtue: every directory design docs live in
     (find them: `grep -rl -i -E '设计|design' docs --include=*.md | xargs -n1 dirname | sort -u`),
     grep the feature's nouns/verbs
     across all of them; **paste the command + hits** into the doc. A sibling
     design found = reconcile it with per-item disposition lines (adopt / replace / defer),
     absorbed **by reading its body**, never by symbol name.
  An **empty search result means "haven't found the layer yet", never "doesn't exist"** —
  locate the real surface (e.g. the actual CLI args file) before concluding.
- **Every row — the contract column (放置契约)**: paste the target module's README
  placement-contract line (`Belongs here:` / `Does NOT belong:`) that admits this row.
  No README for that module → write `无契约` (itself a finding for the gate). Cannot find
  an admitting line → the row is a placement conflict, flag it — do not place by
  peer-analogy alone (a mis-placed neighbor propagates through analogy).

- **Every NEW row that stores or ships something** (schema / migration, event kind, enum
  value on the wire or in a db, config key, a file a running service reads): one line on how
  the **running old binary** reads it during the deploy, and how the new binary reads the old
  data after a rollback. A rename or a removal ships in two deploys — say which half this row is.
- **Every NEW behaviour row**: name the test that proves it, and the inputs on both sides of
  its boundary (just inside → green, just outside → red) fed straight to the decision as a
  pure function. Never "what to break in production code so the test goes red" — a behaviour
  that can only be shown that way is a decision not yet split out; split it.
- **Every NEW name (type, variant, function, module, setting key)**: judged against the
  naming rubric HERE, not at submit — the `type-naming` skill, `${CLAUDE_PLUGIN_ROOT}/rubrics/type_design.yaml`
  (`type_design_python.yaml` / `type_design_typescript.yaml` for those languages), plus the
  project's own name checker rules if it has any. Paste per name: what it IS in the domain
  (a noun for a thing; state goes on an enum variant; no participle / -ing, no usage-site
  modifier, no mechanism or format words), its owner, and that no existing type already
  models the same fact. Code then uses these names verbatim, so the submit-time check finds
  nothing new.

The step-1 prose stays the document's body; this mapping is its anchor. No other tables.

## 第三步 — rubric 检验 + 修改(门,唯一的纪律居所)

Dispatch a **fresh adversarial auditor** (never the writer). **The dispatch is assembled
from the checklist below — never hand-written from memory** (measured failure: the author
forgot the rubric in a hand-written dispatch the same day the skill was written). Before
sending, verify the dispatch contains ALL of:

1. the plugged rubric paths (the project's rubric if present; else the rubrics this plugin
   ships in `${CLAUDE_PLUGIN_ROOT}/rubrics/` — at least `l4_contracts.yaml`,
   `l5_architecture.yaml`, `structural.yaml` and the `type_design*.yaml` for the language);
2. re-verify every `file:line`, **reading past the cited line**;
3. proof-of-absence re-run for every NEW item (search, report what was searched);
4. 重复定义/重复发明 hunted explicitly and **counted separately**;
5. design-corpus sibling sweep (every design directory, not only `docs/design/`) — anything unreconciled = finding;
6. **mapping-row vs README-contract check**: each row's pasted contract line actually
   admits it (and `无契约` rows reported);
7. unenforced claims, contract/shape changes, internal contradictions (prose vs tables —
   amendments must have propagated to every surface);
8. **decided items stand**: an amendment that would reverse anything the design doc lists as
   *decided* (the owner's words) is not made — it is escalated as an open question;
9. **old binary × new data**: every row that stores or ships something has its deploy /
   rollback line, and it holds;
10. **every NEW name passes the naming rubric** (`type-naming`, `type_design*.yaml` + the
    project's name checker rules): re-judge each pasted name; one the submit-time checker would reject is a
    blocking finding now;
11. responsibility class per finding:
   `method-gap / executor-violation / upstream-inherited / grounding-gap / judgment-call`.

A dispatch missing any item is itself a protocol violation — fix the dispatch, not the
auditor.

Findings drive **amendments to the doc**; re-audit — **at most 2 rounds**. Blocking findings
still open after round 2, and every judgment-call, go to the maintainer as open questions:
written into the doc AND onto the repo's issue board (`arc issues block b/<n> --role assignee --said "<what it is
about in one sentence + the question + your recommendation>" --option "A: …" --option "B: …"`), so they are answerable
without opening this session. Findings **accumulate across rounds (union, never replace)** —
absence-type findings are noisy run-to-run.

## Output

`<feature>-impl.md` = CUJ 实现(第一步) + 映射表(第二步) + 修订记录(第三步各轮的
findings 与处置). **门未过(2 轮内清零 blocking,或剩下的已交维护者并得到回答),不写代码。**

## 下一步(过门之后)

门过了(2 轮内 0 blocking,或剩下的维护者已答) = 设计**真正结束**。此时才轮到 **`impl-roadmap` skill**:照*已定稿*的
设计 + 本 impl-map 排里程碑 + 对齐仓的 issue 板(`arc issues`;GitHub 只是镜像，不直接写)。**绝不在门前排 roadmap** —— 门会改
设计(删组件/反转决策),门前排的里程碑会变成死 work-item(实测踩过)。
流水线:`design → impl-design(门)→ impl-roadmap → 写代码`。
