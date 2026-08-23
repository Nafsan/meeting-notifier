import json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
CREDENTIALS_PATH = APP_DIR / "credentials.json"
TOKEN_PATH = APP_DIR / "token.json"
LOG_PATH = APP_DIR / "notifier.log"

DEFAULTS = {
    "calendar_id": "primary",
    "alert_lead_seconds": 60,
    "sync_interval_seconds": 300,
    "snooze_seconds": 60,
    "lookahead_hours": 12,
}


def load_config():
    config = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    return config
