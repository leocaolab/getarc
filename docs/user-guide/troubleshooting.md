# Troubleshooting

| You see | What it means, and what to do |
|---|---|
| `missing credential: env var X is not set` | The provider's API key is not in your environment. Export it (or `source .env`) and run again. This is a real error, not a bug in arc. |
| `` `.arc/config.toml` has a `[providers]` section `` | Your config file is in the old format. Providers are now defined in `~/.tars/config.toml`. Delete the `[providers]` section and keep `[roles]`, which names tars provider ids — or regenerate the file with `arc init --force`. |
| `No provider for role "critic_l5"` | `.arc/config.toml` has no `[roles]` entry for that role, and no `default`. Add `critic_l5 = "<tars provider id>"`. |
| The fixer runs the wrong build or tests, or guesses them | `arc fix` gives the fixer the checks in `presubmit.toml`. Commit one with this repo's real build and test commands (see [Configuration](configuration.md)). |
| `unrecognized subcommand 'auto'` (or `'verify'`, `'refactor'`) | Those commands are gone. Run `arc local-review`, then `arc fix`; `arc fix` fixes and reviews again until the reviewer says LGTM or `[review] max_rounds` is used up. |
| `arc fix` refuses to start because the tree is dirty | The working tree must match HEAD: no changes to tracked files and no untracked files (ignored files are fine). Commit or stash first. |
| `arc tap` says `no arc-tap for this checkout` | No test-history server is set for this repo. Pass `--tap-server`, or set your board's address (`web = "http://…"` in `~/.arc/client.toml`) so the board can name one. |
| You changed arc's source but arc behaves the same | You are running the installed binary. Run `just install` first. |
| Few or empty findings | The reviewer model may be too weak for this code. Try a stronger provider for the critic role; a weak reviewer finding nothing does not mean the code is clean. |

More: `../usage.md` §9.

---

*Back to the [guide index](README.md).*
