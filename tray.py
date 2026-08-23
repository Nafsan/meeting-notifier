import datetime as dt

import pystray

from app_icon import make_icon_image


def _status_text(scheduler):
    status = scheduler.status()
    if status["last_sync_error"]:
        return f"Sync error: {status['last_sync_error'][:40]}"
    if status["last_sync_at"] is None:
        return "Not synced yet"
    ts = dt.datetime.fromtimestamp(status["last_sync_at"]).strftime("%I:%M %p")
    return f"Synced {ts} | {status['upcoming_count']} upcoming"


def create_icon(scheduler, on_open, on_quit):
    def open_dashboard(_icon=None, _item=None):
        on_open()

    def sync_now(_icon, _item):
        scheduler.request_sync()

    def quit_app(icon, _item):
        icon.stop()
        on_quit()

    menu = pystray.Menu(
        pystray.MenuItem(lambda _item: _status_text(scheduler), None, enabled=False),
        pystray.MenuItem("Open dashboard", open_dashboard, default=True),
        pystray.MenuItem("Sync now", sync_now),
        pystray.MenuItem("Quit", quit_app),
    )

    return pystray.Icon("meeting_notifyer", make_icon_image(), "Meeting Notifier", menu)
