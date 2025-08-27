import threading
import time
import random
from core.drip_scheduler import post_review

class AsyncReviewQueue:
    def __init__(self):
        self.queue = []
        self.running = False

    def add(self, review, template_path, post_at_timestamp):
        self.queue.append({
            "review": review,
            "template": template_path,
            "timestamp": post_at_timestamp
        })

    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self.run).start()

    def run(self):
        while self.running:
            now = time.time()
            self.queue.sort(key=lambda x: x["timestamp"])  # Keep queue ordered
            while self.queue and self.queue[0]["timestamp"] <= now:
                task = self.queue.pop(0)
                try:
                    print(f"Posting review scheduled for {time.ctime(task['timestamp'])}")
                    post_review(task["template"], task["review"])
                except Exception as e:
                    print(f"Failed to post review: {e}")
            time.sleep(60)
