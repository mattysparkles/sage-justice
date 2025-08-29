import os
import re
from pathlib import Path
from typing import Dict, List, Optional

class LogManager:
    """Manage per-project log files with size limits."""

    def __init__(
        self,
        base_path: str = "logs",
        max_size_per_project: int = 1024 * 1024,
        max_size_overall: int = 10 * 1024 * 1024,
    ) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.max_size_per_project = max_size_per_project
        self.max_size_overall = max_size_overall

    def _project_path(self, project: str) -> Path:
        return self.base_path / f"{project}.log"

    def add(self, project: str, message: str) -> None:
        """Append a message to a project log and enforce limits."""
        path = self._project_path(project)
        with path.open("a", encoding="utf-8") as f:
            f.write(message + "\n")
        self._enforce_limits()

    def _enforce_limits(self) -> None:
        """Trim logs that exceed per-project or overall limits."""
        # Enforce per-project limit
        for path in self.base_path.glob("*.log"):
            if path.stat().st_size > self.max_size_per_project:
                with path.open("rb") as f:
                    f.seek(-self.max_size_per_project, os.SEEK_END)
                    data = f.read()
                with path.open("wb") as f:
                    f.write(data)
        # Enforce global limit
        files = list(self.base_path.glob("*.log"))
        total = sum(p.stat().st_size for p in files)
        if total > self.max_size_overall:
            files.sort(key=lambda p: p.stat().st_mtime)
            while total > self.max_size_overall and files:
                oldest = files.pop(0)
                total -= oldest.stat().st_size
                oldest.unlink()

    def get_logs(self, project: Optional[str] = None) -> Dict[str, List[str]] | List[str]:
        """Return logs for a project or all projects."""
        if project is None:
            result: Dict[str, List[str]] = {}
            for path in self.base_path.glob("*.log"):
                result[path.stem] = path.read_text(encoding="utf-8").splitlines()
            return result
        path = self._project_path(project)
        if path.exists():
            return path.read_text(encoding="utf-8").splitlines()
        return []


_default_manager: LogManager | None = None


def _get_default_manager() -> LogManager:
    """Return a lazily initialised global LogManager instance."""

    global _default_manager
    if _default_manager is None:
        _default_manager = LogManager()
    return _default_manager


def log_post(site: str, review_text: str, success: bool, error: str | None = None) -> None:
    """Backward compatible helper used by older modules to log review posts.

    Parameters
    ----------
    site: str
        Identifier of the target site or template path.
    review_text: str
        Review content that was attempted to be posted.
    success: bool
        Whether the post succeeded.
    error: str | None
        Optional error message when the post fails.
    """

    mgr = _get_default_manager()
    safe_site = re.sub(r"[^A-Za-z0-9_-]+", "_", site)
    status = "SUCCESS" if success else "FAILURE"
    msg = f"{status}: {review_text}"
    if error:
        msg += f" | {error}"
    mgr.add(safe_site, msg)
