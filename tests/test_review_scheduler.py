import json
import time
from datetime import datetime
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("schedule_engine", ROOT / "scheduler" / "schedule_engine.py")
schedule_engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schedule_engine)
ReviewScheduler = schedule_engine.ReviewScheduler


class Dummy:
    calls = []

    @staticmethod
    def generate(prompt, site=None):
        Dummy.calls.append((prompt, site))


def test_scheduler_rotate_mode(tmp_path, monkeypatch):
    schedule_path = tmp_path / "schedule.json"
    # Prepare schedule with two tasks due now
    now = datetime.now().isoformat()
    schedule = [
        {"prompt": "A", "project": "p", "days": [datetime.now().weekday()], "hours": [datetime.now().hour], "offset": 0, "next_run": now, "status": "Queued"},
        {"prompt": "B", "project": "p", "days": [datetime.now().weekday()], "hours": [datetime.now().hour], "offset": 0, "next_run": now, "status": "Queued"},
    ]
    schedule_path.write_text(json.dumps(schedule))
    monkeypatch.setattr(schedule_engine, "generate_reviews", Dummy.generate)
    scheduler = ReviewScheduler(schedule_path=str(schedule_path), mode="rotate", tick_seconds=0.01)
    scheduler.start()
    time.sleep(0.05)
    scheduler.stop()
    assert Dummy.calls[0][0] == "A"
    assert Dummy.calls[1][0] == "B"
