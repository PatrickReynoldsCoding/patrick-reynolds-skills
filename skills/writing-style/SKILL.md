---
name: writing-style
description: List the plugin's writing styles, or choose the one every new session loads. Use on /writing-style, or when the user asks which writing styles there are, which one is on, or to switch to another one.
argument-hint: "[style name]"
---

# Writing style

The styles are the files in `writing-styles/` (the plugin root is 2 folders above this skill's folder). The plugin's SessionStart hook loads the chosen one in full at the start of every session, after `/clear` and after compaction. The chosen name is kept in `~/.claude/writing-style`.

## With no argument: list the styles
1. Run `python3 <plugin root>/hooks/writing-style/writing_style.py list`. It prints every style, with `*` before the chosen one.
2. Show the list, with the first heading line of each style file, and say which one is chosen (or that none is).
3. Ask which one to choose, as a numbered list.

## With a style name: choose it
1. Run `python3 <plugin root>/hooks/writing-style/writing_style.py choose <name>`. If the name is unknown, it fails: run `list` and show the user the known names.
2. Say that every new session now loads it.
3. The current session keeps its style. To switch now, read the style file and follow it from the next reply.

## Add a style
Add a Markdown file to `writing-styles/`. Its file name, without `.md`, is the style's name.
