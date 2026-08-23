import logging
import queue
import threading
import time

import calendar_sync

log = logging.getLogger("scheduler")

# Once a meeting's alert time has passed by more than this, don't fire it
# (e.g. the PC was asleep through the whole meeting) - avoids a stale alert
# popping up long after the fact.
MAX_OVERDUE_SECONDS = 120

# Once the nearest pending alert is within this many seconds, tighten the
# polling loop for accurate timing. Otherwise sleep in long, cheap chunks.
TIGHTEN_THRESHOLD_SECONDS = 15
MAX_SLEEP_SECONDS = 30
MIN_SLEEP_SECONDS = 0.5


class Scheduler:
    def __init__(self, config):
        self.config = config
        self.alert_queue = queue.Queue()
        self.schedule = {}
        self.last_sync_at = None
        self.last_attempt_at = None
        self.last_sync_error = None
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._lock = threading.Lock()

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._wake_event.set()

    def request_sync(self):
        self._wake_event.set()

    def snooze(self, event_id, seconds):
        with self._lock:
            ev = self.schedule.get(event_id)
            if ev:
                ev["alert_time"] = time.time() + seconds
                ev["fired"] = False
        self._wake_event.set()

    def status(self):
        with self._lock:
            interval = self.config["sync_interval_seconds"]
            return {
                "last_sync_at": self.last_sync_at,
                "last_sync_error": self.last_sync_error,
                "upcoming_count": sum(1 for e in self.schedule.values() if not e["fired"]),
                "next_attempt_at": (self.last_attempt_at + interval) if self.last_attempt_at else None,
            }

    def upcoming_events(self):
        with self._lock:
            events = [
                {
                    "event_id": event_id,
                    "title": ev["title"],
                    "start": ev["start"],
                    "meet_link": ev["meet_link"],
                }
                for event_id, ev in self.schedule.items()
            ]
        events.sort(key=lambda e: e["start"])
        return events

    def _run(self):
        service = None
        while not self._stop_event.is_set():
            now = time.time()
            due_for_attempt = (
                self.last_attempt_at is None
                or now - self.last_attempt_at >= self.config["sync_interval_seconds"]
            )
            if due_for_attempt or self._wake_event.is_set():
                self.last_attempt_at = time.time()
                if service is None:
                    service = self._try_build_service()
                if service is not None:
                    ok = self._sync(service)
                    if not ok:
                        # token/service may have gone bad (revoked, network) -
                        # drop it so the next attempt rebuilds from scratch.
                        service = None

            self._check_due_alerts()

            sleep_for = self._compute_sleep_seconds()
            self._wake_event.wait(timeout=sleep_for)
            self._wake_event.clear()

    def _try_build_service(self):
        try:
            return calendar_sync.build_service()
        except FileNotFoundError as exc:
            # Expected until the user completes the one-time OAuth setup -
            # don't spam the log with a traceback for this.
            with self._lock:
                self.last_sync_error = str(exc)
            log.warning("Calendar not configured yet: %s", exc)
            return None
        except Exception as exc:
            log.exception("Failed to build calendar service")
            with self._lock:
                self.last_sync_error = str(exc)
            return None

    def _sync(self, service):
        try:
            events = calendar_sync.fetch_upcoming_meet_events(
                service,
                self.config["calendar_id"],
                self.config["lookahead_hours"],
            )
            lead = self.config["alert_lead_seconds"]
            with self._lock:
                new_schedule = {}
                for ev in events:
                    start_ts = ev["start"].timestamp()
                    existing = self.schedule.get(ev["id"])
                    new_schedule[ev["id"]] = {
                        "title": ev["title"],
                        "start": start_ts,
                        "meet_link": ev["meet_link"],
                        "alert_time": start_ts - lead,
                        "fired": existing["fired"] if existing else False,
                    }
                self.schedule = new_schedule
                self.last_sync_at = time.time()
                self.last_sync_error = None
            return True
        except Exception as exc:
            log.exception("Calendar sync failed")
            with self._lock:
                self.last_sync_error = str(exc)
            return False

    def _check_due_alerts(self):
        now = time.time()
        with self._lock:
            for event_id, ev in self.schedule.items():
                if ev["fired"]:
                    continue
                if ev["alert_time"] <= now <= ev["alert_time"] + MAX_OVERDUE_SECONDS:
                    ev["fired"] = True
                    self.alert_queue.put(
                        {
                            "event_id": event_id,
                            "title": ev["title"],
                            "start": ev["start"],
                            "meet_link": ev["meet_link"],
                        }
                    )
                elif ev["alert_time"] + MAX_OVERDUE_SECONDS < now:
                    ev["fired"] = True  # too late, skip silently

    def _compute_sleep_seconds(self):
        now = time.time()
        candidates = [self.config["sync_interval_seconds"]]

        if self.last_attempt_at is not None:
            candidates.append(max(0, self.last_attempt_at + self.config["sync_interval_seconds"] - now))

        with self._lock:
            for ev in self.schedule.values():
                if not ev["fired"]:
                    candidates.append(ev["alert_time"] - now)

        soonest = min(candidates)

        if soonest <= TIGHTEN_THRESHOLD_SECONDS:
            return max(MIN_SLEEP_SECONDS, soonest)
        return min(MAX_SLEEP_SECONDS, soonest)
