"""Job queue manager backed by the central SQLite database."""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional

from . import database


class JobQueueManager:
    """Interact with queued jobs stored in the database."""

    def __init__(self) -> None:
        self.lock = Lock()
        # Cached list of jobs for interfaces that expect an in-memory queue
        self.queue: List[Dict[str, Any]] = []

    def add_job(
        self,
        site_name: str,
        review_text: str,
        proxy_id: Optional[int] = None,
        account_id: Optional[int] = None,
        scheduled_time: Optional[float] = None,
    ) -> str:
        """Add a new job to the database."""
        when = datetime.fromtimestamp(scheduled_time) if scheduled_time else None
        with self.lock:
            return database.insert_job(site_name, review_text, proxy_id, account_id, scheduled_time=when)

    def get_next_job(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            return database.fetch_next_job()

    def mark_job_as(self, job_id: str, status: str) -> None:
        with self.lock:
            database.update_job_status(job_id, status)

    def retry_failed_jobs(self) -> None:
        with self.lock:
            database.retry_failed_jobs()

    # ------------------------------------------------------------------
    # Compatibility helpers
    def load_queue(self) -> None:
        """Populate ``self.queue`` with all jobs from the database.

        The previous JSON-backed implementation exposed a ``load_queue``
        method that refreshed an in-memory list of jobs.  The GUI still
        relies on this behaviour.  This method reintroduces that API by
        reading all jobs from the SQLite database and normalising the
        ``scheduled_time`` field to a POSIX timestamp.
        """

        with self.lock:
            conn = database.get_connection()
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at").fetchall()
            conn.close()

            queue: List[Dict[str, Any]] = []
            for row in rows:
                job = dict(row)
                sched = job.get("scheduled_time")
                if isinstance(sched, str):
                    try:
                        job["scheduled_time"] = datetime.fromisoformat(sched).timestamp()
                    except ValueError:
                        job["scheduled_time"] = 0.0
                elif sched is None:
                    job["scheduled_time"] = 0.0
                queue.append(job)

            self.queue = queue


# Backwards compatibility -------------------------------------------------
ReviewQueueManager = JobQueueManager
