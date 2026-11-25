# Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `missing credential: env var X is not set` | the provider's key isn't in the environment — export it (or `source .env`). Honest error, not a bug. |
| `` `.arc/config.toml` has a `[providers]` section `` | an old-shape config. Provider definitions live in `~/.tars/config.toml`; delete the `[providers]` section and keep `[roles]` naming tars provider ids (or regenerate with `arc init --force`). |
| `No provider for role "critic_l5"` | `.arc/config.toml` has no `[roles]` entry for that role (and no `default`) — add `critic_l5 = "<tars provider id>"`. |
| the fixer runs the wrong checks, or guesses them | `arc fix` hands it the checks in `presubmit.toml` — commit one with this repo's real build and tests (see [Configuration](configuration.md)). |
| `unrecognized subcommand 'auto'` (or `'verify'`, `'refactor'`) | those verbs are gone. Run `arc local-review`, then `arc fix`, which fixes and reviews again until LGTM or `[review] max_rounds` turns. |
| `arc fix` refuses a dirty tree | it needs the working tree to be HEAD's (no tracked change, no untracked file; ignored ones are fine) — commit or stash first. |
| stale behavior after changing arc's source | you're running the installed binary — `just install` first. |
| weak/empty findings | the critic is too weak for the target — try a stronger critic provider; don't read "clean" off a weak critic. |

More: `../usage.md` §9.

---

*Back to the [guide index](README.md).*
