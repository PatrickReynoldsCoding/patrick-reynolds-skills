#!/usr/bin/env python3
"""Session shelf: subagent results and todos that Claude holds until you are ready.

Each Claude Code session has its own file, ~/.claude/notes/sessions/<session_id>.md, one item per line:
"- [ ] [ready] 3f2a9c1b: text" (ticked "- [x] " once discussed or done). States: running, ready, parked, blocked.

  pending_results.py statusline       status line segment: a count per state (nothing when the shelf is empty)
  pending_results.py prompt-hook      UserPromptSubmit: todo:/blocked:/done:/shelf: capture, and tells Claude about
                                      ready results (only when they changed); shows you a reminder every few prompts
  pending_results.py subagent-start   SubagentStart: adds a running item
  pending_results.py subagent-stop    SubagentStop: turns the running item into a ready item
  pending_results.py after-compact    PostCompact: makes the next prompt tell Claude about ready results again
"""

import fcntl
import hashlib
import json
import os
import re
import sys
import time
import traceback
from dataclasses import dataclass, replace
from enum import Enum
from typing import Callable, Dict, List, Optional

SHELF_DIRECTORY = os.path.expanduser("~/.claude/notes/sessions")
SHELF_FILE_MAX_AGE_DAYS = 14
SECONDS_PER_DAY = 24 * 60 * 60
PROMPTS_BETWEEN_REMINDERS = 5
MAX_ITEMS_TOLD_TO_CLAUDE = 3
MAX_ITEM_TEXT_LENGTH = 100
AGENT_ID_LENGTH = 8
SESSION_ID_PATTERN = re.compile(r"^[\w-]+$")
SHELF_LINE_PATTERN = re.compile(r"^- \[(?P<done_mark>[ x])\] \[(?P<state>\w+)\] (?P<item_id>\w+): (?P<text>.*)$")
DONE_MARK = "x"
NOT_DONE_MARK = " "
RESET_COLOR = "\033[0m"


class ItemState(Enum):
    RUNNING = "running"
    READY = "ready"
    PARKED = "parked"
    BLOCKED = "blocked"


class CommandKind(Enum):
    TODO = "todo"
    BLOCKED = "blocked"
    DONE = "done"
    SHELF = "shelf"


@dataclass(frozen=True)
class ShelfItem:
    item_id: str
    state: ItemState
    text: str
    is_done: bool


@dataclass(frozen=True)
class ShelfCommand:
    kind: CommandKind
    argument: str


@dataclass(frozen=True)
class HookPayload:
    session_id: str
    prompt: str
    agent_id: str
    agent_type: str
    agent_description: str


@dataclass(frozen=True)
class SessionMeta:
    prompt_count: int
    last_told_to_claude_hash: str


@dataclass(frozen=True)
class PromptHookPlan:
    additional_context: Optional[str]
    reminder: Optional[str]
    updated_meta: SessionMeta


@dataclass(frozen=True)
class StatuslineSegment:
    symbol: str
    color_code: str


STATUSLINE_SEGMENT_BY_STATE: Dict[ItemState, StatuslineSegment] = {
    ItemState.RUNNING: StatuslineSegment(symbol="⟳", color_code="36"),
    ItemState.READY: StatuslineSegment(symbol="✓", color_code="1;33"),
    ItemState.PARKED: StatuslineSegment(symbol="☐", color_code="2"),
    ItemState.BLOCKED: StatuslineSegment(symbol="⏸", color_code="31"),
}
NOTE_STATE_BY_COMMAND_KIND: Dict[CommandKind, ItemState] = {
    CommandKind.TODO: ItemState.PARKED,
    CommandKind.BLOCKED: ItemState.BLOCKED,
}


def shorten_to_first_line(text: str) -> str:
    stripped_lines: List[str] = [line.strip() for line in text.splitlines() if len(line.strip()) > 0]
    if len(stripped_lines) == 0:
        return ""
    first_line: str = stripped_lines[0]
    if len(first_line) <= MAX_ITEM_TEXT_LENGTH:
        return first_line
    return first_line[: MAX_ITEM_TEXT_LENGTH - 1] + "…"


def parse_shelf_line(line: str) -> Optional[ShelfItem]:
    match: Optional[re.Match] = SHELF_LINE_PATTERN.match(line.rstrip("\n"))
    if match is None:
        return None
    try:
        state: ItemState = ItemState(match["state"])
    except ValueError:
        return None
    return ShelfItem(
        item_id=match["item_id"],
        state=state,
        text=match["text"],
        is_done=match["done_mark"] == DONE_MARK,
    )


def format_shelf_line(item: ShelfItem) -> str:
    done_mark: str = DONE_MARK if item.is_done else NOT_DONE_MARK
    return f"- [{done_mark}] [{item.state.value}] {item.item_id}: {item.text}"


def parse_shelf(lines: List[str]) -> List[ShelfItem]:
    items: List[ShelfItem] = []
    for line in lines:
        item: Optional[ShelfItem] = parse_shelf_line(line)
        if item is not None:
            items.append(item)
    return items


def find_item(items: List[ShelfItem], item_id: str) -> Optional[ShelfItem]:
    for item in items:
        if item.item_id == item_id:
            return item
    return None


def waiting_items_in_state(items: List[ShelfItem], state: ItemState) -> List[ShelfItem]:
    waiting_items: List[ShelfItem] = []
    for item in items:
        if item.state == state and not item.is_done:
            waiting_items.append(item)
    return waiting_items


def agent_item_id(agent_id: str) -> str:
    return agent_id[:AGENT_ID_LENGTH]


def with_running_agent(items: List[ShelfItem], agent_id: str, agent_type: str) -> List[ShelfItem]:
    item_id: str = agent_item_id(agent_id)
    if find_item(items, item_id) is not None:
        return items
    return items + [ShelfItem(item_id=item_id, state=ItemState.RUNNING, text=agent_type, is_done=False)]


def with_finished_agent(items: List[ShelfItem], agent_id: str, agent_type: str, agent_description: str) -> List[ShelfItem]:
    item_id: str = agent_item_id(agent_id)
    description: str = shorten_to_first_line(agent_description)
    finished_text: str = description if len(description) > 0 else agent_type
    ready_item: ShelfItem = ShelfItem(item_id=item_id, state=ItemState.READY, text=finished_text, is_done=False)
    items_with_result: List[ShelfItem] = []
    replaced_running_item: bool = False
    for item in items:
        if item.item_id == item_id:
            items_with_result.append(ready_item)
            replaced_running_item = True
        else:
            items_with_result.append(item)
    if not replaced_running_item:
        items_with_result.append(ready_item)
    return items_with_result


def next_note_id(items: List[ShelfItem]) -> str:
    note_numbers: List[int] = [int(item.item_id) for item in items if item.item_id.isdigit()]
    return str(max(note_numbers, default=0) + 1)


def with_new_note(items: List[ShelfItem], state: ItemState, text: str) -> List[ShelfItem]:
    note: ShelfItem = ShelfItem(item_id=next_note_id(items), state=state, text=text, is_done=False)
    return items + [note]


def with_item_done(items: List[ShelfItem], item_id: str) -> List[ShelfItem]:
    items_after_done: List[ShelfItem] = []
    for item in items:
        if item.item_id == item_id:
            items_after_done.append(replace(item, is_done=True))
        else:
            items_after_done.append(item)
    return items_after_done


def parse_shelf_command(prompt: str) -> Optional[ShelfCommand]:
    stripped_prompt: str = prompt.strip()
    for kind in CommandKind:
        prefix: str = f"{kind.value}:"
        if stripped_prompt.lower().startswith(prefix):
            return ShelfCommand(kind=kind, argument=stripped_prompt[len(prefix):].strip())
    return None


def statusline_text(items: List[ShelfItem]) -> str:
    segments: List[str] = []
    for state, segment in STATUSLINE_SEGMENT_BY_STATE.items():
        waiting_count: int = len(waiting_items_in_state(items, state))
        if waiting_count > 0:
            segments.append(f"\033[{segment.color_code}m{segment.symbol}{waiting_count} {state.value}{RESET_COLOR}")
    if len(segments) == 0:
        return ""
    return " " + " ".join(segments)


def shelf_listing(items: List[ShelfItem]) -> str:
    lines: List[str] = []
    for state in ItemState:
        for item in waiting_items_in_state(items, state):
            lines.append(f"{item.item_id}  {state.value:<8} {item.text}")
    if len(lines) == 0:
        return "The shelf is empty."
    return "\n".join(lines)


def ready_results_told_to_claude(ready_items: List[ShelfItem], shelf_path: str) -> str:
    shown_items: List[ShelfItem] = ready_items[:MAX_ITEMS_TOLD_TO_CLAUDE]
    listing: str = "\n".join(f"- {item.item_id}: {item.text}" for item in shown_items)
    not_shown_count: int = len(ready_items) - len(shown_items)
    not_shown_line: str = f"\n(+{not_shown_count} more in the file)" if not_shown_count > 0 else ""
    return (
        f"Subagent results waiting for the user (shelf file {shelf_path}):\n{listing}{not_shown_line}\n"
        "If the user is on another topic, hold them: don't bring them in or switch to them. Discuss them when the "
        "user says they are ready, or at once if the user is waiting for that result, then tick the item ([x]) in "
        "the file."
    )


def hash_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def plan_prompt_hook(items: List[ShelfItem], meta: SessionMeta, shelf_path: str) -> PromptHookPlan:
    ready_items: List[ShelfItem] = waiting_items_in_state(items, ItemState.READY)
    prompt_count: int = meta.prompt_count + 1
    if len(ready_items) == 0:
        return PromptHookPlan(
            additional_context=None,
            reminder=None,
            updated_meta=SessionMeta(prompt_count=prompt_count, last_told_to_claude_hash=""),
        )
    told_to_claude: str = ready_results_told_to_claude(ready_items, shelf_path)
    told_to_claude_hash: str = hash_of(told_to_claude)
    already_told: bool = told_to_claude_hash == meta.last_told_to_claude_hash
    reminder: Optional[str] = None
    if prompt_count % PROMPTS_BETWEEN_REMINDERS == 0:
        plural: str = "s" if len(ready_items) > 1 else ""
        reminder = f"Reminder: {len(ready_items)} subagent result{plural} waiting to discuss: " + "; ".join(
            item.text for item in ready_items
        )
    return PromptHookPlan(
        additional_context=None if already_told else told_to_claude,
        reminder=reminder,
        updated_meta=SessionMeta(prompt_count=prompt_count, last_told_to_claude_hash=told_to_claude_hash),
    )


def shelf_path_of(session_id: str) -> str:
    return os.path.join(SHELF_DIRECTORY, f"{session_id}.md")


def lock_path_of(session_id: str) -> str:
    return os.path.join(SHELF_DIRECTORY, f"{session_id}.lock")


def meta_path_of(session_id: str) -> str:
    return os.path.join(SHELF_DIRECTORY, f"{session_id}.meta.json")


def load_shelf(session_id: str) -> List[ShelfItem]:
    try:
        with open(shelf_path_of(session_id), encoding="utf-8") as shelf_file:
            return parse_shelf(shelf_file.readlines())
    except OSError:
        return []


def write_shelf(session_id: str, items: List[ShelfItem]) -> None:
    shelf_lines: List[str] = ["# Session shelf", ""] + [format_shelf_line(item) for item in items]
    temporary_path: str = shelf_path_of(session_id) + ".tmp"
    with open(temporary_path, "w", encoding="utf-8") as temporary_file:
        temporary_file.write("\n".join(shelf_lines) + "\n")
    os.replace(temporary_path, shelf_path_of(session_id))


def update_shelf(session_id: str, change: Callable[[List[ShelfItem]], List[ShelfItem]]) -> List[ShelfItem]:
    os.makedirs(SHELF_DIRECTORY, exist_ok=True)
    with open(lock_path_of(session_id), "w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        updated_items: List[ShelfItem] = change(load_shelf(session_id))
        write_shelf(session_id, updated_items)
        return updated_items


def load_meta(session_id: str) -> SessionMeta:
    try:
        with open(meta_path_of(session_id), encoding="utf-8") as meta_file:
            raw_meta: dict = json.load(meta_file)
        return SessionMeta(
            prompt_count=int(raw_meta.get("prompt_count", 0)),
            last_told_to_claude_hash=str(raw_meta.get("last_told_to_claude_hash", "")),
        )
    except (OSError, ValueError):
        return SessionMeta(prompt_count=0, last_told_to_claude_hash="")


def save_meta(session_id: str, meta: SessionMeta) -> None:
    os.makedirs(SHELF_DIRECTORY, exist_ok=True)
    with open(meta_path_of(session_id), "w", encoding="utf-8") as meta_file:
        json.dump({"prompt_count": meta.prompt_count, "last_told_to_claude_hash": meta.last_told_to_claude_hash}, meta_file)


def delete_old_session_files() -> None:
    oldest_allowed_time: float = time.time() - SHELF_FILE_MAX_AGE_DAYS * SECONDS_PER_DAY
    try:
        file_names: List[str] = os.listdir(SHELF_DIRECTORY)
    except OSError:
        return
    for file_name in file_names:
        file_path: str = os.path.join(SHELF_DIRECTORY, file_name)
        try:
            if os.path.getmtime(file_path) < oldest_allowed_time:
                os.remove(file_path)
        except OSError:
            continue


def description_of_agent(raw_payload: dict, agent_id: str) -> str:
    for background_task in raw_payload.get("background_tasks") or []:
        if background_task.get("id") == agent_id:
            return str(background_task.get("description") or "")
    return ""


def read_hook_payload() -> HookPayload:
    raw_text: str = sys.stdin.read()
    raw_payload: dict = json.loads(raw_text) if len(raw_text.strip()) > 0 else {}
    agent_id: str = str(raw_payload.get("agent_id") or "")
    return HookPayload(
        session_id=str(raw_payload.get("session_id") or ""),
        prompt=str(raw_payload.get("prompt") or ""),
        agent_id=agent_id,
        agent_type=str(raw_payload.get("agent_type") or ""),
        agent_description=description_of_agent(raw_payload, agent_id),
    )


def has_usable_session_id(payload: HookPayload) -> bool:
    return SESSION_ID_PATTERN.match(payload.session_id) is not None


def blocked_prompt_output(reason: str) -> dict:
    return {"decision": "block", "reason": reason}


def run_note_command(session_id: str, command: ShelfCommand) -> dict:
    if len(command.argument) == 0:
        return blocked_prompt_output(f"Nothing after {command.kind.value}:")
    note_state: ItemState = NOTE_STATE_BY_COMMAND_KIND[command.kind]
    items_after_note: List[ShelfItem] = update_shelf(
        session_id, lambda items: with_new_note(items, note_state, command.argument)
    )
    note: ShelfItem = items_after_note[-1]
    return blocked_prompt_output(f"Shelved as {note.state.value} {note.item_id}: {note.text}")


def run_done_command(session_id: str, command: ShelfCommand) -> dict:
    item_id: str = command.argument
    if find_item(load_shelf(session_id), item_id) is None:
        return blocked_prompt_output(f"No shelf item {item_id!r}.\n{shelf_listing(load_shelf(session_id))}")
    update_shelf(session_id, lambda items: with_item_done(items, item_id))
    return blocked_prompt_output(f"Done {item_id}.")


def run_shelf_command(session_id: str, command: ShelfCommand) -> dict:
    items: List[ShelfItem] = load_shelf(session_id)
    if len(command.argument) == 0:
        return blocked_prompt_output(shelf_listing(items))
    item_id: str = command.argument.split()[0]
    item: Optional[ShelfItem] = find_item(items, item_id)
    if item is None:
        return blocked_prompt_output(f"No shelf item {item_id!r}.\n{shelf_listing(items)}")
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                f"Shelf item {item.item_id} ({item.state.value}): {item.text}\n"
                f"When it is finished, tick it ([x]) in {shelf_path_of(session_id)}."
            ),
        }
    }


def run_shelf_command_by_kind(session_id: str, command: ShelfCommand) -> dict:
    if command.kind in NOTE_STATE_BY_COMMAND_KIND:
        return run_note_command(session_id, command)
    if command.kind == CommandKind.DONE:
        return run_done_command(session_id, command)
    return run_shelf_command(session_id, command)


def run_regular_prompt(session_id: str) -> dict:
    delete_old_session_files()
    meta: SessionMeta = load_meta(session_id)
    plan: PromptHookPlan = plan_prompt_hook(load_shelf(session_id), meta, shelf_path_of(session_id))
    save_meta(session_id, plan.updated_meta)
    output: dict = {}
    if plan.additional_context is not None:
        output["hookSpecificOutput"] = {"hookEventName": "UserPromptSubmit", "additionalContext": plan.additional_context}
    if plan.reminder is not None:
        output["systemMessage"] = plan.reminder
    return output


def run_prompt_hook(payload: HookPayload) -> None:
    shelf_command: Optional[ShelfCommand] = parse_shelf_command(payload.prompt)
    if shelf_command is not None:
        print(json.dumps(run_shelf_command_by_kind(payload.session_id, shelf_command)))
        return
    print(json.dumps(run_regular_prompt(payload.session_id)))


def is_agent_claude_launched(payload: HookPayload) -> bool:
    """Claude Code's own helpers at prompt time fire the subagent hooks too, with no agent type and no result."""
    return len(payload.agent_id) > 0 and len(payload.agent_type) > 0


def run_subagent_start(payload: HookPayload) -> None:
    if not is_agent_claude_launched(payload):
        return
    update_shelf(payload.session_id, lambda items: with_running_agent(items, payload.agent_id, payload.agent_type))


def run_subagent_stop(payload: HookPayload) -> None:
    if not is_agent_claude_launched(payload):
        return
    update_shelf(
        payload.session_id,
        lambda items: with_finished_agent(items, payload.agent_id, payload.agent_type, payload.agent_description),
    )


def run_after_compact(payload: HookPayload) -> None:
    meta: SessionMeta = load_meta(payload.session_id)
    save_meta(payload.session_id, replace(meta, last_told_to_claude_hash=""))


def print_statusline_segment(payload: HookPayload) -> None:
    print(statusline_text(load_shelf(payload.session_id)), end="")


MODE_HANDLERS: Dict[str, Callable[[HookPayload], None]] = {
    "statusline": print_statusline_segment,
    "prompt-hook": run_prompt_hook,
    "subagent-start": run_subagent_start,
    "subagent-stop": run_subagent_stop,
    "after-compact": run_after_compact,
}


def main(mode: str) -> None:
    handler: Optional[Callable[[HookPayload], None]] = MODE_HANDLERS.get(mode)
    if handler is None:
        return
    try:
        payload: HookPayload = read_hook_payload()
        if has_usable_session_id(payload):
            handler(payload)
        elif mode == "prompt-hook":
            print("{}")
    except Exception:
        traceback.print_exc(file=sys.stderr)
        if mode == "prompt-hook":
            print("{}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
