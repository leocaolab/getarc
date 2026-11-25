# Code conventions — an opt-in demo, off by default

arc is **not a style linter** ([README](README.md)): formatting and coding
conventions are your own toolchain's job — `ruff` / `eslint` / `gofmt` /
`clippy`, running in your CI, zero-cost and deterministic. arc spends an LLM
call on the things those tools *can't* do: semantic hazards ([L4](review.md))
and structural rot ([L5](rot.md)).

So why does arc ship convention rules at all? **As a demo.** They show what a
convention rule looks like in the rubric format so you can [write your
own](custom-rubrics.md) — because your conventions are yours, and you'll want
them phrased your way. The built-ins below are a starting point, not a
recommendation to run them: your linters already own this ground, and a
reviewer flagging a naming nit on top of your linter is just noise.

They are therefore all `status: deprecated` — **off the default review set.**
Nothing runs them unless you ask, per id.

## Enabling one

Not today. `[review] enable` / `disable` / `experimental` still parse in
`<repo>/.arc/config.toml`, but nothing reads them: a local review
runs the `stable` rules only, so a `deprecated` rule here never runs. To use one
of these conventions, copy the rule into your repo's own `rubrics/` file with
`status: stable`.

## The demo set — before (X) → after (Y)

Each rule is a convention with a mechanical before/after. This is the shape to
copy into your own rubric.

### `rust_best_practices::migration-affix-in-name`
A `_core` / `_v2` / `_new` affix that outlived the twin it disambiguated from.

```rust
// X — the pyo3 `lookup` twin moved away long ago; `_core` now lies
pub fn lookup_core(conn: &Connection, k: &str) -> …
pub fn store_core(conn: &Connection, …) -> …

// Y — the module path already namespaces it: cache::lookup
pub fn lookup(conn: &Connection, k: &str) -> …
pub fn store(conn: &Connection, …) -> …
```

### `rust_best_practices::unitless-primitive-quantity`
A units/identity quantity crosses an API as a bare integer.

```rust
// X — is `now` secs or millis? is `ttl_days` swappable with a count?
pub fn lookup(conn: &Connection, key: &str, ttl_days: i64, now: i64) -> Option<Hit>

// Y — the type says what it is
/// Unix timestamp, seconds.
pub type UnixSecs = i64;
pub fn lookup(conn: &Connection, key: &str, ttl_days: i64, now: UnixSecs) -> Option<Hit>
```

### `llm_generated_code_smells::obscure-import-or-alias`
An alias so short the reader can't tell what it is at the call site.

```python
# X
from collections import Counter as _C
summary = ", ".join(f"{n} {t}" for t, n in _C(tags).items())

# Y
from collections import Counter
summary = ", ".join(f"{n} {t}" for t, n in Counter(tags).items())
```

### `llm_generated_code_smells::log-string-vs-error-object`
The handler stringifies the error, discarding the stacktrace the logger would attach.

```python
# X — reason=str(e) loses the traceback
except OSError as e:
    log.warning("write_failed", path=path, reason=str(e))

# Y — the logger's exception path keeps cause + stack
except OSError:
    log.exception("write_failed", path=path)
```

### `llm_generated_code_smells::log-event-name-proliferation`
One op emits N event names that differ only by which step failed.

```python
# X — the namespace multiplies per failure mode
except AgentError as e:  log.warning("fix_step1_failed", reason=str(e))
except ParseError as e:  log.warning("fix_step2_failed", reason=str(e))

# Y — one event, the step rides a typed field
except (AgentError, ParseError) as e:
    log.exception("fix_failed", error_type=type(e).__name__)
```

### `llm_generated_code_smells::duplicate-error-handler-shell`
Two try-blocks with the same fallback, in a language with typed dispatch.

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
Several branches assign the same default; the chain hides that there *is* one.

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

That's the point of the demo. A convention rule is just a rubric entry — copy
the shape above (a `name`, a one-line `why`, an `example_bad` / `example_good`
pair, plus the `description` that is the critic's prompt and `status: stable`)
into your repo's `rubrics/` and arc will run it in the same review. See
[custom-rubrics.md](custom-rubrics.md).

---

*See also: [README](README.md) — what arc is and is not · [custom-rubrics.md](custom-rubrics.md) — bring your own rules · [configuration.md](configuration.md) — the config file.*
