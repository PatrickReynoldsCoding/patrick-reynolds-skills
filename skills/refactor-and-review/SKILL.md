---
name: refactor-and-review
description: Walk through a code change with Patrick one bit at a time — say what each bit does, propose a refactor that follows the coding-style guide (clearer names, named helpers and constants, no unused parameters, no comments), make it, run the tests, then (once Patrick confirms why each change was made) add any good before/after example to the guide. Use on /refactor-and-review, or when Patrick asks to "go through this PR and refactor bits one by one", "review and tidy this change", or "refactor this branch with me".
argument-hint: "[base branch or PR number] [file or area to start with]"
---

# Refactor and review

**Goal:** The change reads clearly to a reviewer who doesn't know the project, its behaviour stays exactly the same, and the coding-style guide gets better examples, with the real reasons Patrick gave, at the end.

This is a conversation, not a batch job. Patrick reviews each bit, often names things himself, and decides what changes.

## 1. Before you start
1. **Read the guide:** `knowledge/coding-style.md` in this plugin (the plugin root is 2 folders above this skill's folder). Read the general section and the section for the change's language. Read `knowledge/writing-style.md` for how to write your replies.
2. **Find the change.**
   - Target: the current branch (`HEAD`). Base: the argument, else the base of the branch's open PR (`gh pr view --json baseRefName -q .baseRefName`), else `main`. `git fetch origin` and diff against `origin/<base>` with `--merge-base`.
   - List the files and their size: `git diff --stat --merge-base origin/<base>`. Skip generated files (they say so in their header), lock files and test data. Ask Patrick which file to start with if the argument doesn't say. Otherwise start with the entry point and go down to its helpers.
3. **Read Patrick's own work first.**
   - `git status` and `git diff`: he often has uncommitted edits. Keep them. Never revert or rewrite them.
   - Look for his notes in the code: `grep -rn "NOTES FOR CLAUDE" <changed files>`. Each note is a question or a request. Answer it as one of the bits below, then remove the note line once it is dealt with.
4. **Scope:** only code the change adds or changes. Leave untouched code alone, even in the same function (see the guide's scope rule).
   **Temporary split-pr leftovers:** a branch cut by the split-pr skill can carry placeholders for a later PR in the stack: a comment such as `# Coming in PR #80 …` with a dummy variable or an `if … is not None` block that can't fire yet, or a temporary stub (a function that returns a fixed value, a parameter it ignores, a "Temporary:" docstring). Leave them alone, and don't list them as candidates. They are removed when the later PR lands, and the no-comment and unused-parameter rules don't apply to them. If you are not sure whether something is such a leftover, ask Patrick.
5. **Find the test command** (`pytest`, `sbt test`, …) and run it once, so you know the starting count.

## 2. One bit at a time
A bit is one function, one block or one group of names: small enough to read in one screen.

For each bit:
1. **Show it.** Quote the code (a short block), with a clickable link to its place, labelled `<repo>/<path>:<line>` (follow Patrick's link rule in his CLAUDE.md).
2. **Say what it does** in one or two sentences, with a real value (an input and what comes out). If Patrick asked a question about it, answer that first.
3. **Propose the refactor**, naming the guide rule it follows. Typical ones:
   - a block with one purpose (often a loop that searches for one answer) → a named helper, so the caller reads as a list of steps;
   - a bare condition or literal (`category.startswith("L")`) → a named helper or constant;
   - a vague name (`text`, `count`, `best`, `char`, `start, end`) → a name that says what is in it and what was done to it;
   - a function name whose verb does not fit the work, or has no object (`check_line` → "check it for what?"; `check` sounds like one quick look, but the function weighs a lot of information) → a verb that fits and the thing it works out (`evaluate_line_language`). Generic verbs are fine when they fit, so ask "does this verb fit what the function does?" and prefer the word the repo already uses (`evaluate_…`). Look at EVERY function name in the change, public entry points included. It is easy to skip the entry point because you have read it so often;
   - a parameter no caller passes, or a do-nothing default → remove it, or add it where the first caller is;
   - a comment that explains the code → a name that makes it unnecessary.
   Give the name you suggest and one line on why. If Patrick suggests a name, use his. If he has already renamed something nearby, follow his pattern (e.g. his `detect_script_from_char` → `_detect_script_from_unicode_range`).
4. **Make the change** when Patrick agrees (or straight away if he asked for that). Then run the tests: the counts must not change, and a test must not be edited to pass. Keep any outside contract the same: an API key, a JSON field or a stored name stays, even if the code behind it is renamed.
5. **Say what you changed** in a few lines, and what's next. Wait for Patrick.

Ask before anything bigger than a rename or an extraction: moving code between files, changing behaviour, or changing a public name that other code imports. In a stack of PRs, check whether later PRs import a name before renaming it (`git grep <name> origin/<later branch>`), and say which PRs will need the rename.

## 3. Confirm why we made each change, then update the guide
Patrick often refactors on his own, or asks for a change without saying why. Don't guess the reason when you write a guide rule. Ask first. Do this when Patrick says he is done and asks for the guide update, and never skip it.

1. **List every change.** Collect them all: the commits since the start of the session, `git diff` (uncommitted work, including Patrick's own edits) and the changes you made. Group them by bit (one function, one block or one group of names). Skip nothing, including small renames and removed code or tests.
2. **Go through them one at a time with Patrick.** For each change:
   - Show the before → after (a short block) with a clickable link, as in section 2.
   - Say what you think the reason was, in one line, and that you are not sure (see the writing style, rule 11). If you have no idea, say so.
   - Ask: "Why did we make this change?" Wait for the answer. Don't batch several changes into one question.
3. **Write down his answer** in his own words: the reason, and whether it is a general rule or only fits this code. A reason that only fits this code is not a rule, so it doesn't go in the guide.
4. **Only then update the guide**, using his reasons for the **Why:** line. If an answer contradicts a rule already in the guide, tell him and ask which one stays.

## 4. Add good examples to the guide
When a bit shows a rule well, add it to the guide as a short before → after example, under the rule it belongs to. Do this after the "why" check in section 3, so the **Why:** line says what Patrick told you.
- **Edit the repo, not the installed copy:** `~/personal-repos/patrick-reynolds-skills/knowledge/coding-style.md`.
- Use the real code, cut to the lines that matter, and name the repo and file (e.g. "evaluation-api `line_language_check.py`").
- Add to an existing rule when one fits. Add a new rule only when none does, in the guide's format (**rule** / **Why:** / **How to apply:**), and say so to Patrick.
- Add a row to the naming table when the lesson is a single rename.
- Keep the guide's writing style: short sentences, plain words.
- Commit each addition in the personal repo and push it. Personal repo rules: run git there in its own command (never in the same command as a work path, or the guard hook blocks it), personal identity, the `github-personal` remote, no work-key signing. End the commit message with the Co-Authored-By line.

## 5. Commits and wrap-up
- Don't commit or push the code change until Patrick asks. Collect the bits, then commit them together (renames in their own commit before structural changes, see the guide). In a PR stack, every push to a lower PR means rebasing the PRs above it: say so, and do it only when asked.
- When Patrick stops, give a short summary: the bits changed (with links), the test result, the guide examples added, notes answered, and anything left (names later PRs import, open questions).
