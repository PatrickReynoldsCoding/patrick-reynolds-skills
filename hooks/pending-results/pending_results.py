#!/usr/bin/env python3
"""Pending subagent results: results Claude holds back until you say you are ready.

The list lives in ~/.claude/notes/pending-results.md, one item per line starting with "- [ ] ". Claude adds an item
when a subagent finishes and ticks it ("- [x] ") once it has been discussed.

  pending_results.py statusline   prints a short status line segment when items are pending (nothing otherwise)
  pending_results.py prompt-hook  UserPromptSubmit hook: tells Claude what is pending, and every few prompts shows
                                  you a reminder
"""

import json
import os
import sys

PENDING_FILE = os.path.expanduser("~/.claude/notes/pending-results.md")
PROMPT_COUNT_FILE = os.path.expanduser("~/.claude/notes/.pending-results-prompt-count")
PROMPTS_BETWEEN_REMINDERS = 5
PENDING_MARK = "- [ ] "


def pending_items() -> list:
    try:
        with open(PENDING_FILE, encoding="utf-8") as pending_file:
            return [line[len(PENDING_MARK):].strip() for line in pending_file if line.startswith(PENDING_MARK)]
    except OSError:
        return []


def print_statusline_segment() -> None:
    items = pending_items()
    if len(items) > 0:
        print(f"\033[1;33m [{len(items)} result{'s' if len(items) > 1 else ''} waiting]\033[0m", end="")


def next_prompt_count() -> int:
    try:
        with open(PROMPT_COUNT_FILE, encoding="utf-8") as count_file:
            count = int(count_file.read().strip() or 0) + 1
    except (OSError, ValueError):
        count = 1
    try:
        with open(PROMPT_COUNT_FILE, "w", encoding="utf-8") as count_file:
            count_file.write(str(count))
    except OSError:
        pass
    return count


def run_prompt_hook() -> None:
    sys.stdin.read()
    items = pending_items()
    if len(items) == 0:
        print("{}")
        return
    listing = "\n".join(f"- {item}" for item in items)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                f"Subagent results waiting for the user (from {PENDING_FILE}):\n{listing}\n"
                "Hold them: don't bring them into the current topic or switch to them. Discuss them only when the user "
                "says they are ready, then tick the item ([x]) in that file."
            ),
        }
    }
    if next_prompt_count() % PROMPTS_BETWEEN_REMINDERS == 0:
        output["systemMessage"] = f"Reminder: {len(items)} subagent result{'s' if len(items) > 1 else ''} waiting to discuss: " + "; ".join(items)
    print(json.dumps(output))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "statusline":
        print_statusline_segment()
    elif mode == "prompt-hook":
        run_prompt_hook()
