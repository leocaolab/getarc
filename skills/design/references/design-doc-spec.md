# Design-doc spec — per-section quality bar + skeleton

Load this when writing Phase 1. It defines what "good" looks like for each
section and gives a copy-paste skeleton. The goal is a doc an engineer can
**implement from directly**, not a vision statement.

## The quality bar, section by section

- **Overview & goal** — 1 paragraph. State the non-goals explicitly; a design
  is defined as much by what it refuses to do.
- **CUJs** — concrete, not abstract. "A user runs `x do-thing` on a dirty repo
  and sees a diff preview before anything is written" — not "users can do
  things". Each CUJ is a journey with a beginning and a success end. Number
  them; everything downstream traces back to a CUJ.
- **Feature list** — each row tagged with the CUJ(s) it serves. If a feature
  serves no CUJ, cut it or add the missing CUJ. If a CUJ has no feature, the
  list is incomplete.
- **Requirements** — `FR-n` functional, `NFR-n` non-functional. NFRs must be
  *measurable* ("p95 < 200ms for the warm path", not "fast"). Each traces to a
  feature.
- **Infra** — be honest about what exists vs. what's new; new infra is a cost,
  flag it.
- **Components** — the heart of the doc. Each component MUST list the existing
  code it reuses with `file:line`, what's genuinely new, and a real interface
  (signatures, not prose). A component with no reuse line is suspicious — did
  you check?
- **Interfaces with other modules** — both directions, with real signatures.
  This is where integration bugs are prevented or planted.
- **Main algorithms** — only the non-trivial parts. Pseudocode or numbered
  steps. State invariants ("the registry is never observed half-updated") and
  the edge cases you handle (empty input, cancellation, concurrent calls).
- **Integration / E2E tests** — every CUJ → ≥1 test. setup → action →
  assertion. These become the milestone acceptance gates in the roadmap.
- **Success criteria** — measurable; the union of "all FRs met" + the NFR
  thresholds + "every CUJ's E2E test passes".
- **Performance / Reliability / Security** — each is a real section, not a
  sentence. Performance: hot paths + budgets + what to measure. Reliability:
  failure modes + recovery + idempotency + fail-closed. Security: trust
  boundaries + input validation + authz + sandboxing + secrets.
- **Abstraction & reuse** — the abstraction approach + the full reuse map +
  the new abstractions and their justification. This is the section the user
  explicitly asked for: *which existing functions can be reused/called* — make
  it exhaustive and `file:line`-precise.

## Skeleton (copy, then fill — keep the IDs)

```markdown
# Design — <Feature>

> Status: design, <date>. Author: <you>. Implements: <link to parent doc/issue>.

## 1. Overview & goal
<what, why>. **Non-goals:** <list>.

## 2. Critical User Journeys (CUJs)
- **CUJ-1 — <name>.** Actor: <>. Trigger: <>. Steps: <1→2→3>. Success: <>.
- **CUJ-2 — …**

## 3. Feature list
| Feature | Serves | Notes |
|---|---|---|
| F1 — <> | CUJ-1 | <> |

## 4. Requirements
**Functional**
| # | Requirement | Feature |
|---|---|---|
| FR-1 | <> | F1 |

**Non-functional** (measurable)
| # | Requirement | Threshold | Feature |
|---|---|---|---|
| NFR-1 | latency | p95 < <n>ms warm | F1 |

## 5. Infra
| Need | Exists? | Where / new |
|---|---|---|
| <> | ✅/➕ | `path` or "new" |

## 6. Components
### C1 — <name>
- **Responsibility:** <>.
- **Reuses:** `path:line` (<symbol> — <how>), …
- **New:** <>.
- **Interface:**
  ```rust
  // real signatures
  ```

## 7. Interfaces with other modules
| Direction | Module | Symbol / signature | Purpose |
|---|---|---|---|
| calls → | <mod> | `fn …` (`path:line`) | <> |
| ← called by | <mod> | `…` | <> |

## 8. Main algorithms
### <algorithm name>
```
1. …
2. …
```
Invariants: <>. Edge cases: <>.

## 9. Integration / E2E tests
| Test | CUJ | Setup → Action → Assertion |
|---|---|---|
| E2E-1 | CUJ-1 | <> |

## 10. Success criteria
- [ ] All FR-* met.
- [ ] NFR-* thresholds hit (§4).
- [ ] Every CUJ's E2E test passes (§9).

## 11. Performance considerations
Hot paths: <>. Budgets: <>. Measure: <>.

## 12. Reliability considerations
Failure modes: <>. Recovery / idempotency: <>. Fail-closed defaults: <>.

## 13. Security considerations
Trust boundaries: <>. Validate: <>. Authz / sandbox / secrets: <>.

## 14. Abstraction & reuse
Approach: <>.
**Reuse map** (existing code to call):
| Symbol | Location | How we use it |
|---|---|---|
| <> | `path:line` | <> |
**New abstractions:** <what, and why each is justified>.

```

## Common failure modes to avoid

- Sections that restate the request instead of deciding something.
- Components with no `file:line` reuse references (you didn't ground).
- CUJs with no test, or tests with no CUJ (broken traceability).
- "Fast / reliable / secure" with no number, mechanism, or boundary.
- Inventing a new abstraction where an existing trait/type would do — the
  Reuse map exists to catch exactly this.
- Re-designing a feature that already has a sibling (an existing report, page,
  or event kind) instead of extending it.
- A decision written without the owner's words, or an inference written as decided.
- A new stored value (enum variant, config key, event kind) with no line on how
  the running old binary reads it.
- A fact written in two places, or rebuilt downstream from derived state.
