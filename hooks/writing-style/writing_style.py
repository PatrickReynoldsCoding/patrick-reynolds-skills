#!/usr/bin/env python3
"""Load one of the plugin's writing styles into every session.

The styles are the files in writing-styles/ (low-cognitive-load.md, plain.md, ...). The chosen style's name is the
only line of ~/.claude/writing-style. With no such file, nothing is loaded.

  writing_style.py session-start  SessionStart hook: gives Claude the chosen style in full
  writing_style.py list           prints every style, with "*" before the chosen one
  writing_style.py choose <name>  makes <name> the style of every new session
"""

import json
import sys
from pathlib import Path
from typing import List, Optional

PLUGIN_ROOT: Path = Path(__file__).resolve().parents[2]
WRITING_STYLES_FOLDER: Path = PLUGIN_ROOT / "writing-styles"
CHOSEN_WRITING_STYLE_FILE: Path = Path.home() / ".claude" / "writing-style"


def writing_style_names(writing_styles_folder: Path) -> List[str]:
    return [style_file.stem for style_file in sorted(writing_styles_folder.glob("*.md"))]


def chosen_writing_style_name(chosen_writing_style_file: Path) -> Optional[str]:
    try:
        chosen_name: str = chosen_writing_style_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if len(chosen_name) == 0:
        return None
    return chosen_name


def session_start_output(chosen_name: Optional[str], writing_styles_folder: Path) -> Optional[dict]:
    if chosen_name is None:
        return None
    style_file: Path = writing_styles_folder / f"{chosen_name}.md"
    if not style_file.is_file():
        known_names: str = ", ".join(writing_style_names(writing_styles_folder))
        return {"systemMessage": f"Writing style '{chosen_name}' not found in {writing_styles_folder}. Known styles: {known_names}. Run /writing-style to choose one."}
    style_text: str = style_file.read_text(encoding="utf-8")
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"# Default writing style for this session: {chosen_name} ({style_file})\n\nFollow it in every reply.\n\n{style_text}",
        }
    }


def style_listing(names: List[str], chosen_name: Optional[str]) -> str:
    lines: List[str] = []
    for name in names:
        marker: str = "*" if name == chosen_name else " "
        lines.append(f"{marker} {name}")
    return "\n".join(lines)


def choose_writing_style(name: str, writing_styles_folder: Path, chosen_writing_style_file: Path) -> None:
    if name not in writing_style_names(writing_styles_folder):
        raise ValueError(f"No writing style '{name}' in {writing_styles_folder}")
    chosen_writing_style_file.parent.mkdir(parents=True, exist_ok=True)
    chosen_writing_style_file.write_text(f"{name}\n", encoding="utf-8")


def main(arguments: List[str]) -> int:
    mode: str = arguments[0] if len(arguments) > 0 else ""
    if mode == "session-start":
        output: Optional[dict] = session_start_output(chosen_writing_style_name(CHOSEN_WRITING_STYLE_FILE), WRITING_STYLES_FOLDER)
        if output is not None:
            print(json.dumps(output))
        return 0
    if mode == "list":
        print(style_listing(writing_style_names(WRITING_STYLES_FOLDER), chosen_writing_style_name(CHOSEN_WRITING_STYLE_FILE)))
        return 0
    if mode == "choose" and len(arguments) == 2:
        try:
            choose_writing_style(arguments[1], WRITING_STYLES_FOLDER, CHOSEN_WRITING_STYLE_FILE)
        except ValueError as error:
            print(error, file=sys.stderr)
            return 1
        print(f"Every new session now loads the '{arguments[1]}' writing style.")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
