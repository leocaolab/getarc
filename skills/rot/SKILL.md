---
name: rot
description: >-
  Work through A.R.C. (arc) structural-rot findings — god-modules, cross-file
  clones, duplicated types, repeated idioms. Use when the user says "fix the
  rot" / "handle the rot findings" / "arc rot" after a whole-repo structural
  review. These are multi-file REFACTORS (not point fixes): read the whole
  picture, refactor holistically, gate hard, re-detect. This EDITS code and
  commits — confirm before committing.
allowed-tools: "Bash Read Edit Write"
---

# arc rot — handle structural-rot findings

Rot findings are **structural refactors** (extract-helper, split-god-module,
unify-duplicated-type, extract-trait), not L4 point fixes. Each is a
multi-file *design* change. So: **concurrency 1, sequential, on `main` or one
persistent worktree** — structural changes conflict badly in parallel. Drive
them as a full-context agent (you), not the per-finding `arc fix` pipeline.

## 1. Read the suggestions
```bash
arc rot                      # deterministic detection + the L5 judge (critic_l5) on every suspect
arc rot --file <path>        # scope the cost to a file or folder
arc rot --no-judge           # the deterministic candidates only — no LLM
```
Each verdict is printed as it lands, and the printed run IS the report — arc keeps it
nowhere else (`crates/review/cli/src/workflow/rot/mod.rs`). Keep the output; each
suggestion names its anchor, the other sites it covers and the proposed refactor.

## 2. Triage — do NOT trust the judge blindly
The `duplicated-domain-type` signal is **low precision**: it flags field
overlap as duplication, but structural similarity ≠ same concept. Read the
actual types before refactoring. Common FALSE POSITIVES (leave them, say why):
- **Different abstraction levels** (e.g. per-file `CallEdge` vs repo-wide `RepoCallEdge`).
- **Read/write/insert splits** (`FooIn` / `NewFoo` / `FooRecord` — the DAO pattern).
- **serde wire type vs rich in-memory type** (`Detection` vs `DetectionData`).
- **Single vs batch reports**, **agent variants**, etc.

Real refactor value is usually in **clones (`dup-block`)**, **reinventions**,
and **god-modules** — verify each is genuine (read the copies) before acting.

## 3. Refactor holistically
Read **every** location (not just the primary), then make the change across
all of them in one pass. Fix-pattern for an extracted helper/type: **extract
DOWN to the lowest shared module/package** in the dependency graph (so consumers
call down, never sideways or up) — never "share" by re-exporting from a high one.

## 4. Gate hard (every step)
Run the repo's own build, lint and tests after every change — the checks in its
`presubmit.toml` when it has one, else ask the person which ones.
Structural changes cascade — if it's not green, REVERT, don't paper over it.
Confirm before committing (outward action). One finding/cluster = one commit.

## 5. Prove it is gone
There is nothing to close: rot suggestions are not stored. **Verify by re-detection** —
re-run `arc rot --file <the sites>`; if the clone / idiom / god-module is no longer
reported, the rot is cleared. Report the before/after lines.

## Cadence
Batch by concept, **human-review each batch** before it lands — 60+ refactors
fully autonomous is risky. Report per batch: what was refactored, what was judged a
false positive (with the reason), and the re-detection result.
