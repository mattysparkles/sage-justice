"""Job queue manager backed by the central SQLite database."""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any, Dict, Optional

from . import database


class JobQueueManager:
    """Interact with queued jobs stored in the database."""

    def __init__(self) -> None:
        self.lock = Lock()

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


# Backwards compatibility -------------------------------------------------
ReviewQueueManager = JobQueueManager
