"""Thread-safe asynchronous queue for scheduled reviews."""

import json
import queue
import threading
import time
from pathlib import Path

from core.drip_scheduler import post_review


QUEUE_PATH = Path("queue/review_queue.json")


class AsyncReviewQueue:
    """Queue that persists tasks and processes them asynchronously."""

    def __init__(self) -> None:
        self.queue: "queue.Queue[tuple[float, str, str, str | None, dict | None]]" = queue.Queue()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        try:
            data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
            for item in data:
                # Older queue items may not contain proxy/account
                if len(item) == 3:
                    timestamp, review, template = item
                    proxy = account = None
                else:
                    timestamp, review, template, proxy, account = item
                self.queue.put((timestamp, review, template, proxy, account))
        except FileNotFoundError:
            QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
            QUEUE_PATH.write_text("[]", encoding="utf-8")
        except json.JSONDecodeError:
            pass

    def _save(self) -> None:
        items = list(self.queue.queue)
        QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        QUEUE_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    def add(self, review: str, template_path: str, post_at_timestamp: float, proxy: str | None = None, account: dict | None = None) -> None:
        self.queue.put((post_at_timestamp, review, template_path, proxy, account))
        self._save()
        self.stop_event.set()

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join()

    # ------------------------------------------------------------------
    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                timestamp, review, template, proxy, account = self.queue.get(timeout=1)
            except queue.Empty:
                continue

            while not self.stop_event.is_set():
                delay = timestamp - time.time()
                if delay <= 0:
                    try:
                        post_review(template, review, proxy=proxy, account=account)
                    except Exception as e:  # pragma: no cover - logging only
                        print(f"Failed to post review: {e}")
                    break
                if self.stop_event.wait(timeout=delay):
                    break

            self._save()

