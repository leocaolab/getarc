---
name: dev-velocity
description: Answer how fast a repo's development moves, from the numbers arc's pipeline already keeps — PRs landed per week, merge attempts, landed on the first try, time from opening a PR to landing it, review rounds, issues opened and fixed, time to fix. Reads arc-web's velocity endpoint for the repo and answers the question asked, with the week-by-week table when it helps. Use when asked "how fast are we shipping", "dev velocity", "dev metrics", "how long does a PR take", "how often does the merge check pass first time", "are we keeping up with issues", 我们开发速度怎么样, 每周落地多少, 一个 PR 要多久. Read-only.
allowed-tools: "Bash Read"
version: 0.1.0
---

# dev-velocity

arc writes nothing extra for these numbers. Every one is counted from records the pipeline
keeps for its own work: the merge queue's attempts, the review service's rounds, the issue
board. One request gives all of them, and the answer explains its own fields.

## 1. Find the repo and the pipeline

- The pipeline's web address: `web = "…"` in `~/.arc/client.toml`. No file, or no `web` →
  say this machine is not connected to a pipeline ([Install](../../docs/install.md)) and stop.
- The repo as `owner/name`: from `git remote get-url origin` in the repo the person means
  (`git@github.com:acme/api.git` → `acme/api`). If they named another repo, use that.

## 2. Read

```bash
curl -sS --max-time 30 "$WEB/api/r/$OWNER/$NAME/velocity"
```

- **404** → the pipeline serves no repo by that name. Say so with the name you asked for; do
  not guess another.
- **Cannot connect** → bring back curl's own error. Do not answer from memory or old numbers.

## 3. Read the answer by its own definitions

The answer carries `definitions`: one sentence per field. Read them before you interpret a
number; do not restate them from this page. What matters most:

- **Three sources, each on its own**: `merges`, `reviews`, `issues`. `state: "unread"` means
  that source failed; its `error` is the failure in its own words. Say which source is
  missing and quote the error; answer from the others.
- **A missing week is no record, not zero.** `weeks` starts at the week of the source's
  `first_at`. Before it the source has no record; say that, never "0".
- **`samples` of `of`**: a median or p90 is over `samples` rows; `of − samples` rows gave
  none. When they differ, say how many.
- **Tries, not attempts**: `merges.weeks[].attempts` counts every merge attempt;
  `tries_of_landed / landed` is tries per landed change and leaves out attempts that said
  nothing about the change (a machine failure, an expired credential, a moved target).
- `after_now` / `before_axis` count rows set aside because their dates are impossible. If
  either is above zero, mention it.
- Times are in `ms` (`unit`): show hours for PR lead time, days for time to fix.

## 4. Answer the question asked

| They ask | Answer with |
|---|---|
| how fast are we shipping, week by week | a table, newest week first: landed, attempts, landed first try (as a share of landed), issues opened, issues fixed, critique rounds; then the overall line |
| how long does a PR take | `merges.open_to_land` median and p90, in hours, with `samples` of `of` |
| how often does the merge check pass first time | `landed_first_try / landed`, and `tries_of_landed / landed` |
| how much review is happening | `reviews.weeks[].critique_rounds`; `critiques_per_pr` median and p90; `prs_in_review_without_critique` of `prs_in_review` |
| are we keeping up with issues | `issues.weeks[]` opened vs fixed; `open_to_fixed` median and p90, in days |

Say where it came from in one line: the pipeline address, the repo, `as_of`. If a number
looks surprising, say what record it is counted from (the definition) rather than
explaining it away. The same numbers are on arc-web, **Metrics → Velocity**.
