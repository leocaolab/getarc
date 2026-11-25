---
name: brainstorm
description: Record a design/architecture discussion as a faithful brainstorm document — the directions explored (讨论方向), each with its pro/con, who argued what (参与者及其意见), the final decisions (最终决定), and a raw attributed transcript (历史对话记录). Use when the user says "brainstorm", "写 brainstorm 文档", "记下/存档这个讨论", "把上面的讨论存成文档", or otherwise wants a design debate captured as a durable discussion log rather than a polished spec.
---

# Brainstorm

Capture a real design discussion as a **faithful discussion record** — not a sanitized spec.
The whole value of a brainstorm doc is that a future reader sees the **path**: which
directions were explored, what each traded off, who argued what, where someone was wrong
and got corrected, and what was finally decided. A conclusion with the reasoning and the
dead-ends erased is worth far less — often the reversal is the most valuable line in the doc.

This is the sibling of the `design` skill. `design` produces a development-ready spec (you
*implement from it*); `brainstorm` produces the **discussion behind** such a spec (you
*understand why it is what it is*). A brainstorm doc often graduates into a design doc later,
and may seed a retro or a blog post — so it must be durable and honest.

## Modes — pick from the request

- **New** (default) — "brainstorm X", "写 X 的 brainstorm" → start a new brainstorm doc for a topic.
- **Continue** — "继续/追加到 brainstorm", "brainstorm 文档 2" → append a new thread/section to an
  existing brainstorm doc (a discussion that resumed, or a distinct sub-topic). **Keep every
  earlier section byte-unchanged** — the raw record is append-only, like the discussion itself;
  a reader must be able to see that a question was raised, argued, and possibly reversed *in place*.

If the topic or which doc to continue is ambiguous, state your read in one line and proceed
(the user prefers a prose decision over a choice-card poll); only hard-stop if genuinely blocked.

## Operating principles (these are why the doc is worth anything)

1. **Faithful raw record — corrections stay IN.** Never sanitize. If a position was argued and
   then overturned, record BOTH and the turn between them. Reversals ("that's wrong", "no such
   concept", an idea killed on a second look) are the most valuable part — they mark exactly where
   intuition failed. Deleting them re-hides the trap for the next reader. Do **not** "clean up" an
   earlier section into the final answer; append the correction as its own beat.

2. **Attribute at the source (参与者及其意见).** Every non-trivial opinion is tagged with WHO held
   it — the maintainer, Claude, or an external source (e.g. a pasted Gemini/other-LLM brainstorm).
   Never blend positions into a faceless "we decided". A reader must be able to tell the
   maintainer's call from an external suggestion from Claude's synthesis — and especially which
   external suggestions were **adopted** vs **rejected**. (This is the write-at-source rule applied
   to discussion: the producer's own words, recorded at the moment, not multiplexed onto a shared
   blob and demuxed later.)

3. **Every direction carries pro/con + a verdict.** A direction with no cons is a red flag that you
   flattened it. Each direction ends in exactly one of: **DECIDED** (+ why this beat the
   alternatives), **OPEN** (+ what evidence/experiment would settle it), or **PARKED**.

4. **Ground claims; mark status.** When a claim references code, cite `file:line`. Distinguish
   what is ENFORCED/real today from what is ASPIRATIONAL/proposed — an un-backed claim recorded as
   fact is a future landmine (a reader will act on it). If a "decision" has no code behind it yet,
   label it as intent, not done.

5. **Directions for navigation, chronology for truth.** The top of the doc is organized by
   DIRECTION so it's navigable; the raw, ordered back-and-forth is preserved at the bottom as the
   primary source. The upper sections are an *index into* the transcript, not a replacement for it.

## Document structure (every section, in order)

Write to `<docs-dir>/design/<topic>-brainstorm.md` (match the repo's docs convention; number
siblings when it's a series — `<topic>-brainstorm.md`, `<topic>-brainstorm-2.md`, …). The doc
follows the repository's prevailing doc language.

1. **Header / meta.** Topic; date(s); **participants** (name + role, e.g. *maintainer*, *Claude*,
   *Gemini (pasted)*); status (`live` / `settled` / `superseded`); a one-line "what this is".

2. **TL;DR — final decisions (最终决定).** The landings, up top, as a short list. Each: the
   decision + a one-line why. A reader in a hurry stops here. Mark any that are intent-not-yet-built.

3. **Participants & positions (参与者/意见).** The cast list: who was in the room and their overall
   stance/bias — e.g. "maintainer — pushed X, rejected Y, demanded the computation angle";
   "Gemini (pasted) — proposed Z, partially adopted, one claim overturned"; "Claude — synthesized,
   corrected twice". This makes the attributions in §4 legible at a glance.

4. **Directions discussed (讨论方向).** The heart of the doc. One subsection per direction/fork.
   Each contains:
   - **The question** — what fork was being decided.
   - **Options** — the candidate answers.
   - **Pro / con** — a table or paired list, per option. Honest cons for *every* option (see
     principle 3).
   - **Positions** — who argued for what, attributed (see principle 2).
   - **Verdict** — DECIDED (why it won) / OPEN (what would settle it) / PARKED. If it was decided by
     reversing an earlier view, say so and point to that beat in §7.
   - **Evidence grade (依据)** — every DECIDED verdict is tagged with what it stands on:
     **推理** (argued; no run) / **先例** (settled by reading source or our own prior runs —
     cite `file:line` or the run) / **实测** (measured here). No confidence numbers — fake
     precision. Discipline: a 推理-grade DECIDED is **provisional** until its kill-run passes
     (route it in §6); and if any premise in its chain is a claim about *model behavior*
     ("the LLM will/won't X") or rests only on web testimony, the verdict auto-demotes to
     needs-run — however clean the reasoning reads.

5. **Open questions / parked.** What's unresolved, and for each, the evidence or experiment that
   would resolve it.

6. **Next step (出口 — route the outcome).** The doc's exit is a **recommendation for what
   happens next**, judged by what the load-bearing claims stand on:
   - **→ Spike / PoC first** — some load-bearing premise is a *third-party technology's behavior
     in OUR usage shape* (FFI/GIL/serialization boundaries, version combos…) and the only
     evidence is **testimony** (web docs, blogs, READMEs — someone else's happy path). Criteria:
     load-bearing + no fallback without redesign + testimony-only. Discipline: the spike is
     **M0, risk-first** in the design doc; define the pass/fail 判据 *before* running; findings
     reconcile back into the design doc; spike code is **evidence, disposable** — it must not
     become the implementation by inertia.
   - **→ MVP / kill-run first** — some DECIDED-by-推理 claim has a premise about **LLM behavior,
     runtime magnitudes, or transfer to our setting**, being wrong is expensive downstream, and a
     discriminating run cheaper than building the real thing exists. Emit the experiment list:
     `{ claim / the assumption it rests on / cheapest kill-run / 判据 }`. If the discriminating
     run costs as much as building — build instrumented instead.
   - **→ Straight to design doc** — every load-bearing claim is settled by logic (辩死), by
     reading source / our own prior runs (查死), or is a value commitment (判死). Nothing to run;
     invoke `design`.
   - **Deadlock rule:** if directions could not be ranked after honest argument, the deadlock
     itself is the signal — the discriminating variable is not in the argument space. Stop
     debating; route to the smallest run that forces the answer.

7. **Raw conversation record (历史对话记录).** The faithful, attributed, ordered back-and-forth —
   challenge → pushback → reframe → landing, corrections visible. This is the primary source;
   §§2–6 are its index. Lightly clean for readability (typos, obvious cruft) but do **not** re-argue,
   de-bias, or merge away the reversals. Quote long or load-bearing positions verbatim, attributed.

## Output conventions

- **Write to disk; report the path.** Don't dump the whole doc into chat — summarize what you
  produced and link the file.
- **One topic per doc.** Continue a thread by APPENDING a section; never rewrite earlier ones.
- **Cross-link the siblings** — other brainstorm docs in the series, the design doc it feeds, the
  retro it may seed.
- **Commit + push** when the repo convention expects it — these docs often seed a later post or
  retro, so keep them durable and versioned.
- Use `file_path:line` for every reference to real code.
