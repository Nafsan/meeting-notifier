import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard_ui import _format_countdown


class FormatCountdownTests(unittest.TestCase):
    def test_negative_or_zero_is_in_progress(self):
        self.assertEqual(_format_countdown(-5), "in progress")
        self.assertEqual(_format_countdown(0), "in progress")

    def test_under_a_minute_says_starting_now(self):
        self.assertEqual(_format_countdown(1), "starting now")
        self.assertEqual(_format_countdown(59), "starting now")

    def test_minutes_only_under_an_hour(self):
        self.assertEqual(_format_countdown(90), "in 1m")
        self.assertEqual(_format_countdown(59 * 60), "in 59m")

    def test_hours_and_minutes_at_and_beyond_an_hour(self):
        self.assertEqual(_format_countdown(60 * 60), "in 1h 0m")
        self.assertEqual(_format_countdown(90 * 60), "in 1h 30m")


if __name__ == "__main__":
    unittest.main()
