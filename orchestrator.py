"""Multi-agent orchestrator for processing review posting jobs."""

from __future__ import annotations

import threading
import time
from typing import Optional

from core.queue_manager import JobQueueManager
from core.review_poster import post_review


class ReviewAgent(threading.Thread):
    """Worker thread that posts reviews pulled from the job queue."""

    def __init__(self, agent_id: int, queue: JobQueueManager) -> None:
        super().__init__(name=f"Agent-{agent_id}")
        self.agent_id = agent_id
        self.queue = queue
        self.daemon = True

    def log(self, message: str) -> None:
        print(f"[Agent-{self.agent_id}] {message}")

    def run(self) -> None:  # pragma: no cover - thread logic
        while True:
            job = self.queue.get_next_job()
            if not job:
                return

            job_id = job["job_id"]
            site = job["site_name"]
            text = job["review_text"]

            attempt = 0
            backoff = 1.0
            while attempt < 3:
                try:
                    # Actual proxy/account assignment would occur here
                    post_review(site, text)
                    self.queue.mark_job_as(job_id, "Posted")
                    self.log(f"Posted review to {site} – Job ID {job_id}")
                    break
                except Exception as exc:  # pragma: no cover - network/selenium errors
                    attempt += 1
                    if attempt >= 3:
                        self.queue.mark_job_as(job_id, "Failed")
                        self.log(f"Failed to post review to {site} – Job ID {job_id}: {exc}")
                    else:
                        self.log(f"Error posting to {site} (attempt {attempt}); retrying in {backoff}s")
                        time.sleep(backoff)
                        backoff *= 2


class Orchestrator:
    """Spawn worker agents to process queued jobs."""

    def __init__(self, max_agents: int = 5, queue: Optional[JobQueueManager] = None) -> None:
        self.max_agents = max_agents
        self.queue = queue or JobQueueManager()

    def run(self) -> None:  # pragma: no cover - thread orchestration
        threads = [ReviewAgent(i + 1, self.queue) for i in range(self.max_agents)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


__all__ = ["Orchestrator", "ReviewAgent"]

