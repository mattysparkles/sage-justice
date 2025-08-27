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
            last_used TIMESTAMP
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
            last_tested TIMESTAMP
        )
        """
    )
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
            INSERT INTO accounts (username, password, category, health_status)
            VALUES (?, ?, ?, ?)
            """,
            (
                acc.get("username"),
                acc.get("password"),
                acc.get("platform") or acc.get("category"),
                "healthy",
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
    return dict(row) if row else None


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
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT * FROM proxies ORDER BY last_tested ASC NULLS FIRST LIMIT 1"
    ).fetchone()
    if row:
        cur.execute("UPDATE proxies SET last_tested = CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
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
    return [dict(r) for r in rows]


# Initialise database when module is imported
init_db()

__all__ = [
    "get_connection",
    "get_available_account",
    "mark_account_failed",
    "insert_job",
    "fetch_next_job",
    "update_job_status",
    "retry_failed_jobs",
    "fetch_proxy",
    "log_review",
    "get_all_accounts",
]
