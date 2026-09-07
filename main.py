import os
import sys
import traceback


def _show_fatal_error(exc_type, exc, tb):
    # A --windowed build has no console, so an uncaught exception here would
    # otherwise fail completely silently - nothing on screen, nothing in
    # notifier.log if the failure happened before logging was even set up
    # (e.g. a broken/partial zip extraction missing a bundled dependency).
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        crash_dir = os.path.join(os.environ.get("LOCALAPPDATA", "."), "MeetingNotifier")
        os.makedirs(crash_dir, exist_ok=True)
        with open(os.path.join(crash_dir, "crash.log"), "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Meeting Notifier failed to start",
            "Something went wrong on startup:\n\n"
            + "".join(traceback.format_exception_only(exc_type, exc))
            + "\nDetails were saved to:\n"
            + os.path.join(os.environ.get("LOCALAPPDATA", "."), "MeetingNotifier", "crash.log"),
        )
        root.destroy()
    except Exception:
        pass


sys.excepthook = _show_fatal_error

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
import welcome_ui
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

    root = tk.Tk()
    root.withdraw()

    if not welcome_ui.run_first_time_setup(root):
        log.info("Setup cancelled on first run - exiting")
        root.destroy()
        return

    scheduler = Scheduler(config)
    scheduler.start()

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
