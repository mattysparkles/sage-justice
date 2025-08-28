import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.log_manager import LogManager


def test_per_project_limit(tmp_path):
    log_dir = tmp_path / "logs"
    mgr = LogManager(base_path=str(log_dir), max_size_per_project=20, max_size_overall=100)
    for i in range(10):
        mgr.add("proj1", "x" * 5)
    proj_file = log_dir / "proj1.log"
    assert proj_file.stat().st_size <= 20


def test_global_limit(tmp_path):
    log_dir = tmp_path / "logs"
    mgr = LogManager(base_path=str(log_dir), max_size_per_project=50, max_size_overall=60)
    mgr.add("a", "a" * 40)
    mgr.add("b", "b" * 40)
    # One of the files should be removed to satisfy global limit
    files = list(log_dir.glob("*.log"))
    assert len(files) == 1
