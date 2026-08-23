import logging
import queue
import threading
import time
import tkinter as tk
from logging.handlers import TimedRotatingFileHandler

import dpi_awareness  # noqa: F401 - import side effect must run before any Tk window is created
import alert_ui
import dashboard_ui
import tray
from config import LOG_PATH, load_config
from scheduler import Scheduler

# Rotate every 24h and keep only 1 backup, so nothing older than ~48h ever
# survives - regardless of how much (or little) gets logged in a day.
handler = TimedRotatingFileHandler(
    str(LOG_PATH), when="H", interval=24, backupCount=1, encoding="utf-8"
)
handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler])
log = logging.getLogger("main")

POLL_INTERVAL_MS = 500


def main():
    config = load_config()
    scheduler = Scheduler(config)
    scheduler.start()

    root = tk.Tk()
    root.withdraw()

    quit_requested = threading.Event()
    open_requested = threading.Event()

    def on_quit():
        scheduler.stop()
        quit_requested.set()

    def on_open():
        open_requested.set()

    def preview_alert():
        fake_alert = {
            "event_id": "preview",
            "title": "Design Review Sync",
            "start": time.time() + 60,
            "meet_link": "https://meet.google.com/preview",
        }
        alert_ui.show_alert(root, fake_alert, lambda *_a: None, config["snooze_seconds"])

    icon = tray.create_icon(scheduler, on_open, on_quit)
    icon.run_detached()

    def poll_queue():
        if quit_requested.is_set():
            root.destroy()
            return

        if open_requested.is_set():
            open_requested.clear()
            dashboard_ui.show_dashboard(root, scheduler, config, preview_alert)

        while True:
            try:
                alert_info = scheduler.alert_queue.get_nowait()
            except queue.Empty:
                break
            log.info("Showing alert for %s", alert_info["title"])
            alert_ui.show_alert(
                root, alert_info, scheduler.snooze, config["snooze_seconds"]
            )

        root.after(POLL_INTERVAL_MS, poll_queue)

    root.after(POLL_INTERVAL_MS, poll_queue)
    log.info("Meeting notifier started")
    root.mainloop()


if __name__ == "__main__":
    main()
