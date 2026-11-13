# patrick-reynolds-skills

A Claude Code plugin with general-purpose skills and a small hook catalog.

## Install

```
/plugin marketplace add PatrickReynoldsCoding/patrick-reynolds-skills
/plugin install patrick-reynolds-skills@patrick-reynolds-skills
```

## Skills

| Skill | What it does |
|---|---|
| `explain` | Explain code or an idea in the shared writing style, answer first. `/explain asd <topic>` uses ASD-STE100 Simplified Technical English. |
| `review-annotate-code` | Temporarily annotate a branch's changes with numbered reading-order comments. Can move them to a GitHub PR as review comments. |
| `review-code-change-flow-notes` | Write flow notes for a code change (old vs new code) so you can learn to read it, with a blank for your own summary of each flow. Set `FLOW_NOTES_ROOT` to choose where notes go. |
| `review-code-diagram` | Draw a code flow as an Excalidraw sequence diagram where every box and arrow opens the exact line in IntelliJ. Ships a local server, a link opener app and a VS Code extension (macOS). |
| `refactor-and-review` | Go through a code change with you one bit at a time: say what it does, refactor it to the coding-style guide (names, helpers, no comments), run the tests, and add good before/after examples to the guide. |
| `split-pr` | Split a PR that is too big to review into a stack of small draft PRs, one idea each, merging in order into an integration branch. Offers `/refactor-and-review` first, asks before splitting, allows only named placeholders that are gone at the top, and proves the top matches the original. |
| `excel-table` | Build a styled `.xlsx` table (wrapped cells, fitted row heights, colour groups, legend). |

## Knowledge

Shared docs in `knowledge/`. They are not loaded on their own; skills and your `CLAUDE.md` point at them.

- `knowledge/writing-style.md` — how explanations are written. `explain`, `review-annotate-code`, `review-code-change-flow-notes` and `review-code-diagram` all use it. Edit it here to change the style everywhere.
- `knowledge/coding-style.md` — coding style and best practices (general, Python, Scala / ZIO, Bash). `refactor-and-review` adds examples to it as you refactor.

## Hooks (copy-paste, not auto-installed)

Nothing in `hooks/` runs on install. Copy a hook into `~/.claude/hooks/` and wire it
into `~/.claude/settings.json` as its README says.

- `notify-claude-ready/` — macOS notification when Claude finishes a turn.
- `notify-permission-request/` — macOS notification when Claude asks for permission.
