import datetime as dt
import time as time_module
import tkinter as tk
import webbrowser
import winsound

import dpi_awareness  # noqa: F401 - import side effect must run before any Tk window is created

SCRIM = "#202124"          # Google "surface dark" grey
CARD_BG = "#ffffff"
BADGE_BG = "#e6f4ea"       # soft green tint behind the icon
TEXT_PRIMARY = "#202124"
TEXT_SECONDARY = "#5f6368"
BORDER = "#e8eaed"
MEET_GREEN = "#1e8e3e"
MEET_GREEN_HOVER = "#188038"
OUTLINE_BTN = "#dadce0"
GHOST_HOVER = "#f1f3f4"

CARD_W = 480
TOP_PAD = 40
BOTTOM_PAD = 32


def _stop_sound():
    winsound.PlaySound(None, winsound.SND_PURGE)


def _start_sound():
    winsound.PlaySound(
        "SystemAsterisk",
        winsound.SND_ALIAS | winsound.SND_ASYNC | winsound.SND_LOOP,
    )


def _round_rect_points(x1, y1, x2, y2, r):
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


def _draw_camera_icon(canvas, cx, cy):
    """A simple flat video-camera glyph, drawn (not emoji) for reliable rendering."""
    canvas.create_polygon(
        _round_rect_points(cx - 15, cy - 10, cx + 5, cy + 10, 4),
        fill=MEET_GREEN, outline="", smooth=True,
    )
    canvas.create_polygon(
        cx + 5, cy - 8, cx + 5, cy + 8, cx + 17, cy + 13, cx + 17, cy - 13,
        fill=MEET_GREEN, outline="", smooth=False,
    )


def _make_pill(canvas, cx, cy, w, h, label, fill, text_color, command,
               outline=None, hover_fill=None, font_weight="bold"):
    x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    rect = canvas.create_polygon(
        _round_rect_points(x1, y1, x2, y2, h / 2), fill=fill,
        outline=outline or fill, width=1.4, smooth=True,
    )
    text = canvas.create_text(
        cx, cy, text=label, fill=text_color, font=("Segoe UI", 12, font_weight),
    )

    def on_click(_e):
        command()

    def on_enter(_e):
        canvas.itemconfig(rect, fill=hover_fill or fill)
        canvas.config(cursor="hand2")

    def on_leave(_e):
        canvas.itemconfig(rect, fill=fill)
        canvas.config(cursor="")

    for item in (rect, text):
        canvas.tag_bind(item, "<Button-1>", on_click)
        canvas.tag_bind(item, "<Enter>", on_enter)
        canvas.tag_bind(item, "<Leave>", on_leave)

    return rect, text


def show_alert(root, alert_info, on_snooze, snooze_seconds):
    win = tk.Toplevel(root)
    win.attributes("-fullscreen", True)
    win.attributes("-topmost", True)
    win.configure(bg=SCRIM)
    win.focus_force()

    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()

    canvas = tk.Canvas(win, width=screen_w, height=screen_h, bg=SCRIM, highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    cx = screen_w // 2
    cursor_y = screen_h // 2 - 220  # provisional top; the whole card is re-centered at the end

    # Icon badge
    badge_r = 32
    badge_cy = cursor_y + TOP_PAD + badge_r
    canvas.create_oval(
        cx - badge_r, badge_cy - badge_r, cx + badge_r, badge_cy + badge_r,
        fill=BADGE_BG, outline="",
    )
    _draw_camera_icon(canvas, cx, badge_cy)
    cursor_y = badge_cy + badge_r + 20

    # Title (may wrap to 2 lines for long meeting names)
    title_item = canvas.create_text(
        cx, cursor_y, text=alert_info["title"], font=("Segoe UI", 19, "bold"),
        fill=TEXT_PRIMARY, width=CARD_W - 80, justify="center", anchor="n",
    )
    cursor_y = canvas.bbox(title_item)[3] + 12

    # Date/time line
    start_local = dt.datetime.fromtimestamp(alert_info["start"]).strftime("%A, %I:%M %p").lstrip("0")
    date_item = canvas.create_text(
        cx, cursor_y, text=f"{start_local}  ·  Google Meet",
        font=("Segoe UI", 11), fill=TEXT_SECONDARY, anchor="n",
    )
    cursor_y = canvas.bbox(date_item)[3] + 26

    # Live countdown (seeded with placeholder text so its height is measurable)
    countdown_item = canvas.create_text(
        cx, cursor_y, text="00:00", font=("Segoe UI", 34, "bold"), fill=MEET_GREEN, anchor="n",
    )
    cursor_y = canvas.bbox(countdown_item)[3] + 4

    countdown_caption = canvas.create_text(
        cx, cursor_y, text="until the meeting starts",
        font=("Segoe UI", 10), fill=TEXT_SECONDARY, anchor="n",
    )
    cursor_y = canvas.bbox(countdown_caption)[3] + 36

    def close(stop_sound=True):
        if stop_sound:
            _stop_sound()
        if win.winfo_exists():
            win.destroy()

    def on_join():
        webbrowser.open(alert_info["meet_link"])
        close()

    def on_snooze_click():
        close()
        on_snooze(alert_info["event_id"], snooze_seconds)

    def on_dismiss():
        close()

    primary_btn_y = cursor_y + 23
    secondary_btn_y = primary_btn_y + 46
    _make_pill(
        canvas, cx, primary_btn_y, 190, 46, "Join meeting", MEET_GREEN, "white",
        on_join, hover_fill=MEET_GREEN_HOVER,
    )
    _make_pill(
        canvas, cx - 65, secondary_btn_y, 110, 34, "Snooze",
        CARD_BG, TEXT_PRIMARY, on_snooze_click,
        outline=OUTLINE_BTN, hover_fill=GHOST_HOVER, font_weight="normal",
    )
    _make_pill(
        canvas, cx + 65, secondary_btn_y, 110, 34, "Dismiss", CARD_BG, TEXT_SECONDARY,
        on_dismiss, outline=CARD_BG, hover_fill=GHOST_HOVER, font_weight="normal",
    )

    card_top = screen_h // 2 - 220
    card_bottom = secondary_btn_y + 17 + BOTTOM_PAD
    x1, x2 = cx - CARD_W // 2, cx + CARD_W // 2

    bg = canvas.create_polygon(
        _round_rect_points(x1, card_top, x2, card_bottom, 22),
        fill=CARD_BG, outline=BORDER, width=1, smooth=True,
    )
    canvas.tag_lower(bg)

    # Recenter the whole card vertically now that its true height is known
    true_center = (card_top + card_bottom) / 2
    shift = (screen_h // 2) - true_center
    canvas.move("all", 0, shift)

    def tick():
        if not win.winfo_exists():
            return
        remaining = int(alert_info["start"] - time_module.time())
        if remaining > 0:
            m, s = divmod(remaining, 60)
            canvas.itemconfig(countdown_item, text=f"{m:02d}:{s:02d}")
        else:
            canvas.itemconfig(countdown_item, text="Now", fill=TEXT_PRIMARY)
            canvas.itemconfig(countdown_caption, text="Your meeting is starting")
        win.after(1000, tick)

    tick()

    win.bind("<Escape>", lambda _e: on_dismiss())
    win.protocol("WM_DELETE_WINDOW", on_dismiss)

    _start_sound()
