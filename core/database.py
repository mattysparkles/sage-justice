"""SQLite database utilities for the review bot system.

This module centralises all database interactions.  On import it will
initialise the database (creating tables if they do not yet exist) and
perform a one-time migration of legacy JSON files into the new database.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
import random
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Database initialisation
DB_PATH = Path(os.environ.get("REVIEWBOT_DB", "core/reviewbot.db"))


def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create required tables if they do not exist and migrate old data."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY,
            content TEXT,
            tone TEXT,
            site TEXT,
            account_id INTEGER,
            proxy_id INTEGER,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            site_name TEXT,
            review_text TEXT,
            proxy_id INTEGER,
            account_id INTEGER,
            status TEXT,
            scheduled_time TIMESTAMP,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT,
            category TEXT,
            health_status TEXT,
            last_used TIMESTAMP,
            metadata TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS account_projects (
            account_id INTEGER,
            project TEXT,
            UNIQUE(account_id, project)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS proxies (
            id INTEGER PRIMARY KEY,
            ip_address TEXT,
            port TEXT,
            region TEXT,
            status TEXT,
            last_tested TIMESTAMP,
            username TEXT,
            password TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS proxy_projects (
            proxy_id INTEGER,
            project TEXT,
            UNIQUE(proxy_id, project)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS proxy_assignments (
            proxy_id INTEGER,
            level TEXT,
            target TEXT,
            weight INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 0,
            UNIQUE(proxy_id, level, target)
        )
        """
    )
    # Add username/password columns for older databases
    try:
        cur.execute("ALTER TABLE proxies ADD COLUMN username TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE proxies ADD COLUMN password TEXT")
    except sqlite3.OperationalError:
        pass
    # Add metadata column for accounts in older databases
    try:
        cur.execute("ALTER TABLE accounts ADD COLUMN metadata TEXT")
    except sqlite3.OperationalError:
        pass
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sites (
            name TEXT PRIMARY KEY,
            category TEXT,
            template_path TEXT,
            requires_login BOOLEAN,
            captcha_type TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    _migrate_legacy_json()


# ---------------------------------------------------------------------------
# Legacy JSON migration

def _migrate_legacy_json() -> None:
    """Import data from legacy JSON files if they exist."""
    migrations = {
        Path("queue/job_queue.json"): _import_jobs,
        Path("queue/review_queue.json"): _import_jobs,
        Path("accounts/accounts.json"): _import_accounts,
        Path("proxies/proxies.json"): _import_proxies,
    }

    archive_dir = Path("archive")
    archive_dir.mkdir(exist_ok=True)

    for json_path, importer in migrations.items():
        if json_path.exists():
            try:
                with json_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                importer(data)
                archive_path = archive_dir / json_path.name
                json_path.rename(archive_path)
            except Exception:
                # If migration fails we leave the file untouched
                continue


def _import_jobs(data: Any) -> None:
    if not isinstance(data, list):
        return
    conn = get_connection()
    cur = conn.cursor()
    for job in data:
        job_id = job.get("job_id", str(uuid.uuid4()))
        scheduled = job.get("scheduled_time")
        scheduled_ts = (
            datetime.fromtimestamp(scheduled).isoformat(sep=" ")
            if isinstance(scheduled, (int, float))
            else None
        )
        cur.execute(
            """
            INSERT OR REPLACE INTO jobs
                (job_id, site_name, review_text, proxy_id, account_id, status, scheduled_time, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                job.get("site_name"),
                job.get("review_text"),
                job.get("proxy_id"),
                job.get("account_id"),
                job.get("status", "Pending"),
                scheduled_ts,
                job.get("result"),
            ),
        )
    conn.commit()
    conn.close()


def _import_accounts(data: Any) -> None:
    if not isinstance(data, list):
        return
    conn = get_connection()
    cur = conn.cursor()
    for acc in data:
        cur.execute(
            """
            INSERT INTO accounts (username, password, category, health_status, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                acc.get("username"),
                acc.get("password"),
                acc.get("platform") or acc.get("category"),
                "healthy",
                json.dumps(acc.get("metadata")) if acc.get("metadata") else None,
            ),
        )
    conn.commit()
    conn.close()


def _import_proxies(data: Any) -> None:
    if not isinstance(data, list):
        return
    conn = get_connection()
    cur = conn.cursor()
    for proxy in data:
        cur.execute(
            """
            INSERT INTO proxies (ip_address, port, region, status)
            VALUES (?, ?, ?, ?)
            """,
            (
                proxy.get("ip_address"),
                proxy.get("port"),
                proxy.get("region"),
                proxy.get("status"),
            ),
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Helper functions for application use

def get_available_account() -> Optional[Dict[str, Any]]:
    """Return the least recently used healthy account."""
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT * FROM accounts
        WHERE health_status IS NULL OR health_status != 'failed'
        ORDER BY last_used ASC NULLS FIRST
        LIMIT 1
        """
    ).fetchone()
    if row:
        cur.execute("UPDATE accounts SET last_used = CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
        conn.commit()
    conn.close()
    if not row:
        return None
    account = dict(row)
    meta = account.get("metadata")
    if meta:
        try:
            account["metadata"] = json.loads(meta)
        except json.JSONDecodeError:
            account["metadata"] = {}
    else:
        account["metadata"] = {}
    return account


def mark_account_failed(account_id: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE accounts SET health_status='failed' WHERE id=?", (account_id,))
    conn.commit()
    conn.close()


def insert_job(
    site_name: str,
    review_text: str,
    proxy_id: Optional[int] = None,
    account_id: Optional[int] = None,
    status: str = "Pending",
    scheduled_time: Optional[datetime] = None,
) -> str:
    job_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO jobs (job_id, site_name, review_text, proxy_id, account_id, status, scheduled_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            site_name,
            review_text,
            proxy_id,
            account_id,
            status,
            scheduled_time.isoformat(sep=" ") if scheduled_time else None,
        ),
    )
    conn.commit()
    conn.close()
    return job_id


def fetch_next_job() -> Optional[Dict[str, Any]]:
    """Retrieve the next pending job and mark it running."""
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        """
        SELECT * FROM jobs
        WHERE status = 'Pending'
          AND (scheduled_time IS NULL OR scheduled_time <= CURRENT_TIMESTAMP)
        ORDER BY created_at
        LIMIT 1
        """
    ).fetchone()
    if row:
        job = dict(row)
        cur.execute("UPDATE jobs SET status='Running' WHERE job_id=?", (row["job_id"],))
        conn.commit()
        job["status"] = "Running"
        conn.close()
        return job
    conn.close()
    return None


def update_job_status(job_id: str, status: str, result: Optional[str] = None) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE jobs SET status=?, result=? WHERE job_id=?",
        (status, result, job_id),
    )
    conn.commit()
    conn.close()


def retry_failed_jobs() -> None:
    conn = get_connection()
    conn.execute("UPDATE jobs SET status='Pending' WHERE status='Failed'")
    conn.commit()
    conn.close()


def fetch_proxy() -> Optional[Dict[str, Any]]:
    """Return the next proxy to use."""
    proxy = fetch_proxy_for_scope("global", None)
    if proxy:
        return proxy
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT * FROM proxies ORDER BY last_tested ASC NULLS FIRST LIMIT 1"
    ).fetchone()
    if row:
        cur.execute(
            "UPDATE proxies SET last_tested = CURRENT_TIMESTAMP WHERE id=?",
            (row["id"],),
        )
        conn.commit()
    conn.close()
    return dict(row) if row else None


def log_review(
    content: str,
    tone: Optional[str],
    site: str,
    account_id: Optional[int],
    proxy_id: Optional[int],
    status: str,
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO reviews (content, tone, site, account_id, proxy_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (content, tone, site, account_id, proxy_id, status),
    )
    conn.commit()
    conn.close()


def get_all_accounts() -> list[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM accounts").fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        meta = d.get("metadata")
        if meta:
            try:
                d["metadata"] = json.loads(meta)
            except json.JSONDecodeError:
                d["metadata"] = {}
        else:
            d["metadata"] = {}
        results.append(d)
    return results


def get_account_projects(account_id: int) -> list[str]:
    """Return list of project names associated with an account."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT project FROM account_projects WHERE account_id=?",
        (account_id,),
    ).fetchall()
    conn.close()
    return [r["project"] for r in rows]


def assign_account_to_project(account_id: int, project: str) -> None:
    """Associate an account with a project."""
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO account_projects (account_id, project) VALUES (?, ?)",
        (account_id, project),
    )
    conn.commit()
    conn.close()


def remove_account_from_project(account_id: int, project: str) -> None:
    """Remove an account's association with a project."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM account_projects WHERE account_id=? AND project=?",
        (account_id, project),
    )
    conn.commit()
    conn.close()


def get_accounts_for_project(project: str) -> list[Dict[str, Any]]:
    """Return all accounts linked to the given project."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT a.* FROM accounts a
        JOIN account_projects ap ON a.id = ap.account_id
        WHERE ap.project=?
        """,
        (project,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unassigned_accounts() -> list[Dict[str, Any]]:
    """Return accounts not linked to any project."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM accounts
        WHERE id NOT IN (SELECT account_id FROM account_projects)
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_proxy_projects(proxy_id: int) -> list[str]:
    """Return list of project names associated with a proxy."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT project FROM proxy_projects WHERE proxy_id=?",
        (proxy_id,),
    ).fetchall()
    conn.close()
    return [r["project"] for r in rows]


def assign_proxy_to_project(proxy_id: int, project: str) -> None:
    """Associate a proxy with a project."""
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO proxy_projects (proxy_id, project) VALUES (?, ?)",
        (proxy_id, project),
    )
    conn.commit()
    conn.close()


def remove_proxy_from_project(proxy_id: int, project: str) -> None:
    """Remove a proxy's association with a project."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM proxy_projects WHERE proxy_id=? AND project=?",
        (proxy_id, project),
    )
    conn.commit()
    conn.close()


def get_proxies_for_project(project: str) -> list[Dict[str, Any]]:
    """Return all proxies linked to the given project."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT p.* FROM proxies p
        JOIN proxy_projects pp ON p.id = pp.proxy_id
        WHERE pp.project=?
        """,
        (project,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def assign_proxy(
    proxy_id: int,
    level: str,
    target: str | int | None = None,
    weight: int = 1,
    priority: int = 0,
) -> None:
    """Assign a proxy to a scope with optional weighting and priority."""
    conn = get_connection()
    conn.execute(
        """
        INSERT OR REPLACE INTO proxy_assignments
            (proxy_id, level, target, weight, priority)
        VALUES (?, ?, ?, ?, ?)
        """,
        (proxy_id, level, str(target) if target is not None else None, weight, priority),
    )
    conn.commit()
    conn.close()


def remove_proxy_assignment(proxy_id: int, level: str, target: str | int | None = None) -> None:
    """Remove a proxy assignment from a scope."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM proxy_assignments WHERE proxy_id=? AND level=? AND target IS ?",
        (proxy_id, level, str(target) if target is not None else None),
    )
    conn.commit()
    conn.close()


def fetch_proxy_for_scope(level: str, target: str | int | None = None) -> Optional[Dict[str, Any]]:
    """Return a proxy assigned to the given scope respecting priority and weight."""
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT p.*, pa.weight, pa.priority
        FROM proxy_assignments pa
        JOIN proxies p ON p.id = pa.proxy_id
        WHERE pa.level=? AND (pa.target IS ?)
        """,
        (level, str(target) if target is not None else None),
    ).fetchall()
    if not rows and level != "global":
        conn.close()
        return fetch_proxy_for_scope("global", None)
    if not rows:
        conn.close()
        return None
    max_priority = max(r["priority"] for r in rows)
    candidates = [r for r in rows if r["priority"] == max_priority]
    total_weight = sum(r["weight"] for r in candidates)
    choice = random.uniform(0, total_weight)
    upto = 0.0
    selected = candidates[0]
    for r in candidates:
        upto += r["weight"]
        if choice <= upto:
            selected = r
            break
    cur.execute("UPDATE proxies SET last_tested=CURRENT_TIMESTAMP WHERE id=?", (selected["id"],))
    conn.commit()
    conn.close()
    return dict(selected)


# Additional helpers for management GUIs


def add_account(
    username: str,
    password: str,
    category: str,
    health_status: str = "healthy",
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """Insert a new account into the database and return its ID."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO accounts (username, password, category, health_status, metadata) VALUES (?, ?, ?, ?, ?)",
        (username, password, category, health_status, json.dumps(metadata) if metadata else None),
    )
    conn.commit()
    account_id = cursor.lastrowid
    conn.close()
    return account_id


def delete_account(account_id: int) -> None:
    """Remove an account from the database."""
    conn = get_connection()
    conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    conn.commit()
    conn.close()


def update_account_health(account_id: int, status: str) -> None:
    """Update an account's health status."""
    conn = get_connection()
    conn.execute("UPDATE accounts SET health_status=? WHERE id=?", (status, account_id))
    conn.commit()
    conn.close()


def get_all_proxies() -> list[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT p.*, GROUP_CONCAT(pp.project, ',') AS projects
        FROM proxies p
        LEFT JOIN proxy_projects pp ON p.id = pp.proxy_id
        GROUP BY p.id
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_proxy(
    ip_address: str,
    port: str | None,
    region: str | None = None,
    status: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO proxies (ip_address, port, region, status, username, password) VALUES (?, ?, ?, ?, ?, ?)",
        (ip_address, port, region, status, username, password),
    )
    conn.commit()
    conn.close()


def delete_proxy(proxy_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM proxies WHERE id=?", (proxy_id,))
    conn.commit()
    conn.close()


def update_proxy(proxy_id: int, status: str | None = None, region: str | None = None) -> None:
    conn = get_connection()
    cur = conn.cursor()
    fields: list[str] = []
    values: list[Any] = []
    if status is not None:
        fields.append("status=?")
        values.append(status)
    if region is not None:
        fields.append("region=?")
        values.append(region)
    if fields:
        fields.append("last_tested=CURRENT_TIMESTAMP")
        sql = f"UPDATE proxies SET {', '.join(fields)} WHERE id=?"
        values.append(proxy_id)
        cur.execute(sql, tuple(values))
        conn.commit()
    conn.close()


def job_counts() -> Dict[str, int]:
    """Return counts of jobs grouped by status."""
    conn = get_connection()
    rows = conn.execute("SELECT status, COUNT(*) AS c FROM jobs GROUP BY status").fetchall()
    conn.close()
    return {row["status"]: row["c"] for row in rows}


def count_reviews_today() -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) FROM reviews WHERE DATE(created_at) = DATE('now')"
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def accounts_status_counts() -> Dict[str, int]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT COALESCE(health_status, 'unknown') AS status, COUNT(*) AS c FROM accounts GROUP BY status"
    ).fetchall()
    conn.close()
    return {row["status"]: row["c"] for row in rows}


def proxies_status_counts() -> Dict[str, int]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT COALESCE(status, 'unknown') AS status, COUNT(*) AS c FROM proxies GROUP BY status"
    ).fetchall()
    conn.close()
    return {row["status"]: row["c"] for row in rows}


def pending_jobs_count() -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'Pending'").fetchone()
    conn.close()
    return row[0] if row else 0


def proxies_region_counts() -> Dict[str, int]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT COALESCE(region, 'unknown') AS region, COUNT(*) AS c FROM proxies GROUP BY region"
    ).fetchall()
    conn.close()
    return {row["region"]: row["c"] for row in rows}


# Initialise database when module is imported
init_db()

__all__ = [
    "get_connection",
    "get_available_account",
    "mark_account_failed",
    "add_account",
    "delete_account",
    "update_account_health",
    "insert_job",
    "fetch_next_job",
    "update_job_status",
    "retry_failed_jobs",
    "fetch_proxy",
    "get_all_proxies",
    "add_proxy",
    "delete_proxy",
    "update_proxy",
    "assign_proxy",
    "remove_proxy_assignment",
    "fetch_proxy_for_scope",
    "get_proxy_projects",
    "assign_proxy_to_project",
    "remove_proxy_from_project",
    "get_proxies_for_project",
    "log_review",
    "get_all_accounts",
    "get_account_projects",
    "assign_account_to_project",
    "remove_account_from_project",
    "get_accounts_for_project",
    "get_unassigned_accounts",
    "job_counts",
    "count_reviews_today",
    "accounts_status_counts",
    "proxies_status_counts",
    "pending_jobs_count",
    "proxies_region_counts",
]
