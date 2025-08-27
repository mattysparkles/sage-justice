
import json
import time
import threading
from datetime import datetime, timedelta
from core.review_generator import generate_reviews

class ReviewScheduler:
    def __init__(self, schedule_path="config/schedule.json"):
        self.schedule_path = schedule_path
        self.load_schedule()

    def load_schedule(self):
        try:
            with open(self.schedule_path, "r") as f:
                self.schedule = json.load(f)
        except FileNotFoundError:
            self.schedule = []

    def start(self):
        threading.Thread(target=self.run_loop, daemon=True).start()

    def run_loop(self):
        while True:
            now = datetime.now()
            for task in self.schedule:
                next_run = datetime.fromisoformat(task["next_run"])
                if next_run <= now:
                    print(f"[{now.isoformat()}] Posting review to: {task['site']}")
                    try:
                        generate_reviews(task["prompt"], site=task["site"])
                    except TypeError:
                        generate_reviews(task["prompt"])
                    task["next_run"] = self.get_next_run(task["interval_minutes"])
            self.save_schedule()
            time.sleep(60)

    def get_next_run(self, minutes):
        return (datetime.now() + timedelta(minutes=minutes)).isoformat()

    def save_schedule(self):
        with open(self.schedule_path, "w") as f:
            json.dump(self.schedule, f, indent=2)
