# pending-results (a per-session shelf for subagent results and todos)

## What this does

Each Claude Code session gets its own shelf, `~/.claude/notes/sessions/<session_id>.md`, one line per item:

```
- [ ] [ready] 3f2a9c1b: Explore: Found 4 callers
- [ ] [parked] 1: fix the flaky test
```

| State | Added by | Meaning |
|---|---|---|
| `running` | `SubagentStart` hook | A subagent is working. |
| `ready` | `SubagentStop` hook | A subagent finished. Claude holds the result until you are ready. |
| `parked` | you, with `todo: …` | A todo for later. |
| `blocked` | you, with `blocked: …` | Waiting on something outside the session (CI, a review). |

A new session (including after `/clear`) starts with an empty shelf. `/resume` brings the old shelf back. Shelf files
older than 14 days are deleted.

**Status line** (count per state, nothing when the shelf is empty, no titles):

```
 ⟳2 running  ✓1 ready  ☐4 parked  ⏸1 blocked
```

**Typing into the prompt** (the hook handles these itself, so Claude never sees them and no model turn runs):

| You type | What happens |
|---|---|
| `todo: fix the flaky test` | Shelves a parked item. |
| `blocked: wait for CI on PR 80` | Shelves a blocked item. |
| `done: 3` | Ticks item 3. |
| `shelf:` | Lists the shelf to you. |
| `shelf: 3 let's do this` | Tells Claude item 3 and lets your message through. |

## What it costs in tokens

- Status line, tracking, capture and `shelf:` listing: no tokens. They never reach the model.
- The prompt hook tells Claude only about `ready` results, at most 3, each cut to 100 characters, and only when the
  list changed since the last prompt (and again after a compaction). Parked and blocked items are never sent.
- The reminder every 5th prompt goes to you only.

## Install

1. Copy the script:
   ```
   cp hooks/pending-results/pending_results.py ~/.claude/hooks/ && chmod +x ~/.claude/hooks/pending_results.py
   ```
2. Add the hooks to `~/.claude/settings.json` (merge into the existing arrays):
   ```json
   {
     "hooks": {
       "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "python3 $HOME/.claude/hooks/pending_results.py prompt-hook", "timeout": 5 }] }],
       "SubagentStart": [{ "hooks": [{ "type": "command", "command": "python3 $HOME/.claude/hooks/pending_results.py subagent-start", "timeout": 5 }] }],
       "SubagentStop": [{ "hooks": [{ "type": "command", "command": "python3 $HOME/.claude/hooks/pending_results.py subagent-stop", "timeout": 5 }] }],
       "PostCompact": [{ "hooks": [{ "type": "command", "command": "python3 $HOME/.claude/hooks/pending_results.py after-compact", "timeout": 5 }] }]
     }
   }
   ```
3. Add the segment to the end of your status line script. The status line gets the session id on stdin, so pass the
   JSON on (the script must keep the JSON it read, e.g. `input=$(cat)`):
   ```bash
   echo "$input" | python3 "$HOME/.claude/hooks/pending_results.py" statusline 2>/dev/null
   ```
4. Give Claude the rule, in `~/.claude/CLAUDE.md` or an always-loaded memory:
   > The hooks add subagent results to the session shelf by themselves. When one is listed as waiting and we're on
   > another topic, say in one line that it is ready and carry on. Discuss it when I say I'm ready (or at once if I
   > was waiting for it), then tick it (`- [x]`) in the shelf file named in the hook message.

## Test

```
python3 -m unittest test_pending_results          # from this folder
printf '%s' '{"session_id":"test-1","prompt":"todo: try it"}' | python3 pending_results.py prompt-hook
printf '%s' '{"session_id":"test-1"}' | python3 pending_results.py statusline; echo
```
