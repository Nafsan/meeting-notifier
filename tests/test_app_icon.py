import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

import app_icon


class MakeIconImageTests(unittest.TestCase):
    def test_returns_requested_size_and_mode(self):
        img = app_icon.make_icon_image(48)
        self.assertEqual(img.size, (48, 48))
        self.assertEqual(img.mode, "RGBA")

    def test_default_size_is_64(self):
        img = app_icon.make_icon_image()
        self.assertEqual(img.size, (64, 64))


class SaveIcoTests(unittest.TestCase):
    def test_creates_a_valid_multi_size_ico_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            ico_path = Path(tmp) / "icon.ico"

            app_icon.save_ico(ico_path)

            self.assertTrue(ico_path.exists())
            with Image.open(ico_path) as img:
                self.assertEqual(img.format, "ICO")


if __name__ == "__main__":
    unittest.main()
