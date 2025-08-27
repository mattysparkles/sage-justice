import json
import os
import sys

sys.path.append(os.path.abspath("."))

from core.queue_manager import ReviewQueueManager


def test_get_next_task_persists(tmp_path):
    queue_file = tmp_path / "queue.json"
    manager = ReviewQueueManager(path=str(queue_file))
    manager.add_task({"id": 1})
    manager.add_task({"id": 2})

    task = manager.get_next_task()
    assert task == {"id": 1}
    with open(queue_file) as f:
        assert json.load(f) == [{"id": 2}]

    task = manager.get_next_task()
    assert task == {"id": 2}
    with open(queue_file) as f:
        assert json.load(f) == []
