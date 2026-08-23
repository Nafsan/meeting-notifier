import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calendar_sync import _is_declined, fetch_upcoming_meet_events


class FakeEventsResource:
    def __init__(self, result):
        self._result = result
        self.last_call_kwargs = None

    def list(self, **kwargs):
        self.last_call_kwargs = kwargs
        return self

    def execute(self):
        return self._result


class FakeService:
    def __init__(self, result):
        self._events_resource = FakeEventsResource(result)

    def events(self):
        return self._events_resource


class IsDeclinedTests(unittest.TestCase):
    def test_no_attendees_is_not_declined(self):
        self.assertFalse(_is_declined({}))

    def test_self_declined(self):
        event = {"attendees": [{"self": True, "responseStatus": "declined"}]}
        self.assertTrue(_is_declined(event))

    def test_self_accepted(self):
        event = {"attendees": [{"self": True, "responseStatus": "accepted"}]}
        self.assertFalse(_is_declined(event))

    def test_other_attendees_declining_does_not_count(self):
        event = {"attendees": [{"self": False, "responseStatus": "declined"}]}
        self.assertFalse(_is_declined(event))


class FetchUpcomingMeetEventsTests(unittest.TestCase):
    def _event(self, event_id, **overrides):
        base = {
            "id": event_id,
            "status": "confirmed",
            "summary": f"Event {event_id}",
            "hangoutLink": f"https://meet.google.com/{event_id}",
            "start": {"dateTime": "2026-08-23T11:30:00+06:00"},
        }
        base.update(overrides)
        return base

    def test_returns_only_events_with_a_meet_link_that_are_not_cancelled_or_declined(self):
        events = [
            self._event("keep-1"),
            self._event("cancelled", status="cancelled"),
            self._event("no-meet-link", hangoutLink=None),
            self._event("declined", attendees=[{"self": True, "responseStatus": "declined"}]),
            self._event("all-day", start={"date": "2026-08-24"}),
        ]
        service = FakeService({"items": events})

        result = fetch_upcoming_meet_events(service, "primary", 12)

        self.assertEqual([e["id"] for e in result], ["keep-1"])
        self.assertEqual(result[0]["title"], "Event keep-1")
        self.assertEqual(result[0]["meet_link"], "https://meet.google.com/keep-1")
        self.assertIsInstance(result[0]["start"], dt.datetime)

    def test_missing_summary_falls_back_to_placeholder_title(self):
        # No "summary" key at all (not just an empty one) - .get()'s default
        # only kicks in when the key is absent.
        event = {
            "id": "no-title",
            "status": "confirmed",
            "hangoutLink": "https://meet.google.com/no-title",
            "start": {"dateTime": "2026-08-23T11:30:00+06:00"},
        }
        service = FakeService({"items": [event]})

        result = fetch_upcoming_meet_events(service, "primary", 12)

        self.assertEqual(result[0]["title"], "(no title)")

    def test_no_items_returns_empty_list(self):
        service = FakeService({})

        result = fetch_upcoming_meet_events(service, "primary", 12)

        self.assertEqual(result, [])

    def test_passes_calendar_id_and_query_flags_through(self):
        service = FakeService({"items": []})

        fetch_upcoming_meet_events(service, "team@group.calendar.google.com", 6)

        kwargs = service._events_resource.last_call_kwargs
        self.assertEqual(kwargs["calendarId"], "team@group.calendar.google.com")
        self.assertEqual(kwargs["singleEvents"], True)
        self.assertEqual(kwargs["orderBy"], "startTime")


if __name__ == "__main__":
    unittest.main()
