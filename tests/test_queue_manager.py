import json
import os
import sys
import time

sys.path.append(os.path.abspath("."))

from core.queue_manager import JobQueueManager


def test_add_and_get_job(tmp_path):
    queue_file = tmp_path / "queue.json"
    manager = JobQueueManager(path=str(queue_file))
    job_id = manager.add_job("trustpilot", "review", scheduled_time=time.time() - 1)

    job = manager.get_next_job()
    assert job is not None
    assert job["job_id"] == job_id
    assert job["status"] == "Running"
    with open(queue_file) as f:
        data = json.load(f)
    assert data[0]["status"] == "Running"


def test_mark_and_retry(tmp_path):
    queue_file = tmp_path / "queue.json"
    manager = JobQueueManager(path=str(queue_file))
    job_id = manager.add_job("site", "text")
    manager.mark_job_as(job_id, "Failed")
    manager.retry_failed_jobs()
    with open(queue_file) as f:
        data = json.load(f)
    assert data[0]["status"] == "Pending"

