# Coding Style

## How to build it: make it work and measure it, then refactor

**Build the simplest version that works first, and measure it before you make it pretty.**
**Why:** The first version is the yardstick. On a one-pass text scanner, the first version used local mutable buffers and was the fastest and leanest version we ever had. Every later refactor was judged against its numbers. Without a measured first version, you can't tell whether a refactor made things worse.
**How to apply:** Write the straightforward version, even with local `var`s or mutable collections if that is the clearest fast way. Then measure, and write the numbers down:
- **Memory:** peak heap or allocation on the biggest real input, e.g. the largest document size the service accepts.
- **CPU and latency:** single calls, and calls run in parallel, on small and large inputs.
- **Output:** what it returns for a wide set of inputs.

Only then start to refactor.

**Lock the behaviour before you refactor: a snapshot test and the same benchmark, run after every step.**
**Why:** A refactor must change how the code reads, not what it does or what it costs. A big snapshot catches tiny output changes that hand-written tests miss.
**How to apply:**
- **Snapshot test:** run thousands of input combinations through the code, and save both a hash of the output and a readable output file. Run it on the base branch too, so you know the starting hash.
- **After every refactor commit:** run the snapshot and the benchmark. Put the before → after numbers in the commit message, e.g. "Same output (10,080-case snapshot unchanged). 1,500-page input: 87 → 94 ms."
- **Budget:** a small cost for a clear readability gain is fine. Making the scanner immutable cost about 5–8% (87 → 94 ms) with identical output, and that was accepted. If a step costs more than that, or memory grows with the input when it didn't before, stop and report the numbers before you go on.

**When there are several reasonable designs, build each one on its own branch and compare them.**
**Why:** Opinions about which design reads best are cheap to test and expensive to argue about. Real code and real numbers settle it.
**How to apply:** Give each option a letter and a branch (`<ticket>-option-a`, `-option-b`, …), all from the same base. Run the same snapshot and benchmark on each one. Report a table with output (same/different), latency, memory and a short readability note, then recommend one. Options can be combined (e.g. "D+E"). Treat a difference smaller than run-to-run noise as no difference.

**Do renames in their own commit, before structural changes.**
**Why:** A rename-only commit is easy to review: nothing changes except names. Mixed into a restructure, it hides the real change.
**How to apply:** Commit the renames first, then move code into new files or types. If Patrick renamed something, keep his name. He did it for a reason.
In a stack of PRs, make the rename in the lowest PR that adds the name, then rebase the PRs above it and run the tests on each. Leave a name that later PRs import (e.g. `script_of`) for a separate rename across the whole stack, so one PR's rename doesn't break the next.

## General — best practices & style (all languages)

**Extract logic into well-named helper functions before they get long.**
**Why:** Long functions are hard to test in isolation and obscure intent.
**How to apply:** If a block of logic inside a function has a clear purpose, pull it into a private helper with a name that says what it does. A loop that searches for one answer is a good sign: give it a name and return the answer. The calling function then reads as a list of its steps.

Example (evaluation-api `line_language_check.py`). Before, one function did three things inline:
```python
def detect_script_from_char(character: str) -> Optional[str]:
    unicode_category = unicodedata.category(character)
    if not _is_letter(unicode_category):
        return None
    code_point = ord(character)
    for first_code_point, last_code_point, script in _SCRIPT_RANGES:
        if first_code_point <= code_point <= last_code_point:
            return script
    ...
    unicode_name = unicodedata.name(character, "")
    if "LATIN" in unicode_name or "ORDINAL INDICATOR" in unicode_name:
        return "latin"
    return unicode_name.split(" ", 1)[0].lower() or "other"
```
After, each step has a name, and the top function reads as the order of the steps:
```python
def detect_script_from_char(character: str) -> Optional[str]:
    unicode_category = unicodedata.category(character)
    if not _is_letter(unicode_category):
        return None
    script_from_range = _detect_script_from_unicode_range(ord(character))
    if script_from_range is not None:
        return script_from_range
    ...
    return _detect_script_from_unicode_name(character)


def _detect_script_from_unicode_range(code_point: int) -> Optional[str]:
    for first_code_point, last_code_point, script in _SCRIPT_RANGES:
        if first_code_point <= code_point <= last_code_point:
            return script
    return None
```
Follow the naming pattern the code already uses (here Patrick's `detect_script_from_…`), so related helpers read as a family.

**When refactoring a branch's diff, only touch code the branch actually added or changed — never pre-existing code the branch didn't touch, even in the same function.**
**Why:** Confirmed across a 4-repo refactor pass (ask-imanage-api/queue/search-agent/llm-service, 2026-07-08): scope creep into untouched code mixes unrelated changes into the PR, makes the diff unreviewable/unattributable, and risks regressions in code nobody asked to change. It's also fine — expected, even — to find zero extraction-worthy blocks in a branch; don't manufacture extractions just to have something to show.
**How to apply:** Run `git diff <base>..<branch>` first and scope all extraction candidates to the actual diff hunks. If an extraction-worthy block sits right next to untouched code in the same function, leave the untouched part alone even if it looks improvable. If an extracted helper has only one call site, make it a local nested function rather than a class/object-level method; promote to object-level only when genuinely reused by multiple call sites in the same file.

**Separate orchestration from computation — callers own the wiring.**
**Why:** Functions that do their own data fetching/transformation AND computation are hard to unit-test.
**How to apply:** e.g. `get_retrieval_scores` takes `List[RetrievalData]`; the caller calls `get_retrieval_data` first. Each function does one thing.

**Separate pure computation from I/O — pure functions are testable and composable.**
**Why:** Pure functions (no side effects, deterministic inputs/outputs) are easier to test, reason about, and reuse. I/O is a separate concern.
**How to apply:** Extract pure logic (e.g., `_apply_sbt_version_to_lines()` takes lines, returns updated lines) from I/O wrappers (e.g., `update_sbt_version()` reads file, calls pure function, writes result).

**Never weaken a type with optional/nullable defaults to paper over missing test data — fix the test data instead.**
**Why:** Weakening a model's type to avoid updating a fixture hides a real design problem.
**How to apply:** If making a field required breaks tests, add the field to the test fixtures. The model should reflect reality.

**Replace if-elif/switch chains with lookup tables (maps/dicts).**
**Why:** Branch chains are verbose, error-prone to extend, and often have subtle bugs (e.g. string transformations applied before comparison).
**How to apply:** Module-level maps with descriptive names replace chains cleanly. Name a map `<VALUE>_BY_<KEY>` (`LINGUA_LANGUAGE_BY_CODE`, `_OTHER_HAN_LANGUAGE_BY_LANGUAGE`) or `<KEY>_TO_<VALUE>` (`_ENV_SUFFIX_TO_DISPLAY_NAME`), so a lookup reads as a sentence: `_OTHER_HAN_LANGUAGE_BY_LANGUAGE["ja"]`.

**No single-character variable names — everything must be descriptive.**
**Why:** Code is read far more than written. `recorded_version` vs `candidate_version` is immediately clear; `a` vs `b` requires context-switching.
**How to apply:** Use semantic names that explain the variable's purpose. Loop indices where context is obvious (e.g., `for i in range(10)`) are acceptable; data variables always get full names.

**Name things for what they are in the problem, not for their role in the algorithm.**
**Why:** Generic algorithm words (`pending`, `bucket`, `capacity`, `buffer`, `state`, `result`, `items`, `tokens`) make the reader keep a mental map from code to meaning. A domain name gives that meaning directly. Long names are fine, because the reader saves more time than the writer spends.
**How to apply:** Ask "what is in it?" and "for what?", and put both answers in the name:

| Generic | Says what it is |
|---|---|
| `pending` | `waitingLines` |
| `bucket` | `bestMatchesPerPattern` |
| `capacity` | `matchesToKeepPerPattern` |
| `tokens` (a parameter) | `documentTokens` |
| `firstPos`, `prevEnd` | `positionOfFirstReadLine`, `endOfLastReadLine` |
| `hasPhrase` | `anyPhraseQuery` (a boolean reads as a question about the input) |
| `text` (after URLs were removed) | `text_without_urls`: say what has already been done to the value |
| `count`, `characters` | `letter_count`, `distinct_characters`: say what is counted or collected |
| `start, end` (a range) | `first_code_point, last_code_point` |
| `best`, `code`, `char` | `most_likely`, `language_code`, `character`: no abbreviations |
| `longest`, `run` | `longest_run`, `current_run` |
| `MIN_FOREIGN_LETTERS` | `MIN_LETTERS_OF_A_FOREIGN_ALPHABET`: a constant says what it limits, and of what |
| `LineVerdict.check` | `LineVerdict.decided_by`: a field says its role, not just a topic |

**Name functions for what they do in the problem, not with generic verbs.**
**Why:** `accept`, `observe`, `process`, `handle`, `finish`, `start` say that something happens, not what. The reader has to open the function to find out.
**How to apply:** Use a verb and the thing it acts on: `accept(line)` → `scoreLine(line)`; `observe(line)` → `showToMatchersAndWait(line)`; `acceptOldest` → `scoreFirstWaitingLine`; `finish` → `closeLastMatches`; `start(...)` → `newScanState(...)`.

**Name every intermediate value, lambda parameter and destructured tuple.**
**Why:** In a fold or a recursive loop, the reader has to know at each step what the value is now. `acc`, `x`, `(a, b)` and `current` hide that.
**How to apply:**
- Fold accumulators and results: `lastState` → `stateAfterLastLine`; `observed` → `stateWithLineWaiting`.
- Lambda parameters: `(previous, x)` → `(scanState, currentLine)`.
- Destructured tuples: `val (oldest, rest) = queue.dequeue` → `val (firstLineInQueue, restOfQueue) = ...`.
- Recursive-loop parameters: `from(index, current, bucket)` → `moveFrom(matcherIndex, matchersSoFar, bestMatchesSoFar)`.
- Values inside a step: `ranking` / `nextRanking` → `patternBestMatches` / `updatedPatternBestMatches`.

**Give a bare condition or literal a name: a small helper or a constant.**
**Why:** `category.startswith("L")` or `category == "Lm"` makes the reader stop and work out what "L" means. A name answers that where the code is read.
**How to apply:** Wrap the check in a helper named for the question it answers, and put the literal in a named constant: `if not _is_letter(unicode_category)`, with `_LETTER_CATEGORY_PREFIX = "L"` and `_MODIFIER_LETTER_CATEGORY = "Lm"`. If a reviewer asks "why do we check X?", the answer is usually a missing name.

**Keep names in an outside contract when you rename the code behind it.**
**Why:** An API response key, a JSON field or a stored column is read by other code (a dashboard, another repo). Renaming it breaks them.
**How to apply:** Rename the internal field and keep the external key: `LineVerdict.decided_by` is still written as `"check"` in `line_analysis`. Say so in the commit message.

**Don't add a parameter until a caller passes it, and don't give it a do-nothing default.**
**Why:** An unused parameter with an identity default (`without_kept_as_written=_nothing_kept_as_written`) makes the reader look for a caller that doesn't exist, and asks "why is this here?".
**How to apply:** Add the parameter in the change (or the PR in a stack) where the first caller passes it. If every caller passes it, make it required. Remove the default function too.

**Use one word for one idea, and pick the word the users of the code see.**
**Why:** When the code says "fragment" and the API says "snippet" for the same thing, readers wonder whether they are two things.
**How to apply:** Choose the word from the public API or the product, and use it in type names, fields, functions, test names and comments. Keep a library's own word only where you talk about that library, e.g. "a port of Lucene's `mergeContiguousFragments`".

**Use named arguments when a call has several values of the same type, or values whose meaning isn't clear from the call.**
**Why:** `rank(tokens, 1200, 100, 4, queries)` can't be checked by reading it. Named arguments make a wrong order visible.
**How to apply:** `scan(documentLines = lines, textLength = text.length, matchesToKeepPerPattern = shown + 1, patterns = patterns)`. Also put each parameter on its own line when the signature doesn't fit on one line.

**Don't add comments to code, config or workflow files. Explain with names instead.**
**Why:** The team removes comments in review because they go stale (2026-10-05: a reviewer flagged them on sidewinder#79, Patrick asked for all added comments to be stripped from every CIN-4044 PR, and extract-common already had a "Remove added explanatory comments" commit). A comment that explains the code usually means a name is missing. The reasoning belongs in the commit message and the PR description, which don't rot alongside the code.
**How to apply:**
- Write no new `#` / `//` comments, including inline trailing ones such as `# CVE-…` on a dependency pin or `# TEMPORARY` markers. When a comment seems needed, first try a clearer name, a small named helper or a named constant (see "Give a bare condition or literal a name").
- Put the reasoning in the commit message or the PR body.
- When editing a line that already carries a comment, don't rewrite the comment text. Leave existing comments the change doesn't touch alone.
- **The one exception:** outside knowledge the code depends on and no name can carry, such as a standard, a spec or a data format. Write a short comment with a link to the source. Example (asked for by Patrick in evaluation-api#78): the Unicode general categories behind `_is_letter`, with `https://www.unicode.org/reports/tr44/#General_Category_Values`.

**Use sealed error type hierarchies, not string messages.**
**Why:** Strings can't be pattern-matched exhaustively; a sealed hierarchy forces callers to handle every case and keeps error context structured.
**How to apply:** Define a sealed trait (or enum) as the root error type, with specific case classes for each failure mode carrying relevant fields (e.g. `MCPError(tool: String, message: String, cause: Option[Throwable])`). Wire errors through the type system, not exception messages.

**Put one idea in each file, and give each file one test file with the same name.**
**Why:** A reader who wants "how are matches ranked?" opens one file. A 600-line file with four ideas makes them scroll and guess.
**How to apply:** When a file holds several separate ideas (input types, the per-kind matchers, the result types, the main loop), move them into a package with one file per idea, and the main entry point in a file named after it. Mirror the layout in the tests: `Matchers.scala` → `MatchersTest.scala`. Put example data shared by the tests in one `<Package>TestData` file. Don't use names like `ExampleTest`: a test file is named after the code it tests.

**Write tests that read like documentation of the behaviour.**
**Why:** A good test name tells the reader the rule without them reading the code. A failing test then says which rule broke.
**How to apply:** Name each test as a sentence about what the code does, using the domain words, e.g. `"keeps the earlier match when two matches score the same"`. Use small, real-looking inputs (a real sentence, not `"a b c"`). Group tests by the function they test (`suite("scoreLine")`), and cover private helpers through their package-private access.

**Separate service interface from implementation — callers depend on the trait, not the class.**
**Why:** Swapping implementations (for tests, different backends, staged rollouts) requires no call-site changes when the interface is stable.
**How to apply:** Define a trait for every service with the public contract. Put the implementation in a separate (often private) class. Expose a factory or layer in a companion object. Callers reference only the trait.

## Python

**Use plain for-loops, not list comprehensions, for multi-step logic.**
**Why:** List comprehensions that do non-trivial work read bottom-up; for-loops read top-down.
**How to apply:** Reserve comprehensions for simple transformations (e.g. `[x.id for x in items]`). Use a for-loop with named intermediate variables any time there are conditions, multiple steps, or an append.

**Use Pydantic models at system boundaries; don't do isinstance/dict-key guards inside business logic.**
**Why:** Defensive dict-access throughout the codebase hides schema issues and adds noise.
**How to apply:** Parse raw dicts into Pydantic models at the entry point (file load, API response). Internal functions work with typed models, not dicts.

## Scala / ZIO

**Service pattern: trait + private impl + companion object with `live: ZLayer`.**
**Why:** Decouples interface from construction; ZIO's DI is type-driven so the layer is the only wiring point.
**How to apply:**
```scala
trait MyService {
  def doThing(x: String): ZIO[Scope, MyError, Result]
}
object MyService {
  val live: ULayer[MyService] = ZLayer.succeed(new MyServiceImpl())
  def doThing(x: String): ZIO[MyService & Scope, MyError, Result] =
    ZIO.serviceWithZIO[MyService](_.doThing(x))
}
private class MyServiceImpl() extends MyService { ... }
```

**Make state immutable: case classes stepped with `copy`, carried by `foldLeft` or a `@tailrec` loop.**
**Why:** Each step returns a new value, so you can test any one step on its own and print any state you get. Hidden changes inside a mutable object can't surprise the next step. In a one-pass scanner this cost only about 5–8% latency (see "Lock the behaviour before you refactor").
**How to apply:**
- Replace `var` fields and `mutable.*` collections with fields of an immutable `final case class`. Each method returns the next state (`copy(...)`).
- Carry the state over the input with `input.foldLeft(State.initial)((state, item) => state.step(item))`.
- Replace `while` loops with `@tailrec` local functions.
- Use immutable `Queue`, `Vector` and `Set`.
- Keep it cheap: when a step changes nothing (most steps in a scan), return `this`, and check `next eq current` before you update a Vector slot. Then the common case allocates nothing.
- The first measured version may use local mutation (see "Build the simplest version that works first"). Make it immutable in a later commit, with the snapshot and the benchmark unchanged. Tests may still use mutation.

**When one class switches on its input kind in several places, split it into a sealed trait with one case class per kind.**
**Why:** A class with `Option` fields that only one kind uses, plus a `match` on the kind in each method, mixes two behaviours together. With one type per kind, each type holds only its own state, and the compiler checks each case.
**How to apply:** e.g. `class Matcher(pattern)` with `Option[PhraseState]` and `pattern match` in 3 methods → `sealed trait Matcher` with `KeywordMatcher` and `PhraseMatcher`. Put the part both kinds share (counters, current match, marks) in its own case class that each one holds (`progress: MatchProgress`). Use a factory on the companion (`Matcher.forPattern(pattern)`).

**Use sealed trait / enum ADTs for all closed value sets.**
**Why:** The compiler enforces exhaustive pattern matching; adding a case surfaces every unhandled site immediately.
**How to apply:** `sealed trait Decision` with `case class`/`case object` subtypes for every variant. Use `enum` (Scala 3) when the cases are simple. Never use bare strings for values with a fixed set of options.

**Derive Circe codecs in companion objects — never inline.**
**Why:** Keeps the case class body clean; scoping in the companion makes implicits available everywhere the type is used.
**How to apply:**
```scala
case class QueryRequest(query: String, limit: Int)
object QueryRequest {
  implicit val decoder: Decoder[QueryRequest] = deriveDecoder
  implicit val encoder: Encoder[QueryRequest] = deriveEncoder
}
```
Use `Configuration.default.withSnakeCaseMemberNames` for API contracts where JSON uses snake_case.

**Thread ZIO dependency requirements through intersection types — never use global state.**
**Why:** The type signature documents every dependency; the compiler prevents missing wiring; no implicit globals.
**How to apply:** `ZIO[UserService & AuthService & Scope, AppError, Result]` — list every dependency in `R`. Compose layers in `Main` / `run`, not inside service implementations.

**Use `ZIO.attempt` for code that throws; `ZIO.succeed` for pure values; `ZIO.fromEither` for Either.**
**Why:** Correctly captures the effect boundary. Wrapping pure code in `attempt` is unnecessary overhead; missing `attempt` around throwing code leaks exceptions.
**How to apply:**
```scala
ZIO.attempt(parser.parse(body))          // may throw
ZIO.succeed(context.copy(done = true))   // pure
ZIO.fromEither(decode[Foo](json))        // circe Either
```

**Use for-comprehensions for sequential ZIO chains — not nested `.flatMap` calls.**
**Why:** For-comprehensions linearise async steps top-to-bottom; nested flatMap creates rightward drift and obscures the happy path.
**How to apply:** Any chain of more than two steps should be a for-comprehension with named bindings at each step.

**Use `foreachPar` for parallelism; `Semaphore` to cap concurrency; `Ref` for shared mutable state.**
**Why:** These are the ZIO primitives that compose cleanly with the effect system — no raw threads or `var`.
**How to apply:**
- `ZIO.foreachPar(items)(process)` — fan out
- `Semaphore.make(n).flatMap(sem => ZIO.foreachPar(items)(sem.withPermit(process(_))))` — capped fan out
- `Ref.make(initial).flatMap(ref => ...)` — safe mutable cell inside effects

**Make config errors fatal with `.orDie`; don't propagate `Config.Error` to callers.**
**Why:** Missing config is a startup problem, not a runtime one. Propagating it forces every caller to handle an error that can only be fixed by an operator.
**How to apply:** `ZIO.config[AppConfig](config).orDie` in the layer definition. App crashes at startup with a clear message rather than failing silently mid-request.

**Use type aliases to name complex types — especially ZIO environment intersections.**
**Why:** Long `ZIO[A & B & C & D, E, F]` signatures hurt readability and become a maintenance burden when the dependency set changes.
**How to apply:**
```scala
type SearchDeps = LLMClient & MCPClient & UserContextService & Scope
def search(...): ZIO[SearchDeps, AgentError, SearchResult]
```

**Use extension methods to add utility to ZIO effects without subclassing.**
**Why:** Keeps cross-cutting concerns (metrics, logging wrappers, error unwrapping) out of the core type hierarchy.
**How to apply:**
```scala
extension [R, E, A](zio: ZIO[R, E, A])
  def withTimer(metric: Metric): ZIO[R, E, A] = ...
```

## Bash

_(No rules captured yet.)_
