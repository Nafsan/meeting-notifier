# Setup

## Got a `MeetingNotifier.zip` from a teammate?

This is all you need — no Python, no git, no manual credentials file:

1. Unzip it anywhere (Desktop, Downloads, wherever).
2. Double-click `MeetingNotifier.exe` inside the unzipped folder.
3. A welcome window appears. Click **Sign in with Google** and complete the
   sign-in in the browser that opens. Google will first show a "this app
   isn't verified" notice — that's expected; click **Advanced > Go to
   Meeting Notifier (unsafe)** to continue. It's safe: this app only asks
   for read-only access to your own calendar.
4. Leave "Start automatically when I log in" checked if you want it running
   every time you log in (recommended).

That's it — the tray icon appears once you're signed in. See
**Day-to-day usage** below for what the tray menu does.

---

## Setting this up from source (for whoever builds/maintains it)

### Requirements

- Windows 10/11 (uses `winsound` and Windows Startup/Start Menu folders —
  won't run as-is on macOS/Linux).
- Python 3.10+ (built and tested on 3.12).
- A Google account with a calendar you want alerts from.

This repo includes a `.python-version` file pinning `3.12.10` — that's only
used by [pyenv](https://github.com/pyenv/pyenv) / [pyenv-win](https://github.com/pyenv-win/pyenv-win),
and only if you already have it installed. If you don't use pyenv, ignore
that file — just make sure whatever `python`/`pip` you normally use is 3.10+.
If you do use pyenv-win but don't have 3.12.10 installed, either run
`pyenv install 3.12.10` or edit/delete `.python-version` to match a version
you already have.

### 1. Create Google OAuth credentials (one-time, do this yourself in your browser)

1. Go to https://console.cloud.google.com/ and create a new project (or pick
   an existing one you're fine using for this).
2. Go to **APIs & Services > Library**, search for **Google Calendar API**,
   and click **Enable**.
3. Go to **APIs & Services > OAuth consent screen**.
   - Fill in an app name (e.g. "Meeting Notifier") and your email where
     required.
   - User type — pick based on your Google account:
     - **If your Google account is on a Google Workspace domain** (e.g.
       `you@yourcompany.com`) and you only want people on that same domain
       to use this: choose **Internal**. This is the simplest option —
       no "unverified app" warning screen for anyone, no verification ever
       required, no Publishing status/Testing/Production step at all, and
       no home page/privacy policy/domain fields to fill in. It's simply
       restricted to your Workspace org.
     - **Otherwise** (personal `@gmail.com` account, or you want people
       outside your org to use it too): choose **External**, and set
       **Publishing status to "In production"** (not "Testing") on the
       **Audience** page. Since this app only requests the
       `calendar.readonly` scope — a "sensitive," not "restricted," scope —
       and you'll have well under 100 users, this doesn't require Google's
       formal verification process, it's just a toggle. This matters for
       two reasons:
       - Teammates never need to be individually added as "Test users" —
         they just click through Google's one-time "unverified app"
         warning themselves on first sign-in.
       - **Testing-status tokens silently expire after exactly 7 days**,
         forcing everyone (including you) to re-sign-in weekly. Production
         status doesn't have this trap.
       - If Google blocks Publish with an "OAuth configuration is
         incomplete" banner, it usually wants at least the **Application
         home page** field on the Branding page filled in with a URL you
         actually own — don't use a domain you don't control (e.g.
         `github.com` itself), Google will reject it since domain
         ownership can't be verified. Easiest fix: leave the App
         domain/home page fields blank entirely and try Publish again
         first; only fill them in if Google still insists.
4. Go to **APIs & Services > Credentials > Create Credentials > OAuth client
   ID**.
   - Application type: **Desktop app**.
   - Name it anything, e.g. "Meeting Notifier Desktop".
5. Click **Download JSON** on the created client, rename the downloaded file
   to `credentials.json`, and place it directly in this `meeting_notifier/`
   folder (next to `main.py`).

### 2. Install dependencies

```
pip install -r requirements.txt
```

Run this from inside `meeting_notifier/`.

### 3. First run (completes the OAuth login)

```
python main.py
```

The same welcome window packaged builds show will appear — click
**Sign in with Google** to complete OAuth (and check the autostart box if you
want it, same as a packaged install). Leave it running to confirm it works,
then quit from the tray icon.

### 4. (Optional) re-run autostart setup on its own

The welcome window's checkbox already does this on first run. If you skipped
it, or want to toggle it later, use the tray icon's "Toggle autostart" item,
or run:

```
python install_autostart.py
```

Safe to re-run any time. To remove it: `python install_autostart.py --uninstall`.

---

## Sharing with your team

Once your OAuth client's Publishing status is "In production" (step 1
above), build a package teammates can just unzip and run:

```
pip install pyinstaller
pyinstaller --name MeetingNotifier --onedir --windowed --icon icon.ico --add-data "credentials.json;." main.py
```

Then zip the output folder (`dist/MeetingNotifier/`) — e.g. right-click it >
**Send to > Compressed (zipped) folder**, or in PowerShell:
`Compress-Archive -Path dist\MeetingNotifier -DestinationPath MeetingNotifier-win.zip`.

Share that zip file directly with teammates (Slack DM, a shared drive with
restricted access, etc.) — **not** via the public git repo. `dist/`,
`build/`, and `*.spec` are gitignored for exactly this reason: the zip
embeds your real `credentials.json`, and while that's safe to share within
your team (see README.md's security notes for why), it shouldn't end up
somewhere public.

Rebuild and re-share the zip any time you change the code.

---

## Restarting after you Quit from the tray

Quitting from the tray only stops that running instance — it doesn't relaunch
it. To start it again immediately: search "Meeting Notifier" in the Start
menu and click it. It will otherwise only restart automatically the next
time you log into Windows (if autostart is enabled).

## Day-to-day usage

Right-click (or click, for the default action) the tray icon for:
- **Open dashboard** — a window showing your upcoming meetings with live
  countdowns, a green/amber/red sync status dot, a "Sync now" button, and a
  "Preview alert" button that pops the full-screen alert on demand so you can
  check it looks right without waiting for a real meeting.
- **Sync now** — force an immediate calendar refresh.
- **Toggle autostart** — turn the login-autostart entry on or off.
- **Quit** — stops the running instance (see above for restarting).

## Notes

- `credentials.json` and `token.json` contain access to your calendar (read
  only) — don't share `token.json` or commit either to git (both already in
  `.gitignore`). See README.md for why sharing `credentials.json` itself
  within your team is fine.
- **File locations**: running from source, `config.json`/`credentials.json`/
  `token.json`/`notifier.log` live next to `main.py`. Running a packaged
  build (the .exe), they live in `%LOCALAPPDATA%\MeetingNotifier\` instead —
  this survives even if you move or delete the unzipped app folder.
- Settings like alert lead time (`alert_lead_seconds`) and sync frequency
  (`sync_interval_seconds`) live in `config.json` — edit and restart the app
  to apply changes.
- Logs are written to `notifier.log` if something isn't working as expected.
  It rotates every 24h and keeps 1 backup, so nothing older than ~48h is
  ever kept.
- `icon.ico` is auto-generated the first time autostart is set up — safe to
  delete, it's regenerated automatically (already in `.gitignore`).
- The welcome/sign-in window only ever appears once — it's skipped as soon
  as a `token.json` exists.
