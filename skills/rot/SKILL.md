---
name: rot
description: >-
  Work through A.R.C. (arc) structural-rot findings — god-modules, cross-file
  clones, duplicated types, repeated idioms. Use when the user says "fix the
  rot", "handle the rot findings", or "arc rot" after a whole-repo structural
  review. These are multi-file refactors (not point fixes): inspect the full
  context, refactor holistically, verify with tests, and re-run detection.
  Edits code and commits — confirm before committing.
allowed-tools: "Bash Read Edit Write"
---

# arc rot — handle structural-rot findings

Rot findings are **structural refactors** (extracting a shared helper, splitting a god-module, unifying duplicated types, or extracting a trait), not single-line bug fixes. Because each one spans multiple files, handle them **sequentially (concurrency 1) on `main` or a single persistent worktree** — parallel refactors will conflict. Drive them directly with full repo context rather than using `arc fix`.

## 1. Run detection
```bash
arc rot                      # deterministic detection + L5 LLM judge (critic_l5) on each candidate
arc rot --file <path>        # limit scope and cost to a specific file or directory
arc rot --no-judge           # deterministic candidates only — no LLM calls
```
Each verdict is printed to stdout as it finishes, and `arc` does not persist the report anywhere else — keep the terminal output. Each suggestion names the primary anchor, the related sites, and the proposed refactor.

## 2. Triage — don't trust the judge blindly
The `duplicated-domain-type` detector is **low-precision**: it flags field overlap as duplication, even when two types represent different concepts. Always read the actual types before merging them. Common **false positives** (leave them alone and explain why):
- **Different abstraction levels** (e.g., per-file `CallEdge` vs. repo-wide `RepoCallEdge`).
- **Read/write/insert splits** (`FooIn` / `NewFoo` / `FooRecord` — the DAO pattern).
- **Wire DTOs vs. rich in-memory types** (`Detection` vs. `DetectionData`).
- **Single vs. batch reports**, or distinct agent variants.

The highest-value refactors are usually **code clones (`dup-block`)**, **reinvented helpers**, and **god-modules** — verify each copy before editing.

## 3. Refactor holistically
Read **every** affected site before editing, then update all of them in a single pass. When extracting a shared helper or type, **push it down to the lowest shared module/package** in the dependency graph so callers depend downward — never "share" by re-exporting from a higher-level module.

## 4. Verify strictly after every step
Run the repository's full build, lint, and test suite after each refactor (using `presubmit.toml` if present, otherwise ask the user which checks to run). Structural changes ripple easily — if checks fail, **revert** rather than papering over the failure. Ask the user before committing, and keep it to one logical finding/cluster per commit.

## 5. Prove it is resolved
Because rot suggestions aren't stored in a database, **verify by re-running detection**: run `arc rot --file <affected-paths>` and confirm the clone, idiom, or god-module is no longer flagged. Report the before/after output.

## Cadence
Group refactors by concept and **have a human review each batch** before landing — running 60+ structural refactors unattended is risky. For each batch, report what was refactored, what was skipped as a false positive (and why), and the re-detection result.
