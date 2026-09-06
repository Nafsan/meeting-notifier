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

**If someone shared a `MeetingNotifier.zip` with you**: unzip it, run
`MeetingNotifier.exe`, click "Sign in with Google" in the welcome window.
That's the whole thing — see [SETUP.md](SETUP.md) for details.

**If you're setting this up from source** (to run it yourself or to build a
package for your team): see **[SETUP.md](SETUP.md)** for the full walkthrough
(Google Cloud OAuth setup, installing dependencies, first run, packaging).
Quick version, once you have `credentials.json` from Google Cloud Console in
this folder:

```
pip install -r requirements.txt
python main.py                    # first run shows the sign-in window
```

## How it's built

| Piece | File | Role |
|---|---|---|
| Paths | `config.py` | Loads `config.json`; also decides where user data lives - next to the script when run from source, `%LOCALAPPDATA%\MeetingNotifier\` when packaged |
| Calendar sync + OAuth | `calendar_sync.py` | Fetches upcoming events with a Meet link via the Google Calendar API (read-only scope); bootstraps the bundled `credentials.json` into place on first run when packaged |
| Scheduler | `scheduler.py` | Background thread: syncs on an interval, tracks per-event alert times, decides when an alert is due |
| Welcome/sign-in | `welcome_ui.py` | First-run only: "Sign in with Google" + "start at login" dialog, skipped once `token.json` exists |
| Full-screen alert | `alert_ui.py` | Tkinter popup — countdown, sound, Join/Snooze/Dismiss |
| Dashboard | `dashboard_ui.py` | Tkinter window — upcoming meetings, sync status, "Preview alert" |
| Tray icon | `tray.py` | System tray icon + menu (pystray) |
| Entry point | `main.py` | Wires everything together, owns the Tk main loop and logging setup |
| Autostart/shortcut | `autostart.py`, `app_icon.py`, `install_autostart.py` | Windows Startup entry + Start Menu shortcut with icon; works both from source and packaged |

**Stack:** Python 3.12, Tkinter (GUI), [pystray](https://github.com/moses-palmer/pystray)
(tray icon), Pillow (icon generation), `google-api-python-client` +
`google-auth-oauthlib` (Calendar access), `winsound` (alert sound). No web
server, no database, no external services besides the Google Calendar API.
Packaged into a standalone Windows app with
[PyInstaller](https://pyinstaller.org/) — see SETUP.md's "Sharing with your
team" section.

## Running tests

Unit tests cover the non-GUI logic (scheduling/alert timing, calendar event
filtering, config loading, etc.) using only the standard library's
`unittest` — no extra dependencies to install:

```
python -m unittest discover -s tests -v
```

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
- Nothing is sent anywhere except calls to Google's Calendar API directly
  from your machine. There's no backend server and no telemetry.
- This is a personal/local tool, not hardened for multi-user or shared-machine
  use — anyone with access to your Windows user account can read
  `token.json` and use it to read your calendar.
- Logs (`notifier.log`) can include meeting titles and times; it auto-rotates
  every 24h (keeps 1 backup) so at most ~48h of logs ever exist on disk.

**`credentials.json` vs `token.json` — very different sensitivity:**
- `token.json` (your personal access/refresh token, created after *your own*
  sign-in) is what actually grants read access to *your* calendar. Never
  share it, never commit it — it's in `.gitignore` and, when packaged, lives
  in `%LOCALAPPDATA%\MeetingNotifier\`, not inside the shareable zip.
- `credentials.json` (the OAuth *client* — identifies the app to Google, not
  a person) is intentionally bundled into the shared team package. For a
  Google "Desktop app" OAuth client, this isn't treated as confidential
  ([RFC 8252](https://datatracker.ietf.org/doc/html/rfc8252)) — it can't be
  kept secret in a distributed binary anyway, so Google doesn't rely on it
  for security. What actually protects calendar data is (a) the OAuth
  consent screen gate at sign-in time, and (b) each person's own
  `token.json`, generated only after *they* complete *their own* sign-in.
  It's still not something to publish somewhere public (e.g. a public
  GitHub repo) — share the built zip directly with your team instead, which
  is why `dist/`/`build/`/`*.spec` are gitignored.

## Known limitations

- Windows-only (uses `winsound` and Windows Startup/Start Menu folders).
- Only checks a single calendar (`primary` by default — configurable in
  `config.json`).
- Only alerts for events with a Google Meet link (`hangoutLink`); plain
  calendar events without Meet are ignored by design.
- No mobile/cross-device notification — desktop-only, as scoped.
