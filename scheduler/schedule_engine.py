
import json
import time
import threading
from datetime import datetime, timedelta
from core.review_generator import generate_reviews

class ReviewScheduler:
    """Lightweight scheduler for posting reviews."""

    def __init__(self, schedule_path: str = "config/schedule.json"):
        self.schedule_path = schedule_path
        self.load_schedule()
        self.running = False
        self.thread = None  # type: threading.Thread | None

    def load_schedule(self):
        try:
            with open(self.schedule_path, "r") as f:
                self.schedule = json.load(f)
        except FileNotFoundError:
            self.schedule = []
        for task in self.schedule:
            task.setdefault("status", "Queued")

    def add_task(self, prompt: str, site: str | None = None, interval_minutes: int = 60) -> None:
        """Add a new scheduled review task."""
        task = {
            "prompt": prompt,
            "site": site,
            "interval_minutes": interval_minutes,
            "next_run": self.get_next_run(interval_minutes),
            "status": "Queued",
        }
        self.schedule.append(task)
        self.save_schedule()

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.running = True
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False

    def run_loop(self) -> None:
        while self.running:
            now = datetime.now()
            for task in self.schedule:
                next_run = datetime.fromisoformat(task["next_run"])
                if next_run <= now:
                    task["status"] = "Posting"
                    try:
                        generate_reviews(task["prompt"], site=task["site"])
                    except TypeError:
                        generate_reviews(task["prompt"])
                    except Exception:
                        task["status"] = "Failed"
                        task["next_run"] = self.get_next_run(task["interval_minutes"])
                        continue
                    task["status"] = "Posted"
                    task["next_run"] = self.get_next_run(task["interval_minutes"])
            self.save_schedule()
            time.sleep(60)

    def get_next_run(self, minutes):
        return (datetime.now() + timedelta(minutes=minutes)).isoformat()

    def save_schedule(self):
        with open(self.schedule_path, "w") as f:
            json.dump(self.schedule, f, indent=2)
