import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


class LoadConfigTests(unittest.TestCase):
    def test_returns_defaults_when_file_missing(self):
        with patch.object(config, "CONFIG_PATH", Path("this-file-does-not-exist.json")):
            result = config.load_config()

        self.assertEqual(result, config.DEFAULTS)

    def test_file_values_override_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"alert_lead_seconds": 120}), encoding="utf-8")

            with patch.object(config, "CONFIG_PATH", path):
                result = config.load_config()

        self.assertEqual(result["alert_lead_seconds"], 120)
        self.assertEqual(result["calendar_id"], config.DEFAULTS["calendar_id"])

    def test_does_not_mutate_the_shared_defaults_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"calendar_id": "custom"}), encoding="utf-8")

            with patch.object(config, "CONFIG_PATH", path):
                config.load_config()

        self.assertEqual(config.DEFAULTS["calendar_id"], "primary")


if __name__ == "__main__":
    unittest.main()
