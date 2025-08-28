import importlib
import importlib
import os
import sys
import time

sys.path.append(os.path.abspath("."))


def setup_db(tmp_path):
    os.environ["REVIEWBOT_DB"] = str(tmp_path / "test.db")
    import core.database as database
    importlib.reload(database)
    import core.queue_manager as qm
    importlib.reload(qm)
    return database, qm.JobQueueManager


def test_add_and_get_job(tmp_path):
    database, JobQueueManager = setup_db(tmp_path)
    manager = JobQueueManager()
    job_id = manager.add_job("trustpilot", "review", scheduled_time=time.time() - 1)
    job = manager.get_next_job()
    assert job is not None
    assert job["job_id"] == job_id
    assert job["status"] == "Running"
    with database.get_connection() as conn:
        status = conn.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()[0]
        assert status == "Running"


def test_mark_and_retry(tmp_path):
    database, JobQueueManager = setup_db(tmp_path)
    manager = JobQueueManager()
    job_id = manager.add_job("site", "text")
    manager.mark_job_as(job_id, "Failed")
    manager.retry_failed_jobs()
    with database.get_connection() as conn:
        status = conn.execute("SELECT status FROM jobs WHERE job_id=?", (job_id,)).fetchone()[0]
        assert status == "Pending"


def test_load_queue(tmp_path):
    database, JobQueueManager = setup_db(tmp_path)
    manager = JobQueueManager()
    manager.add_job("a", "text", scheduled_time=time.time())
    manager.add_job("b", "text", scheduled_time=time.time())
    manager.load_queue()
    assert len(manager.queue) == 2
    assert all(isinstance(job["scheduled_time"], float) for job in manager.queue)
