---
name: review-code-change-flow-notes
description: Help the user learn to read a code change. Pick the 3–5 key flows that teach the change best, and list the other flows the change touches (happy, edge, failure, unchanged-but-affected) in an optional section. Each flow is written twice, in separate parts: how it works on the old code, then on the new code, with every step linked to the code, and a blank space for the user to explain the flow in one sentence. Writes a markdown file into a project folder under $FLOW_NOTES_ROOT (default ~/flow-notes). `check` marks the user's sentences. Use on /review-code-change-flow-notes, or when asked to "list the flows in this change", "make flow notes for this branch", or "help me read this diff before and after".
argument-hint: "[<repo> <branch|commit|base..head>] [--project <folder>] | check [<notes file>]"
---

# Code change flow notes

**Goal:** The reader learns to read a code change. They read each flow on the **old** code, then on the **new** code, and write **one sentence** in their own words to explain it. Claude then marks the sentence. Writing the sentence is the learning step, so **Claude never writes it for them.**

**One person can't review every flow.** So the file starts with the **3–5 key flows**: the ones that teach the change best. All other flows go in an optional **Other flows** part.

**Old and new are read apart, not side by side.** Part 1 is the old code, Part 2 is the new code. Name each part after its branch (e.g. `main` and `option5`).

## Arguments
| Argument | What it does |
|---|---|
| *(none)* | The current repo and branch: everything since it left the default branch, plus uncommitted changes (ask first, see **Before you start**) |
| `<repo> <branch>` | That repo (found under the user's usual code folder, or at the path given) and branch, from its merge base with the default branch |
| `<repo> <commit>` or `<repo> <base>..<head>` | That commit or range |
| `--project <folder>` | Write into this project folder instead of making a new one |
| `check [<notes file>]` | Mark the reader's sentences in a notes file (see **Checking**) |

Find the default branch with `git symbolic-ref refs/remotes/origin/HEAD` (fall back to `main`). The base is `git merge-base <head> origin/<default>`.

## Project folder
- **Parent dir:** `$FLOW_NOTES_ROOT` if set, else `~/flow-notes/`.
- **Each run makes a new project folder** there, named `<short-kebab-topic>` (e.g. `snippet-tool-bug`). Ask the reader for the name if the topic isn't clear from the branch.
- **If the reader names an existing folder** (`--project` or in their request), use it. Look at what is in it first.
- **File name:** `flow-notes-<repo>-<branch-or-short-sha>.md`. Use `/` → `-` in the branch name.
- **Never overwrite** an existing notes file that has the reader's writing in it. If the file is there, ask: update it (keep their sentences), or write a new file with `-v2`.

## Before you start
1. **Check the code is checked out.** New-code links point at the local checkout, so the files on disk must be the new version. If not, stop and ask the reader to check it out.
2. **Check for uncommitted changes** (`git status`). If there are any, ask the reader: include them, or only the committed change? Don't guess. If another session is still working on the branch, wait for it to finish.
3. **Check for `CODE-EXPLAINER` comments** (`git grep -n CODE-EXPLAINER`). They move line numbers. Tell the reader, and note it in the file.
4. **Find the "why".** Read the ticket if there is one. If not, use the commit messages and the PR description (`gh pr view`). Write the "why" as facts from those sources, and name the source.

## Steps
1. **Read the whole change** (`git diff <base>...<head>`, plus `git diff` if uncommitted work is in scope). Then read the old code and the surrounding code, until you know how each flow ran before and how it runs now.
2. **Find the entry points.** An entry point is where a flow starts: an API endpoint, an MCP tool call, a queue message, a scheduled job, a config load.
3. **List all the flows.** A flow is one path from an entry point to an output, for one kind of input. Name it `input → output`, e.g. "Keywords mode, words found → best N snippets".
   - **Happy paths:** the normal inputs that work. There are often several (one per mode, option or input shape).
   - **Edge cases:** inputs that work but are unusual: empty, one item, very large, at the start or end, exact limit.
   - **Failure paths:** errors, timeouts, bad input, missing data. Say what the caller gets back.
   - **Unchanged but affected:** flows the change did not touch, but that call changed code. This is where regressions hide.
   - Only list flows the change touches.
4. **Pick the 3–5 key flows.** Choose the set that gives the best teaching:
   - the main pipeline, end to end (you need it to read the rest);
   - the flow that shows the bug or the reason for the change;
   - the flow most real calls take (e.g. the default mode);
   - the flow that shows the change's key idea or trick.
   Say in one line why each one is a key flow. Put them in reading order. Every other flow goes in **Other flows**.
5. **Write each flow twice:** once in Part 1 (old code), once in Part 2 (new code).
   - Numbered steps, 3–11 per flow. Each step is one short line plus its links. No side-by-side tables.
   - Each part must make sense on its own. If a step is the same, write it again with its own links. Don't write "same as before" in a key flow.
   - In **Other flows**, keep each flow short: an "On <old>" and an "On <new>" list (or one line each), the tests, and "My sentence".
   - If the flow is new, the old part says "Did not exist".
   - Steps say **what** happens (facts), not the summary. Don't put the one-sentence answer in the steps or the flow name.
6. **Links: every link opens in the reader's editor.** Never use GitHub links.
   - **Format:** ask the user which link format opens code in their editor, and use it everywhere. Examples: `vscode://file<absolute path>:<line>` (VS Code), `idea://open?file=<absolute path>&line=<line>` (IntelliJ). Below, `<link>` means that format. The `review-code-diagram` skill in this plugin ships a VS Code extension (`idea-link/vscode-extension/`, with `build-and-install.sh`) that opens `vscode://paddymac.idealine<absolute path>:<line>` links in IntelliJ from VS Code's markdown preview.
   - **Check the format works** where the user reads the notes. Some markdown previews only open http(s) and their own editor's scheme. Test one link with the user first.
   - **All links point at the normal local checkout**, for old and new code. **No worktrees.** The reader switches branch themselves: `git checkout <old branch>` before Part 1, `git checkout <new branch>` before Part 2.
   - **Line numbers come from git, not from disk**, because the reader may have either branch checked out: old code from `git show <base-sha>:<path>`, new code from `git show <new branch>:<path>`. Check that the old branch (e.g. local `main`) is at the base sha. If it isn't, tell the reader which commit to check out instead.
   - Say at the top of the file, and at the top of Parts 1 and 2, which branch to check out. In Part 3, say that "On <old>" links need the old branch and "On <new>" links and tests need the new one.
   - Write placeholders (e.g. `[[A:SS:41]]`, `[[B:SS:41]]`) and expand them with a script. The script also prints each linked line, so you can check it is the code you mean, and fails if a file or line doesn't exist. 
7. **Find the tests for each flow** (in the new-code part). Link them. If there is none, write **No test**. That is a gap, so list it in **Gaps** too.
8. **Write the file** (template below). Follow the shared writing style in `${CLAUDE_PLUGIN_ROOT}/writing-styles/plain.md` (the plugin root is 2 folders above this skill's folder). Flow steps stay facts; the style applies to the "Why", the notes and your **Claude check** comments.
9. **Reply** with:
   - the file path;
   - the key flows and why;
   - the number of other flows, and how many have no test;
   - which branch to check out for each part.

   Remind the reader to run `/review-code-change-flow-notes check` when they have written their sentences.

## File template
````markdown
# Flow notes: <repo> <branch>

**Change:** <base-sha short>..<head-sha short> (<n> commits[, plus uncommitted changes])

**Why (from <source>):**
- <the reason for the change, from the ticket, commits or PR>

**Made:** <date>

**Links:** all open in your editor, in your checkout `<path>`. Line numbers only match when the right branch is checked out:
- **Part 1 (<old>):** run `git checkout <old branch>` first.
- **Part 2 (<new>):** run `git checkout <new branch>` first.
- Links use the format agreed with the reader. The first time, the editor may ask to allow the link. Say yes.

## How to use this file
1. `git checkout <old branch>`, then read **Part 1 (<old>)**. It shows how the code worked before the change.
2. `git checkout <new branch>`, then read **Part 2 (<new>)**. It shows the same flows after the change.
3. After each flow, write **one sentence** under "My sentence": what does this flow do?
4. Start with the **key flows**. Part 3 has the other flows. They are optional.
5. When you're done, run `/review-code-change-flow-notes check`.

**Words used below:** <jargon, one line each>

## The key flows (read these)
| # | Flow | Why it's a key flow |
|---|---|---|
| K1 | <input → output> | <one line> |

---

# Part 1: <old> (old code)

## K1 on <old>. <input → output>
1. <what happens> ([file:line](<link>))
2. …

**My sentence:**
>

**Claude check:**
> _(empty until you run check)_

---

# Part 2: <new> (new code)

## K1 on <new>. <input → output>
1. <what happens> ([file:line](<link>))
2. …

**Tests:** [file:line](<link>) <test name> · …

**My sentence:**
>

**Claude check:**
> _(empty until you run check)_

---

# Part 3: other flows (optional)

## O1. <input → output> (<happy | edge | failure | unchanged, affected>)
**On <old>:**
1. …

**On <new>:**
1. …

**Tests:** … or **No test**

**My sentence:**
>

---

## Gaps
- <flows with no test, and anything that looked wrong while listing the flows>

## My overall notes
>
````

## Checking
`/review-code-change-flow-notes check [<notes file>]` (if no file is given, use the newest `flow-notes-*.md` in the project folder, or ask):
1. Read the file. For each flow with a sentence under **My sentence**, read the code for that flow again (old code for Part 1, new code for Part 2).
2. Under **Claude check** (add one under an Other flow if it has none), write one of:
   - **Correct.** Plus what they got right, in one line.
   - **Partly correct.** Plus what is missing or wrong, and a link to the line that shows it.
   - **Not correct.** Plus what the flow really does, and a link.
3. Be honest. Don't call it correct to be nice. Don't rewrite their sentence: point at the gap, so they can fix it.
4. Change only the **Claude check** fields. Never edit their sentences or notes.
5. Reply with a count (correct / partly / not correct) and the flows to look at again.
