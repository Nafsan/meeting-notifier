import pystray

from app_icon import make_icon_image


def create_icon(scheduler, on_open, on_quit):
    def open_dashboard(_icon=None, _item=None):
        on_open()

    def sync_now(_icon, _item):
        scheduler.request_sync()

    def quit_app(icon, _item):
        icon.stop()
        on_quit()

    # All menu text here is static - sync status lives in the dashboard
    # instead, which can refresh live without needing to rebuild the native
    # tray menu (a real OS-level operation, not a cheap one) on a timer.
    menu = pystray.Menu(
        pystray.MenuItem("Open dashboard", open_dashboard, default=True),
        pystray.MenuItem("Sync now", sync_now),
        pystray.MenuItem("Quit", quit_app),
    )

    return pystray.Icon("meeting_notifyer", make_icon_image(), "Meeting Notifier", menu)
