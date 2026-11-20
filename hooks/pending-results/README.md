# pending-results (hold subagent results until you're ready)

## What this does

When a subagent or background task finishes while you're in the middle of another topic, Claude would usually jump to
its results. This keeps them on hold instead:

- **A list on disk:** `~/.claude/notes/pending-results.md`, one line per held result (`- [ ] …`, ticked `- [x] …` once
  discussed). It survives compaction and new sessions.
- **Status line:** shows `[N results waiting]` in yellow while anything is held.
- **Hook (`UserPromptSubmit`):** on every message it tells Claude what is held and to keep it out of the current topic;
  every 5th message it shows you a reminder.
- **A rule for Claude** (below), so it adds items to the list instead of switching topic.

## Install

1. Copy the script:
   ```
   cp hooks/pending-results/pending_results.py ~/.claude/hooks/ && chmod +x ~/.claude/hooks/pending_results.py
   ```
2. Add the hook to `~/.claude/settings.json` (merge into any existing `UserPromptSubmit` array):
   ```json
   {
     "hooks": {
       "UserPromptSubmit": [
         { "hooks": [{ "type": "command", "command": "python3 $HOME/.claude/hooks/pending_results.py prompt-hook", "timeout": 5 }] }
       ]
     }
   }
   ```
3. Add the segment to the end of your status line script (the one `statusLine.command` runs):
   ```bash
   python3 "$HOME/.claude/hooks/pending_results.py" statusline 2>/dev/null
   ```
4. Give Claude the rule, in `~/.claude/CLAUDE.md` or an always-loaded memory:
   > When a subagent or background task finishes while we're discussing something else: say it finished in one line,
   > add `- [ ] <topic>: <one-line summary or question> — details: <path>` to `~/.claude/notes/pending-results.md`
   > (saving any detail to a file), and carry on with the current topic. Raise held results only when I say I'm ready,
   > or in one line at a natural pause. Go through them one at a time and tick each once discussed.

## Test

```
printf '# Pending\n\n- [ ] test item\n' > ~/.claude/notes/pending-results.md
python3 ~/.claude/hooks/pending_results.py statusline; echo
echo '{}' | python3 ~/.claude/hooks/pending_results.py prompt-hook
```
