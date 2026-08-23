import datetime as dt
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import CREDENTIALS_PATH, TOKEN_PATH

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

log = logging.getLogger("calendar_sync")


def get_credentials():
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"Missing {CREDENTIALS_PATH}. See SETUP.md to create OAuth "
                "credentials in Google Cloud Console."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_service():
    creds = get_credentials()
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _is_declined(event):
    attendees = event.get("attendees")
    if not attendees:
        return False
    for attendee in attendees:
        if attendee.get("self") and attendee.get("responseStatus") == "declined":
            return True
    return False


def fetch_upcoming_meet_events(service, calendar_id, lookahead_hours):
    now = dt.datetime.now(dt.timezone.utc)
    time_max = now + dt.timedelta(hours=lookahead_hours)

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    results = []
    for event in events_result.get("items", []):
        if event.get("status") == "cancelled":
            continue

        meet_link = event.get("hangoutLink")
        if not meet_link:
            continue

        if _is_declined(event):
            continue

        start_raw = event.get("start", {}).get("dateTime")
        if not start_raw:
            continue

        start = dt.datetime.fromisoformat(start_raw.replace("Z", "+00:00"))

        results.append(
            {
                "id": event["id"],
                "title": event.get("summary", "(no title)"),
                "start": start,
                "meet_link": meet_link,
            }
        )

    return results
