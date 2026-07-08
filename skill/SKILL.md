---
name: arc-review
description: >-
  Adversarial, cross-file code review. Use when reviewing a branch, diff,
  PR, or specific files for bugs that single-file / diff-only review
  misses — cross-file contract mismatches, invariants broken across
  modules, architectural drift, structural rot. Runs the local `arc` CLI
  (Critic↔Fixer adversarial engine, call-graph aware). Trigger on
  requests like "review this", "check this branch for bugs", "arc review",
  "is this codebase rotting", or a pre-commit / pre-PR review.
allowed-tools: Bash(arc *), Bash(curl *), Bash(tar *), Bash(uname *), Bash(mkdir *), Bash(mv *)
argument-hint: "[path-or-scope, default: current changes]"
---

# arc — adversarial cross-file code review

`arc` reviews code with an adversarial Critic↔Fixer loop over the repo's
call graph, so it catches cross-file bugs a single-file linter or a
diff-only AI review cannot see. Findings persist as tracked entities in
`<repo>/.arc/` with a status and a history. This skill drives the
locally-installed `arc` binary.

## Step 1 — make sure `arc` is installed (auto-download if missing)

Run `arc --version`. If it prints a version, go to Step 2.

If it's **not found**, offer to install the free prebuilt binary from
getarc (ask the user first), then re-check `arc --version`:

```bash
# auto-pick the release asset for this machine, install to ~/.local/bin (no sudo)
case "$(uname -sm)" in
  "Darwin arm64") asset=arc-darwin-arm64.tar.gz ;;
  "Linux x86_64") asset=arc-linux-x64.tar.gz ;;
  *) echo "No prebuilt binary for $(uname -sm) yet — see https://github.com/leocaolab/getarc"; exit 1 ;;
esac
mkdir -p ~/.local/bin
curl -L "https://github.com/leocaolab/getarc/releases/latest/download/$asset" | tar xz
mv arc ~/.local/bin/ && arc --version
# ensure ~/.local/bin is on PATH (add to your shell profile if `arc` still isn't found)
```

To **update** an existing install, re-run the same block — it always
fetches the latest release.

## Step 2 — make sure it's configured

`arc` maps review roles to LLM providers. Two files:

- `<repo>/.arc/config.toml` — the role → provider-name map (committable, no secrets).
- `~/.tars/config.toml` — the provider definitions + where the API keys live (never committed).

```bash
arc init          # interactive: pick a Critic + Fixer provider, writes .arc/config.toml
```

If a review fails with a config/auth error, surface the one missing
thing (usually an unset API-key env var named in `~/.tars/config.toml`)
and let the user fix it. Don't loop on it.

## Step 3 — run the review

Default to the current working tree. Scope it by what's under review:

```bash
arc review                       # per-file L4 review of the working tree (default)
arc review --file <path>         # just a file or directory
arc review --commit <sha>        # review one commit's diff instead
arc rot                          # whole-repo STRUCTURAL review — god-modules,
                                 #   cross-file duplication, dead code, layering,
                                 #   weak types (the rot the working-tree pass won't see)
```

`--mode enrich` (the default) gives the Critic each file plus its
call-graph callers/callees; `--mode file` isolates a file; `--mode
cluster` partitions the whole call graph into review units. `arc` must
run inside a git repository (it anchors `.arc/` and reads git).

## Step 4 — report, then act

```bash
arc report                       # the board — every finding, grouped by file, with status
arc report --status open         # filter to one lens (open|fixed|merged|verified|closed|…)
```

Summarize arc's findings for the user, leading with the **cross-file**
ones (the bugs single-file review misses) — name the call chain and the
two files involved. Do NOT invent findings; report only what `arc`
output. Then offer next steps:

- `arc fix` — let the Fixer resolve open findings in an isolated worktree (merges back on a clean build)
- `arc auto` — hands-off loop: review → fix → verify → merge → commit
- `arc resolve <id> --as wontfix` — set a verdict directly (`new|fixed|verified|wontfix|agreed|escalated|duplicate`)
- `arc ack <id>` — acknowledge a finding
- `arc close <id>` — close a finding that's merged ∧ verified

Full flags for any verb: `arc <cmd> --help`.
