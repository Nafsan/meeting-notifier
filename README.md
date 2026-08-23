# Meeting Notifier

A small Windows tray app that stays synced with your Google Calendar and
fires a hard-to-miss, full-screen alert **1 minute before** any meeting with
a Google Meet link — built because Google Calendar/Meet's own browser and
Chat notifications are easy to miss (buried behind windows, dismissed too
easily, or silenced by Focus Assist).

## What it does

- Polls your Google Calendar every few minutes for upcoming events that have
  a Google Meet link.
- Schedules a precise, self-correcting alarm for `meeting_start - 1 minute`
  per event (self-correcting so it still fires correctly even if the PC was
  asleep).
- At alert time, shows a full-screen, topmost popup with a looping sound —
  meeting title, live countdown, and **Join / Snooze / Dismiss** buttons.
- Lives in the system tray with a dashboard showing upcoming meetings,
  live countdowns, and sync health at a glance.

## Setup

See **[SETUP.md](SETUP.md)** for the full walkthrough (Google Cloud OAuth
setup, installing dependencies, first run, and enabling autostart / a
searchable Start Menu entry).

Quick version, once you have `credentials.json` from Google Cloud Console
(see SETUP.md step 1) in this folder:

```
pip install -r requirements.txt
python main.py                    # first run completes Google sign-in
python install_autostart.py       # runs at login + adds a Start Menu shortcut
```

## How it's built

| Piece | File | Role |
|---|---|---|
| Calendar sync + OAuth | `calendar_sync.py` | Fetches upcoming events with a Meet link via the Google Calendar API (read-only scope) |
| Scheduler | `scheduler.py` | Background thread: syncs on an interval, tracks per-event alert times, decides when an alert is due |
| Full-screen alert | `alert_ui.py` | Tkinter popup — countdown, sound, Join/Snooze/Dismiss |
| Dashboard | `dashboard_ui.py` | Tkinter window — upcoming meetings, sync status, "Preview alert" |
| Tray icon | `tray.py` | System tray icon + menu (pystray) |
| Entry point | `main.py` | Wires everything together, owns the Tk main loop and logging setup |
| Autostart/shortcut | `install_autostart.py`, `app_icon.py` | One-time setup: Windows Startup entry + Start Menu shortcut with icon |

**Stack:** Python 3.12, Tkinter (GUI), [pystray](https://github.com/moses-palmer/pystray)
(tray icon), Pillow (icon generation), `google-api-python-client` +
`google-auth-oauthlib` (Calendar access), `winsound` (alert sound). No web
server, no database, no external services besides the Google Calendar API.

## Performance

Designed to be effectively idle:
- The scheduler never busy-waits — it sleeps until the next thing that could
  matter (next alert or next sync), tightening to ~1s only in the final
  seconds before an alert. Otherwise it wakes at most every ~30s.
- One calendar API call every 5 minutes (configurable) — negligible.
- The tray icon and dashboard are event-driven (native OS message loops),
  not polling loops.
- Expect ~0% CPU at idle and ~30-50MB memory, typical for a small
  Python/Tkinter process.

## Security & privacy notes

- Uses the **read-only** Calendar API scope (`calendar.readonly`) — this app
  cannot modify, delete, or create calendar events.
- `credentials.json` (your OAuth client) and `token.json` (your access/refresh
  token) are stored locally in this folder and are in `.gitignore` — never
  commit or share them.
- Nothing is sent anywhere except calls to Google's Calendar API directly
  from your machine. There's no backend server and no telemetry.
- This is a personal/local tool, not hardened for multi-user or shared-machine
  use — anyone with access to your Windows user account can read
  `token.json` and use it to read your calendar.
- Logs (`notifier.log`) can include meeting titles and times; it auto-rotates
  every 24h (keeps 1 backup) so at most ~48h of logs ever exist on disk.

## Known limitations

- Windows-only (uses `winsound` and Windows Startup/Start Menu folders).
- Only checks a single calendar (`primary` by default — configurable in
  `config.json`).
- Only alerts for events with a Google Meet link (`hangoutLink`); plain
  calendar events without Meet are ignored by design.
- No mobile/cross-device notification — desktop-only, as scoped.
