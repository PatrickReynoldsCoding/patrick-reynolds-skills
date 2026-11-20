import tempfile
import unittest
from pathlib import Path

import writing_style


class WritingStyleTest(unittest.TestCase):
    def setUp(self):
        self.temporary_folder = tempfile.TemporaryDirectory()
        self.writing_styles_folder: Path = Path(self.temporary_folder.name) / "writing-styles"
        self.writing_styles_folder.mkdir()
        (self.writing_styles_folder / "plain.md").write_text("# Plain\n\nAnswer first.\n", encoding="utf-8")
        (self.writing_styles_folder / "low-cognitive-load.md").write_text("# Low cognitive load\n\nOne question per reply.\n", encoding="utf-8")
        self.chosen_writing_style_file: Path = Path(self.temporary_folder.name) / ".claude" / "writing-style"

    def tearDown(self):
        self.temporary_folder.cleanup()


class WritingStyleNamesTest(WritingStyleTest):
    def test_every_markdown_file_in_the_folder_is_a_style_named_after_the_file(self):
        actual_names = writing_style.writing_style_names(self.writing_styles_folder)

        self.assertEqual(actual_names, ["low-cognitive-load", "plain"])


class ChosenWritingStyleNameTest(WritingStyleTest):
    def test_the_chosen_style_is_the_only_line_of_the_file(self):
        self.chosen_writing_style_file.parent.mkdir()
        self.chosen_writing_style_file.write_text("low-cognitive-load\n", encoding="utf-8")

        self.assertEqual(writing_style.chosen_writing_style_name(self.chosen_writing_style_file), "low-cognitive-load")

    def test_no_style_is_chosen_when_the_file_is_missing(self):
        self.assertIsNone(writing_style.chosen_writing_style_name(self.chosen_writing_style_file))

    def test_no_style_is_chosen_when_the_file_is_empty(self):
        self.chosen_writing_style_file.parent.mkdir()
        self.chosen_writing_style_file.write_text("\n", encoding="utf-8")

        self.assertIsNone(writing_style.chosen_writing_style_name(self.chosen_writing_style_file))


class SessionStartOutputTest(WritingStyleTest):
    def test_the_chosen_style_is_given_to_claude_in_full(self):
        style_file: Path = self.writing_styles_folder / "low-cognitive-load.md"
        expected_output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": f"# Default writing style for this session: low-cognitive-load ({style_file})\n\nFollow it in every reply.\n\n# Low cognitive load\n\nOne question per reply.\n",
            }
        }

        actual_output = writing_style.session_start_output("low-cognitive-load", self.writing_styles_folder)

        self.assertEqual(actual_output, expected_output)

    def test_nothing_is_loaded_when_no_style_is_chosen(self):
        self.assertIsNone(writing_style.session_start_output(None, self.writing_styles_folder))

    def test_an_unknown_style_shows_the_user_the_known_styles(self):
        expected_output = {"systemMessage": f"Writing style 'chatty' not found in {self.writing_styles_folder}. Known styles: low-cognitive-load, plain. Run /writing-style to choose one."}

        actual_output = writing_style.session_start_output("chatty", self.writing_styles_folder)

        self.assertEqual(actual_output, expected_output)


class StyleListingTest(unittest.TestCase):
    def test_the_chosen_style_is_marked_with_a_star(self):
        actual_listing = writing_style.style_listing(["low-cognitive-load", "plain"], "plain")

        self.assertEqual(actual_listing, "  low-cognitive-load\n* plain")


class ChooseWritingStyleTest(WritingStyleTest):
    def test_choosing_a_style_writes_its_name_to_the_file(self):
        writing_style.choose_writing_style("plain", self.writing_styles_folder, self.chosen_writing_style_file)

        self.assertEqual(self.chosen_writing_style_file.read_text(encoding="utf-8"), "plain\n")

    def test_choosing_an_unknown_style_fails_and_leaves_the_file_alone(self):
        with self.assertRaises(ValueError):
            writing_style.choose_writing_style("chatty", self.writing_styles_folder, self.chosen_writing_style_file)

        self.assertFalse(self.chosen_writing_style_file.exists())


if __name__ == "__main__":
    unittest.main()
