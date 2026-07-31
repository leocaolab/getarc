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
allowed-tools: Bash(arc *), Bash(curl *), Bash(tar *), Bash(uname *), Bash(mkdir *), Bash(mv *), Read, Write, Edit
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

## Step 2 — configure providers, FOR the user (ask, then write it)

Don't just dump `arc init` on the user — **do the setup for them.** arc maps
review **roles** (critic, fixer) to LLM **providers** defined in tars. Two files:

- `~/.tars/config.toml` — provider definitions: `type`, `default_model`, and the
  env var holding the API key. **The model lives HERE, once.**
- `<repo>/.arc/config.toml` — the role → provider-**id** map + a `[gate]`
  build/test command. Committable, no secrets, **no model pins**.

Steps:

1. See what's already there: run `arc init` — it reads `~/.tars/config.toml` and
   offers those providers. If the list is empty, help the user define one (step 3).
2. **Ask the user two things:**
   - *Which LLM provider(s) do you have?* — e.g. Anthropic API, Google Gemini,
     OpenAI, DeepSeek, the Claude CLI you're already logged into (`claude_cli`,
     no key), or a local OpenAI-compatible endpoint.
   - *For each: the default model + the env var holding its API key* — e.g.
     Gemini → `gemini-2.5-flash` / `GEMINI_API_KEY`.
   **Recommend** a *non-Claude critic* (Gemini / DeepSeek tend to *find* more)
   **+ Claude as the fixer**, kept in different families so the review is
   genuinely independent.
3. Write `~/.tars/config.toml` with those providers — model + auth live HERE
   (shape per tars; keys shown are the common ones):
   ```toml
   [providers.gemini_flash]
   type          = "gemini"
   default_model = "gemini-2.5-flash"
   api_key_env   = "GEMINI_API_KEY"

   [providers.claude_cli]
   type = "claude_cli"          # uses your `claude login` session — no API key
   ```
4. Then map roles for the repo — `arc init` (the providers now show up) or write
   `<repo>/.arc/config.toml` directly. **Reference providers by id — never a model
   string:**
   ```toml
   [roles]
   critic = "gemini_flash"      # a provider id from tars (its model lives there)
   fixer  = "claude_cli"
   [gate]
   command = "cargo build"      # language-specific: npx tsc --noEmit / pytest / go build …
   ```

If a review later fails with an auth error, surface the one missing thing
(usually an unset API-key env var) and let the user fix it — don't loop.

## Step 3 — run the review

Default to the current working tree. Scope it by what's under review:

```bash
arc review                       # per-file L4 review of the working tree (default)
arc review --file <path>         # just a file or directory
arc review --commit <sha>        # review one commit's diff instead
arc rot                          # whole-repo STRUCTURAL review — god-modules,
                                 #   cross-file duplication, layering, weak types
                                 #   (the rot the working-tree pass won't see)
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

- `arc fix` — Fixer resolves open findings in an isolated worktree (**FIX-ONLY — does not merge**)
- `arc verify` — independent Verifier re-checks the fixes → verified / reopen / escalate
- `arc close` — land verified fixes onto HEAD (**the single, verify-gated merger**)
- `arc auto` — hands-off, ONE pass: review → fix → verify → close → commit (re-run for another pass)
- `arc resolve <id> --as wontfix` — set a verdict directly (`new|fixed|verified|wontfix|agreed|escalated|duplicate`)

Full flags for any verb: `arc <cmd> --help`.
