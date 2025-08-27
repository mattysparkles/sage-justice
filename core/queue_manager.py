"""Thread-safe persistent job queue manager."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional


class JobQueueManager:
    """Manage a persistent queue of review posting jobs.

    Jobs are stored as dictionaries in a JSON file. Access to the
    underlying list is guarded by a threading lock so the queue can be
    safely used from multiple threads.
    """

    def __init__(self, path: str = "queue/job_queue.json") -> None:
        self.path = Path(path)
        self.lock = Lock()
        self.queue: List[Dict[str, Any]] = []
        self.load_queue()

    # ------------------------------------------------------------------
    # persistence helpers
    def load_queue(self) -> None:
        """Load queue contents from disk."""
        with self.lock:
            if self.path.exists():
                with self.path.open("r", encoding="utf-8") as f:
                    self.queue = json.load(f)
            else:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.queue = []
                self._save_queue_locked()

    def _save_queue_locked(self) -> None:
        """Write current queue to disk. Caller must hold ``self.lock``."""
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self.queue, f, indent=2)

    def save_queue(self) -> None:
        """Persist queue to disk."""
        with self.lock:
            self._save_queue_locked()

    # ------------------------------------------------------------------
    # queue operations
    def add_job(
        self,
        site_name: str,
        review_text: str,
        proxy_id: Optional[str] = None,
        account_id: Optional[str] = None,
        scheduled_time: Optional[float] = None,
    ) -> str:
        """Add a new job to the queue.

        Returns the generated job id.
        """

        job = {
            "site_name": site_name,
            "review_text": review_text,
            "proxy_id": proxy_id,
            "account_id": account_id,
            "scheduled_time": scheduled_time if scheduled_time is not None else time.time(),
            "job_id": str(uuid.uuid4()),
            "status": "Pending",
        }
        with self.lock:
            self.queue.append(job)
            self._save_queue_locked()
        return job["job_id"]

    def get_next_job(self) -> Optional[Dict[str, Any]]:
        """Retrieve the next pending job and mark it as running."""

        with self.lock:
            now = time.time()
            for job in self.queue:
                if job["status"] == "Pending" and job["scheduled_time"] <= now:
                    job["status"] = "Running"
                    self._save_queue_locked()
                    return job
            return None

    def mark_job_as(self, job_id: str, status: str) -> None:
        """Update the status of a job by its id."""

        with self.lock:
            for job in self.queue:
                if job["job_id"] == job_id:
                    job["status"] = status
                    break
            self._save_queue_locked()

    def retry_failed_jobs(self) -> None:
        """Reset status of all failed jobs back to pending."""

        with self.lock:
            for job in self.queue:
                if job.get("status") == "Failed":
                    job["status"] = "Pending"
            self._save_queue_locked()


# Backwards compatibility -------------------------------------------------
# Some older parts of the codebase may still import ``ReviewQueueManager``.
# Provide it as an alias to ``JobQueueManager`` so existing imports continue
# to function.
ReviewQueueManager = JobQueueManager

