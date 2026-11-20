---
name: review-annotate-code
description: Temporarily annotate the code changes Claude made on the current branch (or in a given commit) with numbered CODE-EXPLAINER comments that tell the reader what to read, in what order, and how the change flows. Use on /review-annotate-code, or when asked to "annotate the changes", "walk me through the diff in the code", or "explain this branch/commit in the code". `/review-annotate-code clear` removes every annotation; `/review-annotate-code gh-clear` moves them onto the branch's GitHub PR as review comments, then removes them from the code.
argument-hint: "[commit | base..head | clear | gh-clear]"
---

# Annotate code changes

**Goal:** The reader opens the files and follows numbered comments, in order, to understand a change. Each comment is a stop on a tour. The numbers say **what to read, in what order**. The order follows **how the change flows** (how the code runs or how data moves), not the order of files in the diff.

The comments are **temporary**. They're for reading only. They must never be committed.

## Arguments
| Argument | What to annotate |
|---|---|
| *(none)* | This branch: everything since it left the default branch (`git merge-base HEAD origin/<default>`), plus uncommitted changes |
| `<commit>` | That one commit (`git show <commit>`) |
| `<base>..<head>` | That range |
| `clear` | Remove every annotation (see **Clearing**) |
| `gh-clear` | Post every annotation to the branch's open GitHub PR as review comments, then remove them from the code (see **Moving annotations to the PR**) |

Find the default branch with `git symbolic-ref refs/remotes/origin/HEAD` (fall back to `main`).

## Before you start
1. **Check that the code you'll annotate is in the working tree.** If the commit or range isn't checked out (the files on disk don't contain it), stop and ask the reader to check it out. Don't annotate a different version of the code.
2. **Check for old annotations:** `git grep -n "CODE-EXPLAINER"`. If there are any, ask whether to clear them first.
3. **Note which files already have uncommitted changes.** You'll be adding lines to files the reader may also be editing, so tell them which ones in the summary.

## Steps
1. **Read the whole change** (`git diff <base>...HEAD`, plus `git diff` for uncommitted work, or `git show <commit>`). Read the surrounding code too, until you understand why each change is there.
2. **Find the flows.** A flow is one path through the change that makes sense on its own. For example: "a request comes in → is validated → is stored", or "the new helper → where it's used → its test".
   - **One flow:** label the comments `CODE-EXPLAINER-1`, `CODE-EXPLAINER-2`, …
   - **Two or more flows:** label them `CODE-EXPLAINER-A-1`, `A-2`, … for the flow to read first, then `CODE-EXPLAINER-B-1`, `B-2`, … for the second, and so on. Put the most important flow (or the one the others depend on) first.
3. **Choose the stops and their order.** Start where the flow starts (the entry point, or the place the change is triggered). Then follow the calls and data in the order they happen. End with the **tests** that prove the flow works.
   - Every changed hunk should be covered by a stop, or be clearly part of one. Skip pure noise (imports, formatting) unless it matters.
   - Use enough stops to tell the story, and no more. Usually 3–10 per flow.
4. **Write each comment** on its own line(s), **directly above** the line it explains, in that language's comment syntax (see the table). Indent it to match the code.
5. **Add the "next stop" hints** (see **Next-stop hints**). Where a stop's code calls the function that holds the next stop, put a trailing comment on that call's line, so they can cmd+click straight to it. Then, as the very last edit, end each flow with a link to the next flow (see **Flow-to-flow links**).
6. **Change nothing else.** Only add comment lines, plus the trailing next-stop hints. Never edit, move or reformat code. Never add comments to generated files, lockfiles or vendored code.
7. **Check:**
   - `git diff` shows only added `CODE-EXPLAINER` lines, and code lines whose only change is an appended `<-- cmd+clk … for CODE-EXPLAINER-…` hint, on top of the real change.
   - The code still compiles. Comments can't break most languages, but check languages with odd comment rules.
8. **Give the reader the reading map** (see below).

## Comment format
```
<comment syntax> CODE-EXPLAINER-<flow>-<n>: <what this stop shows>
```
- The first comment of each flow says what the flow is about and where it ends up, e.g. `CODE-EXPLAINER-A-1: (Flow A: where a child task's trace goes) …`.
- Refer back and forward by label when it helps: "remember A-2? this is where that value gets used".
- Keep each comment short: 1–3 lines. If you need more, add another stop.

| Language | Syntax |
|---|---|
| Scala, Java, Kotlin, JS/TS, Go, C, Rust, Swift | `// CODE-EXPLAINER-1: …` |
| Python, Bash, YAML, HOCON (`.conf`), Ruby, TOML | `# CODE-EXPLAINER-1: …` |
| SQL, Lua | `-- CODE-EXPLAINER-1: …` |
| HTML, XML, Markdown | `<!-- CODE-EXPLAINER-1: … -->` |
| CSS | `/* CODE-EXPLAINER-1: … */` |
| JSON (no comments allowed) | don't edit it; describe that stop in the reading map instead |

## Next-stop hints
**Goal:** when the next stop is inside a function that this stop's code calls, the reader cmd+clicks the call and lands on it, without hunting for the file.

**Format:** a trailing comment at the end of the **code line that makes the call**, in that language's line-comment syntax:
```
<code line> <comment syntax> <-- cmd+clk <functionName> for CODE-EXPLAINER-<next label>
```
Example:
```scala
  ): Task[FirstPass] =
    // CODE-EXPLAINER-A-2: Keywords and phrase go in together. Note the + 1: we keep one spare fragment, so B-5 can answer
    // "are there more matches?" without another pass. Main highlighted the whole document again for N + 1.
    rankFragments(text, keywordQuery :: phraseQueryOpt.toList, settings, settings.snippetsPerDoc + 1).map { ranked => // <-- cmd+clk rankFragments for CODE-EXPLAINER-A-3
```

**Rules:**
- **Only when a call leads there.** Add a hint only if the next stop (the next label in the same flow) is in the function called on that line, or in that function's body. `<functionName>` is the name to cmd+click, exactly as written in the call (e.g. `rankFragments`, `selector.accept` → `accept`).
- **Put it on the call's line,** not on the annotation. It may be the line under the annotation or a later line of the same stop.
- **No call leads there?** For example, the next stop is a test, another file reached by data not by a call, or the start of a new flow. Then add no hint. The reading map covers it.
- **Several calls lead to different next stops?** Hint the call to the next label. Don't hint stops further ahead or behind, with one exception (the "after" case below).
- **The call goes through a helper first?** Hint the helper call with `(via <helper>)`, and add a second hint on the line inside the helper that makes the real call:
  `previousPass.accept(currentToken) // <-- cmd+clk accept for CODE-EXPLAINER-A-6 (via Pass.accept)`
- **The next stop is a dead end?** If stop N calls stop N+1 and then stop N+2, but N+1 calls nothing that leads on, hint the N+2 call on stop N's line with `(after <N+1 label>)`. the reader reads N+1, comes back, and clicks on:
  `val ranked = StreamingHighlighter.rank(…) // <-- cmd+clk rank for CODE-EXPLAINER-A-5 (after A-4)`
- **Don't add a hint** where a trailing comment could change the code:
  - inside a string, a multi-line string or a block comment;
  - after a line continuation (`\` in Bash or Python);
  - in a language with no line comments (JSON, HTML, CSS).
- **One hint per line.** If a line already ends with a comment, add the hint after it with a space, not inside it.
- The hint contains `CODE-EXPLAINER`, so `git grep -n "CODE-EXPLAINER"` finds it, and **Clearing** removes it.

## Flow-to-flow links
**Goal:** at the end of a flow, the reader clicks once to start the next flow.

- The **last stop of each flow** ends with 2 more comment lines (continuation lines of that stop):
  ```scala
  // That's the end of Flow A. Next: Flow B (<what Flow B is about>), stop B-1:
  // idea://open?file=<absolute path of B-1's file>&line=<line of B-1's CODE-EXPLAINER comment>
  ```
- The **last flow** links back to the start: `That's the end of Flow C, and of the tour. Back to the start, stop A-1:` + the link to A-1.
- **Only one flow?** End its last stop with `That's the end of the tour.` and no link.
- Write `stop B-1`, **never** `CODE-EXPLAINER-B-1`, in these lines. Otherwise clearing and `gh-clear` read them as the start of a new annotation.
- **Add these links last,** after every other annotation is in place, so the line numbers in the links are final. Adding a link only adds lines to the last stop's file. If that's the same file as the target and the target is below it, add the 2 lines to the target's line number.
- Use the user's clickable-link format for code references if they have one (for example `idea://open?file=<abs path>&line=<n>` for IntelliJ; full path, never `~`). IntelliJ may not make `idea://` clickable inside a code comment. If not, the reader copies it into a browser.

## The reading map (your reply)
After annotating, reply with:
1. **The flows, in reading order:** one line each on what each flow is about.
2. **A table per flow:** label → file:line → one-line summary → **next-stop hint** (the function to cmd+click, or "—" if there's no hint). Make each file:line a clickable link in the user's preferred format (see above). Line numbers are the comment lines **after** annotating.
3. **Files that also had the reader's uncommitted changes**, if there are any.
4. A reminder: "Run `/review-annotate-code clear` before you commit."

## Clearing
`/review-annotate-code clear`:
1. `git grep -n "CODE-EXPLAINER"` to list them.
2. Remove **only** those comment lines. For a multi-line comment, remove its continuation lines too.
3. Remove every **next-stop hint**: cut the trailing ` <comment syntax> <-- cmd+clk … for CODE-EXPLAINER-…` (and the space before it) from the end of its code line. Keep the code line itself, exactly as it was. Never delete that line.
4. Check that `git grep "CODE-EXPLAINER"` finds nothing, and that `git diff` no longer shows any annotation lines or hint changes.
5. Tell the reader how many annotations and hints you removed, from which files.

**Never commit annotations.** If the reader asks you to commit while annotations exist, clear them first, or ask.

## Moving annotations to the PR (`gh-clear`)
This keeps the tour, but on GitHub instead of in the code. Each annotation becomes a review comment on the line it explains, so reviewers can follow the same order.

1. **Find the PR:** `gh pr view --json number,url,headRefOid,headRepository,headRepositoryOwner,baseRefName` on the current branch.
   - **No open PR:** stop and tell the reader. Offer `clear` instead.
   - **Local `HEAD` isn't the PR's head commit (`headRefOid`):** stop. The reader must push first, or confirm the PR head is the code they means. Comments must point at the code that's on GitHub.
2. **Collect the annotations:** `git grep -n "CODE-EXPLAINER"`. For each one, record:
   - the label;
   - the full text (the first line plus its continuation comment lines, without the comment markers);
   - the file;
   - **the code line it sits above** (the first non-annotation line after it);
   - its **next-stop hint**, if the stop has one: the function name and the label it points to.
3. **Find each target line in the PR's version of the file.** Line numbers on disk include the annotation lines, and may include the reader's uncommitted edits, so don't use them as-is.
   - Take the target code line's text **without any next-stop hint** (cut the trailing `<-- cmd+clk …` comment first), and find it in `git show <headRefOid>:<file>`.
   - If it appears more than once, pick the occurrence closest to *(the line on disk − the annotation lines above it)*.
   - If you can't find it, say so and leave that annotation out of the inline comments. Put it in the review body instead.
4. **Check which lines can take an inline comment.** GitHub only accepts review comments on lines inside the PR's diff hunks (changed lines or their context).
   - Get the hunks from `gh pr diff <n>` or `GET /repos/{owner}/{repo}/pulls/{n}/files` (`patch`).
   - A stop on a line **outside** the diff (e.g. an unchanged entry-point line used for context) goes in the review body instead. Link it to the line: `https://github.com/<owner>/<repo>/blob/<headRefOid>/<path>#L<n>`.
5. **Build one review** (event `COMMENT`, not approve or request changes):
   - **Review body:**
     - a short intro ("Reading guide for this PR, in order");
     - the flows with one line each;
     - the full reading order (label → file:line);
     - the text of any stops that couldn't go inline, with their links.
   - **One comment per inline stop:** `path`, `line`, `side: "RIGHT"`, and a body like:
     ```
     **CODE-EXPLAINER-A-2** · Flow A, stop 2 of 8

     <the annotation text, as written>

     Next: `rankFragments` → CODE-EXPLAINER-A-3
     ```
   - Keep the text **as written**: same wording, same style. Only remove the comment markers and join the lines.
   - Add the "Next:" line only for a stop with a next-stop hint. GitHub can't cmd+click, so name the function and the label.
   - In a flow-to-flow link, replace the `idea://` link with a GitHub link to the next flow's first stop: `https://github.com/<owner>/<repo>/blob/<headRefOid>/<path>#L<n>`, where `<n>` is that stop's line in the PR's version of the file.
6. **Show the reader what will be posted:**
   - the PR link;
   - how many inline comments, and how many go in the body;
   - the review body.

   **Post only after they say yes.** It's visible to everyone on the PR. Skip this check only if they already said to go ahead in the same request.
7. **Post it:** `gh api repos/{owner}/{repo}/pulls/{n}/reviews --input review.json`, with `{"commit_id": headRefOid, "event": "COMMENT", "body": …, "comments": [...]}`.
   - Write `review.json` to the scratchpad.
   - If GitHub rejects a comment (HTTP 422, line not in the diff), move that stop to the body and post again. Don't drop it.
8. **Only after the review posted successfully,** run the **Clearing** steps to remove the annotations from the code. If posting failed, leave the code as it is and report the error.
9. **Report:**
   - the review link (`html_url` from the response);
   - how many comments were posted inline and how many went in the body;
   - that the code is clean (`git grep "CODE-EXPLAINER"` finds nothing).
   - Remind the reader that any uncommitted non-annotation edits are still there, untouched.

## Comment Style
Read `${CLAUDE_PLUGIN_ROOT}/writing-styles/plain.md` (the plugin root is 2 folders above this skill's folder) and follow it. It has the rules, with `CODE-EXPLAINER` examples.

On top of that, for comments:

**Keep:** 1–3 lines per comment, plain words, short sentences. No emoji.

Example:
```scala
// CODE-EXPLAINER-A-2: Here's the heart of it. Why not borrow the parent's trace id, like before?
// Because the child then overwrites the parent's trace. Now every task uses its OWN id.
val parentCtx = userContext.map(ctx => parentContextFromTaskId(ctx.taskId))
```
