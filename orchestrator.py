"""Multi-agent orchestrator for processing review posting jobs."""

from __future__ import annotations

import threading
import time
from core import database
from core.review_poster import post_review


class ReviewAgent(threading.Thread):
    """Worker thread that posts reviews pulled from the job queue."""

    def __init__(self, agent_id: int) -> None:
        super().__init__(name=f"Agent-{agent_id}")
        self.agent_id = agent_id
        self.daemon = True

    def log(self, message: str) -> None:
        print(f"[Agent-{self.agent_id}] {message}")

    def run(self) -> None:  # pragma: no cover - thread logic
        while True:
            job = database.fetch_next_job()
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
                    database.update_job_status(job_id, "Posted")
                    database.log_review(text, None, site, job.get("account_id"), job.get("proxy_id"), "Posted")
                    self.log(f"Posted review to {site} – Job ID {job_id}")
                    break
                except Exception as exc:  # pragma: no cover - network/selenium errors
                    attempt += 1
                    if attempt >= 3:
                        database.update_job_status(job_id, "Failed", str(exc))
                        self.log(f"Failed to post review to {site} – Job ID {job_id}: {exc}")
                    else:
                        self.log(f"Error posting to {site} (attempt {attempt}); retrying in {backoff}s")
                        time.sleep(backoff)
                        backoff *= 2


class Orchestrator:
    """Spawn worker agents to process queued jobs."""

    def __init__(self, max_agents: int = 5) -> None:
        self.max_agents = max_agents

    def run(self) -> None:  # pragma: no cover - thread orchestration
        threads = [ReviewAgent(i + 1) for i in range(self.max_agents)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


__all__ = ["Orchestrator", "ReviewAgent"]

