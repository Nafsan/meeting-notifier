import queue
import threading
import tkinter as tk

import autostart
import calendar_sync
import dpi_awareness  # noqa: F401 - import side effect must run before any Tk window is created
from config import TOKEN_PATH

BG = "#f8f9fa"
CARD_BG = "#ffffff"
TEXT_PRIMARY = "#202124"
TEXT_SECONDARY = "#5f6368"
MEET_GREEN = "#1e8e3e"
MEET_GREEN_HOVER = "#188038"
BADGE_BG = "#e6f4ea"


def run_first_time_setup(root):
    """Shows a one-time welcome/sign-in dialog if there's no token yet.

    Returns True once the user is signed in (either already was, or just
    completed sign-in here), or False if they closed the window without
    signing in.
    """
    if TOKEN_PATH.exists():
        return True

    result = {"success": False}
    outcome_queue = queue.Queue()

    win = tk.Toplevel(root)
    win.title("Welcome to Meeting Notifier")
    win.configure(bg=BG)
    win.geometry("460x420")
    win.resizable(False, False)

    badge = tk.Canvas(win, width=64, height=64, bg=BG, highlightthickness=0)
    badge.pack(pady=(28, 12))
    badge.create_oval(0, 0, 64, 64, fill=BADGE_BG, outline="")
    badge.create_text(32, 32, text="\U0001F4C5", font=("Segoe UI Emoji", 26))

    tk.Label(
        win, text="Meeting Notifier", font=("Segoe UI", 16, "bold"), bg=BG, fg=TEXT_PRIMARY,
    ).pack()
    tk.Label(
        win,
        text="Watches your Google Calendar and gives you a hard-to-miss\n"
        "alert before every meeting with a Google Meet link.",
        font=("Segoe UI", 10), bg=BG, fg=TEXT_SECONDARY, justify="center",
    ).pack(pady=(6, 20))

    tk.Label(
        win,
        text="When you sign in, Google will show a “this app hasn't been\n"
        "verified” notice — that's expected. Click Advanced, then\n"
        "“Go to Meeting Notifier (unsafe)” to continue. It's only asking\n"
        "for read-only access to your own calendar.",
        font=("Segoe UI", 9), bg=BG, fg=TEXT_SECONDARY, justify="center",
    ).pack(padx=30, pady=(0, 16))

    status_label = tk.Label(win, text="", font=("Segoe UI", 9), bg=BG, fg=TEXT_SECONDARY)
    status_label.pack()

    autostart_var = tk.BooleanVar(value=True)
    tk.Checkbutton(
        win, text="Start automatically when I log in", variable=autostart_var,
        bg=BG, fg=TEXT_PRIMARY, activebackground=BG, font=("Segoe UI", 9),
    ).pack(pady=(4, 16))

    sign_in_btn = tk.Button(
        win, text="Sign in with Google", font=("Segoe UI", 12, "bold"),
        bg=MEET_GREEN, fg="white", activebackground=MEET_GREEN_HOVER, activeforeground="white",
        relief="flat", padx=24, pady=10, cursor="hand2",
    )
    sign_in_btn.pack()

    def do_sign_in():
        try:
            calendar_sync.get_credentials()
            outcome_queue.put(("success", None))
        except Exception as exc:
            outcome_queue.put(("error", str(exc)))

    def on_sign_in_click():
        sign_in_btn.config(state="disabled", text="Waiting for Google sign-in…")
        status_label.config(text="A browser window should open shortly.")
        threading.Thread(target=do_sign_in, daemon=True).start()

    def poll_outcome():
        try:
            kind, detail = outcome_queue.get_nowait()
        except queue.Empty:
            if win.winfo_exists():
                win.after(200, poll_outcome)
            return

        if kind == "success":
            if autostart_var.get():
                try:
                    autostart.install()
                except Exception:
                    pass  # non-fatal - the app still works without autostart
            result["success"] = True
            win.destroy()
        else:
            sign_in_btn.config(state="normal", text="Sign in with Google")
            status_label.config(text=f"Sign-in failed: {detail[:60]}", fg="#d93025")

    sign_in_btn.config(command=on_sign_in_click)
    win.after(200, poll_outcome)

    win.protocol("WM_DELETE_WINDOW", win.destroy)
    win.transient(root)
    win.grab_set()
    root.wait_window(win)

    return result["success"]
