# arc-review — Claude Code Skill

A thin Claude Code skill that drives the locally-installed `arc` CLI for
adversarial, cross-file code review. The skill is **not** the product —
it's a doorway that tells Claude when and how to call `arc`, and
bootstraps the install on first use.

> Scope note: this skill targets **Claude Code only**. For Cursor /
> Claude Desktop reach, use the MCP adapter in `../mcp/`.

## Install (personal — all your projects)

```bash
mkdir -p ~/.claude/skills/arc-review
cp SKILL.md ~/.claude/skills/arc-review/SKILL.md
```

## Install (project — shared with your team via git)

```bash
mkdir -p .claude/skills/arc-review
cp SKILL.md .claude/skills/arc-review/SKILL.md
git add .claude/skills/arc-review/SKILL.md
```

Teammates get it automatically on clone.

## Use

In Claude Code:

```
review this branch with arc
```

Claude loads the skill, ensures `arc` is installed (offering to
`brew install` it if missing), runs `arc review`, and reports the
cross-file findings.

## Distribute as a plugin (optional)

To ship via a Claude Code plugin marketplace, place this directory at
`<plugin>/skills/arc-review/` inside a plugin with a `plugin.json`, then
users install with `/plugin install <plugin>@<source>`.

## Fill-ins before publishing

- `<your-org>/arc/arc` — the real Homebrew tap/formula.
- `arc init` — confirm the exact config-bootstrap command.
- `<ARC_API_KEY_ENV>` — the real env var / config key for the LLM key.
