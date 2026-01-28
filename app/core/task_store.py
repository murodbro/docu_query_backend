"""SQLite-based task storage for multi-worker compatibility."""

import sqlite3

import os
from datetime import datetime
from typing import Dict, Optional
from contextlib import contextmanager

from app.core.schemas import TaskStatus


DB_PATH = os.getenv("TASK_DB_PATH", "./task_store.db")


def _get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initialize the database and create tables."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                failed_at TEXT,
                chunks INTEGER,
                pages INTEGER,
                error TEXT,
                ok INTEGER DEFAULT 1
            )
        """)


def create_task(task_id: str, filename: str) -> Dict:
    """Create a new task record."""
    created_at = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO tasks (task_id, status, filename, created_at, ok)
            VALUES (?, ?, ?, ?, 1)
            """,
            (task_id, TaskStatus.PROCESSING.value, filename, created_at),
        )
    return {
        "status": TaskStatus.PROCESSING,
        "filename": filename,
        "created_at": created_at,
    }


def get_task(task_id: str) -> Optional[Dict]:
    """Get task status by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()

        if not row:
            return None

        result = {
            "status": row["status"],
            "filename": row["filename"],
            "created_at": row["created_at"],
        }

        if row["ok"] is not None:
            result["ok"] = bool(row["ok"])
        if row["completed_at"]:
            result["completed_at"] = row["completed_at"]
        if row["failed_at"]:
            result["failed_at"] = row["failed_at"]
        if row["chunks"] is not None:
            result["chunks"] = row["chunks"]
        if row["pages"] is not None:
            result["pages"] = row["pages"]
        if row["error"]:
            result["error"] = row["error"]

        return result


def complete_task(task_id: str, chunks: int, pages: int):
    """Mark a task as completed."""
    completed_at = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = ?, completed_at = ?, chunks = ?, pages = ?, ok = 1
            WHERE task_id = ?
            """,
            (TaskStatus.COMPLETED.value, completed_at, chunks, pages, task_id),
        )


def fail_task(task_id: str, error: str):
    """Mark a task as failed."""
    failed_at = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = ?, failed_at = ?, error = ?, ok = 0
            WHERE task_id = ?
            """,
            (TaskStatus.FAILED.value, failed_at, error, task_id),
        )


# Initialize database on module import
init_db()
