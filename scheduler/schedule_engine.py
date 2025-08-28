import json
import time
import threading
import random
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

try:
    from core.review_generator import generate_reviews
except Exception:  # pragma: no cover - fallback when dependencies missing
    def generate_reviews(*args, **kwargs):
        return None


DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class ReviewScheduler:
    """Flexible scheduler supporting multiple modes and logging."""

    def __init__(
        self,
        schedule_path: str = "config/schedule.json",
        mode: str = "rotate",
        tick_seconds: int = 60,
    ) -> None:
        self.schedule_path = schedule_path
        self.mode = mode
        self.tick_seconds = tick_seconds
        self.running = False
        self.paused = False
        self.thread: threading.Thread | None = None
        self.current_index = 0
        self.logger = logging.getLogger("scheduler")
        if not self.logger.handlers:
            handler = logging.FileHandler("logs/scheduler.log")
            handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False
        self.load_schedule()

    # -----------------------------------------------------
    # Schedule management
    # -----------------------------------------------------
    def load_schedule(self) -> None:
        try:
            with open(self.schedule_path, "r", encoding="utf-8") as f:
                self.schedule: List[Dict[str, Any]] = json.load(f)
        except FileNotFoundError:
            self.schedule = []
        for task in self.schedule:
            task.setdefault("status", "Queued")
            task.setdefault("project", "default")
            task.setdefault("days", list(range(7)))
            task.setdefault("hours", list(range(24)))
            task.setdefault("offset", 0)
            task.setdefault("next_run", self.compute_next_run(task))

    def validate_task(self, task: Dict[str, Any]) -> None:
        for day in task.get("days", []):
            if day not in range(7):
                raise ValueError("day must be in 0..6")
        for hour in task.get("hours", []):
            if hour not in range(24):
                raise ValueError("hour must be in 0..23")
        if task.get("offset", 0) < 0:
            raise ValueError("offset must be >= 0")

    def add_task(
        self,
        prompt: str,
        project: str = "default",
        site: str | None = None,
        days: List[int] | None = None,
        hours: List[int] | None = None,
        offset: int = 0,
    ) -> None:
        """Add a new scheduled review task."""
        task = {
            "prompt": prompt,
            "site": site,
            "project": project,
            "days": days or list(range(7)),
            "hours": hours or list(range(24)),
            "offset": offset,
            "status": "Queued",
        }
        self.validate_task(task)
        task["next_run"] = self.compute_next_run(task)
        self.schedule.append(task)
        self.save_schedule()

    def compute_next_run(self, task: Dict[str, Any]) -> str:
        now = datetime.now()
        offset = timedelta(minutes=task.get("offset", 0))
        for delta_days in range(8):
            day_candidate = now + timedelta(days=delta_days)
            if task["days"] and day_candidate.weekday() not in task["days"]:
                continue
            for hour in sorted(task["hours"]):
                candidate = day_candidate.replace(
                    hour=hour, minute=0, second=0, microsecond=0
                ) + offset
                if candidate > now:
                    return candidate.isoformat()
        return (now + timedelta(days=7)).isoformat()

    def preview_task(self, task: Dict[str, Any]) -> str:
        days = ", ".join(DAY_NAMES[d] for d in task["days"])
        hours = ", ".join(f"{h:02d}:00" for h in task["hours"])
        return f"{days} at {hours} offset {task.get('offset',0)}m"

    # -----------------------------------------------------
    # Control methods
    # -----------------------------------------------------
    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.running = True
        self.paused = False
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()
        self.logger.info("Scheduler started")

    def pause(self) -> None:
        self.paused = True
        self.logger.info("Scheduler paused")

    def resume(self) -> None:
        self.paused = False
        self.logger.info("Scheduler resumed")

    def stop(self) -> None:
        self.running = False
        self.logger.info("Scheduler stopped")

    # -----------------------------------------------------
    # Core loop
    # -----------------------------------------------------
    def run_loop(self) -> None:
        while self.running:
            if self.paused:
                time.sleep(self.tick_seconds)
                continue
            now = datetime.now()
            due = [t for t in self.schedule if datetime.fromisoformat(t["next_run"]) <= now]
            tasks_to_run: List[Dict[str, Any]] = []
            if self.mode == "all":
                tasks_to_run = due
            elif self.mode == "random" and due:
                tasks_to_run = [random.choice(due)]
            elif due:
                tasks_to_run = [due[self.current_index % len(due)]]
                self.current_index += 1
            for task in tasks_to_run:
                task["status"] = "Posting"
                self.logger.info(
                    "Posting prompt '%s' for project %s", task["prompt"], task["project"]
                )
                try:
                    generate_reviews(task["prompt"], site=task.get("site"))
                except TypeError:
                    generate_reviews(task["prompt"])
                except Exception:
                    task["status"] = "Failed"
                    task["next_run"] = self.compute_next_run(task)
                    continue
                task["status"] = "Posted"
                task["next_run"] = self.compute_next_run(task)
            self.save_schedule()
            time.sleep(self.tick_seconds)

    # -----------------------------------------------------
    def save_schedule(self) -> None:
        with open(self.schedule_path, "w", encoding="utf-8") as f:
            json.dump(self.schedule, f, indent=2)
