import datetime as dt
import time
import tkinter as tk
import webbrowser

BG = "#f8f9fa"
CARD_BG = "#ffffff"
BORDER = "#e0e0e0"
TEXT_PRIMARY = "#202124"
TEXT_SECONDARY = "#5f6368"
BLUE = "#1a73e8"
GREEN = "#1e8e3e"
AMBER = "#f9ab00"
RED = "#d93025"
CHIP_BG = "#e8f0fe"

REFRESH_MS = 1000
STALE_MULTIPLIER = 2  # sync considered "stale" if overdue by more than 2x its interval


def _format_countdown(seconds):
    if seconds <= 0:
        return "in progress"
    total_minutes = int(seconds // 60)
    if total_minutes < 1:
        return "starting now"
    if total_minutes < 60:
        return f"in {total_minutes}m"
    hours, minutes = divmod(total_minutes, 60)
    return f"in {hours}h {minutes}m"


def _round_rect_points(x1, y1, x2, y2, r):
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


class Dashboard:
    _instance = None

    @classmethod
    def show(cls, root, scheduler, config, preview_alert_fn):
        if cls._instance is not None and cls._instance.is_alive():
            cls._instance.win.deiconify()
            cls._instance.win.lift()
            cls._instance.win.focus_force()
            return
        cls._instance = Dashboard(root, scheduler, config, preview_alert_fn)

    def __init__(self, root, scheduler, config, preview_alert_fn):
        self.scheduler = scheduler
        self.config = config
        self.preview_alert_fn = preview_alert_fn

        self.win = tk.Toplevel(root)
        self.win.title("Meeting Notifier")
        self.win.configure(bg=BG)
        self.win.geometry("520x640")
        self.win.minsize(440, 480)

        self._rendered_ids = None
        self._row_widgets = {}

        self._build_header()
        self._build_list_area()
        self._build_footer()

        self.win.protocol("WM_DELETE_WINDOW", self._close)
        self._refresh()

    def is_alive(self):
        try:
            return bool(self.win.winfo_exists())
        except tk.TclError:
            return False

    def _close(self):
        self._alive = False
        self.win.destroy()

    # ---- layout ----

    def _build_header(self):
        header = tk.Frame(self.win, bg=BG)
        header.pack(fill="x", padx=20, pady=(20, 8))

        tk.Label(
            header, text="\U0001F4C5 Meeting Notifier", font=("Segoe UI", 16, "bold"),
            bg=BG, fg=TEXT_PRIMARY,
        ).pack(anchor="w")

        status_row = tk.Frame(header, bg=BG)
        status_row.pack(fill="x", pady=(8, 0))

        self.status_dot = tk.Canvas(status_row, width=10, height=10, bg=BG, highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0, 6), anchor="n")
        self.status_dot_id = self.status_dot.create_oval(0, 0, 10, 10, fill=GREEN, outline="")

        # Status text and the sync button live in separate rows so a long
        # status message (e.g. a sync error) can never overlap the button -
        # it just wraps onto a second line instead.
        self.status_label = tk.Label(
            status_row, text="Not synced yet", font=("Segoe UI", 10), bg=BG, fg=TEXT_SECONDARY,
            justify="left", anchor="w", wraplength=440,
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        sync_row = tk.Frame(header, bg=BG)
        sync_row.pack(fill="x", pady=(6, 0))

        sync_btn = tk.Button(
            sync_row, text="Sync now", font=("Segoe UI", 9), bg=CARD_BG, fg=BLUE,
            relief="solid", bd=1, padx=10, pady=2, cursor="hand2",
            command=self.scheduler.request_sync,
        )
        sync_btn.pack(side="right")

    def _build_list_area(self):
        container = tk.Frame(self.win, bg=BG)
        container.pack(fill="both", expand=True, padx=20, pady=8)

        self.canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.list_frame = tk.Frame(self.canvas, bg=BG)

        self.list_frame.bind(
            "<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind(
            "<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_footer(self):
        footer = tk.Frame(self.win, bg=BG)
        footer.pack(fill="x", padx=20, pady=(4, 16))

        tk.Button(
            footer, text="Preview alert", font=("Segoe UI", 9), bg=CARD_BG, fg=TEXT_SECONDARY,
            relief="solid", bd=1, padx=10, pady=4, cursor="hand2",
            command=self.preview_alert_fn,
        ).pack(side="left")

        self.next_sync_label = tk.Label(
            footer, text="", font=("Segoe UI", 9), bg=BG, fg=TEXT_SECONDARY,
        )
        self.next_sync_label.pack(side="right")

    # ---- data refresh ----

    def _render_rows(self, events):
        now = time.time()
        new_ids = tuple(ev["event_id"] for ev in events)

        # Same set of meetings as last tick - update the live bits (countdown,
        # time, title) in place instead of destroying/recreating every row,
        # which is what was causing the visible flicker every refresh.
        if new_ids == self._rendered_ids:
            for ev in events:
                widgets = self._row_widgets.get(ev["event_id"])
                if not widgets:
                    continue
                widgets["title"].configure(text=ev["title"])
                start_local = dt.datetime.fromtimestamp(ev["start"]).strftime("%I:%M %p").lstrip("0")
                widgets["time"].configure(text=start_local)
                remaining = ev["start"] - now
                widgets["chip"].configure(text=" " + _format_countdown(remaining) + " ")
            return

        for child in self.list_frame.winfo_children():
            child.destroy()
        self._row_widgets = {}
        self._rendered_ids = new_ids

        if not events:
            tk.Label(
                self.list_frame,
                text="No upcoming meetings with a Google Meet link\nin the next "
                f"{self.config['lookahead_hours']}h.",
                font=("Segoe UI", 10), bg=BG, fg=TEXT_SECONDARY, justify="center",
            ).pack(pady=40)
            return

        for ev in events:
            self._render_row(ev, now)

    def _render_row(self, ev, now):
        row = tk.Frame(self.list_frame, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        row.pack(fill="x", pady=5)

        accent = tk.Frame(row, bg=GREEN, width=4)
        accent.pack(side="left", fill="y")

        body = tk.Frame(row, bg=CARD_BG)
        body.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        title_label = tk.Label(
            body, text=ev["title"], font=("Segoe UI", 11, "bold"), bg=CARD_BG, fg=TEXT_PRIMARY,
            anchor="w", wraplength=340, justify="left",
        )
        title_label.pack(anchor="w")

        start_local = dt.datetime.fromtimestamp(ev["start"]).strftime("%I:%M %p").lstrip("0")
        meta_row = tk.Frame(body, bg=CARD_BG)
        meta_row.pack(anchor="w", pady=(4, 0))

        time_label = tk.Label(
            meta_row, text=start_local, font=("Segoe UI", 9), bg=CARD_BG, fg=TEXT_SECONDARY,
        )
        time_label.pack(side="left")

        remaining = ev["start"] - now
        chip = tk.Label(
            meta_row, text=" " + _format_countdown(remaining) + " ", font=("Segoe UI", 9, "bold"),
            bg=CHIP_BG, fg=BLUE,
        )
        chip.pack(side="left", padx=(8, 0))

        actions = tk.Frame(row, bg=CARD_BG)
        actions.pack(side="right", padx=12)
        tk.Button(
            actions, text="Join", font=("Segoe UI", 9, "bold"), bg=GREEN, fg="white",
            relief="flat", padx=10, pady=3, cursor="hand2",
            command=lambda link=ev["meet_link"]: webbrowser.open(link),
        ).pack()

        self._row_widgets[ev["event_id"]] = {"title": title_label, "time": time_label, "chip": chip}

    def _refresh(self):
        if not self.is_alive():
            return

        status = self.scheduler.status()
        self._update_status(status)

        events = self.scheduler.upcoming_events()
        self._render_rows(events)

        if status["next_attempt_at"]:
            remaining = max(0, int(status["next_attempt_at"] - time.time()))
            self.next_sync_label.configure(text=f"Next sync in {remaining}s")
        else:
            self.next_sync_label.configure(text="")

        self.win.after(REFRESH_MS, self._refresh)

    def _update_status(self, status):
        if status["last_sync_error"]:
            self.status_dot.itemconfig(self.status_dot_id, fill=RED)
            self.status_label.configure(text=f"Sync issue: {status['last_sync_error'][:48]}")
            return

        if status["last_sync_at"] is None:
            self.status_dot.itemconfig(self.status_dot_id, fill=AMBER)
            self.status_label.configure(text="Not synced yet")
            return

        age = time.time() - status["last_sync_at"]
        interval = self.config["sync_interval_seconds"]
        ts = dt.datetime.fromtimestamp(status["last_sync_at"]).strftime("%I:%M %p").lstrip("0")

        if age > interval * STALE_MULTIPLIER:
            self.status_dot.itemconfig(self.status_dot_id, fill=RED)
            self.status_label.configure(text=f"Sync stale - last synced {ts}")
        else:
            self.status_dot.itemconfig(self.status_dot_id, fill=GREEN)
            self.status_label.configure(
                text=f"Synced {ts} - {status['upcoming_count']} upcoming"
            )


def show_dashboard(root, scheduler, config, preview_alert_fn):
    Dashboard.show(root, scheduler, config, preview_alert_fn)
