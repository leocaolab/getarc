# Custom rubrics — bring your own rules

To add your own review rule, write a YAML file and commit it in your repo's `rubrics/` directory. arc's built-in rules are YAML files too (in arc's own `rubrics/`); yours sit next to them without changing them.

A rule file looks like this:

```yaml rubric.yaml
name: My Team Rules
description: House rules for this repo.
rules:
  - name: no-raw-sql-in-handlers
    status: stable          # stable | experimental | deprecated
    description: |
      ANTI-PATTERN: a request handler builds SQL from strings inline instead of
      going through the repository layer. The token (a `SELECT`/`format!` in a
      handler) is only an example — flag the hazard: query construction leaking
      into the transport layer. Do NOT flag parameterized calls through the repo.
```

## How arc picks it up

- **Where:** `rubrics/*.yaml` in your repo. This is the only way in — `arc local-review --rubric-file` and `--extra-rubrics` are gone.
- **Add or replace:** a file with a new name is **added** to the built-in rules. A file with the same name as a built-in one (for example `rust_best_practices.yaml`) **replaces** it.
- **Which version:** arc reads `rubrics/` as git has it at the base of the change under review, not from your working tree. A rule you add in a change starts applying once that change has landed.
- **Rule id:** `<file name without .yaml>::<rule name>`. Saved as `rubrics/my-rules.yaml`, the rule above is `my-rules::no-raw-sql-in-handlers`.

Which rules run is set in the clone's `.arc/config.toml`, under `[review]`: by default only `stable` rules run; `experimental = true` adds the experimental ones; `enable = ["<rule id>", …]` runs those rules whatever their status, deprecated included; `disable = ["<rule id>", …]` turns rules off, even ones also listed in `enable`. A rule id that no rubric holds is an error. `[review]` cannot add rule files — only `rubrics/` does.

## Three things that catch people out

- **A rule without `status` does not run.** `status` defaults to `experimental`, and only `stable` rules run by default. Give a real rule `status: stable`.
- **A misspelled key is an error.** Unknown keys are rejected (`deny_unknown_fields`), so a typo fails the load instead of being ignored.
- **A rule applies to every language** unless you limit it — with a file-level `language: [rust, ...]` header, or a per-rule `universality: [rust]`.

> **The rule's `description` is the prompt the reviewer reads.** Write it the way the built-in rules are written: name the problem, give the concrete code only as an example, and say where the rule stops and its neighbours begin, so one problem gives one finding. To add a **rot** (L5) check rather than a per-file rule, see [rot.md](rot.md) for what makes a structural signal.

---

*Next: [How arc reviews (L4)](review.md) · [Rot (L5)](rot.md) · [The commands](commands.md).*
