# Install

## Quickstart

### Agent setup

Paste this into your coding agent (Claude Code, Codex, or another) in the repository you want arc in. It installs all of arc with you — the CLI here, then the pipeline machine (the server suite, the board, the repo registered with its review routes) — and ends with a first PR the pipeline landed, asking before it touches anything global.

```text wrap
Set up A.R.C. (arc) in this repository with the arc-setup skill. If you're in Claude Code, run `claude plugin marketplace add leocaolab/getarc`, then `claude plugin install arc@getarc`. If you're in another agent, run `npx skills add leocaolab/getarc --skill arc-setup` and select your agent. Use one installation method. You can read the skill directly at https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md (raw: https://raw.githubusercontent.com/leocaolab/getarc/main/skills/arc-setup/SKILL.md). Then use the arc-setup skill to install and configure arc here.
```

The rest of this page is the whole install by hand.

arc is one tool with two halves: the `arc` CLI, on every machine where people or agents write code, and the **server suite**, on one machine you own, which runs the pipeline — review, merge, release. Installing arc means installing both. Everything ships as release binaries from **[getarc releases](https://github.com/leocaolab/getarc/releases/latest)**; no source is needed.

The whole path, in order:

1. **Install** (this page) — the CLI on each machine, the suite on the pipeline machine.
2. **[Configure](configuration.md)** — providers in tars, the repo's files, the pipeline machine's `machine.toml`.
3. **[Set up the pipeline](onboarding.md)** — initialize the repo, register it, start the services, connect the clients, land a first PR.

## What goes on which machine

| Machine | Install | What it runs |
|---|---|---|
| your laptop, and every machine an agent writes code on | the `arc` CLI, `gh`, and the skills plugin if you use Claude Code | `arc init`, `arc local-review` / `arc fix` before you submit, `arc submit`, the agent hooks |
| one pipeline machine (Linux recommended) | the server suite, `arc` included, plus `git`, `gh` and the tools your gate runs | the review service, the merge server, the board, the chat server, the nightly releaser |

The pipeline machine can also be one you write code on; the two halves only need to reach each other over the network.

## The CLI (macOS Apple Silicon, Linux x86_64)

One line:

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh
```

`install.sh` picks this machine's build, checks it against the release's `SHA256SUMS`, runs its `--version` before replacing anything, and puts `arc` in `~/.local/bin` (or `--to DIR`; `--version vX.Y.Z` for another release). It never uses `sudo` and never edits your shell profile — when the directory is not writable or not on `PATH`, it prints the line to change. There is no build for Intel Macs, arm64 Linux or Windows.

Or by hand:

```bash
# macOS (Apple Silicon); on Linux x86_64 use arc-linux-x64.tar.gz
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/arc-darwin-arm64.tar.gz
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/SHA256SUMS
shasum -a 256 -c SHA256SUMS --ignore-missing   # Linux: sha256sum -c SHA256SUMS --ignore-missing
tar -xzf arc-darwin-arm64.tar.gz arc
mv arc ~/.local/bin/                            # anywhere on your PATH
arc --version                                   # arc X.Y.Z (<commit> <build time>)
```

**VS Code extension:** `arc-vscode.vsix` is an asset of the same release; install it with `code --install-extension arc-vscode.vsix`.

### Or let your coding agent set it up

In the repo you want arc on, paste this into Claude Code, Codex or another coding agent:

```text
Install the arc-setup skill. If you're in Claude Code, run `claude plugin marketplace add leocaolab/getarc`, then `claude plugin install arc@getarc`. If you're in another agent, run `npx skills add leocaolab/getarc --skill arc-setup` and select your agent. Use one installation method. You can read the skill directly at https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md (raw: https://raw.githubusercontent.com/leocaolab/getarc/main/skills/arc-setup/SKILL.md). Then use the arc-setup skill to install and configure arc in this repository.
```

The [arc-setup skill](https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md) installs the binary, then the providers in tars, `arc init`'s roles, `presubmit.toml` and the merge gate, then walks you through the pipeline machine ([Set up the pipeline](onboarding.md)) to a first landed PR, asking before anything global. What each skill and plugin does: [Skills and plugins](skills.md).

| Step | Asks | Writes |
|---|---|---|
| `install.sh` | nothing | the `arc` binary, in `~/.local/bin` (or `--to`) |
| the arc-setup skill | which models to use — when `claude` is on your PATH it proposes Claude Code (no API key) — and before every global write | `~/.tars/config.toml`, `.arc/config.toml`, `presubmit.toml`, `merge.yml`; on the pipeline machine `~/.arc/machine.toml` and the units; `~/.arc/client.toml` and the agent hooks |
| `arc init` (in a terminal) | which provider reviews and which fixes, from those already in `~/.tars/config.toml`; with none there it stops and says so | `.arc/config.toml`, `.arc/.gitignore` |

### GitHub's CLI (`gh`)

arc talks to GitHub through `gh`, and names whoever runs a command: the coding agent's session when you run it from one, else your `gh` login. So:

- `arc submit` opens the pull request through `gh`: every machine that submits needs `gh auth login`;
- `arc local-review` and `arc fix` run from Claude Code, Codex or agy need no `gh`; from a plain terminal they need the login, and without it stop with `cannot tell who is submitting`.

Install `gh` from [cli.github.com](https://cli.github.com), `brew install gh` or your distribution's package. `gh auth login` is interactive, so you run it yourself.

## The pipeline machine

Which machine to pick — Linux with systemd user services, and what a Mac cannot do — is the first step of [Set up the pipeline](onboarding.md#2-choose-the-machine).

### What the machine needs besides arc

- **`git` 2.38 or newer** (the merge server refuses to start on an older one: it merges with `git merge-tree --write-tree`).
- **`gh`, logged in as a GitHub user that can push to the repo's target branch** (`gh auth login`, once, as the user the services run as). The merge server pushes what it lands; the review service reads PR labels and posts reviews through `gh`.
- **Every tool your merge gate runs** — compilers, test runners, linters — on the `PATH` you give the services (`[machine] path`, [Configuration](configuration.md#arcmachinetoml--the-pipeline-machine)). arc installs nothing: a `setup-*` action in a workflow is only checked against the version the machine already has ([Merge](merge-gate.md#what-arc-runs-in-a-workflow-file)).
- **Providers in `~/.tars/config.toml`** for the real reviewers, as on any machine ([Configuration](configuration.md#tarsconfigtoml--providers-and-keys)). With `claude_cli`, log in to Claude Code on this machine as the service user.

### The server suite

```bash
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/arc-suite-linux-x64.tar.gz
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/SHA256SUMS
sha256sum -c SHA256SUMS --ignore-missing          # arc-suite-linux-x64.tar.gz: OK
tar -xzf arc-suite-linux-x64.tar.gz               # unpacks ./arc-suite-linux-x64/: the ten binaries and a README
install -m 755 arc-suite-linux-x64/arc* ~/.local/bin/
arc-server --version
```

The README in the tarball names each binary and what it needs of the system (the glibc and libstdc++ versions on Linux). Each service's `install` writes a unit that runs the binary from the path it was run at, so keep the binaries where you put them. The services start after their configuration: [Set up the pipeline](onboarding.md).

| Binary | What it is |
|---|---|
| `arc` | the CLI |
| `arc-server` | the merge server, one per repo: lands reviewed PRs; it also registers repos (`arc-server install`, `arc-server tenant …`) |
| `arc-review` | the review service, one per repo: takes submitted updates, calls the reviewers, grants the pass |
| `arc-reviewer` | the reviewer `arc-review` runs on one PR version |
| `arc-fixer` | the author's side `arc-review` can run to answer findings |
| `arc-web` | the board: projects and issues, review pages, merge queue, release page; the one address clients ask |
| `arc-bridge` | the chat server between agent sessions, services and people; also the issue board |
| `arc-releaser` | the nightly release (optional) |
| `arc-deployer` | runs your repo's declared deploy job (optional) |
| `arc-tap` | the central test-history store (optional) |

## What a release holds

Every release on getarc carries the same files; `SHA256SUMS` lists the checksum of each.

| File | What it is |
|---|---|
| `install.sh` | the one-line installer above |
| `arc-darwin-arm64.tar.gz`, `arc-linux-x64.tar.gz` | the `arc` CLI alone |
| `arc-suite-darwin-arm64.tar.gz`, `arc-suite-linux-x64.tar.gz` | the server suite, `arc` included, with a README |
| `arc-skills.tar.gz` | the Claude Code skills plugin ([Skills and plugins](skills.md)) |
| `arc-vscode.vsix` | the VS Code extension |

## Upgrade

The CLI, on each machine:

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh                          # the latest release
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh -s -- --version vX.Y.Z   # one release, also to go back
```

The skills plugin is upgraded through Claude Code ([Skills and plugins](skills.md#upgrade)).

The server suite, on its machine: fetch the new `arc-suite-*.tar.gz` and its `SHA256SUMS`, check, unpack, and put the binaries over the old ones at the same paths (the units name those paths, so they need no rewrite). Then check the machine and restart what runs:

```bash
arc-server tenant check --offline                          # no FAIL before you restart
systemctl --user restart arc-web arc-bridge
systemctl --user restart 'arc-server@*' 'arc-review@*'     # and 'arc-tap@*' where test history is on
```

Every binary has `--version`, which says which build runs.

---

*Next: [Configuration](configuration.md) · [Set up the pipeline](onboarding.md) · [Skills and plugins](skills.md).*
