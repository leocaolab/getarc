---
name: shift-left-rust
description: How to WRITE genuinely clean Rust — universal good-code principles in Rust idiom, stated in full so the skill is self-contained and portable (works in any repo; nothing else needed). The positive form of common review anti-patterns, so the code is clean the FIRST time. The aim is the principle itself, not passing any linter. Load before writing or editing Rust (a fix, a new function, any codegen). Triggers include writing/editing .rs, "fix this Rust", "add a Rust function".
---

# Writing clean Rust (shift-left)

The goal in one line: **write the version the next reader — human or model — can
extend without re-reading the whole thing.** Clear structure = the correct next
line is obvious. Checklist, not an essay.

> **The target is the principle, not passing a reviewer.** Every rule is stated in full
> here, so it works in any repo. A `stem::name` in parentheses names the review-rubric
> rule this one mirrors; the full rule, with its reason and examples, is in the arc-skills
> plugin's `rubrics/<stem>.yaml` — open it when you want more, never because you must.
> Never write code merely to keep a detector quiet — a linter with finite recall
> going silent is not proof the code is clean; gaming its blind spots is the failure.

## Separate decisions from mechanism (not only IO from logic)

A decision is a function of the facts it decides on — scalars, fixed arrays, slices in; a decision out. Everything that stores, moves, accumulates, queues or times data is **mechanism**: IO is one kind; buffers and containers (`Vec`, `VecDeque`, maps), queues, allocators and clocks are others. Mechanism calls decisions; decisions never touch mechanism. The test of the shape: the decision's signature has no container and no `&mut`, and its boundary tests take only scalars. "No IO in this crate" does not mean decisions are separated.

1. **Fetch, then decide.** Async fetch materializes the data; a *pure sync* fn computes.
   - ❌ `for u in items { let s = store::hash(db,&u.p).await?; if s==cur { keep.push(u) } }`
   - ✅ `let rows = fetch_all(db,&items).await?;` → `let (keep,skip) = partition(rows);`  *(pure, no runtime)*
2. **A decider returns a plan; it does not do the IO.**
   - ❌ `if stale { db.close(id).await?; notify(id).await?; }`
   - ✅ `-> Command::Close(id)` — the caller (shell) performs the effect
3. **Business logic takes data as args** — no db / fs / net / `Instant::now()` inside, and no `block_on` wrapped around a pure computation.
4. **A decision is not a method that also moves bytes.** A buffer's `push` that compares a length, picks when to compact and dates a half frame mixes three decisions into the mechanism.
   - ❌ `fn push(&mut self, bytes) { …extend…; if len > self.max { … }; if self.read*2 >= self.buf.len() { self.buf.drain(..) } }`
   - ✅ `fn cut(header: [u8; 4], max: u32) -> Cut` and `fn should_compact(read: usize, len: usize) -> bool`, called by `push`.

## Type your data and errors

4. **Named struct, not a tuple** across a boundary; `#[derive(Deserialize)]` struct, not `serde_json::Value`.
   - ❌ `-> Result<(String, String)>` · `v.get("file").and_then(Value::as_str)`
   - ✅ `struct Loc { path: String, line: usize }`
   - A private tuple whose member types already say what each is (`(SyncSender<T>, JoinHandle<()>)`) may stay unnamed; across a module or `pub` boundary, name it.
   - **Fields that come and go together are one struct.** Two `Option`s that are always both `Some` or both `None` (or one implies the other) are one `Option<Struct>` — two can be built half-set.
     - ❌ `title: Option<String>, title_source: Option<Source>`
     - ✅ `title: Option<Title>` with `struct Title { text: String, source: Source }`
   - **A field that describes another (`truncated`, `count`, `shown`) comes from the function that produced that other.** Computed beside it from a different argument, it can say "showing 120" while all of them were sent.
5. **Typed errors: `thiserror` enum + `#[from]`,** never `Result<_, String>` / `.to_string()` at a boundary.
   - ❌ `.map_err(|e| e.to_string())?`
   - ✅ `#[error(transparent)] Db(#[from] DbError)` → just `?`
   - **Shape the error by what the caller does with it.** A variant per way a caller handles it (retry / refuse / skip); a failure every caller only logs or bubbles is ONE struct — a sentence plus `#[source]` for the cause chain (the typed stand-in for `anyhow`). A variant only a test matches is no reason to keep it: assert what is observable, or the error's words.
     - ✅ `#[error("reading {at}")] struct ReadError { at: RefName, #[source] source: GitError }`
   - **Forwarding one error? Return it.** No enum whose single job is `#[error(transparent)]` around another error.
   - **"Malformed" errors belong to the edge that parses.** An adapter parses git's output / JSON / argv into types once; code past it holds `ObjectId` / `RefName` and never produces `NotAnOid`.
     The parse also checks what the input claims about itself (a length, a count, a checksum) once, and a mismatch is a typed error carrying the raw text — "carried as-is, not enforced" accepts a truncated input as whole.
   - **Once parsed, pass the type down.** Holding a `RepoRoot` / `RepoPath` / `BranchName`, hand that on; `.as_path()` / `.as_str()` appear only where it becomes text — the IO call, a format, an adapter's row or DTO column — never to fill a domain field or a parameter that could hold the type — otherwise the next reader parses it again, or not at all.
   - **"Not mine" is `Option`, not `Err`.** Skip it with `filter_map`; don't raise `Err(Elsewhere)` to log it.
6. **Closed set → `enum`,** not a stringly-typed value checked at runtime.
   - ❌ `if verdict == "accepted"`
   - ✅ `enum Verdict { Accepted, Ignored }`
   - **A field that exists only in one state lives in that variant,** not beside the enum as an `Option`. A field doc saying "only set when …" is the tell.
     - ❌ `status: Status, reason: Option<Reason> // only when Status::Refused`
     - ✅ `enum Status { Refused { reason: Reason }, … }`
   - **Words on the wire come from the enum.** Need the variant as text in JSON → `#[derive(Serialize)]` + `#[serde(rename_all = "…")]`, not a `match` to `&'static str` (a hand-written `as_str()` for a column or log word is still fine). A column storing which variant a payload-carrying enum is → derive the discriminants (`strum::EnumDiscriminants`), not a hand-written string table.
   - **Compared values are bound, not spliced.** In SQL a member's word that is compared (`WHERE status = ?`) is a bound parameter, never `format!`ed in; one that is query structure (a column alias, a view definition, a migration's CHECK) is written in the text.
   - **Only for vocabularies you decide on.** A set your code matches or chooses among is yours — an enum, even when the words come from elsewhere (an ingest that picks one `gitOperation` key by precedence → `GitOperationKind`). Words your code only copies through and never branches on stay text (another tool's `commit.kind`); an enum guessed from the values seen so far rejects its next word.
   - **A wire shape written by one compilation unit and read by another** (two crates, or Rust and TypeScript) **is pinned by one shared sample**, kept with the writer so the path follows the dependency edge (a TypeScript test can only import from its own tree, so there it sits with the UI). The writer's test produces the sample through the production serializer — never a hand-written expectation, which would be a third opinion — and proves it writes it; the reader's test proves it reads it. When it goes red, the failure message says the way through: read the diff first, then refresh. For a closed set crossing into TypeScript, Rust serializes every member, TS compares its list. Two hand-written member lists are two definitions.
   - **"Every member" comes from a derive** (`strum::VariantNames` / `EnumIter`). Without one, where the list lives follows who reads it: the test alone → in the test beside an exhaustive `match`; production too (a strict decoder's vocabulary, the candidates a parse tries) → on the type as `ALL`.
   - **A tool's own sentinel output can pass the parse.** git prints `HEAD` for a detached checkout and `BranchName::parse("HEAD")` succeeds; recognise the sentinel first, into its own variant (`Head::Detached`), then parse the rest, and pin it with a test (`a_detached_head_is_detached_not_a_branch_named_head`). Having fixed one reader, grep every other site that runs the same command (`rev-parse --abbrev-ref`) — the next one has the same bug.
   - **Before tightening a read** (`String` → enum, lenient → strict), check the stored history fits — wherever it is stored (`sqlite3 -readonly` the distinct values; saved JSON, parquet likewise) — and put what you found in the PR.

## Don't swallow, don't hide

7. **No `unwrap` / `expect` / `panic` in core or logic code** — return `Result`, propagate with `?`. You cannot handle the failure at this layer, so you have no right to decide the process dies. Walk every `Option` / `Result` through these four steps before you write the unbox: (`rust_best_practices::no-unwrap-in-library`)
   1. **Can this `None` / `Err` happen in the real world?** Think through all of it: IO and syscalls, external input (wire bytes, recorded data, HTTP, another process's JSON), state that changed between two calls, concurrency and ordering, config, platform differences, containers (cgroup quota, cpuset, a masked `/sys`).
   2. **It can → pass the `Result` out**, carrying the raw input and the real error, to the layer that can decide: the startup code, the supervisor, the caller who asked.
   3. **It can't, but the compiler doesn't know → change the type or the shape so it can't be written**, instead of writing "impossible":
      - check-then-take (`is_some()` then `unwrap()`, `contains_key` then `map[&k]`, `is_empty()` then `max().unwrap()`) → one step: `let-else` / `match` / `entry`
      - looking an id up again (`orders.get_mut(&id).expect("working order")`) → pass the entity you already found
      - a field that is `Option` because only one mode has it → two types
      - call A to change state, then find the result with B (`switch(..)` then `find(..).expect(..)`) → A returns the result, or B returns `Result` and you pass it on
      - a default `NonZero::new(c).expect(..)` at run time → a typed `const` (compile-time: a wrong one does not build)
      - slice to array `try_into().unwrap()` → a reader that returns `[u8; N]`
      - a string / number validated after construction → parse once at the edge into the type; the inside holds the type
   4. **The type can't be changed** (usually a std trait signature wider than the truth, e.g. `fmt::Write for String` returns `fmt::Result`) → `expect("<proof>")`, the message a proof a reviewer can check: why it can't happen, what guarantees it. `"checked"`, `"finished"`, `"not zero"` are not proofs. This is the only exemption.
   - **When a panic is allowed.** The Linux kernel's rule: `BUG_ON` is deprecated — use `WARN` and handle the "impossible" case; `panic()` only when essential boot init fails; at run time return `-errno`; user input never BUGs; an oops kills the one task, not the kernel.
     - compile time (`const` evaluation) — yes: a failure does not build;
     - startup, before the main loop / serving starts — fail fast, but **only the outermost startup code decides to die**; libraries return `Result`, startup exits with `?` and the reason (non-zero exit), the supervisor restarts and alerts;
     - steady state — no. Return `Result`; an "impossible" case is a `WARN_ON_ONCE`: alert, and isolate the smallest unit (refuse this request / order, stop this job, drop this connection), the process keeps running;
     - external input — never, at any time;
     - continuing would cause irreversible damage (a corrupted ledger that keeps placing orders, state about to be persisted broken) — an explicit stop path (a kill switch), not a stray panic that happens to stop it;
     - tests — unwrap freely.
   - **A panic inside `tokio::spawn` or a spawned thread does not stop the process** — the task silently vanishes, neither failing fast nor handled. Do what can fail at startup before the spawn, and return it with `?`.
     - ❌ `tokio::spawn(async move { let mut term = signal(SignalKind::terminate()).expect("SIGTERM"); … })`
     - ✅ `let mut term = signal(SignalKind::terminate())?; tokio::spawn(async move { term.recv().await; … });`
   - **Indexing and arithmetic are partial too:** `map[&k]`, `v[i]`, `&s[a..b]`, integer division by zero — the same four steps.
8. **Don't discard the error arm.** No `let _ = fallible();` — handle it or `?`.
   - A best-effort reading whose result has no failure slot (an environment probe, "this comment has no line to sit on") may turn a parse failure into `None` only under a marker comment saying what is dropped and why no reader needs it — arc's reviewer accepts `// [arc:intentional-handle] reason: …` (`l4_contracts::swallowed-exception`), free prose does not; anywhere else, widen the type to carry the failure and its raw text.
9. **Don't paper a failed own-data unbox with a default.** `x.unwrap_or(0)` on a DB read hides corruption — model real absence as `Option<T>`, propagate the broken invariant with the id.
   - Swallowing is the other face of the panic: `unwrap_or(default)` / `.ok()` / `let _ =` / `if let Ok(..)` that drops the `Err` go through the same four steps as item 7. Only two cases are right, each under the item-8 marker saying why it is safe: the default IS what the value means (`None` = not configured, use the configured default), or nobody cares about the dropped result (a reply to a caller who already left).
   - **Degrading is the caller's decision, not the library's.** The library returns `Result`; the caller chooses to degrade and records why (a log line, an alert). A library that degrades silently runs its caller in degraded mode without anyone knowing.
     - ❌ `fn detect() -> Cpus` that, when `/sys` is unreadable, counts every logical CPU as a physical core
     - ✅ `fn detect() -> Result<Cpus, CpuReadError>`; startup decides: fall back to the logical count and alert, or exit
     - Check the world before adding the invariant that seems to come with it: "physical cores > logical CPUs is an error" is false on Linux, where `available_parallelism()` counts the cgroup quota and the physical count comes from the affinity mask (`--cpus=2` on a 32-core cpuset is logical 2, physical 32).
   - When a wire contract you don't own encodes absence as a sentinel (`pr: 0` = no PR), the domain still holds `Option`; the wire DTO encodes it once, through a named constant (`NO_PR`), and the PR lists the readers that still need it. What decides it is whether the data is rewritten whole: a shape each write replaces entirely (a JSON snapshot) becomes `null` / an absent key with no sentinel constant; a stored column with history (`pr INTEGER NOT NULL DEFAULT 0`) keeps its sentinel as that column's convention, decoded once at the read edge, the constant living in the store that owns the column.

## Subtract, don't patch

10. **Iterator chain over a mut accumulator** when clearer: `.iter().filter(..).map(..).collect()`.
11. **`let x = if c { a } else { b };` / `let-else`,** not `let mut x = None; if c { x = Some(..) }`.
12. **Explicit `enum State` + `match`,** not a few `let mut` flags mutated across a loop (the compiler then checks exhaustiveness).
13. **Trait / polymorphism** for an `if kind == .. else if ..` type-ladder repeated at ≥2 sites.

## Fluency (流畅) — one altitude, one job, one railway

The bar: a fn reads top-to-bottom at ONE cognitive altitude, does ONE thing, flows
down a single happy-path rail, and reads as a **chain of transformations** — each
step turns one value into the next, with no mutable accumulator threaded through and
nothing to simulate in your head. (Each tell names the rubric rule it mirrors.)

14. **One level of abstraction per fn.** Push `block_on`, `tracing::info!`, `format!` blocks into named helpers; the top reads like a table of contents. (`llm_generated_code_smells::mixed-abstraction-levels`)
15. **One responsibility — no conjoined verbs.** No `build_and_review`, no `open_and_migrate`: two verbs = two fns, the caller composes. (`l5_architecture::l5-M-one-responsibility-per-unit-srp`)
16. **Business logic separated from infra.** The pure decision holds no DB / git / LLM / runtime; IO is fetched at the edge and passed in as data. And a **domain type never carries a `db` / connection / context field** — those handles live in the shell, passed alongside the data, never baked into it. (`fp_lens::core-buried-outward`, `decision-executes-its-own-effect`)
17. **Railway-oriented (ROP): linear happy path, short error arm.** `?` short-circuits; the `Err` / `else` arm is a one-line bail, NEVER a home for long code. Reading top-to-bottom sees only the success flow. (`l5_architecture::l5-A-errors-as-values` · `llm_generated_code_smells` railway pattern)
18. **Paragraph the body: setup → work → return.** Group the lines into visible phases (gather inputs · do the work · assemble the result), a blank line between; no interleaving. *(no dedicated rubric rule yet — read by a human.)*
19. **Parameter object, not a cross-domain bucket brigade.** Group cohesive params; never a 13-arg signature threading DB + config + flags + raw data. (`l5_architecture::l5-M2-cross-domain-arity`, `rust_best_practices::primitive-obsession-long-param-list`)
20. **A returned struct carries facts, not UI.** The `Corpus` / `Outcome` you hand to the next stage holds domain data only — never a `notifications: Vec<String>` of pre-formatted banner lines, never a `Sender` / channel. Render banners at the edge FROM the facts.
    - A view / wire struct carries only facts the reader cannot compute. A ratio, a count, a `len()`, a total over a list it already holds — the reader computes it: the backend records facts, the frontend derives. *(`type_design::two-representations-of-one-fact`)*

## Place types by owner

Before adding a type at all: **say in one sentence what it is — if you can't, it isn't needed**; reuse an existing type that already holds the data; every type name (struct / enum — states and errors included / `type` alias) is a **noun** (Google's convention); adjectives and participles go on enum **variants** only (`State::Closed`, not `enum Watched`); an error type is named the way std names one, `<verb><object>Error` per [C-WORD-ORDER](https://rust-lang.github.io/api-guidelines/naming.html#c-word-order) (`ParseIntError`, `RecvTimeoutError`; not `struct NotAHello`), and its variants say the cause (`io::ErrorKind::NotFound`, `TryRecvError::Disconnected`, `NotDelivered`); an enum that mixes success with why-it-failed is a disguised `Result`; no junk words (`Manager` / `Helper` / `Util` / `Data` / `Info`); grep the name for collisions. Full checklist: the `type-naming` skill.

21. **Private first: no `pub` without a caller outside the module.** Default to private, then `pub(crate)`; `pub` only for a contract another crate speaks.
    - ❌ `pub struct ReviewContext` in a shared types crate, read by one module
    - ✅ `struct ReviewContext` inside the review module that builds and consumes it
    - **Fields too.** A type with an invariant keeps its fields private; the one way in is `TryFrom` / `parse`. Not `pub` fields plus a `validate()` that a caller can skip.
    - `pub` also hides dead code from the `dead_code` lint: what only a test, or nobody, calls stays silent while it is `pub`. When narrowing makes it warn, that is a finding — report it, saying whether it is the root or cascades from another item (name it). Don't make it quiet: `#[allow(dead_code)]`, or `pub` put back *as the answer*, closes the hole again. Judging it is a separate decision that proves its premise first — a library verb, the surface of a paused command, a product driver that fires only when the target repo is that language are not dead. While the finding is filed and judged, `pub` is a legal waiting place; item 27's "delete" is for code already proved dead.
    - A `type` alias is transparent to rustc: the lint looks through the alias at the type it names, so narrowing the alias itself never trips `private_interfaces` — even when it is a `pub` field's type (`RepoCallee` as `pub struct RepoCallEdge`'s `pub callee`, its twin `RepoCaller` still `pub`). Check every signature it appears in yourself.
22. **Owner's crate, not the user's.** A type goes where its lifecycle is produced; readers depend on the owner. Two domains that "share" a `type X = String` get two newtypes and one `From`/`TryFrom` at the boundary — not one alias in a common crate.
    - ❌ `pub type FailureId = String;` used by the merge gate AND the test-output parser
    - ✅ `test_output::ParsedFailure(String)` · `merge::FailureId(String)` · `impl From<ParsedFailure> for FailureId` where merge reads the parse
    - **The only reader is not the owner, nor is the only builder.** Ask whose fact the type states, not who calls or constructs it. A `GithubAccount` (the GitHub account `gh` acts as, or GitHub's own reason it could not say) stays in the GitHub adapter crate though only a web page reads it and only that page wraps the adapter's `Result` into it; a `#[derive(Serialize)]` does not make it the reader's DTO. Test: when a second app needs it tomorrow, would it have to depend on today's only reader? Then it lives in the wrong place. (`type_design::type-lives-away-from-its-owner`)
    - A domain newtype with no invariant takes `From<String>` at the boundary and neither `From<&str>` nor `Deref<Target = str>` — `.into()` would quietly turn any literal into a domain value, and a `str` deref hands callers every `str` method so they forget they hold a domain value; read through an explicit `.as_str()`. A name the code itself owns is a constant built by `const fn from_static(&'static str)` (`RuleId::MANUAL`) — the literal is the code's, not a caller's input. One with an invariant only parses (`TryFrom` / `parse`). (An error built from a message is not a domain newtype.) Tests build values from literals through the owner crate's `testkit` — a `testkit` module in that crate (`#[cfg(any(test, feature = "testkit"))]`), not just the feature.
23. **Adapter types stay in the adapter.** A DB row / HTTP DTO / CLI report is its adapter's; convert with `From`/`TryFrom` at the edge; no `sqlx::FromRow` / web-framework derives on a domain type; a row never reaches the core.
    - Two columns holding one fact (`outcome` + `finished_at`) are one field in the domain type; the adapter splits and joins them and refuses a row where they disagree. A derived column may be written, but the in-memory type doesn't carry it — compute it from the source field at write time.
24. **No facade re-exports across domains.** `pub use other_domain::X` to "keep paths working" hides who owns X — change the callers' paths instead.

## Say less

25. **Comments: minimal; the default is none.** The full rules, with examples, are the `coding-convention` skill; load it too.
    - First fix the code: rename, extract, simplify. A comment that re-says the code or the signature is deleted (`/// Returns the user ID.` on `fn user_id`).
    - Keep only what the code cannot say: **why** (an outside constraint, a bug worked around, an ordering or concurrency rule, why *not* the obvious way) and what a caller cannot see (side effects, errors, panics, units, edge cases).
    - A fn doc is one verb-first sentence (`Waits until …`); a field or variant doc only when it adds a unit, range or invariant.
    - Every comment is a complete sentence with a subject and a verb, never a fragment (`/// On macOS, performance cores only.` is a fragment).
    - One or two plain sentences a newcomer understands. No history (git has it), no step lists, no private jargon; an issue number points to the story, it is not the reason.
    - Test: hide the code and read only the comments — you learn the intent and the traps, not the steps.
26. **Reuse a crate before hand-rolling** (hashing, parsing, dedup) — check what's already a dep.
27. **Delete dead code** — no `#[allow(dead_code)]` shim, no "keep it + tolerate it" compat layer.
28. **Magic literal → `const` with its unit;** and never `#[allow(clippy::..)]` to mask a real design flaw — fix the design.

