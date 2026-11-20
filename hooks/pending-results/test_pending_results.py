import os
import tempfile
import unittest
from typing import List
from unittest import mock

import pending_results
from pending_results import (
    CommandKind,
    ItemState,
    PromptHookPlan,
    SessionMeta,
    ShelfCommand,
    ShelfItem,
)

SESSION_ID: str = "0b1c2d3e-aaaa-bbbb-cccc-1234567890ab"
EMPTY_META: SessionMeta = SessionMeta(prompt_count=0, last_told_to_claude_hash="")
SHELF_PATH: str = "/notes/sessions/session.md"


def ready_item(item_id: str, text: str) -> ShelfItem:
    return ShelfItem(item_id=item_id, state=ItemState.READY, text=text, is_done=False)


class ShelfLineTest(unittest.TestCase):
    def test_a_line_written_for_an_item_is_read_back_as_the_same_item(self):
        expected_item = ShelfItem(item_id="3f2a9c1b", state=ItemState.READY, text="Explore: found 4 callers", is_done=False)

        actual_items = pending_results.parse_shelf([pending_results.format_shelf_line(expected_item)])

        self.assertEqual(actual_items, [expected_item])

    def test_a_ticked_line_is_read_as_done(self):
        expected_item = ShelfItem(item_id="2", state=ItemState.PARKED, text="fix the flaky test", is_done=True)

        actual_items = pending_results.parse_shelf(["- [x] [parked] 2: fix the flaky test"])

        self.assertEqual(actual_items, [expected_item])

    def test_lines_that_are_not_items_are_skipped(self):
        shelf_lines = ["# Session shelf", "", "- [ ] [unknown] 1: bad state", "- [ ] [parked] 2: good"]
        expected_items = [ShelfItem(item_id="2", state=ItemState.PARKED, text="good", is_done=False)]

        actual_items = pending_results.parse_shelf(shelf_lines)

        self.assertEqual(actual_items, expected_items)


class AgentItemsTest(unittest.TestCase):
    def test_a_started_agent_is_added_as_running_under_its_short_id(self):
        expected_items = [ShelfItem(item_id="a1b2c3d4", state=ItemState.RUNNING, text="Explore", is_done=False)]

        actual_items = pending_results.with_running_agent([], "a1b2c3d4e5f6", "Explore")

        self.assertEqual(actual_items, expected_items)

    def test_a_finished_agent_turns_its_running_item_into_a_ready_item_named_by_its_description(self):
        running_items = pending_results.with_running_agent([], "a1b2c3d4e5f6", "Explore")
        expected_items = [ready_item("a1b2c3d4", "Find callers of scoreLine")]

        actual_items = pending_results.with_finished_agent(
            running_items, "a1b2c3d4e5f6", "Explore", "Find callers of scoreLine"
        )

        self.assertEqual(actual_items, expected_items)

    def test_a_finished_agent_with_no_running_item_is_added_as_ready(self):
        expected_items = [ready_item("a1b2c3d4", "Explore")]

        actual_items = pending_results.with_finished_agent([], "a1b2c3d4e5f6", "Explore", "")

        self.assertEqual(actual_items, expected_items)

    def test_a_long_description_line_is_cut_to_the_maximum_text_length(self):
        long_line = "x" * 300

        shortened_line = pending_results.shorten_to_first_line(long_line)

        self.assertEqual(len(shortened_line), pending_results.MAX_ITEM_TEXT_LENGTH)
        self.assertTrue(shortened_line.endswith("…"))


class NotesTest(unittest.TestCase):
    def test_a_new_note_gets_the_next_number_even_when_earlier_notes_are_done(self):
        items = [
            ShelfItem(item_id="1", state=ItemState.PARKED, text="first", is_done=True),
            ShelfItem(item_id="a1b2c3d4", state=ItemState.READY, text="Explore", is_done=False),
        ]
        expected_note = ShelfItem(item_id="2", state=ItemState.PARKED, text="second", is_done=False)

        actual_items = pending_results.with_new_note(items, ItemState.PARKED, "second")

        self.assertEqual(actual_items[-1], expected_note)

    def test_marking_an_item_done_ticks_only_that_item(self):
        items = [
            ShelfItem(item_id="1", state=ItemState.PARKED, text="first", is_done=False),
            ShelfItem(item_id="2", state=ItemState.PARKED, text="second", is_done=False),
        ]
        expected_items = [items[0], ShelfItem(item_id="2", state=ItemState.PARKED, text="second", is_done=True)]

        actual_items = pending_results.with_item_done(items, "2")

        self.assertEqual(actual_items, expected_items)


class ShelfCommandTest(unittest.TestCase):
    def test_todo_prefix_is_read_whatever_its_case(self):
        expected_command = ShelfCommand(kind=CommandKind.TODO, argument="fix the flaky test")

        actual_command = pending_results.parse_shelf_command("  Todo: fix the flaky test ")

        self.assertEqual(actual_command, expected_command)

    def test_a_normal_prompt_is_not_a_shelf_command(self):
        self.assertIsNone(pending_results.parse_shelf_command("what is a todo list?"))


class StatuslineTest(unittest.TestCase):
    def test_an_empty_shelf_shows_nothing(self):
        self.assertEqual(pending_results.statusline_text([]), "")

    def test_each_state_with_waiting_items_shows_its_count_and_done_items_are_not_counted(self):
        items = [
            ShelfItem(item_id="a1", state=ItemState.RUNNING, text="Explore", is_done=False),
            ShelfItem(item_id="a2", state=ItemState.RUNNING, text="Plan", is_done=False),
            ready_item("a3", "Explore: done"),
            ShelfItem(item_id="1", state=ItemState.PARKED, text="old", is_done=True),
            ShelfItem(item_id="2", state=ItemState.BLOCKED, text="wait for CI", is_done=False),
        ]
        expected_text = " \033[36m⟳2 running\033[0m \033[1;33m✓1 ready\033[0m \033[31m⏸1 blocked\033[0m"

        actual_text = pending_results.statusline_text(items)

        self.assertEqual(actual_text, expected_text)


class PromptHookPlanTest(unittest.TestCase):
    def test_nothing_is_told_to_claude_when_no_result_is_ready(self):
        parked_item = ShelfItem(item_id="1", state=ItemState.PARKED, text="todo", is_done=False)
        expected_plan = PromptHookPlan(
            additional_context=None, reminder=None, updated_meta=SessionMeta(prompt_count=1, last_told_to_claude_hash="")
        )

        actual_plan = pending_results.plan_prompt_hook([parked_item], EMPTY_META, SHELF_PATH)

        self.assertEqual(actual_plan, expected_plan)

    def test_ready_results_are_told_to_claude_once_and_not_again_while_unchanged(self):
        items = [ready_item("a1", "Explore: found 4 callers")]

        first_plan = pending_results.plan_prompt_hook(items, EMPTY_META, SHELF_PATH)
        second_plan = pending_results.plan_prompt_hook(items, first_plan.updated_meta, SHELF_PATH)

        self.assertIn("a1: Explore: found 4 callers", first_plan.additional_context)
        self.assertIsNone(second_plan.additional_context)

    def test_a_new_ready_result_is_told_to_claude_again(self):
        first_plan = pending_results.plan_prompt_hook([ready_item("a1", "first")], EMPTY_META, SHELF_PATH)

        second_plan = pending_results.plan_prompt_hook(
            [ready_item("a1", "first"), ready_item("a2", "second")], first_plan.updated_meta, SHELF_PATH
        )

        self.assertIn("a2: second", second_plan.additional_context)

    def test_only_the_first_three_results_are_told_to_claude_and_the_rest_are_counted(self):
        items = [ready_item(f"a{number}", f"result {number}") for number in range(5)]

        plan = pending_results.plan_prompt_hook(items, EMPTY_META, SHELF_PATH)

        self.assertIn("a2: result 2", plan.additional_context)
        self.assertNotIn("a3: result 3", plan.additional_context)
        self.assertIn("(+2 more in the file)", plan.additional_context)

    def test_the_user_is_reminded_on_every_fifth_prompt(self):
        items = [ready_item("a1", "Explore: found 4 callers")]
        meta_before_fifth_prompt = SessionMeta(prompt_count=4, last_told_to_claude_hash="")

        plan = pending_results.plan_prompt_hook(items, meta_before_fifth_prompt, SHELF_PATH)

        self.assertEqual(plan.reminder, "Reminder: 1 subagent result waiting to discuss: Explore: found 4 callers")


class SessionFilesTest(unittest.TestCase):
    def setUp(self):
        self.shelf_directory = tempfile.TemporaryDirectory()
        directory_patch = mock.patch.object(pending_results, "SHELF_DIRECTORY", self.shelf_directory.name)
        directory_patch.start()
        self.addCleanup(directory_patch.stop)
        self.addCleanup(self.shelf_directory.cleanup)

    def test_a_todo_typed_by_the_user_is_shelved_and_the_prompt_is_blocked(self):
        command = ShelfCommand(kind=CommandKind.TODO, argument="fix the flaky test")
        expected_output = {"decision": "block", "reason": "Shelved as parked 1: fix the flaky test"}

        actual_output = pending_results.run_shelf_command_by_kind(SESSION_ID, command)

        self.assertEqual(actual_output, expected_output)
        expected_items: List[ShelfItem] = [
            ShelfItem(item_id="1", state=ItemState.PARKED, text="fix the flaky test", is_done=False)
        ]
        self.assertEqual(pending_results.load_shelf(SESSION_ID), expected_items)

    def test_two_sessions_do_not_see_each_others_items(self):
        pending_results.run_shelf_command_by_kind(SESSION_ID, ShelfCommand(kind=CommandKind.TODO, argument="mine"))

        self.assertEqual(pending_results.load_shelf("another-session"), [])

    def test_done_ticks_the_item_and_the_status_line_no_longer_counts_it(self):
        pending_results.run_shelf_command_by_kind(SESSION_ID, ShelfCommand(kind=CommandKind.TODO, argument="mine"))

        actual_output = pending_results.run_shelf_command_by_kind(SESSION_ID, ShelfCommand(kind=CommandKind.DONE, argument="1"))

        self.assertEqual(actual_output, {"decision": "block", "reason": "Done 1."})
        self.assertEqual(pending_results.statusline_text(pending_results.load_shelf(SESSION_ID)), "")

    def test_shelf_with_an_item_number_tells_claude_that_item_and_lets_the_prompt_through(self):
        pending_results.run_shelf_command_by_kind(SESSION_ID, ShelfCommand(kind=CommandKind.TODO, argument="fix the flaky test"))

        actual_output = pending_results.run_shelf_command_by_kind(
            SESSION_ID, ShelfCommand(kind=CommandKind.SHELF, argument="1 let's do this now")
        )

        self.assertNotIn("decision", actual_output)
        self.assertIn("Shelf item 1 (parked): fix the flaky test", actual_output["hookSpecificOutput"]["additionalContext"])

    def test_session_files_older_than_the_maximum_age_are_deleted(self):
        pending_results.run_shelf_command_by_kind(SESSION_ID, ShelfCommand(kind=CommandKind.TODO, argument="old"))
        shelf_path = pending_results.shelf_path_of(SESSION_ID)
        thirty_days_ago = os.path.getmtime(shelf_path) - 30 * pending_results.SECONDS_PER_DAY
        os.utime(shelf_path, (thirty_days_ago, thirty_days_ago))

        pending_results.delete_old_session_files()

        self.assertFalse(os.path.exists(shelf_path))



class IsAgentClaudeLaunchedTest(unittest.TestCase):
    def test_an_agent_with_a_type_is_one_claude_launched(self):
        payload = pending_results.HookPayload(session_id=SESSION_ID, prompt="", agent_id="a03890672cd0e5ac5", agent_type="general-purpose", agent_description="")

        self.assertTrue(pending_results.is_agent_claude_launched(payload))

    def test_an_agent_with_no_type_is_a_claude_code_helper_and_is_not_shelved(self):
        payload = pending_results.HookPayload(session_id=SESSION_ID, prompt="", agent_id="a92dd2a8c1f0b3e4d", agent_type="", agent_description="")

        self.assertFalse(pending_results.is_agent_claude_launched(payload))

if __name__ == "__main__":
    unittest.main()
