---
name: shift-left-swift
description: How to WRITE genuinely clean Swift — universal good-code principles in Swift idiom (value types, enums with associated values, typed throws, SwiftPM targets, structured concurrency, SwiftUI shells), stated in full so the skill is self-contained and portable (works in any repo; nothing else needed). The positive form of common review anti-patterns, so the code is clean the FIRST time, plus how a Haskell-style model (data types + signatures first) translates into Swift and where the translation drifts. The aim is the principle itself, not passing any linter. Load before writing or editing Swift (a fix, a new function, any codegen). Triggers include writing/editing .swift or Package.swift, "fix this Swift", "add a Swift function", "SwiftUI view model".
---

# Writing clean Swift (shift-left)

The goal in one line: **write the version the next reader — human or model — can
extend without re-reading the whole thing.** Clear structure = the correct next
line is obvious. Checklist, not an essay.

> **The target is the principle, not passing a reviewer.** Every rule is stated in full
> here, so it works in any repo. A `stem::name` in parentheses names the review-rubric
> rule this one mirrors; the full rule, with its reason and examples, is in the arc-skills
> plugin's `rubrics/<stem>.yaml` — open it when you want more, never because you must.
> Never write code merely to keep a detector quiet — a linter with finite recall
> going silent is not proof the code is clean; gaming its blind spots is the failure.

## Model first: Haskell → Swift

Write the model before the code: data types and signatures in a `model.hs` (it need not
compile), one sentence per function saying what it turns into what; then translate. Swift
takes this translation better than most mainstream languages, because it has real sum
types, value semantics and exhaustive `switch`:

| Haskell model | Swift |
|---|---|
| `data S = A \| B x \| C { f :: y }` (sum) | `enum S { case a; case b(X); case c(f: Y) }` |
| `data P = P { a :: A, b :: B }` (product) | `struct P { let a: A; let b: B }` |
| recursive `data T = Leaf \| Node T T` | `indirect enum T { case leaf; case node(T, T) }` |
| `newtype D = D Double` with an invariant | `struct D { let seconds: Double; init?(seconds:) }` with no other initializer |
| smart constructor `mk :: … -> Either E X` | `private init` + `static func make(…) -> Result<X, E>` (or `init(…) throws(E)`) |
| `Maybe a` / `Either e a` | `A?` / `Result<A, E>` — note the parameter order flips — or `throws(E)` |
| `step :: S -> Ev -> (S, [Eff])` | a free `func step(_ s: S, _ e: Ev) -> (S, [Eff])` in a target with no IO |
| `IO (Either E a)` | `func f() throws(E) -> A`, or `async -> Result<A, E>` |
| the shell that folds `step` over IO | a `final class` (often `@MainActor`, observable) that holds the state and runs the effects |
| module = the set of things it may import | a SwiftPM target; its `dependencies:` are the only modules it can see |

Check after translating: every Swift type and function has its prototype in the model, and
every model line landed.

**What Swift has, and what it lacks.** Swift has complete ADTs: enums with associated
values, `indirect` enums for recursion, structs, and a `switch` the compiler checks for
exhaustiveness. It has **no GADTs and no higher-kinded types** — you cannot write
`data Expr a where IntE :: Int -> Expr Int`, nor abstract over `F<_>` (no `Functor f`). The
approximations, in order of how often they pay off:

- **Phantom type + constrained extension** — a type parameter that only marks a state, with
  methods that exist only for one marker: `struct Handle<State> { … }`, `enum Open {}`,
  `extension Handle where State == Open { func read() -> Data }`.
- **`~Copyable` + `consuming` typestate** (Swift 5.9+) — a value that can be used once:
  `struct Connection: ~Copyable { consuming func close() -> ClosedConnection }`; after
  `close()` the compiler refuses any further use of the old value.
- **Protocol with an associated type** — one type per family member, with the family's
  shape in the protocol (`protocol Request { associatedtype Reply: Decodable }`); this is the
  nearest thing to a GADT's "the index decides the result type".

**When enum + `step`, when typestate.** Events that arrive at run time, asynchronously, in
an order the compiler cannot know (a permission dialog answered late, a delegate callback
after stop, a server reply) → an `enum` state and a pure `step`; the type system cannot
rule those out, so `step` must answer every pair. A resource API whose call order is known
when you write the call site (open → write → close; build → send) → typestate (phantom or
`~Copyable`), so the wrong order does not compile.

**Where the translation drifts** — each has a rule below:
- `default:` in `step` turns a total function into one that silently ignores every future case (item 9).
- `public` on everything, because Swift's default `internal` stops at the target edge (item 21).
- Synthesized `Codable` bypasses the smart constructor (item 6).
- Haskell's effect types have no Swift counterpart: a `func` may do IO without saying so; only the target edge proves purity, and `Foundation` is a hole in it (item 1).
- SwiftUI wants a mutable reference object; the model has none — keep it a shell around the pure `step` (item 15).

## Separate decisions from mechanism (not only IO from logic)

A decision is a function of the facts it decides on — scalars, small value types, arrays in; a
decision out. Everything that stores, moves, accumulates, queues or times data is
**mechanism**: IO is one kind; buffers, collections held in an object, queues, timers and
clocks are others. Mechanism calls decisions; decisions never touch mechanism. The test of
the shape: the decision's signature has no `inout`, no class reference and no `async`, and its
boundary tests take only values.

1. **Put the pure core in its own SwiftPM target, and let the manifest prove it.** The core
   target lists no dependencies and imports no `AVFoundation` / `SQLite3` / `SwiftUI` /
   networking package; the adapters and the app depend on it, never the other way. A target
   that needs no `import Foundation` at all is the strongest proof. When it needs `Date`,
   `UUID` or `Data`, `Foundation` also brings `FileManager`, `URLSession`, `Date()` and
   `UUID()` — those stay out by review: grep the core for them.
   - ❌ one target where `RecordingLibrary.swift` and `step` sit side by side, so `step` can call `FileManager` and nothing notices
   - ✅ `.target(name: "Core")`, `.target(name: "Storage", dependencies: ["Core"])`, `.executableTarget(name: "App", dependencies: ["Core", "Storage"])`
2. **Fetch, then decide.** An `async` adapter materializes the data; a *pure sync* function computes.
   - ❌ `for u in items { let s = try await store.hash(u.path); if s == current { keep.append(u) } }`
   - ✅ `let rows = try await store.hashes(of: items)` → `let (keep, skip) = partition(rows, current: current)`
3. **A decider returns a plan; it does not do the IO.** Effects are an `enum` the shell runs. (`fp_lens::decision-executes-its-own-effect`)
   - ❌ `case (.recording(let t), .stopRequested): recorder.stop(); library.adopt(file, t)`
   - ✅ `case (.recording(let t), .stopRequested): return (.saving, [.finishCapture(recordedAt: t)])`
4. **Clocks and ids come in as arguments.** `Date()` and `UUID()` are effects; the shell reads them and passes them to the core (`.captureStarted(at: Date())`).

## Type your data and errors

5. **Named `struct`, not a tuple or `[String: Any]`,** across a boundary. A private tuple whose member types already say what each is may stay unnamed; across a target or `public` boundary, name it. (`llm_generated_code_smells::untyped-bag-across-boundary`)
   - **Fields that come and go together are one value.** Two optionals that are always both set or both `nil` are one `Optional<Struct>`.
   - **A field that exists only in one state lives in that case,** not beside the enum as an optional (`case recording(startedAt: Date)`, not `state` + `startedAt: Date?`). (`l5_architecture::l5-P-illegal-states-unrepresentable`)
6. **Parse at the edge with `Codable`, not `JSONSerialization`.** `JSONSerialization` + `[String: Any]` + `as?` casts is the untyped path, and it has a trap: values come back as `NSNumber`, so `json["exitCode"] as? Int` accepts `true` as `1`, and `as? Double` accepts `true` as `1.0`. `JSONDecoder` refuses a Bool where an `Int` is declared, and its `DecodingError` names the path. Decode into a `private` DTO struct in the adapter, then convert to the domain type. (`swift_best_practices::untyped-json-at-boundary`, `l5_architecture::l5-O-parse-dont-validate`)
   - ❌ `guard let code = json["exit_code"] as? Int, let stderr = json["stderr"] as? String else { return nil }`
   - ✅ `private struct ProcessFailedDTO: Decodable { let exitCode: Int; let stderr: String }` with `decoder.keyDecodingStrategy = .convertFromSnakeCase`
   - A tagged union on the wire (`{"kind": "timed_out", …}`) is a hand-written `init(from:)` that switches on `kind` once; an unknown `kind` throws with the word it got.
   - **Synthesized `Decodable` bypasses your smart constructor.** It assigns the stored properties directly, even when the only `init` is `private`, so `{"start": 3, "end": 2}` decodes into an `Excerpt` that `make` would refuse. A type with an invariant writes `init(from:)` that decodes the raw fields and calls `make`: `self = try Excerpt.make(start: s, end: e).get()`. (`swift_best_practices::synthesized-decodable-skips-invariant`)
   - **A synthesized `Codable` enum is a stored format.** `case computing(ServerID)` encodes as `{"computing":{"_0":…}}`: renaming a case or adding a label changes what is on disk. A round-trip test (`decode(encode(x)) == x`) survives the rename and the old rows still break; pin the stored form with a literal sample written by the old encoder, or write `CodingKeys` by hand. (`swift_best_practices::synthesized-codable-enum-stored-unpinned`)
7. **Typed errors: an `enum` conforming to `Error` per domain, carrying the raw words;** `throws(E)` (SE-0413: needs a Swift 6 compiler, and works under a `swift-tools-version: 5.9` manifest in Swift 5 language mode) where the caller branches on the cause. Never `Error` stringified at a boundary. (`l4_contracts::untyped-error-origin`, `type_design::error-kind-in-a-string`)
   - ❌ `throw NSError(domain: "lib", code: 1, userInfo: [NSLocalizedDescriptionKey: "move failed"])`
   - ✅ `case transferFailed(from: String, to: String, systemMessage: String)`
   - **Shape the error by what the caller does with it.** A case per way a caller handles it; a failure every caller only shows is one struct with the sentence and the system's message.
   - **Keep each foreign `do` narrow.** A `do` block that mixes your typed throws with an untyped system call erases your type, and you end up rescuing it with `catch let f as MyFailure { throw f }`. Wrap each system call in its own `do`/`catch` that maps to your case; then the outer function stays `throws(MyFailure)` without the rescue.
   - **"Not mine" is `nil`, not an error.** `compactMap` skips it.
   - **A failable `init?` drops the reason.** Use it only when there is exactly one way to fail (`PositiveDuration(seconds:)`); with two or more, return `Result<T, E>` or `throws(E)`.
8. **Closed set → `enum`,** not a `String` compared at run time. Words on the wire come from the enum's raw values (`enum Source: String { case recorded, imported }`, parsed once with `Source(rawValue:)`), not from a `switch` to string literals.

## Don't swallow, don't hide

9. **No `default:` on your own closed enum.** `default` turns off the exhaustiveness check: the next case you add is silently treated as "nothing happens" everywhere. List the pairs that are ignored, so a new case is a compile error until someone decides. `default:` is right only on an open set — an `Int` status code, a `String` from outside, argv. A system enum you do not own and that is not `@frozen` gets `@unknown default`, which still warns when a known case is missing. (`swift_best_practices::default-arm-on-own-closed-enum`, `fp_lens::total-seeming-pattern-match`)
   - ❌ `switch (state, event) { case (.idle, .startRequested): …; default: return (state, []) }`
   - ✅ `case (.uploading, .polled), (.computing, .submitted), (.done, _), (.failed, _): return (state, [])`
10. **No `!`, `try!`, `as!`, `fatalError`, `precondition` in library or core code** — return a typed error and let the caller decide. Walk every optional and every `throws` through four steps before you unbox: (`swift_best_practices::trap-on-fallible-value`)
    1. **Can the `nil` / error happen in the real world?** IO, external input, state that changed between two calls, ordering of async callbacks, platform and sandbox differences.
    2. **It can → throw or return it**, carrying the raw input and the system's message, to the layer that can decide.
    3. **It can't, but the compiler doesn't know → change the shape:** check-then-take (`if dict[k] != nil { dict[k]! }`) → `if let` / `guard let`; looking an id up again → pass the value you already found; an API returning an optional array whose `first` you force → the API that throws (`FileManager.default.url(for:in:appropriateFor:create:)` instead of `urls(for:in:).first!` plus a separate `createDirectory`).
       - ❌ `let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!` then `try? FileManager.default.createDirectory(at: base, …)`
       - ✅ `try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true)` inside `do`/`catch` that maps to `.directoryUnavailable(path:systemMessage:)`
    4. **The type can't change** → `guard let x else { preconditionFailure("<proof>") }`, the message a proof a reviewer can check. This is the only exemption.
    - **When a trap is allowed:** startup code before the app serves (only the outermost decides to die), and tests (`try #require(…)`). Never on external input; never in steady state — show the failure and isolate the smallest unit (this request, this take).
11. **No `try?` that drops the reason.** `try?` is `let _ =` for errors: the failure becomes `nil` and the message is gone. Use it only when `nil` is the whole truth and the raw input travels on (the caller reports the body it could not parse) — otherwise `do`/`catch` and keep `error`. (`swift_best_practices::try-optional-drops-the-error`, `l4_contracts::swallowed-exception`)
    - ❌ `catch { return nil }` followed by `copyIntoLibrary(url) ?? url` — the copy failed and the app silently keeps the original URL
    - ✅ `catch { throw .transferFailed(from: src.path, to: dest.path, systemMessage: error.localizedDescription) }`
    - **Degrading is the caller's decision.** A library that falls back by itself runs its caller degraded with nobody knowing. (`l4_contracts::silent-default-on-config-miss`)
    - Stored rows that do not decode are kept and shown with their defect (`UnreadableRow(row:defect:)`), never skipped. (`l4_contracts::silent-continue-past-corrupt-own-data`)
12. **An error inside `Task { }` disappears.** A `Task` whose body throws stores the error in its `value`; nobody awaits it, so the failure vanishes — the same as a panic inside `tokio::spawn`. Give every unstructured `Task` a non-throwing body that turns the failure into state the user sees, or return the `Task` so the caller can await it. Prefer structured concurrency (`async let`, `withTaskGroup`) where the parent waits. (`swift_best_practices::error-lost-in-unstructured-task`)
    - ❌ `Task { try await runner.upload(take) }`
    - ✅ `Task { switch await server.submit(…) { case .failure(let f): trouble[id] = f; case .success(let r): … } }`
    - **Cancellation is not a failure.** `Task.sleep` throws only `CancellationError`; stop quietly on it, don't show it, and don't retry past it. (`effect_state::cancellation-signal-swallowed`)

## Concurrency and the UI shell

13. **Value types by default; `class` only for something with identity and a lifetime** — a connection, a recorder, the observable object a view watches. Domain data is `struct` and `enum`, `let` unless the model says it changes. Mark them `Sendable`; a `public` type never gets `Sendable` inferred, so say it. (`l5_architecture::l5-J-immutability-and-data-flow`)
14. **Isolate the shell, not the core.** The observable shell is `@MainActor final class`; the core is plain functions on values and needs no actor. A non-`Sendable` adapter class (an SQLite handle) lives inside one isolation domain — owned by a `@MainActor` object or turned into an `actor` — and "use it from one thread" is a type, not a comment. Build in Swift 6 language mode (or `-strict-concurrency=complete`) so the compiler checks it. (`swift_best_practices::non-sendable-state-shared-across-isolation`, `effect_state::shared-mutable-state-in-decision-layer`)
    - Delegate callbacks arrive on other threads and out of order: mark them `nonisolated`, hop with `Task { @MainActor in self.send(event) }`, and let the pure `step` ignore an event that no longer applies — that is why `step` must answer every pair.
    - Blocking work (decoding a long audio file) goes to `Task.detached` and comes back as a value; the main actor never blocks.
15. **SwiftUI state is the shell around a pure reducer.** The `ObservableObject` / `@Observable` object holds the current state, calls `step`, stores the result, runs the effects. The view reads state and sends events; it does not decide. A `switch` in a view body chooses what to draw, never what happens next. (`swift_best_practices::decision-in-swiftui-view`, `fp_lens::core-buried-outward`)
    - ❌ `Button("Stop") { if recorder.isRecording && file != nil { library.adopt(file!) } }`
    - ✅ `Button("Stop") { recorder.send(.stopRequested) }`
    - Store first, then memory: when a state is persisted, write it, and only on success replace the published copy — the screen never shows what the disk does not have.
16. **Break reference cycles where an owner holds a closure that captures it.** An object that stores a closure capturing `self` (a child built with a callback to its owner) uses `[weak self]`; a short-lived `Task` or a `Timer` you invalidate may capture strongly. (`swift_best_practices::owner-closure-captures-self-strongly`)

## Subtract, don't patch

17. **`map` / `filter` / `compactMap` over a mutable accumulator** when clearer.
18. **`let x = c ? a : b` / `guard let … else { return }`,** not `var x: T?` assigned in branches.
19. **Explicit `enum State` + `switch`,** not a few `Bool` flags mutated across a loop. (`l5_architecture::l5-Q-loop-is-state-machine`)
20. **Test boundaries with Swift Testing.** `@Test(arguments: […])` runs one pure decision on both sides of a line (`0.4, 0.4` is a click, not an excerpt); `#expect(throws: E.case)` pins the error; `try #require(x)` unwraps in a test. Tests feed facts to decisions; a decision you can only test through an object with a timer is still buried in mechanism. (`test_quality::happy-path-only-enumeration`)

## Place types by owner

Before adding a type: **say in one sentence what it is — if you can't, it isn't needed**; type
names are nouns (`RecorderState`, `CaptureFailure`), cases say the state or the cause
(`.microphoneDenied`, `.endedUnexpectedly`); no `Manager` / `Helper` / `Util` / `Data` / `Info`.

21. **Narrowest access that compiles: `private` → `fileprivate` → `internal` → `package` → `public`.** Swift's default `internal` stops at the target edge, so a multi-target package pushes everything to `public`. Inside one package, use `package` (SwiftPM 5.9+, SE-0386): visible to the package's other targets, invisible to anyone who depends on the package. `public` is for a library product other packages import. (`swift_best_practices::public-where-package-suffices`, `type_design::type-visibility-wider-than-its-use`)
    - ❌ `public enum LibraryFailure` in a package with no `products:` — nobody outside can import it
    - ✅ `package enum LibraryFailure`
    - **Fields too.** A type with an invariant has `let` fields and a `private init`; the one way in is `make` / `init?` / `init(from:)` through `make`. `public var` on an invariant field lets any caller break it.
22. **Owner's target, not the reader's.** A type lives where its lifecycle is produced; readers depend on the owner. Two domains that share a `typealias ID = String` get two structs and one conversion at the boundary. (`type_design::type-lives-away-from-its-owner`)
23. **Adapter types stay in the adapter.** A database row (`RawRow` exactly as SQLite returned it), an HTTP DTO, a CLI report belong to their adapter; a pure `decode(_:) -> Result<Domain, Unreadable>` converts once. A row never reaches the core.

## Fluency (流畅) — one altitude, one job, one railway

24. **One level of abstraction per function.** Push `URLRequest` assembly, `NSLog`, string formatting into named helpers. (`llm_generated_code_smells::mixed-abstraction-levels`)
25. **One responsibility — no conjoined verbs.** No `recordAndSave`. (`l5_architecture::l5-M-one-responsibility-per-unit-srp`)
26. **Railway: linear happy path, short error arm.** `guard … else { throw … }` / `return .failure(…)` on one line; the `catch` arm maps and leaves, never a home for long code. (`l5_architecture::l5-A-errors-as-values`)
27. **Paragraph the body: setup → work → return,** a blank line between. *(no dedicated rubric rule yet — read by a human.)*
28. **A returned value carries facts, not UI.** The failure enum carries the system's words; the sentence the user reads is rendered at the edge (`describe(_:)` in the app target) from those facts.

## Say less

29. **Comments: minimal; the default is none.** The full rules are the `coding-convention` skill; load it too. A doc comment (`///`) is one verb-first sentence (`Returns …`, `Holds …`); keep only what the code cannot say — why, units, invariants, what a caller cannot see.
30. **Reuse Foundation and the standard library before hand-rolling** (`JSONDecoder`, `URLComponents`, `ISO8601DateFormatter`, `Duration`).
31. **Delete dead code** — no `@available(*, deprecated)` shim kept for nobody, no commented-out views.
32. **Magic literal → a `static let` with its unit in the name** (`levelHistory = 240`, `pollInterval: Duration = .seconds(2)`). (`llm_generated_code_smells::magic-literal`)
