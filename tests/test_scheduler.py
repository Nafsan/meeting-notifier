import datetime as dt
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scheduler import (
    MAX_OVERDUE_SECONDS,
    MAX_SLEEP_SECONDS,
    MIN_SLEEP_SECONDS,
    TIGHTEN_THRESHOLD_SECONDS,
    Scheduler,
)


def make_config(**overrides):
    config = {
        "calendar_id": "primary",
        "alert_lead_seconds": 60,
        "sync_interval_seconds": 300,
        "snooze_seconds": 60,
        "lookahead_hours": 12,
    }
    config.update(overrides)
    return config


class AlertFiringTests(unittest.TestCase):
    def test_fires_alert_when_due(self):
        scheduler = Scheduler(make_config())
        now = time.time()
        scheduler.schedule = {
            "evt1": {
                "title": "Standup", "start": now + 60, "meet_link": "https://meet/x",
                "alert_time": now - 1, "fired": False,
            },
        }

        scheduler._check_due_alerts()

        self.assertTrue(scheduler.schedule["evt1"]["fired"])
        queued = scheduler.alert_queue.get_nowait()
        self.assertEqual(queued["event_id"], "evt1")
        self.assertEqual(queued["title"], "Standup")

    def test_does_not_fire_before_alert_time(self):
        scheduler = Scheduler(make_config())
        now = time.time()
        scheduler.schedule = {
            "evt1": {
                "title": "Standup", "start": now + 120, "meet_link": "https://meet/x",
                "alert_time": now + 60, "fired": False,
            },
        }

        scheduler._check_due_alerts()

        self.assertFalse(scheduler.schedule["evt1"]["fired"])
        self.assertTrue(scheduler.alert_queue.empty())

    def test_skips_very_stale_alert_without_queuing(self):
        # e.g. the PC was asleep through the whole meeting - shouldn't pop an
        # alert long after the fact.
        scheduler = Scheduler(make_config())
        now = time.time()
        scheduler.schedule = {
            "evt1": {
                "title": "Standup", "start": now - 500, "meet_link": "https://meet/x",
                "alert_time": now - (MAX_OVERDUE_SECONDS + 10), "fired": False,
            },
        }

        scheduler._check_due_alerts()

        self.assertTrue(scheduler.schedule["evt1"]["fired"])
        self.assertTrue(scheduler.alert_queue.empty())

    def test_does_not_refire_an_already_fired_alert(self):
        scheduler = Scheduler(make_config())
        now = time.time()
        scheduler.schedule = {
            "evt1": {
                "title": "Standup", "start": now + 10, "meet_link": "https://meet/x",
                "alert_time": now - 1, "fired": True,
            },
        }

        scheduler._check_due_alerts()

        self.assertTrue(scheduler.alert_queue.empty())


class SnoozeTests(unittest.TestCase):
    def test_snooze_resets_fired_and_pushes_alert_time_forward(self):
        scheduler = Scheduler(make_config())
        now = time.time()
        scheduler.schedule = {
            "evt1": {
                "title": "Standup", "start": now + 30, "meet_link": "https://meet/x",
                "alert_time": now - 30, "fired": True,
            },
        }

        scheduler.snooze("evt1", 45)

        ev = scheduler.schedule["evt1"]
        self.assertFalse(ev["fired"])
        self.assertAlmostEqual(ev["alert_time"], now + 45, delta=2)

    def test_snooze_on_unknown_event_id_is_a_noop(self):
        scheduler = Scheduler(make_config())
        scheduler.schedule = {}

        scheduler.snooze("does-not-exist", 45)  # should not raise

        self.assertEqual(scheduler.schedule, {})


class SyncTests(unittest.TestCase):
    def test_sync_preserves_fired_state_for_existing_events_and_defaults_new_ones(self):
        scheduler = Scheduler(make_config(alert_lead_seconds=60))
        start_dt = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=30)
        scheduler.schedule = {
            "evt1": {
                "title": "Old title", "start": start_dt.timestamp(), "meet_link": "old-link",
                "alert_time": start_dt.timestamp() - 60, "fired": True,
            },
        }
        fake_events = [
            {"id": "evt1", "title": "Standup", "start": start_dt, "meet_link": "https://meet/evt1"},
            {"id": "evt2", "title": "New meeting", "start": start_dt, "meet_link": "https://meet/evt2"},
        ]

        with patch("calendar_sync.fetch_upcoming_meet_events", return_value=fake_events):
            ok = scheduler._sync(service=object())

        self.assertTrue(ok)
        self.assertTrue(scheduler.schedule["evt1"]["fired"], "existing fired state should survive a resync")
        self.assertFalse(scheduler.schedule["evt2"]["fired"], "a newly-seen event should not start out fired")
        self.assertEqual(scheduler.schedule["evt1"]["title"], "Standup", "fields should refresh from the latest fetch")
        self.assertIsNotNone(scheduler.last_sync_at)
        self.assertIsNone(scheduler.last_sync_error)

    def test_sync_failure_is_caught_and_recorded_without_raising(self):
        scheduler = Scheduler(make_config())

        with patch("calendar_sync.fetch_upcoming_meet_events", side_effect=RuntimeError("boom")):
            ok = scheduler._sync(service=object())

        self.assertFalse(ok)
        self.assertIn("boom", scheduler.last_sync_error)

    def test_missing_credentials_sets_warning_without_raising(self):
        scheduler = Scheduler(make_config())

        with patch("calendar_sync.build_service", side_effect=FileNotFoundError("no credentials.json")):
            service = scheduler._try_build_service()

        self.assertIsNone(service)
        self.assertIn("credentials.json", scheduler.last_sync_error)

    def test_unexpected_service_build_error_is_caught(self):
        scheduler = Scheduler(make_config())

        with patch("calendar_sync.build_service", side_effect=RuntimeError("network down")):
            service = scheduler._try_build_service()

        self.assertIsNone(service)
        self.assertIn("network down", scheduler.last_sync_error)


class SleepTimingTests(unittest.TestCase):
    def test_defaults_to_capped_sleep_when_nothing_imminent(self):
        scheduler = Scheduler(make_config(sync_interval_seconds=300))

        sleep_for = scheduler._compute_sleep_seconds()

        self.assertEqual(sleep_for, MAX_SLEEP_SECONDS)

    def test_tightens_when_an_alert_is_imminent(self):
        scheduler = Scheduler(make_config(sync_interval_seconds=300))
        now = time.time()
        scheduler.schedule = {
            "evt1": {
                "title": "Standup", "start": now + 10, "meet_link": "x",
                "alert_time": now + 5, "fired": False,
            },
        }

        sleep_for = scheduler._compute_sleep_seconds()

        self.assertLessEqual(sleep_for, TIGHTEN_THRESHOLD_SECONDS)
        self.assertGreaterEqual(sleep_for, MIN_SLEEP_SECONDS)
        self.assertAlmostEqual(sleep_for, 5, delta=1)

    def test_ignores_already_fired_events_when_computing_sleep(self):
        scheduler = Scheduler(make_config(sync_interval_seconds=300))
        now = time.time()
        scheduler.schedule = {
            "evt1": {
                "title": "Standup", "start": now + 2, "meet_link": "x",
                "alert_time": now + 1, "fired": True,
            },
        }

        sleep_for = scheduler._compute_sleep_seconds()

        self.assertEqual(sleep_for, MAX_SLEEP_SECONDS)


class StatusAndUpcomingEventsTests(unittest.TestCase):
    def test_upcoming_events_sorted_by_start_time(self):
        scheduler = Scheduler(make_config())
        now = time.time()
        scheduler.schedule = {
            "later": {"title": "Later", "start": now + 200, "meet_link": "x", "alert_time": now + 140, "fired": False},
            "sooner": {"title": "Sooner", "start": now + 50, "meet_link": "y", "alert_time": now - 10, "fired": False},
        }

        events = scheduler.upcoming_events()

        self.assertEqual([e["event_id"] for e in events], ["sooner", "later"])

    def test_status_reports_error_and_upcoming_count(self):
        scheduler = Scheduler(make_config(sync_interval_seconds=300))
        scheduler.last_sync_error = "boom"
        scheduler.last_attempt_at = time.time()
        scheduler.schedule = {
            "a": {"title": "A", "start": 0, "meet_link": "x", "alert_time": 0, "fired": False},
            "b": {"title": "B", "start": 0, "meet_link": "x", "alert_time": 0, "fired": True},
        }

        status = scheduler.status()

        self.assertEqual(status["last_sync_error"], "boom")
        self.assertEqual(status["upcoming_count"], 1)
        self.assertAlmostEqual(status["next_attempt_at"], scheduler.last_attempt_at + 300, delta=1)


if __name__ == "__main__":
    unittest.main()
