import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import autostart


class LaunchTargetTests(unittest.TestCase):
    def test_frozen_targets_the_exe_itself_with_no_args(self):
        with patch.object(autostart, "FROZEN", True), \
             patch.object(autostart.sys, "executable", r"C:\fake\MeetingNotifier.exe"):
            target, args = autostart._launch_target()

        self.assertEqual(target, r"C:\fake\MeetingNotifier.exe")
        self.assertEqual(args, "")

    def test_dev_mode_targets_pythonw_with_main_py_argument(self):
        with patch.object(autostart, "FROZEN", False):
            target, args = autostart._launch_target()

        self.assertIn("main.py", args)
        self.assertTrue(target)  # resolves to some interpreter path


class IsAutostartEnabledTests(unittest.TestCase):
    def test_reports_false_when_no_entry_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(autostart, "startup_folder", return_value=Path(tmp)):
                self.assertFalse(autostart.is_autostart_enabled())

    def test_reports_true_when_entry_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / autostart.VBS_NAME).write_text("", encoding="utf-8")
            with patch.object(autostart, "startup_folder", return_value=Path(tmp)):
                self.assertTrue(autostart.is_autostart_enabled())


if __name__ == "__main__":
    unittest.main()
