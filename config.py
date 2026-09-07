import json
import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    # PyInstaller --onedir: sys._MEIPASS is the folder containing the .exe
    # and any bundled data files (a permanent location for --onedir, unlike
    # the temp extraction --onefile builds use).
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    # User-writable files go in the standard per-user app-data location, not
    # next to the exe - the exe may be run straight out of a zip-extracted
    # Downloads folder that could get deleted or re-extracted over.
    USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MeetingNotifier"
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
    USER_DATA_DIR = BUNDLE_DIR

USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

APP_DIR = USER_DATA_DIR
CONFIG_PATH = USER_DATA_DIR / "config.json"
CREDENTIALS_PATH = USER_DATA_DIR / "credentials.json"
TOKEN_PATH = USER_DATA_DIR / "token.json"
LOG_PATH = USER_DATA_DIR / "notifier.log"

# Only relevant when frozen: a read-only template shipped inside the package,
# copied to CREDENTIALS_PATH on first run if that doesn't exist yet.
BUNDLED_CREDENTIALS_PATH = BUNDLE_DIR / "credentials.json"

DEFAULTS = {
    "calendar_id": "primary",
    "alert_lead_seconds": 60,
    "sync_interval_seconds": 300,
    "snooze_seconds": 300,
    "lookahead_hours": 12,
}


def load_config():
    config = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    return config
