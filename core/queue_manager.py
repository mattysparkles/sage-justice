
import json
import time
from threading import Lock

class ReviewQueueManager:
    def __init__(self, path="queue/review_queue.json"):
        self.path = path
        self.lock = Lock()
        self._load_queue()

    def _load_queue(self):
        try:
            with open(self.path, "r") as f:
                self.queue = json.load(f)
        except FileNotFoundError:
            self.queue = []
            self._save_queue()

    def _save_queue(self):
        with open(self.path, "w") as f:
            json.dump(self.queue, f, indent=2)

    def add_task(self, task):
        with self.lock:
            self.queue.append(task)
            self._save_queue()

    def get_next_task(self):
        with self.lock:
            if self.queue:
                task = self.queue.pop(0)
                self._save_queue()
                return task
            return None

    def peek(self):
        with self.lock:
            return self.queue[0] if self.queue else None

    def is_empty(self):
        with self.lock:
            return len(self.queue) == 0
