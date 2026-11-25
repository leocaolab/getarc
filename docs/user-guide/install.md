# Install

arc has two parts, and installing arc means installing both:

- the `arc` command, on every machine where people or agents write code;
- the **server suite**, on one machine you own. It runs the pipeline: review, merge, release.

Both come as ready-built binaries from **[getarc releases](https://github.com/leocaolab/getarc/releases/latest)**. You do not need the source.

The whole setup, in order:

1. **Install** (this page): `arc` on each machine, the server suite on the pipeline machine.
2. **[Configure](configuration.md)**: models (providers) in tars, the repo's files, the pipeline machine's `machine.toml`.
3. **[Set up the pipeline](onboarding.md)**: prepare the repo, register it, start the services, connect your machines, land a first PR.

<a id="or-let-your-coding-agent-set-it-up"></a>
## Let your coding agent install it

In the repository you want arc in, paste this into Claude Code, Codex or another coding agent:

```text wrap
Set up A.R.C. (arc) in this repository with the arc-setup skill. If you're in Claude Code, run `claude plugin marketplace add leocaolab/getarc`, then `claude plugin install arc@getarc`. If you're in another agent, run `npx skills add leocaolab/getarc --skill arc-setup` and select your agent. Use one installation method. You can read the skill directly at https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md (raw: https://raw.githubusercontent.com/leocaolab/getarc/main/skills/arc-setup/SKILL.md). Then use the arc-setup skill to install and configure arc here.
```

The agent uses the [arc-setup skill](https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md) to install everything with you, in this order:

1. the `arc` binary;
2. the models in tars, and which model reviews and which fixes (`arc init`);
3. `presubmit.toml` and the merge gate (`merge.yml`);
4. the pipeline machine: the server suite, the board, and this repo registered with the reviewers it should get ([Set up the pipeline](onboarding.md));
5. a first PR that the pipeline lands.

It asks before it changes anything outside the repository. What each skill and plugin does: [Skills and plugins](skills.md).

What each step asks you, and which files it writes:

| Step | Asks | Writes |
|---|---|---|
| `install.sh` | nothing | the `arc` binary, in `~/.local/bin` (or `--to`) |
| the arc-setup skill | which models to use (when `claude` is on your PATH, it suggests Claude Code, which needs no API key), and before every change outside the repo | `~/.tars/config.toml`, `.arc/config.toml`, `presubmit.toml`, `merge.yml`; on the pipeline machine, `~/.arc/machine.toml` and the systemd units; `~/.arc/client.toml` and the agent hooks |
| `arc init` (in a terminal) | which provider reviews and which fixes, picked from the ones already in `~/.tars/config.toml`; if there are none, it stops and says so | `.arc/config.toml`, `.arc/.gitignore` |

The rest of this page is the same install, by hand.

## What goes on which machine

| Machine | Install | What you run there |
|---|---|---|
| your laptop, and every machine an agent writes code on | `arc`, `gh`, and the skills plugin if you use Claude Code | `arc init`; `arc local-review` / `arc fix` before you submit; `arc submit`; the agent hooks |
| one pipeline machine (Linux recommended) | the server suite (which includes `arc`), plus `git`, `gh` and every tool your merge gate runs | the review service, the merge server, the board, the chat server, the nightly release |

You can also write code on the pipeline machine. The two parts only need to reach each other over the network.

## The CLI (macOS Apple Silicon, Linux x86_64)

Install `arc` with one line:

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh
```

`install.sh` downloads the build for this machine, checks it against the release's `SHA256SUMS`, and runs its `--version` before it replaces anything. It puts `arc` in `~/.local/bin`; use `--to DIR` for another directory, or `--version vX.Y.Z` for another release. It never uses `sudo` and never edits your shell profile: if the directory is not writable or not on your `PATH`, it prints the line you need to change. There is no build for Intel Macs, arm64 Linux or Windows.

Or install it by hand:

```bash
# macOS (Apple Silicon); on Linux x86_64 use arc-linux-x64.tar.gz
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/arc-darwin-arm64.tar.gz
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/SHA256SUMS
shasum -a 256 -c SHA256SUMS --ignore-missing   # Linux: sha256sum -c SHA256SUMS --ignore-missing
tar -xzf arc-darwin-arm64.tar.gz arc
mv arc ~/.local/bin/                            # anywhere on your PATH
arc --version                                   # arc X.Y.Z (<commit> <build time>)
```

**VS Code extension:** `arc-vscode.vsix` is a file in the same release. Install it with `code --install-extension arc-vscode.vsix`.

### GitHub's CLI (`gh`)

arc talks to GitHub through `gh`. It also needs to know who is running each command. Inside a coding agent's session, that is the session; in a plain terminal, it is your `gh` login. So:

- `arc submit` opens the pull request through `gh`. Run `gh auth login` on every machine you submit from.
- `arc local-review` and `arc fix` need no `gh` when you run them from Claude Code, Codex or agy. From a plain terminal they need the login; without it they stop with `cannot tell who is submitting`.

Install `gh` from [cli.github.com](https://cli.github.com), with `brew install gh`, or with your distribution's package manager. `gh auth login` asks you questions, so run it yourself.

## The pipeline machine

Which machine to choose (Linux with systemd user services, and what a Mac cannot do) is the first step of [Set up the pipeline](onboarding.md#2-choose-the-machine).

### What the machine needs besides arc

- **`git` 2.38 or newer.** The merge server merges with `git merge-tree --write-tree` and refuses to start on an older git.
- **`gh`, logged in as a GitHub user that can push to the repo's target branch.** Run `gh auth login` once, as the user the services run as. The merge server pushes the PRs it lands; the review service reads PR labels and posts reviews through `gh`.
- **Every tool your merge gate runs** (compilers, test runners, linters), on the `PATH` you give the services (`[machine] path`, see [Configuration](configuration.md#arcmachinetoml--the-pipeline-machine)). arc installs none of them: a `setup-*` action in a workflow only checks that the machine already has the right version ([Merge](merge-gate.md#what-arc-runs-in-a-workflow-file)).
- **Providers in `~/.tars/config.toml`** for the real reviewers, as on any machine ([Configuration](configuration.md#tarsconfigtoml--providers-and-keys)). If you use `claude_cli`, log in to Claude Code on this machine as the user the services run as.

### The server suite

```bash
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/arc-suite-linux-x64.tar.gz
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/SHA256SUMS
sha256sum -c SHA256SUMS --ignore-missing          # arc-suite-linux-x64.tar.gz: OK
tar -xzf arc-suite-linux-x64.tar.gz               # unpacks ./arc-suite-linux-x64/: the ten binaries and a README
install -m 755 arc-suite-linux-x64/arc* ~/.local/bin/
arc-server --version
```

The README in the tarball lists each binary and what it needs from the system (on Linux, the glibc and libstdc++ versions). Each service's `install` command writes a systemd unit that runs the binary from where it is now, so leave the binaries where you put them. You start the services after you configure them: see [Set up the pipeline](onboarding.md).

| Binary | What it is |
|---|---|
| `arc` | the CLI |
| `arc-server` | the merge server, one per repo: lands reviewed PRs. It also registers repos (`arc-server install`, `arc-server tenant …`) |
| `arc-review` | the review service, one per repo: takes each change you submit, calls the reviewers, and grants the pass (the permission to land) |
| `arc-reviewer` | the reviewer that `arc-review` runs on one version of a PR |
| `arc-fixer` | answers findings for the author, when `arc-review` is set to run it |
| `arc-web` | the board: projects and issues, review pages, merge queue, release page. Every client machine is given its address |
| `arc-bridge` | the chat server between agent sessions, services and people; it also holds the issue board |
| `arc-releaser` | the nightly release (optional) |
| `arc-deployer` | runs the deploy job your repo declares (optional) |
| `arc-tap` | the central store of test history (optional) |

## What a release holds

Every release on getarc has the same files. `SHA256SUMS` lists the checksum of each.

| File | What it is |
|---|---|
| `install.sh` | the one-line installer above |
| `arc-darwin-arm64.tar.gz`, `arc-linux-x64.tar.gz` | the `arc` CLI alone |
| `arc-suite-darwin-arm64.tar.gz`, `arc-suite-linux-x64.tar.gz` | the server suite, including `arc`, with a README |
| `arc-skills.tar.gz` | the Claude Code skills plugin ([Skills and plugins](skills.md)) |
| `arc-vscode.vsix` | the VS Code extension |

## Upgrade

Upgrade `arc` on each machine:

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh                          # the latest release
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh -s -- --version vX.Y.Z   # a given release; also how you go back
```

Upgrade the skills plugin through Claude Code ([Skills and plugins](skills.md#upgrade)).

Upgrade the server suite on its machine: download the new `arc-suite-*.tar.gz` and its `SHA256SUMS`, check the checksum, unpack it, and copy the binaries over the old ones at the same paths. The systemd units point at those paths, so you do not need to rewrite them. Then check the machine and restart the services:

```bash
arc-server tenant check --offline                          # no FAIL before you restart
systemctl --user restart arc-web arc-bridge
systemctl --user restart 'arc-server@*' 'arc-review@*'     # and 'arc-tap@*' where test history is on
```

Every binary has `--version`, which tells you which build is running.

---

*Next: [Configuration](configuration.md) · [Set up the pipeline](onboarding.md) · [Skills and plugins](skills.md).*
