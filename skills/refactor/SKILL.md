---
name: refactor
description: Refactor code to follow the coding-style guide (knowledge/coding-style.md). Use on /refactor, or when Patrick asks to "refactor this", "tidy this up to our style" or "make this follow the coding guide". For a slow, one-bit-at-a-time walkthrough that also adds examples to the guide, use /refactor-and-review instead.
argument-hint: "[file, function or branch to refactor]"
---

# Refactor

Refactor the code to follow `knowledge/coding-style.md` in this plugin (the plugin root is 2 folders above this skill's folder).

1. **Read the guide:** the general section, and the section for the code's language.
2. **Find the code:** the argument (a file, a function or a branch). With no argument, use the uncommitted changes (`git diff`), else ask Patrick what to refactor.
3. **Refactor it** to follow the guide. Keep the behaviour the same, keep outside contracts (API keys, JSON fields, stored names), and only touch code in scope: the argument, or the code the branch changed.
4. **Run the tests** and make sure the counts don't change. Don't edit a test to make it pass.
5. **Say what you changed** in a few lines, with the guide rule behind each change. Don't commit or push unless Patrick asks.
