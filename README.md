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
| `refactor` | Refactor code to follow `knowledge/coding-style.md`, keep the behaviour the same, and run the tests. The short version of `refactor-and-review`. |
| `refactor-and-review` | Go through a code change with you one bit at a time: say what it does, refactor it to the coding-style guide (names, helpers, no comments), run the tests, and add good before/after examples to the guide. |
| `split-pr` | Split a PR that is too big to review into a stack of small draft PRs, one idea each, merging in order into an integration branch. Offers `/refactor-and-review` first, asks before splitting, allows only named placeholders that are gone at the top, and proves the top matches the original. |
| `excel-table` | Build a styled `.xlsx` table (wrapped cells, fitted row heights, colour groups, legend). |
| `text-me` | Send a push notification to your phone through ntfy. Reads the topic from the `NTFY_TOPIC` environment variable, so the secret is never in the repo. |
| `writing-style` | List the writing styles, or choose the one every new session loads (see Writing styles). |

## Writing styles

One file per style in `writing-styles/`. Choose one with `/writing-style <name>`: the plugin's SessionStart hook then loads it in full at the start of every session (and after `/clear` and compaction). The choice is kept in `~/.claude/writing-style`; with no choice, nothing is loaded.

- `low-cognitive-load.md` — for readers who tire from reading: short replies, one question at a time, notes kept for you, pauses.
- `plain.md` — how explanations are written: answer first, say why, real examples. `explain`, `review-annotate-code`, `review-code-change-flow-notes`, `review-code-diagram`, `refactor-and-review` and `split-pr` use it.

## Knowledge

Shared docs in `knowledge/`. They are not loaded on their own; skills and your `CLAUDE.md` point at them.

- `knowledge/coding-style.md` — coding style and best practices (general, Python, Scala / ZIO, Bash). `refactor-and-review` adds examples to it as you refactor.

## Hooks

`hooks/hooks.json` installs one hook with the plugin: `writing-style/`, which loads the chosen writing style (see above).

The others are copy-paste and don't run on install. Copy one into `~/.claude/hooks/` and wire it
into `~/.claude/settings.json` as its README says.

- `notify-claude-ready/` — macOS notification when Claude finishes a turn.
- `notify-permission-request/` — macOS notification when Claude asks for permission.
- `pending-results/` — hold subagent results until you're ready, with a status line count and reminders.
