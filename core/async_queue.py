import threading
import time
import queue

from core.drip_scheduler import post_review

class AsyncReviewQueue:
    def __init__(self):
        self.queue: "queue.PriorityQueue[tuple[float, str, str]]" = queue.PriorityQueue()
        self.running = False
        self.thread: threading.Thread | None = None
        self._event = threading.Event()

    def add(self, review, template_path, post_at_timestamp):
        self.queue.put((post_at_timestamp, review, template_path))
        self._event.set()

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run)
            self.thread.start()

    def stop(self):
        if self.running:
            self.running = False
            self._event.set()
            if self.thread:
                self.thread.join()

    def run(self):
        while self.running:
            try:
                timestamp, review, template = self.queue.get(timeout=1)
            except queue.Empty:
                continue

            while self.running:
                delay = timestamp - time.time()
                if delay <= 0:
                    try:
                        print(f"Posting review scheduled for {time.ctime(timestamp)}")
                        post_review(template, review)
                    except Exception as e:
                        print(f"Failed to post review: {e}")
                    break

                if self._event.wait(timeout=delay):
                    # A new task may have an earlier timestamp
                    self._event.clear()
                    self.queue.put((timestamp, review, template))
                    break
