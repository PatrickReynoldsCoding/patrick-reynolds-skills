---
name: split-pr
description: Split a pull request that is too big to review into a stack of small draft PRs, one idea each, that merge in order into an integration branch and then into main. Asks first whether to run /refactor-and-review before splitting, proposes the split for approval, keeps temporary code to named placeholders that are all gone at the top of the stack, and proves the top of the stack matches the original. Use on /split-pr, or when Patrick says a PR is too big to review, asks to "split this PR", "make a stack", or "break this into smaller PRs".
argument-hint: "<PR number or branch>"
---

# Split a PR into a reviewable stack

**Goal:** a reviewer can read each PR on its own, in one sitting, and understand what it adds and why. Always think about the reviewer: what they read first, what they can skim, what they need to know from earlier PRs.

## 0. Before anything: refactor first?
Ask Patrick whether to run `/refactor-and-review` on the change before splitting it. Tidying names and helpers in one branch is easier than in five, and every later fix to a lower PR means rebasing the ones above it. Only start splitting when he says so.

## 1. Read the change
1. Read the coding-style guide (`knowledge/coding-style.md` in this plugin; the plugin root is 2 folders above this skill's folder) and `knowledge/writing-style.md` for PR descriptions.
2. `git fetch origin`. Read the PR (`gh pr view <n>`), its description and comments, and `git diff --stat --merge-base origin/<base>...origin/<branch>`.
3. Sort the added lines into **hand-written code**, **tests**, **docs** and **generated files** (they say so in their header: character tables, coverage files, lock files). Generated files don't count towards size, but list them.
4. Map how the new modules depend on each other (which file imports which), and how the tests are grouped (by class or file).
5. Check for other PRs built on this one (`gh pr list --base <branch>`). They will move on top of the stack.

## 2. Propose the split, and ask
**One idea per PR.** Never split one idea over several PRs, even if it is big; say why it is big instead.
- **Size:** under 200 hand-written lines (code + tests) is the sweet spot; over 1,000 should be avoided. Both are guides, not rules: one idea that can't be cut stays whole.
- **Order:** build order, so each PR only uses what earlier PRs added. Each PR carries its own tests.
- **Introduce code where it is first used.** A function, parameter or field arrives in the PR whose code first calls it, not earlier "for later". Don't add something in one PR that a later PR replaces, except the placeholders below.

Show Patrick a table, then wait for his OK. Always ask first; never split without approval:

| # | Idea | Files | Code / tests / docs / generated lines | Placeholders needed | What the reviewer reads closely |
|---|---|---|---|---|---|

Also say: the integration branch name, which PRs go over the size guide and why, and which other PRs will move on top.

## 3. Placeholders (temporary code)
Sometimes PR n needs something only a later PR provides. Use the smallest placeholder that keeps the code honest:
- **Preferred: a value, not a new function.** At the place where the logic will run, set a well-named value to the do-nothing result, with one `#` comment naming the PR that brings the logic (number and title) and what it will do. Keep the code that uses the value, so the reader sees where the check will go. This is the one comment the no-comments rule allows, because it is deleted when the logic arrives.
  ```python
  # Coming in PR #80 "ASKIM-3362 scorer v2 (3/5): reference profiles and bracket check": in a non-Latin answer, a line with no letter of the answer's alphabet and 2+ Latin words left after names are blanked → whole_line_in_another_language
  whole_line_in_another_language: Optional[LineVerdict] = None
  if whole_line_in_another_language is not None:
      return whole_line_in_another_language
  ```
- **Only when callers already need a function or method**, keep it with a do-nothing body and a docstring that starts with `Temporary:` and names the PR that replaces it, e.g. `analyze_word_level_adherence` returning `(1.0, [])` in part 1. Don't create a new placeholder method just to hold a future check (Patrick rejected `_find_whole_line_in_another_language` returning `None` for this).
- **Removing a rule whose replacement needs later inputs:** remove it in the lowest PR, put the value placeholder there, and add the replacement in the PR where its inputs first exist. Don't add a weaker version low down and rewrite it higher up.

**At the top of the stack, every placeholder must be gone**, and so must anything else no longer needed: a do-nothing default class (`NoTransliteratedNameCheck` left as a default was not accepted), an unused parameter, a one-line wrapper kept only because tests call it (point the tests at the real function instead), an import. Check with `git grep -n "Temporary:\|Coming in PR"` on the top branch, and look at each default value that does nothing. Delete leftovers in the PR that made them unnecessary.

## 4. Build the stack
- **Integration branch:** `<ticket>-<short-name>` from `origin/<base of the original PR>`, pushed with no commits. Every stack PR merges into it in order; it goes to the base (usually `main`) at the end, so a partial change never runs anywhere.
- **Branches:** `<ticket>-<short>-<n>-<idea>`, e.g. `ASKIM-3362-v2-1-line-check`. Work in worktrees inside the repo (`<repo>/.claude/worktrees/<name>`).
- **Commits:** one clean commit per PR. Changes Patrick agrees to during the split (removing obsolete code, a rename) get their own clearly named commit in the PR they belong to.
- **Tests:** the full test suite must pass at every PR on its own. Record the counts per PR.
- **PRs:** drafts. Base of PR 1 = the integration branch; base of PR n = PR n-1's branch. Title `<ticket> <name> (n/N): <idea>`. Body, in the writing style:
  - what this PR adds and why, in plain words;
  - which files to read closely, which to skim (tests), which are generated;
  - placeholders it adds or removes;
  - "Part n of N, merge in order into `<integration branch>`", with links to every part;
  - line counts and how to test.
  Put background that covers the whole change (eval results, how it was tested) in PR 1 only.
- End each commit with the Co-Authored-By line and each PR body with the Claude Code footer. Follow the git rules in Patrick's CLAUDE.md (signing, no bypassing hooks, `--force-with-lease` only).

## 5. Prove it
1. **Same result:** the top of the stack has exactly the same files as the original branch, except the changes Patrick agreed to. Show `git diff <original head> <top of stack> --stat`, and list each difference.
2. **Nothing added then replaced:** for each later PR, trace the lines it removes back to the PR that added them (`git diff -U0 <commit>^ <commit>` for the removed ranges, then `git blame` those ranges on `<commit>^`). Report anything added in one PR and removed or rewritten in a later one. Only placeholders should show up; anything else means code arrived too early. Also look for logic whose **meaning** changes higher up while its lines stay (e.g. a limit that counts all letters in part 1 but only the letters left after names are blanked from part 2): report it, because a reviewer of the lower PR judges the wrong version.
3. **No leftovers:** `git grep "Temporary:\|Coming in PR"` on the top branch is empty, and no do-nothing defaults, unused parameters or test-only wrappers remain.
4. Move PRs that were built on the original on top of the stack: rebase onto the top branch, run the tests, push with `--force-with-lease`, and change their base (`gh pr edit <n> --base <top branch>`). Check their diff shows only their own change.

## 6. Hand over
- Don't touch the original PR or its branch: report that the stack replaces it and let Patrick decide.
- Merge advice: merge commits, not squash (a squash makes the next PR show the earlier commits again until it is rebased). When a merged branch is deleted, GitHub moves the next PR's base to the integration branch by itself.
- Report: the integration branch, each PR (link, idea, line counts, test result), placeholders and where they are removed, the equality check, the add-then-replace trace, moved PRs, and anything to decide.

## When a lower PR changes later
Patrick reviews one PR at a time and edits it in his own checkout while you work.
- **Work on top of his uncommitted edits.** Never commit, stash, reset or check out in his checkout unless he asks. Keep his names. If a file changes while you work, read it again before editing.
- **Collect the fixes, rebase once.** Don't commit or rebase after every fix. When he says the PR is done, commit it (renames first), then rebase the PRs above it in order, run the full tests on each, and push with `--force-with-lease`. Say which PRs moved.
- **Before changing PR n, check what later PRs do to the same code:** whether they use a name you rename (`git grep <name> origin/<later branch>`), and whether they rewrite the same function (`git diff origin/<PR n branch> origin/<PR n+1 branch> -- <file>`). Tell Patrick which later PRs will need the change carried up or will conflict, before you make it.
- **Tests:** when you move tests between classes, check the target class name isn't already used in the file. Python keeps only the last class of a name, so the first one's tests stop running without an error.
