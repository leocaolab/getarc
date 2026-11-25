# Code conventions — an opt-in demo, off by default

arc is **not a style linter** ([README](README.md)). Formatting and coding
conventions belong to your own tools — `ruff` / `eslint` / `gofmt` / `clippy`
in your CI — which are free and give the same answer every time. arc spends an
LLM call on what those tools *can't* check: problems in what the code means
([L4](review.md)) and structural rot ([L5](rot.md)).

So why does arc ship convention rules at all? **As examples.** They show what a
convention rule looks like in the rubric format, so you can [write your
own](custom-rubrics.md) in your own words — your conventions are yours. They
are a starting point, not a recommendation to run them: your linters already
cover this, and a reviewer adding naming nits on top of your linter is just
noise.

That is why they all have `status: deprecated`: **they do not run unless you
turn them on, one rule id at a time.**

## Turning one on

Name the rule in `[review] enable` in the clone's `.arc/config.toml`:

```toml config.toml
[review]
enable = ["rust_best_practices::migration-affix-in-name"]
```

`enable` runs a rule whatever its status. To change a rule's wording, copy it
into your repo's own `rubrics/` file with `status: stable` instead
([Custom rubrics](custom-rubrics.md)).

## The demo set — before (X) → after (Y)

Each rule below shows code that breaks the convention (X) and the fix (Y).
This is the shape to copy into your own rubric.

### `rust_best_practices::migration-affix-in-name`
A `_core` / `_v2` / `_new` suffix that stayed after the other version it told apart was gone.

```rust
// X — the pyo3 `lookup` twin moved away long ago; `_core` now lies
pub fn lookup_core(conn: &Connection, k: &str) -> …
pub fn store_core(conn: &Connection, …) -> …

// Y — the module path already namespaces it: cache::lookup
pub fn lookup(conn: &Connection, k: &str) -> …
pub fn store(conn: &Connection, …) -> …
```

### `rust_best_practices::unitless-primitive-quantity`
A value with a unit (seconds, days, an id) is passed through an API as a bare integer.

```rust
// X — is `now` secs or millis? is `ttl_days` swappable with a count?
pub fn lookup(conn: &Connection, key: &str, ttl_days: i64, now: i64) -> Option<Hit>

// Y — the type says what it is
/// Unix timestamp, seconds.
pub type UnixSecs = i64;
pub fn lookup(conn: &Connection, key: &str, ttl_days: i64, now: UnixSecs) -> Option<Hit>
```

### `llm_generated_code_smells::obscure-import-or-alias`
An import alias so short that the reader can't tell what it is where it's used.

```python
# X
from collections import Counter as _C
summary = ", ".join(f"{n} {t}" for t, n in _C(tags).items())

# Y
from collections import Counter
summary = ", ".join(f"{n} {t}" for t, n in Counter(tags).items())
```

### `llm_generated_code_smells::log-string-vs-error-object`
The handler turns the error into a string, throwing away the stack trace the logger would have kept.

```python
# X — reason=str(e) loses the traceback
except OSError as e:
    log.warning("write_failed", path=path, reason=str(e))

# Y — the logger's exception path keeps cause + stack
except OSError:
    log.exception("write_failed", path=path)
```

### `llm_generated_code_smells::log-event-name-proliferation`
One operation logs a different event name for each step that can fail.

```python
# X — the namespace multiplies per failure mode
except AgentError as e:  log.warning("fix_step1_failed", reason=str(e))
except ParseError as e:  log.warning("fix_step2_failed", reason=str(e))

# Y — one event; the error type goes in a field
except (AgentError, ParseError) as e:
    log.exception("fix_failed", error_type=type(e).__name__)
```

### `llm_generated_code_smells::duplicate-error-handler-shell`
Two try-blocks with the same fallback, where one try with an arm per error type would do.

```python
# X
try:    output = agent.run(...)
except AgentError as e:
    log.warning("agent_failed", reason=str(e)); return file, {}
try:    replies = parse(output)
except ParseError as e:
    log.warning("parse_failed", reason=str(e)); return file, {}

# Y — one try, per-type arms sharing the fallback once
try:
    output = agent.run(...)
    replies = parse(output)
except AgentError as e:
    log.warning("agent_failed", reason=str(e)); return file, {}
except ParseError as e:
    log.warning("parse_failed", reason=str(e)); return file, {}
```

### `llm_generated_code_smells::branch-redundancy-default-leak`
Several branches assign the same default value, which hides that there is a default at all.

```python
# X — the default is repeated, its symmetry invisible
if post_fix_run_id:
    rec = storage.get_run(post_fix_run_id)
    if rec is not None:  threads, target = _deserialize(rec.threads), post_fix_run_id
    else:                threads, target = threads, run_id
else:                    threads, target = threads, run_id

# Y — lift the default, override only what changes
threads, target = threads, run_id
if post_fix_run_id:
    rec = storage.get_run(post_fix_run_id)
    if rec is not None:
        threads, target = _deserialize(rec.threads), post_fix_run_id
```

## Writing your own instead

That is what the examples are for. A convention rule is just a rubric entry.
Copy the shape above — a `name`, a one-line `why`, an `example_bad` /
`example_good` pair (give both or neither), the `description` the reviewer
reads as its prompt, and `status: stable` — into your repo's `rubrics/`, and
arc runs it in the same review. See [custom-rubrics.md](custom-rubrics.md).

---

*See also: [README](README.md) — what arc is and is not · [custom-rubrics.md](custom-rubrics.md) — bring your own rules · [configuration.md](configuration.md) — the config file.*
