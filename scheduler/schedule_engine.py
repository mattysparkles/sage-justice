"""Review scheduling engine with project-aware modes and logging."""

from __future__ import annotations

import json
import logging
import random
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

try:  # pragma: no cover - depends on external modules
    from core.review_generator import generate_reviews
except Exception:  # pragma: no cover - fallback when dependencies missing
    def generate_reviews(*args, **kwargs):
        return None

from core import project_hub

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class ReviewScheduler:
    """Flexible scheduler supporting global or per-project schedules.

    The scheduler can operate on a single schedule file or a directory of
    per-project schedules. Projects can be scheduled in rotate, random or all
    modes. Tasks within a project have their own selection mode and support
    offset configuration.
    """

    def __init__(
        self,
        schedule_path: str = "config/schedule.json",
        mode: str = "rotate",
        project_mode: str = "rotate",
        tick_seconds: int = 60,
    ) -> None:
        self.schedule_path = schedule_path
        self.mode = mode  # task selection mode within a project
        self.project_mode = project_mode
        self.tick_seconds = tick_seconds
        self.running = False
        self.paused = False
        self.thread: threading.Thread | None = None
        self.project_indices: Dict[str, int] = {}
        self.current_project = 0
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
        """Load schedules from file or directory."""
        path = Path(self.schedule_path)
        self.project_schedules: Dict[str, List[Dict[str, Any]]] = {}
        if path.is_dir():
            for file in path.glob("*.json"):
                try:
                    data = json.loads(file.read_text(encoding="utf-8"))
                except FileNotFoundError:
                    data = []
                self.project_schedules[file.stem] = data
        else:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                data = []
            for task in data:
                project = task.get("project", "default")
                self.project_schedules.setdefault(project, []).append(task)

        for project, tasks in self.project_schedules.items():
            for task in tasks:
                task.setdefault("status", "Queued")
                task.setdefault("project", project)
                task.setdefault("days", list(range(7)))
                task.setdefault("hours", list(range(24)))
                task.setdefault("offset", 0)
                task.setdefault("next_run", self.compute_next_run(task))
            self.project_indices.setdefault(project, 0)

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
        self.project_schedules.setdefault(project, []).append(task)
        self.project_indices.setdefault(project, 0)
        self.save_schedule()

    def remove_task(self, project: str, index: int) -> None:
        tasks = self.project_schedules.get(project)
        if tasks and 0 <= index < len(tasks):
            del tasks[index]
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
    def run_loop(self) -> None:  # pragma: no cover - involves sleeping
        while self.running:
            if self.paused:
                time.sleep(self.tick_seconds)
                continue

            now = datetime.now()
            due_projects: List[tuple[str, List[Dict[str, Any]]]] = []
            for project, tasks in self.project_schedules.items():
                due = [t for t in tasks if datetime.fromisoformat(t["next_run"]) <= now]
                if due:
                    due_projects.append((project, due))

            selected: List[tuple[str, List[Dict[str, Any]]]] = []
            if self.project_mode == "all":
                selected = due_projects
            elif self.project_mode == "random" and due_projects:
                selected = [random.choice(due_projects)]
            elif due_projects:
                project, tasks = due_projects[self.current_project % len(due_projects)]
                self.current_project += 1
                selected = [(project, tasks)]

            for project, tasks in selected:
                if not project_hub.enforce_constraints(project):
                    self.logger.warning(
                        "Skipping project %s due to insufficient resources", project
                    )
                    for t in tasks:
                        t["status"] = "Skipped"
                        t["next_run"] = self.compute_next_run(t)
                    continue

                task_list: List[Dict[str, Any]] = []
                if self.mode == "all":
                    task_list = tasks
                elif self.mode == "random" and tasks:
                    task_list = [random.choice(tasks)]
                elif tasks:
                    idx = self.project_indices.get(project, 0)
                    task_list = [tasks[idx % len(tasks)]]
                    self.project_indices[project] = idx + 1

                for task in task_list:
                    task["status"] = "Posting"
                    self.logger.info(
                        "Posting prompt '%s' for project %s", task["prompt"], task["project"]
                    )
                    try:
                        generate_reviews(task["prompt"], site=task.get("site"))
                    except TypeError:
                        generate_reviews(task["prompt"])
                    except Exception as exc:  # pragma: no cover - log unexpected
                        task["status"] = "Failed"
                        self.logger.error("Task failed for project %s: %s", project, exc)
                        task["next_run"] = self.compute_next_run(task)
                        continue
                    task["status"] = "Posted"
                    task["next_run"] = self.compute_next_run(task)

            self.save_schedule()
            time.sleep(self.tick_seconds)

    # -----------------------------------------------------
    def save_schedule(self) -> None:
        path = Path(self.schedule_path)
        if path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
            for project, tasks in self.project_schedules.items():
                file = path / f"{project}.json"
                file.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
        else:
            all_tasks: List[Dict[str, Any]] = []
            for project, tasks in self.project_schedules.items():
                for t in tasks:
                    t = dict(t)
                    t["project"] = project
                    all_tasks.append(t)
            path.write_text(json.dumps(all_tasks, indent=2), encoding="utf-8")

    # -----------------------------------------------------
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Return all tasks in a flattened list for UI consumption."""
        tasks: List[Dict[str, Any]] = []
        for project, plist in self.project_schedules.items():
            for t in plist:
                t = dict(t)
                t["project"] = project
                tasks.append(t)
        return tasks

