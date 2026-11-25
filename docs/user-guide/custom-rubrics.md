# Custom rubrics — bring your own rules

arc's rubric is a set of YAML files in `rubrics/`; you can add your own without touching arc's. A rule is plain YAML:

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

Feed it in one way (`arc local-review --rubric-file` and `--extra-rubrics` are gone): commit it in the repo's own `rubrics/` directory. A file whose stem matches a built-in (`rust_best_practices.yaml`) **overrides** it; a new stem is **added**. Review reads `rubrics/*.yaml` from the commit under review, not from the working tree.

`.arc/config.toml`'s `[review]` section does NOT add files. Its `enable` / `disable` / `experimental` keys still parse but nothing reads them — a local review runs the `stable` rules only. Rule ids are `<file-stem>::<rule-name>`, so the rule above is `my-rules::no-raw-sql-in-handlers`.

Three things that bite:

- **`status` defaults to `experimental`** — an omitted `status` means the rule never runs (only `stable` rules do). Ship a real rule with `status: stable`.
- **Unknown fields are rejected** (`deny_unknown_fields`) — a typo'd key fails the load, it isn't ignored.
- **Language scope**: a rule runs on ALL languages by default. Limit it with a file-level `language: [rust, ...]` header or a per-rule `universality: [rust]`.

> The rule `description` IS the prompt — write it the way the built-ins are written: name the hazard, give the token only as an example, and draw the boundary against neighbours so one site → one finding. To add a **rot** (L5) axis rather than a per-file rule, see [rot.md](rot.md) for what makes a structural signal.

---

*Next: [How arc reviews (L4)](review.md) · [Rot (L5)](rot.md) · [The commands](commands.md).*
