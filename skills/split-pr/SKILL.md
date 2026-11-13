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
Sometimes PR n needs something only PR n+1 provides. Then add a **named placeholder** in PR n:
- a function or value named for what is coming, that does nothing safely (returns `None`, an empty list, a pass);
- a docstring that starts with `Temporary:` and says what it will do and which part replaces it;
- no `#` comments.
Example: `analyze_word_level_adherence` returning `(1.0, [])` in part 1, with "Temporary: the word check comes in part 2 …".

**At the top of the stack, every placeholder must be gone**, and so must anything else no longer needed (a do-nothing default class, an unused parameter, an import). Check with `git grep -n "Temporary:"` on the top branch, and look at each default value that does nothing. Delete leftovers in the PR that made them unnecessary.

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
2. **Nothing added then replaced:** for each later PR, trace the lines it removes back to the PR that added them (`git diff -U0 <commit>^ <commit>` for the removed ranges, then `git blame` those ranges on `<commit>^`). Report anything added in one PR and removed or rewritten in a later one. Only placeholders should show up; anything else means code arrived too early.
3. **No leftovers:** `git grep "Temporary:"` on the top branch is empty, and no do-nothing defaults remain.
4. Move PRs that were built on the original on top of the stack: rebase onto the top branch, run the tests, push with `--force-with-lease`, and change their base (`gh pr edit <n> --base <top branch>`). Check their diff shows only their own change.

## 6. Hand over
- Don't touch the original PR or its branch: report that the stack replaces it and let Patrick decide.
- Merge advice: merge commits, not squash (a squash makes the next PR show the earlier commits again until it is rebased). When a merged branch is deleted, GitHub moves the next PR's base to the integration branch by itself.
- Report: the integration branch, each PR (link, idea, line counts, test result), placeholders and where they are removed, the equality check, the add-then-replace trace, moved PRs, and anything to decide.

## When a lower PR changes later
After a review fix on PR n: rebase the PRs above it in order, run the full tests on each, push with `--force-with-lease`. Before renaming anything in PR n, check whether later PRs use the name (`git grep <name> origin/<later branch>`) and carry the rename up. Say which PRs moved.
