"""SQLite database helpers for the scoreboard app."""
import os
import sqlite3
from pathlib import Path

# Default to a file next to this module; can be overridden with the
# SCOREBOARD_DB env var so docker-compose can point at a mounted volume.
DB_PATH = Path(
    os.environ.get("SCOREBOARD_DB", str(Path(__file__).parent / "scoreboard.db"))
)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # Defensive: if the DB file was wiped after import (or this is the first
    # connection ever), make sure the tables exist. Cheap thanks to IF NOT EXISTS.
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES classes (id) ON DELETE CASCADE
        );
        """
    )


def init_db() -> None:
    """Create tables if they don't exist."""
    with get_conn() as conn:
        _ensure_schema(conn)


# ---------- Class operations ----------

def list_classes() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, name FROM classes ORDER BY created_at ASC"
        ).fetchall()


def create_class(name: str) -> int:
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO classes (name) VALUES (?)", (name,))
        return cur.lastrowid


def delete_class(class_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM classes WHERE id = ?", (class_id,))


# ---------- Student operations ----------

def list_students(class_id: int) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, name, score FROM students "
            "WHERE class_id = ? ORDER BY score DESC, id ASC",
            (class_id,),
        ).fetchall()


def add_student(class_id: int, name: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO students (class_id, name) VALUES (?, ?)",
            (class_id, name),
        )
        return cur.lastrowid


def delete_student(student_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))


def rename_student(student_id: int, new_name: str) -> bool:
    """Rename a student. Returns False if the new name collides in the class."""
    new_name = new_name.strip()
    if not new_name:
        return False
    with get_conn() as conn:
        row = conn.execute(
            "SELECT class_id FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        if row is None:
            return False
        clash = conn.execute(
            "SELECT 1 FROM students WHERE class_id = ? AND name = ? AND id <> ?",
            (row["class_id"], new_name, student_id),
        ).fetchone()
        if clash:
            return False
        conn.execute(
            "UPDATE students SET name = ? WHERE id = ?", (new_name, student_id)
        )
        return True


def adjust_score(student_id: int, delta: int) -> int | None:
    """Update a student's score and return the new score."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE students SET score = score + ? WHERE id = ?",
            (delta, student_id),
        )
        row = conn.execute(
            "SELECT score FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        return row["score"] if row else None


def reset_class_scores(class_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE students SET score = 0 WHERE class_id = ?", (class_id,)
        )


# ---------- Admin / export ----------

def class_summary() -> list[sqlite3.Row]:
    """One row per class with student count and total score."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT c.id, c.name, c.created_at,
                   COUNT(s.id) AS student_count,
                   COALESCE(SUM(s.score), 0) AS total_score,
                   COALESCE(AVG(s.score), 0) AS avg_score,
                   COALESCE(MAX(s.score), 0) AS max_score
            FROM classes c
            LEFT JOIN students s ON s.class_id = c.id
            GROUP BY c.id
            ORDER BY c.created_at ASC
            """
        ).fetchall()


def export_snapshot() -> dict:
    """Full nested snapshot of all data for export."""
    with get_conn() as conn:
        classes = conn.execute(
            "SELECT id, name, created_at FROM classes ORDER BY created_at ASC"
        ).fetchall()
        students = conn.execute(
            """SELECT s.id, s.class_id, s.name, s.score, s.created_at, c.name AS class_name
               FROM students s
               JOIN classes c ON c.id = s.class_id
               ORDER BY s.class_id, s.score DESC, s.id ASC"""
        ).fetchall()
    return {
        "exported_at": _now_iso(),
        "classes": [dict(r) for r in classes],
        "students": [dict(r) for r in students],
    }


def _now_iso() -> str:
    import datetime as _dt
    return _dt.datetime.now().isoformat(timespec="seconds")