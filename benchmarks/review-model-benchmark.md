# Review-model benchmark — DeepSeek vs Gemini (flash vs pro)

**Date:** 2026-06-11 · **Task:** `arc review` (find-only, no fix) of the whole
`arc_review` crate (15 source files, L4 correctness + L5 architecture per file).
**Telemetry:** `ARC_DEBUG=1` (per-call latency / tokens from `.arc/tars/
pipeline_events.db`; findings from `.arc/arc.db`). Concurrency 4. Same crate, same
rubric, same arc build for all four — only `critic_l4`/`critic_l5` swapped.

## Conclusion — the operational policy (TL;DR)

The whole study collapses to one routing rule:

1. **Every review → non-thinking `deepseek-v4-flash`** (set `thinking="off"`). ~1 min,
   **$0.015/crate (20× cheaper than gemini-flash)**, ~9 CORE — it gets the *bulk*. This is
   the default; run it on every change. (gemini-2.5-flash is a comparable, pricier second.)
2. **Occasionally → ONE pass with a strong reasoner** (`claude_sdk`/sonnet or a `-pro`
   tier) to sweep the **deliberation tail**: temporal/state-machine, security-boundary,
   cross-function bugs the fast flashes **structurally miss**. Proof: `breaker.rs`'s
   `latched-state-outlives-its-cause` was **claude-only across all six runs** (worked
   example in §Step 3). Run it on state-machine / concurrency / security-sensitive code or
   as a pre-release sweep — **not** every review (claude ≈ 40 min, pros 9–11 min).
3. **Reasoning is a deep-audit / fix-time asset, never a fast-find one.** Toggling
   *thinking* on a weak flash buys nothing (10× slower, 0 gain); a fundamentally *stronger
   model* buys the tail. The decision is never "enable thinking?" — it's "occasionally run
   a strong model?".
   - **Refinement (proposed, untested): the deep-audit pass should run a FOCUSED rubric.**
     Don't just swap the model — **turn the simple idiom rules OFF and give the strong model
     ONLY the deliberation-class rubric** (state-machine / temporal / security-boundary /
     cross-function). A 50-rule rubric dilutes attention; a short hard-only rubric
     concentrates the expensive model's deliberation on the tail and wastes none of its
     budget re-finding what the flash already caught — different model **and** different
     rubric ⇒ near-zero overlap. Needs two small additions: a curated `rubrics/deep_audit.yaml`
     (complexity is orthogonal to L4/L5 — `latched-state` is an L4 rule — so it's a curated
     set or a `tier:` tag, not `--arch`) + a `--rubric-only` mode (today `--rubric-file`
     *appends*; `rubric_set_for` always includes the base). Falsifiable test: claude on
     deliberation-only vs full rubric — more tail, less time?
4. **Always triage.** Raw output is ~⅔ soft/dup/noise on every model; surface CORE first.
   And **ensemble > single** — CORE overlap is low; each model is a distinct lens (gemini =
   security/resource · -pro = input/boundary · deepseek = own-data-integrity · claude =
   deep-reasoning/temporal).

Everything below is the evidence. *(Note: the §Verdict / §Cost / §Overlap sections were
computed before the deepseek thinking instrumentation was fixed and under-credit
non-thinking deepseek-flash; §Step 2 + §Step 3 are the correction of record.)*

## Raw numbers

| Model | wall | latency/call | LLM calls | in tok | out tok | cached | findings |
|---|---:|---:|---:|---:|---:|---:|---:|
| **gemini-2.5-flash** | **51 s** | **2 s** | 65 | 1.19 M | 25 K | 509 K | 43 |
| gemini-3.1-pro (think=auto) | 549 s | 68 s | 28 | 509 K | 10 K | 220 K | 14 |
| deepseek-v4-flash | 305 s | 35 s | 31 | 510 K | 92 K | 358 K | 12 |
| deepseek-v4-pro | 683 s | 85 s | 31 | 541 K | 126 K | 369 K | 10 |

## Quality (the part the numbers hide)

A finding count is meaningless without precision. Decomposing each model's findings:

| Model | total | **unique (file+rule)** | **dup-spam** | ad-hoc (ungrounded) |
|---|---:|---:|---:|---:|
| gemini-flash | 43 | 30 | **13** | 4 |
| gemini-pro | 14 | 12 | 2 | 0 |
| deepseek-flash | 12 | 11 | 1 | 0 |
| deepseek-pro | 10 | 10 | **0** | 0 |

- **gemini-flash** has the highest recall (30 unique) but is **noisy**: 13 duplicate
  findings (e.g. the same `llm_client.rs` poison-recovery flagged **7×**) + 4
  ungrounded `free_review::ad-hoc`. ~30 % of its output is noise a dedup pass would
  drop.
- **gemini-pro / deepseek-flash / deepseek-pro** are all **clean**: ~0 ad-hoc, ~0–2
  dups. deepseek-pro is the cleanest (every finding unique + grounded) — but lowest
  recall.

Spot-checks (claude judging the actual code):

- ✅ **Convergent = trustworthy.** `breaker.rs::Breaker::new` (panics via `assert!`
  on bad config) was flagged by **both** pro models (`no-panic-on-input`) — a real
  rule-match (though arguably an *intentional* fail-loud, i.e. a likely wontfix).
  `build.rs`'s hardcoded XOR key (`no-hardcoded-secrets`) was flagged by both
  geminis. Cross-model agreement is the strongest signal of a true positive.
- ⚠️ **Soft / debatable findings exist in all.** `llm_client.rs`'s
  `.lock().unwrap_or_else(|e| e.into_inner())` is poison-recovery — a *defensible*
  resilience idiom, not really a swallowed exception. gemini-flash flagged it 7×
  (noise); the pro models flagged it 0–1× (selective). The grounded rule matches are
  technically valid, but a meaningful slice are low-actionability smells (unit-less
  i64 on serde DTOs, intentional asserts).

## Signal vs noise — the most important result

A raw count is a trap. I (claude) judged **every** finding against the actual code
and bucketed it: **CORE** (a real, actionable issue worth a fix), **SOFT** (a valid
rule-match but low-value / intentional → a likely won't-fix), **NOISE** (duplicate,
ungrounded ad-hoc, test-code, or a misapplied rule).

| Model | unique | **CORE** | SOFT (won't-fix) | NOISE + dups |
|---|---:|---:|---:|---:|
| gemini-2.5-flash | 30 | **~7** | ~16 | ~7 (+13 dup) |
| deepseek-v4-flash | 11 | ~6 | ~4 | ~1 |
| gemini-pro (3.1) | 12 | ~8 | ~4 | 0 |
| **deepseek-v4-pro** | 10 | **~9** | ~1 | 0 |

**The headline recall ranking is an illusion. Every model finds roughly the SAME
number of CORE issues (~6–9); the pro models find slightly MORE.** gemini-flash's "30"
is ~7 core findings buried under ~23 soft/noise:

- **hot-path-heap-thrash ×6 on COLD paths** (prompt-building / pagination functions
  that run once per review — not hot at all).
- **the same poison-recovery idiom (`unwrap_or_else(|e| e.into_inner())`) flagged 8×**
  across llm_client/role_client — a defensible resilience pattern, counted eight times.
- **build-script `.unwrap()` ×2** (panicking in `build.rs` is idiomatic), a `write!`-to-
  `String` `.expect()` (never fails), a `&Path` flagged as a "unitless primitive"
  (misapplied rule), and 4 ungrounded `ad-hoc`.

Meanwhile **deepseek-v4-pro had the highest signal AND caught a real bug nobody else
did**: `breaker.rs`'s `max_retries + 1` integer overflow on caller-supplied input
(`unchecked-arithmetic-on-input`). The pro models converge on the genuinely
actionable set (hardcoded key, validate-external-input, swallowed errors that lose
context, shadow global state) with almost no noise.

**So the quality ranking is the REVERSE of the count ranking:**
`deepseek-pro ≈ gemini-pro  >  deepseek-flash  >  gemini-flash`.
More findings ≠ more comprehensive — gemini-flash trades precision for a count a dedup
+ cold-path filter would mostly erase. Cross-model agreement (a CORE finding 3+ models
all raise) remains the single best true-positive signal.

## Overlap & ensemble — the models are complementary, not interchangeable

Aligning CORE findings by *site* (same underlying issue, even when the rule name
differs) across the four models:

| Core issue (site) | gem-flash | gem-pro | ds-flash | ds-pro |
|---|:-:|:-:|:-:|:-:|
| pipeline_builder config-load swallows errors | ✓ | ✓ | ✓ | ✓ |
| transport `REG` global mutable shadow-state | ~✓ | ✓ | ✓ | ✓ |
| build.rs hardcoded XOR key | ✓ | ✓ | · | · |
| breaker::new panics on input | · | ✓ | · | ✓ |
| validators `rel` path from LLM unvalidated | · | ✓ | · | ✓ |
| role_client incomplete-error-context | ✓ | · | · | ✓ |
| untyped-error-origin (String error) | ✓ | · | · | ✓ |
| verifier swallows JSON/confidence parse err | ✓ | ✓ | · | · |
| **breaker `max_retries+1` int overflow** | · | · | · | ✓ |
| **critic_agent silent-continue-past-corrupt** | · | · | ✓ | · |
| **pipeline_builder SQLite concurrency pragma** | ✓ | · | · | · |
| **env.rs env::var error classification** | · | ✓ | · | · |
| cleanup_rewrite swallows LlmError | · | · | ✓ | · |
| judge stringly-typed verdict | ~✓ | · | · | ✓ |

**Core overlap is LOW.** Of ~14 distinct core issues in the union, only **2 are
convergent (≥3 models)** — the config-swallow and the global shadow-state, which are
therefore the most trustworthy true positives. The best single model (deepseek-pro)
covers ~9/14 ≈ 60 %; **no model finds them all**, and each has a distinct lens:

- **gemini family** → security / resource (the hardcoded key — *both* deepseeks
  missed it — and the SQLite concurrency pragma).
- **-pro tiers** → external-input + boundary (validate-external-input, panic-on-input,
  the `max_retries+1` overflow — all missed by the flashes).
- **deepseek family** → own-data integrity (silent-continue-past-corrupt, shadow-state).

**So the strongest configuration is an ENSEMBLE, not a pick.** gemini-flash (fast,
cheap, catches the security/resource lens) + deepseek-pro (high signal, catches
input-validation + the overflow) together cover ~12/14 core and patch each other's
~40 % blind spot. Any single model leaves real issues on the table.

## Pagination rounds (why gemini-flash's count is inflated)

Each file is reviewed L4 + L5, and within each the model may **paginate** — return
findings + `exhausted:false` and get re-prompted for more — until it declares
`exhausted:true`. Calls ÷ files is the rounds proxy:

| Model | calls | calls/file | ≈ rounds |
|---|---:|---:|---:|
| gemini-flash | 65 | 4.3 | **~2** (kept asking "more?") |
| gemini-pro | 28 | 1.9 | ~1 |
| deepseek-flash | 31 | 2.1 | ~1 |
| deepseek-pro | 31 | 2.1 | ~1 |

gemini-flash's lead is largely the **second pagination round**, whose marginal
findings are mostly soft smells / dups; the other three hit `exhausted` on round 1.
More rounds bought count, not core.

## Cost (official pricing)

Billed at each model's published rate against THIS run's actual tokens. Cached input
is the cache-read portion of the total input (charged at the cache rate); the rest is
fresh input. DeepSeek rates from api-docs.deepseek.com (v4-flash/-pro are real
models, dramatically cheaper than the public chat/reasoner I first proxied). Gemini
flash from Google's page; gemini-pro proxied at gemini-2.5-pro rates (3.1-pro-preview
list price unpublished — likely higher, so its number is a floor).

| Model | in (fresh + cache) | out | **$/review** | $/unique finding | full repo ×15 |
|---|---|---:|---:|---:|---:|
| gemini-2.5-flash | 678 K + 509 K | 25 K | $0.304 | $0.0101 | $4.56 |
| gemini-pro (3.1) | 290 K + 220 K | 10 K | $0.527 | $0.0439 | $7.91 |
| **deepseek-v4-flash** | 152 K + 358 K | 92 K | **$0.048** | **$0.0044** | **$0.72** |
| deepseek-v4-pro | 172 K + 369 K | 126 K | $0.186 | $0.0186 | $2.79 |

Rates per 1M (in fresh / out / cache-read): gemini-flash $0.30/$2.50/$0.075 ·
gemini-pro $1.25/$10/$0.31 · ds-flash $0.14/$0.28/$0.0028 · ds-pro $0.435/$0.87/$0.0036.

**deepseek-v4-flash is ~6× cheaper than gemini-flash ($0.048 vs $0.304) and the
cheapest per finding ($0.0044).** Its cache-read is essentially free ($0.0028/M) and
its output is $0.28/M, so even its verbose 92 K-token output barely costs anything.
Both -pro tiers are dominated: pricier AND slower AND lower-recall.

## Verdict

> ⚠️ **Partially superseded — read Step 2 first.** The deepseek rows in this and the
> Cost / Overlap sections were measured with its reasoning channel silently ON (slow) and
> uncounted (the `thinking_tokens` bug), so they UNDER-credit deepseek-flash. With
> non-thinking deepseek-flash properly instrumented (Step 2) it is the review *value*
> winner, not gemini-flash. The relative shape below (count≠core, thinking-is-fix-time,
> ensemble-beats-single) still holds.

**The flash models beat their own pro siblings for review.** Pro (both families)
costs 2–13× the wall-clock and ~13× the per-call latency, finds *fewer* findings, and
buys **no precision** worth that price — gemini-pro/deepseek-pro aren't cleaner than
deepseek-flash, just slower and lower-recall. Reasoning depth doesn't help *finding*
the way it helps *fixing*.

**Once you count CORE findings instead of raw findings, every model is in the same
band (~6–9) — so the axes that actually separate them are NOISE, SPEED, and COST, not
"comprehensiveness."**

- **deepseek-v4-flash — the routine / CI default.** Cheapest by 6× ($0.048/crate,
  $0.72 full-repo), cleanest-per-token signal of the two flashes (1 noise vs
  gemini-flash's ~20), and ~the same core count. Its only tax is latency (35 s/call,
  5 min/crate) — invisible in an async gate. **This is the cheap-and-good-for-review
  sweet spot.**
- **gemini-2.5-flash — the interactive option, with an asterisk.** 17–42× faster, so
  worth its 6× price when a human is waiting — but its raw output is ~⅔ noise
  (cold-path "hot-path" flags, an 8× duplicated poison idiom, build-script unwraps).
  Usable, but only behind a dedup + cold-path filter; without one it cries wolf.
- **the -pro tiers — the occasional deep audit.** Highest signal (≈0 noise) and the
  only models to catch the subtle `max_retries+1` overflow — but 2–13× slower and
  pricier for ~1–2 extra core findings. Reach for deepseek-pro for a high-stakes
  one-shot audit, not the routine pass.

**More findings ≠ more comprehensive.** gemini-flash's count lead evaporates under the
core/noise split; the pro models are the most *thorough*, the flashes the most
*economical*, and cross-model agreement is the trustworthy true-positive signal.

**deepseek's strongest home is still the FIXER** (verbose structured tool-use is the
asset there). Default routing: **find = deepseek-flash (CI/routine) or gemini-flash
(interactive, + a noise filter); fix = deepseek-flash; deep audit = deepseek-pro.**

**deepseek-flash > deepseek-pro** for *both* roles tested: flash is 2× faster, finds
more, and is equally grounded. Don't pay for deepseek-pro on review.

## Caveats

- One run per model (LLM output is non-deterministic; recall varies run-to-run ±a
  few). The *direction* (flash≫pro on speed; gemini-flash≫all on recall+speed) is
  large enough to trust; exact counts aren't.
- gemini-flash's 1.19 M input tokens > others' ~510 K because pagination re-sends
  context across its 65 calls. Cost-per-finding still favors it (it's so fast/cheap),
  but a token-billed deployment should weigh the pagination overhead.
- "Quality" here is grounding + dedup + spot-checks, not a full true/false-positive
  audit of all 79 findings.
- **The target is a CLEAN, mature codebase.** arc_review has only ~14 distinct core
  issues to find at all (mostly intentional / by-design), so this benchmark measures
  **precision and noise-tolerance, not hidden-bug recall** — there aren't many hidden
  bugs to recall. On a genuinely buggy target the recall gap between models could
  matter more and re-order things; don't over-generalize the "core counts are
  similar" result to a messy codebase.

## Next step (step 2, per the plan)

Add a **thinking-mode** axis: deepseek `extra_body.thinking on/off` and gemini
`think=off/auto/budget`, holding the model fixed, to isolate how much of pro's
cost/behavior is the reasoning channel vs the base model — and whether thinking helps
*review* recall/precision at all (this run suggests not).

---

# Appendix A — the CORE findings, with the actual code

Every finding below is a real, grounded issue. `[finders]` = which models raised it
(the more, the more trustworthy). Judge for yourself whether each is worth a fix.

**A1 · Hardcoded XOR key** — `build.rs` · `[gemini-flash, gemini-pro]` (both deepseeks missed it)
```rust
/// 32-byte rotating XOR key. Must match arc_core/build.rs ...
const KEY: [u8; 32] = [/* literal byte array — redacted */];
```
A literal key in source. By-design (prompt *obfuscation*, not real crypto), so likely
a wontfix — but a real `no-hardcoded-secrets` hit, and only the geminis saw it.

**A2 · Integer overflow on caller input** — `breaker.rs::max_attempts` · `[deepseek-pro ONLY]`
```rust
pub fn max_attempts(&self, max_retries: usize) -> usize {
    match self.state { State::HalfOpen => 1, _ => max_retries + 1 }   // overflows at usize::MAX
}
```
`max_retries` is caller-supplied; `+ 1` panics (debug) / wraps (release) at the
boundary. Subtle, real, and **only deepseek-pro caught it** — its signature unique find.

**A3 · Config load swallows every error** — `pipeline_builder::provider_timeout_secs` · `[ALL 4]`
```rust
fn provider_timeout_secs(config_path: &str, provider_id: &str) -> Option<u64> {
    let raw = std::fs::read_to_string(config_path).ok()?;   // file missing/unreadable → None
    let doc = raw.parse::<toml::Value>().ok()?;             // malformed TOML → None
    ...
```
Missing file, unreadable file, corrupt TOML all collapse to `None` (= silent default
timeout) with zero signal. **The convergent finding — all four models — = the most
trustworthy true positive.**

**A4 · Untyped error + dropped context** — `role_client` · `[gemini-flash, deepseek-pro]`
```rust
let tars_cfg_str = tars_cfg.to_str()
    .ok_or_else(|| LlmError::Resolve("tars config path is not valid UTF-8".to_string()))?;
```
`LlmError::Resolve(String)` is the stringly-typed-error anti-pattern (one of our
most-fired rules), and the message omits the offending path. Callers must `.contains()`
to branch.

**A5 · Process-global mutable state** — `transport/mod.rs` · `[~ALL 4]`
```rust
fn provider_breakers() -> &'static Mutex<HashMap<String, Breaker>> {
    static REG: OnceLock<Mutex<HashMap<String, Breaker>>> = OnceLock::new(); ...
```
A global circuit-breaker registry that persists across tests and hides coupling.
Convergent (`shadow-state-in-module` / `referential-transparency-violation`).

**A6 · External (LLM) path used unvalidated** — `validators.rs` snippet-grounded · `[gemini-pro, deepseek-pro]`
The `rel` file path comes straight from the (untrusted) LLM response and is used to
read the tree. `security_common::validate-external-input` — a real trust boundary the
two **flash** models both missed.

**A7 · Silent-continue past corrupt own data** — `critic_agent.rs` · `[deepseek-flash ONLY]`
```rust
let entry = match parsed.get(uid) {
    Some(e) if e.is_object() => e,
    _ => continue,            // a malformed finding silently vanishes — no log
};
```
deepseek's signature lens: own-data integrity. A dropped finding leaves no trace.

**A8 · env::var failure modes collapsed** — `env.rs` · `[gemini-pro ONLY]`
```rust
match std::env::var("HOME") {
    Ok(h) if !h.is_empty() => ...,
    _ => PathBuf::from(".tars/config.toml"),   // NotPresent vs NotUnicode vs empty — all the same silent fallback
}
```

**A9 · Verifier swallows parse errors** — `verifier.rs` · `[gemini-flash, gemini-pro]` ·
JSON parse `Err(_)` and confidence `ParseFloatError` both discarded silently.
**A10 · `RewriteFailure::LlmCall(String)`** — `cleanup_rewrite_llm.rs` · `[deepseek-pro, deepseek-flash]` ·
untyped-error-origin at the transport boundary.
**A11 · SQLite store, concurrency pragma** — `pipeline_builder::open_event_stores` ·
`[gemini-flash ONLY]` · gemini's resource lens (note: arc sets WAL in arc_db — verify before acting).
**A12 · Stringly-typed verdict** — `judge.rs` · `[deepseek-pro]` · `VerdictFields.verdict: Option<String>` validated elsewhere.

# Appendix B — five SOFT / won't-fix findings (you be the judge)

All five are *technically valid* rule matches. None is worth a fix. This is the noise
a count rewards and a fix loop would waste turns on.

**B1 · Poison recovery flagged as "swallowed exception"** — `llm_client.rs` · gemini-flash flagged it **8×**
```rust
let mut g = self.inner.structured_output.lock().unwrap_or_else(|e| e.into_inner());
```
Recovering a poisoned mutex guard is a *deliberate resilience idiom* (one thread's
panic shouldn't brick every future lock). Not a swallowed error — and counted eight times.

**B2 · `impl Into<String>` flagged "hot-path-heap-thrash"** — `transport/mod.rs::complete` · gemini-flash
```rust
pub fn complete(env: &LlmCallEnv<'_>, user: impl Into<String>, ...)
```
`impl Into<String>` is THE idiomatic ergonomic-argument pattern, and `complete` runs
once per network call — there is no hot path here.

**B3 · `.unwrap()` in a build script** — `build.rs` · gemini-flash (`no-unwrap-in-library`)
```rust
let entry = entry.expect("read_dir entry");
let stem = path.file_stem().unwrap().to_str().unwrap();
```
`build.rs` is a build script. Panicking on a build error is correct — you *want* the
build to fail loud. The "library" rule doesn't apply.

**B4 · Cold path flagged "hot-path-heap-thrash"** — `critic_agent::json_get_str_or` · gemini-flash
A prompt-building helper run once per finding during a (already network-bound) review.
The `.to_string()` is irrelevant next to the LLM round-trip it feeds.

**B5 · Intentional assert flagged "no-panic-on-input"** — `breaker.rs::new` · gemini-pro, deepseek-pro
```rust
// Both yield a silently dead breaker — assert instead.
assert!(window_size >= 1, "window_size must be >= 1, got {window_size}");
```
The panic is the *documented design choice* — fail loud on a programming error at
construction rather than ship a silently dead breaker. A defensible wontfix (even
two models flagging it doesn't make it actionable).

---

# Step 2 — Thinking mode (does reasoning help *review*?)

Held the model fixed, flipped the thinking channel, re-ran arc_review. (Required a
tars fix first: the openai adapter only spoke vLLM's `chat_template_kwargs`, so
DeepSeek's `thinking:{type}` toggle never reached the wire — now mapped, tars f51b419.)

(Also needed tars 8f45159: the usage parser hardcoded `thinking_tokens: 0`, so DeepSeek
reasoning was never counted — the instrumentation blind spot that made the deepseek runs
below look like "never engaged". With the toggle AND the capture fixed, on/off is now
properly measured.)

| Model | thinking | wall | latency/call | findings (unique) | thinking tok | $/crate |
|---|---|---:|---:|---:|---:|---:|
| gemini-2.5-flash | **off** | 51 s | 2 s | 43 (30) | 0 | $0.30 |
| gemini-2.5-flash | **on (auto)** | **514 s** | 29 s | 42 | 340 K | — |
| **deepseek-v4-flash** | **off (non-think)** | **62 s** | 5 s | **50 (38), 1 ad-hoc** | 0 | **$0.015** |
| deepseek-v4-flash | **on (think)** | 243 s | 32 s | 16 | ~80 K | — |

**Two results — one expected, one that overturns the main benchmark.**

**(1) Thinking does not help review — confirmed on BOTH models, now instrumented.**
gemini-flash + thinking: 10× wall-clock (51→514 s), 340 K thinking tokens, zero findings
gained (42 vs 43). deepseek-flash + thinking: 4× slower (62→243 s, 5→32 s/call) and
**fewer** findings (16 vs 50) for 80 K reasoning tokens. Reasoning is a **FIX-time asset**
(plan a multi-step edit), not a FIND-time one — spotting a swallowed error or a hardcoded
key is pattern recognition, not deliberation.

**(2) ⚠️ The main benchmark mis-measured deepseek-flash — it had thinking ON the whole
time.** DeepSeek's toggle **defaults to enabled**, and the original benchmark ran before
the tars toggle/capture fixes, so its "deepseek-flash" row (305 s, 12 findings, 35 s/call)
was actually **thinking-ON, uninstrumented**. The TRUE *non-thinking* deepseek-flash is a
different animal: **62 s wall (≈ gemini-flash's 51 s), 5 s/call, 50 findings (38 unique),
$0.015/crate — 20× cheaper than gemini-flash ($0.30).** Verified:
`actual_model=deepseek-v4-flash`, empty thinking field, grounded rule-ids.

**Quality (claude-judged the 50, same CORE/SOFT/NOISE bar as §Signal):**

| | unique | **CORE** | SOFT | NOISE |
|---|---:|---:|---:|---:|
| non-thinking deepseek-flash | 38 | **~9** | ~24 | ~10 |
| gemini-flash | 30 | ~7 | ~16 | ~7 (+13 dup) |

deepseek-flash's CORE is slightly *higher* (~9 vs 7) and includes a sharp one gemini
missed — a blocking `std::sync::Mutex` on the async path (`shared-store-concurrency`). But
**it is NOT cleaner** — the earlier "1 ad-hoc" stat was misleading: most of its noise is
*grounded-rule-but-non-actionable*, which the ad-hoc counter doesn't catch. It flagged
`build.rs` `.unwrap()` **6×** while literally writing *"infallible at build time but still
flag"*, flagged code tagged `[arc:intentional-handle]`, and flagged an item that already
carries `#[must_use]`. Its noise floor is the same order as gemini's — just a different
flavor (self-aware build-script spam + flagging-the-intentional, vs gemini's
cold-path-as-hot + an 8× poison-idiom dup). Both need a noise filter.

**So the corrected standing: non-thinking deepseek-flash wins on VALUE, not on
cleanliness.** Slightly higher CORE recall + comparable noise + ≈ gemini speed + **20×
cheaper**. gemini-flash looked like "the §Verdict winner" only because deepseek was
benchmarked with its reasoning channel silently on (slow) and uncounted (looked
weak-and-cheap). The §Verdict / §Cost / §Overlap sections above were computed on that
mis-instrumented deepseek and **under-credit it** — treat this section as the correction
of record. *(Single instrumented run; deepseek's count varies run-to-run, so confirm the
38-unique / ~9-CORE with a repeat before hard-wiring routing — the speed/cost deltas are
structural and safe.)*

**Updated routing:** review (find) → **deepseek-v4-flash, thinking OFF** (set
`thinking="off"` explicitly — the toggle works now); gemini-flash a close, pricier
second. Thinking OFF for ALL review; reasoning only in the fixer. The instrumentation gap
that hid this (DeepSeek reasoning ran but went uncounted) is now fixed.

## Step 2 — Cost / token / price (instrumented, official rates)

Per-run token totals from `pipeline_events`, billed at each model's published rate
(per 1M, fresh-in / out / cache-read): deepseek-flash `$0.14 / $0.28 / $0.0028` ·
gemini-flash `$0.30 / $2.50 / $0.075` · gemini-pro `$1.25 / $10 / $0.31` · deepseek-pro
`$0.435 / $0.87 / $0.0036`. `output_tokens = completion_tokens` (DeepSeek bills reasoning
as output), so these `$` are correct even where the old `thinking_tokens` telemetry read 0.

| Run | calls | in (K) | out (K) | cache (K) | **$/crate** | $/finding | full-repo ×15 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **deepseek-flash · thinking OFF** | 44 | 726 | 19 | 668 | **$0.0153** | **$0.0004** | **$0.23** |
| deepseek-flash · thinking ON | 31 | 510 | 92 | 358 | $0.0479 | $0.0044 | $0.72 |
| gemini-2.5-flash | 65 | 1187 | 25 | 509 | $0.3038 | $0.0101 | $4.56 |
| gemini-pro (3.1) | 28 | 509 | 10 | 220 | $0.5270 | $0.0439 | $7.91 |
| deepseek-pro | 31 | 541 | 126 | 369 | $0.1859 | $0.0186 | $2.79 |

**Headline numbers.**
- **Non-thinking deepseek-flash is the cheapest by an order of magnitude: $0.015 per
  crate, $0.0004 per (unique) finding, $0.23 for the whole repo.** That is **20× cheaper
  than gemini-flash** ($0.30) and **25× cheaper per finding** ($0.0004 vs $0.0101).
- **Thinking's cost premium on deepseek: 3.1×** ($0.015 → $0.048). The driver is output —
  reasoning balloons it from 19 K to 92 K tokens (the step-2 thinking-ON re-run pushed it
  to ~427 K out; reasoning output is highly variable but always multiples of OFF). So
  thinking is *more expensive, slower, AND lower-recall* for review — a clean triple loss.
- **Why deepseek-flash is so cheap:** its cache-read is near-free ($0.0028/M) and its
  output rate is $0.28/M (gemini-flash's output is $2.50/M = ~9×). Non-thinking keeps
  output tiny (19 K), so the bill is dominated by the ~free cached input.
- **Cost ranking (cheapest → priciest per crate):** ds-flash-OFF $0.015 ≪ ds-flash-ON
  $0.048 < ds-pro $0.19 < gemini-flash $0.30 < gemini-pro $0.53.

**Caveat:** single instrumented run each; token counts vary run-to-run (deepseek output
especially). The *structural* deltas — deepseek's ~free cache + cheap output, gemini's 9×
output rate, thinking's output blow-up — are stable; the exact dollars are ±.

## Step 3 — Claude (sonnet-4-5) as reviewer

Same arc_review crate, `critic = claude_sdk` (Agent SDK daemon, `claude login` creds, no
API key). Claude doesn't bill per token (subscription/seat), and its calls don't flow
through the openai/gemini telemetry path, so the comparison is wall-clock + findings +
quality, not tokens/$.

| Model | wall | unique | ad-hoc | ~CORE | $/crate |
|---|---:|---:|---:|---:|---:|
| **claude-sonnet-4-5 (sdk)** | **2392 s (39 min)** | 16 | **0** | **~10** | subscription |
| non-thinking deepseek-flash | 62 s | 38 | 1 | ~9 | $0.015 |
| gemini-2.5-flash | 51 s | 30 | 4 | ~7 | $0.30 |
| gemini-pro (3.1) | 549 s | 12 | 0 | ~8 | $0.53 |
| deepseek-pro | 683 s | 10 | 0 | ~9 | $0.19 |

**Claude is the precision winner — and the throughput loser by a mile.**
- **Highest signal: 16 unique, 0 ad-hoc, ~10 CORE.** Zero ungrounded noise.
- **But 39 minutes** — ~40× slower than gemini/deepseek-flash (51–62 s for the same
  crate). That's `claude_sdk` at ~45 tok/s doing paginated structured review.

### Insight — the "deliberation tail" (the real reason to pay for a slow model)

There is a small CLASS of findings that **only the slow, strong-reasoning models surface,
and the fast flashes structurally miss** — and it's not noise, it's the subtlest real
bugs. Aligning across the whole study:

| Deliberation-class finding | flashes | gem-pro | ds-pro | **claude** |
|---|:-:|:-:|:-:|:-:|
| `validators::validate-external-input` (LLM-path security) | ✗ ✗ | ✓ | ✓ | ✓ |
| `breaker::no-panic-on-input` / `max_retries+1` overflow | ✗ ✗ | ✓ | ✓ | ~ |
| **`breaker::latched-state-outlives-its-cause`** (temporal state-machine) | ✗ ✗ | ✗ | ✗ | **✓ only** |

- **A "deliberation tier" exists** — claude + the two `-pro` models converge on
  security-boundary + temporal/state-machine bugs that NO flash (gemini or deepseek)
  reports. claude goes one further: the latched-state finding is **claude-only across all
  six runs** — a genuinely hard, cross-state temporal bug.
- **This SHARPENS, not contradicts, "thinking doesn't help review."** Toggling thinking
  *on the same flash model* added nothing (Step 2) — a weak model reasoning harder stays
  weak. But a fundamentally **stronger reasoner** (claude, the pro tiers) catches a subtle
  *tail* the flashes can't — ~1–2 unique CORE — **at 10–40× the wall-clock**. So:
  deliberation buys the *tail*, not the *bulk*; the flashes already get the bulk (~9 CORE)
  in 1 minute.
- **Ensemble implication (extends §Overlap):** claude is the **deep-reasoning lens** of
  the ensemble — the one that catches temporal/state-machine subtlety. The ideal coverage
  is *flash for the bulk, fast + cheap* + *one slow strong model (claude or a pro) for the
  deliberation tail on high-stakes code*. Each lens is real; none is redundant.

### Worked example — `latched-state-outlives-its-cause` (the claude-only finding)

The actual code claude flagged, `crates/arc_review/src/breaker.rs` (a circuit breaker).
Module doc, line 5: *"OPEN — calls short-circuit with CircuitOpenError."*

```rust
pub enum State { Closed, Open, HalfOpen }

/// How many attempts the caller should make for the next invocation.
/// In half_open: exactly one probe. Otherwise: `max_retries + 1`.
pub fn max_attempts(&self, max_retries: usize) -> usize {
    match self.state {
        State::HalfOpen => 1,
        _ => max_retries + 1,          // ← Closed AND **Open** both land here
    }
}

fn trip(&mut self, now: Instant) {     // breaker trips when failures ≥ threshold
    self.state = State::Open;          // the LATCH is set
    self.opened_at = Some(now);
    self.window.clear();               // the CAUSE (the failure count) is erased
}
```

**What "latched-state-outlives-its-cause" means.** A state machine sets a sticky state
(the *latch*) when some condition (the *cause*) fires; the cause then clears, but the
latch deliberately persists — and somewhere the code fails to *honor* the latch, behaving
as if it were the default state. The state outlives its cause yet doesn't enforce its own
meaning.

**Here, concretely:** `trip()` sets `State::Open` (the latch) and immediately
`window.clear()`s the failures that caused it. `State::Open` is supposed to mean
"short-circuit — block calls" (the doc). But `max_attempts` lumps `Open` into the `_ =>`
arm with `Closed`, so a **tripped, open breaker hands back a full `max_retries + 1` retry
budget — identical to a healthy one.** A caller that trusts `max_attempts` to gate will
run a full retry loop against the very dependency the breaker just declared *down*. The
latch is set but toothless in the one function that allocates work; the open state's
authority is silently delegated to a caller who "may not enforce it" (claude's words).

**Why this is the deliberation tail.** It is invisible to pattern-matching. Catching it
requires tracing the *state machine* (Closed/Open/HalfOpen + `trip` + cooldown), noticing
`Open` falls into the catch-all arm, AND cross-checking the module doc's "Open
short-circuits" contract against what `max_attempts` returns. Note the same function is
where **deepseek-pro** independently flagged the `max_retries + 1` *integer overflow* — a
different sophisticated lens on the same hot-spot: deepseek saw the *arithmetic*, claude
saw the *state-machine semantics*, and every flash saw neither.

**Verdict: Claude is a *deep-audit* model, not a routine reviewer.** Its quality matches
or beats deepseek-pro, but at 3–5× deepseek-pro's wall-clock and gated behind a Claude
seat. The earlier "claude finds bugs poorly" prior is **half-corrected**: claude's
*precision is the best measured*; its problem is *speed*, not quality. This is consistent
with the whole study's lesson — Claude's strength is deliberation (sophisticated,
cross-function, state-machine reasoning), which is a **fix-time / deep-audit** asset, not
a fast-find one. Keep routine review on non-thinking deepseek-flash; reach for Claude only
for a high-stakes one-shot audit where 40 minutes is acceptable.

### Transport — `claude_sdk` ≫ `claude_cli` (don't use the CLI)

Ran `critic = claude_cli` (same sonnet-4-5, but each call is a fresh `claude -p`
subprocess instead of the warm SDK daemon). **Killed after 11.5 min with 0/16 files done**
— pathologically slow, projecting 45–60 min+ vs the SDK's 39. Two structural reasons,
both visible in the run:

- **Cold subprocess per call.** `claude_sdk` warm-pools one Node daemon (`claude login`
  creds, reused across calls); `claude_cli` spins up a brand-new `claude -p -
  --output-format json` process for every file (4 alive at once at concurrency 4),
  each idle-waiting on a fully-buffered (non-streaming) response.
- **No structured-output capability** (logged 4×: *"provider 'claude_cli' has no
  structured-output capability — using prompt-based JSON"*) — so the model free-writes the
  findings JSON in prose, which is longer and flakier to parse than the SDK's schema path.

**Findings would be ≈ `claude_sdk`'s (same model), so nothing analytic is lost by
stopping.** The transport verdict stands on its own: **for Claude-as-reviewer use the SDK
daemon, never the CLI** — and Claude review is a deep-audit-only path regardless (§Step 3).

**Caveat (observed, 2026-06-11).** In this run `claude_cli` was far slower than the SDK
path at the same task — a transport-level difference, not an arc-side change (arc's
invocation is identical for both). The takeaway is simply: for Claude-as-reviewer, prefer
the SDK daemon over per-call subprocesses.
