from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Iterable, Optional

import numpy as np

from backend.config import DB_PATH, DEFAULT_SETTINGS, ensure_directories


def _now() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def connect() -> sqlite3.Connection:
    ensure_directories()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS face_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                embedding_data BLOB NOT NULL,
                pose_label TEXT NOT NULL,
                FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS attendance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL,
                confidence_score REAL,
                FOREIGN KEY(employee_id) REFERENCES employees(id)
            );

            CREATE TABLE IF NOT EXISTS attendance_log_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                changed_at TIMESTAMP NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                attendance_log_id INTEGER,
                before_data TEXT,
                after_data TEXT,
                reason TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        audit_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(attendance_log_audit)").fetchall()
        }
        if "reason" not in audit_columns:
            conn.execute(
                "ALTER TABLE attendance_log_audit "
                "ADD COLUMN reason TEXT NOT NULL DEFAULT ''"
            )
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)",
                (key, value),
            )


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM system_settings WHERE key = ?", (key,)
        ).fetchone()
        if row:
            return row["value"]
        return default


def get_all_settings() -> dict[str, str]:
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM system_settings").fetchall()
        data = {row["key"]: row["value"] for row in rows}
    for key, value in DEFAULT_SETTINGS.items():
        data.setdefault(key, value)
    return data


def set_setting(key: str, value: str) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO system_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def set_settings(updates: dict[str, str]) -> None:
    with get_db() as conn:
        for key, value in updates.items():
            conn.execute(
                "INSERT INTO system_settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )


def next_employee_id() -> str:
    with get_db() as conn:
        rows = conn.execute("SELECT id FROM employees").fetchall()
    numbers = []
    for row in rows:
        emp_id = row["id"]
        if emp_id.startswith("EMP-"):
            suffix = emp_id.split("-", 1)[-1]
            if suffix.isdigit():
                numbers.append(int(suffix))
    nxt = max(numbers, default=100) + 1
    return f"EMP-{nxt}"


def create_employee(emp_id: str, name: str, department: str) -> dict[str, Any]:
    created = _now()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO employees (id, name, department, is_active, created_at) "
            "VALUES (?, ?, ?, 1, ?)",
            (emp_id, name, department, created),
        )
    return {
        "id": emp_id,
        "name": name,
        "department": department,
        "is_active": 1,
        "created_at": created,
    }


def list_employees(active_only: bool = False) -> list[dict[str, Any]]:
    sql = "SELECT * FROM employees"
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY created_at DESC"
    with get_db() as conn:
        return [dict(row) for row in conn.execute(sql).fetchall()]


def get_employee(emp_id: str) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM employees WHERE id = ?", (emp_id,)
        ).fetchone()
        return dict(row) if row else None


def update_employee(emp_id: str, **fields: Any) -> None:
    if not fields:
        return
    allowed = {"name", "department", "is_active"}
    parts = []
    values: list[Any] = []
    for key, value in fields.items():
        if key in allowed:
            parts.append(f"{key} = ?")
            values.append(value)
    if not parts:
        return
    values.append(emp_id)
    with get_db() as conn:
        conn.execute(
            f"UPDATE employees SET {', '.join(parts)} WHERE id = ?", values
        )


def delete_employee(emp_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM face_embeddings WHERE employee_id = ?", (emp_id,))
        conn.execute("DELETE FROM employees WHERE id = ?", (emp_id,))


def add_embedding(emp_id: str, embedding: np.ndarray, pose_label: str) -> None:
    blob = np.asarray(embedding, dtype=np.float32).tobytes()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO face_embeddings (employee_id, embedding_data, pose_label) "
            "VALUES (?, ?, ?)",
            (emp_id, blob, pose_label),
        )


def embeddings_for_employee(emp_id: str) -> list[tuple[str, np.ndarray]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT pose_label, embedding_data FROM face_embeddings WHERE employee_id = ?",
            (emp_id,),
        ).fetchall()
    out = []
    for row in rows:
        vec = np.frombuffer(row["embedding_data"], dtype=np.float32)
        out.append((row["pose_label"], vec))
    return out


def all_embeddings(exclude_employee_id: Optional[str] = None) -> list[tuple[str, np.ndarray]]:
    sql = "SELECT employee_id, embedding_data FROM face_embeddings"
    params: tuple[str, ...] = ()
    if exclude_employee_id:
        sql += " WHERE employee_id != ?"
        params = (exclude_employee_id,)
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        (row["employee_id"], np.frombuffer(row["embedding_data"], dtype=np.float32))
        for row in rows
    ]


def group_embeddings_by_employee(active_only: bool = True) -> dict[str, list[np.ndarray]]:
    sql = (
        "SELECT e.id AS employee_id, f.embedding_data "
        "FROM face_embeddings f "
        "JOIN employees e ON e.id = f.employee_id"
    )
    if active_only:
        sql += " WHERE e.is_active = 1"
    grouped: dict[str, list[np.ndarray]] = {}
    with get_db() as conn:
        for row in conn.execute(sql).fetchall():
            vec = np.frombuffer(row["embedding_data"], dtype=np.float32)
            grouped.setdefault(row["employee_id"], []).append(vec)
    return grouped


def insert_log(
    employee_id: str,
    event_type: str,
    status: str,
    confidence_score: Optional[float] = None,
    timestamp: Optional[str] = None,
) -> dict[str, Any]:
    ts = timestamp or _now()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO attendance_logs "
            "(employee_id, timestamp, event_type, status, confidence_score) "
            "VALUES (?, ?, ?, ?, ?)",
            (employee_id, ts, event_type, status, confidence_score),
        )
        log_id = cur.lastrowid
    return {
        "id": log_id,
        "employee_id": employee_id,
        "timestamp": ts,
        "event_type": event_type,
        "status": status,
        "confidence_score": confidence_score,
    }


def last_log_for_employee(employee_id: str) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM attendance_logs WHERE employee_id = ? "
            "ORDER BY timestamp DESC, id DESC LIMIT 1",
            (employee_id,),
        ).fetchone()
        return dict(row) if row else None


def get_log(log_id: int) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM attendance_logs WHERE id = ?", (log_id,)
        ).fetchone()
    return dict(row) if row else None


def update_log(log_id: int, reason: str, **fields: Any) -> None:
    allowed = {"timestamp", "event_type", "status"}
    changes = {key: value for key, value in fields.items() if key in allowed}
    if not changes:
        return
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM attendance_logs WHERE id = ?", (log_id,)
        ).fetchone()
        if not row:
            return
        before = dict(row)
        changed = {
            key: value for key, value in changes.items() if before[key] != value
        }
        if not changed:
            return
        assignments = ", ".join(f"{key} = ?" for key in changed)
        conn.execute(
            f"UPDATE attendance_logs SET {assignments} WHERE id = ?",
            [*changed.values(), log_id],
        )
        after = {**before, **changed}
        _insert_log_audit(
            conn,
            "edit",
            before["employee_id"],
            log_id,
            before,
            after,
            reason,
        )


def _insert_log_audit(
    conn: sqlite3.Connection,
    action: str,
    employee_id: str,
    log_id: Optional[int],
    before: Optional[dict[str, Any]],
    after: Optional[dict[str, Any]],
    reason: str,
) -> None:
    conn.execute(
        "INSERT INTO attendance_log_audit "
        "(changed_at, actor, action, employee_id, attendance_log_id, before_data, after_data, reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            _now(),
            "admin",
            action,
            employee_id,
            log_id,
            json.dumps(before, sort_keys=True) if before is not None else None,
            json.dumps(after, sort_keys=True) if after is not None else None,
            reason,
        ),
    )


def insert_manual_log(
    employee_id: str,
    event_type: str,
    status: str,
    reason: str,
    timestamp: Optional[str] = None,
) -> dict[str, Any]:
    ts = timestamp or _now()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO attendance_logs "
            "(employee_id, timestamp, event_type, status, confidence_score) "
            "VALUES (?, ?, ?, ?, NULL)",
            (employee_id, ts, event_type, status),
        )
        record = {
            "id": cur.lastrowid,
            "employee_id": employee_id,
            "timestamp": ts,
            "event_type": event_type,
            "status": status,
            "confidence_score": None,
        }
        _insert_log_audit(
            conn, "manual_present", employee_id, cur.lastrowid, None, record, reason
        )
    return record


def delete_logs_for_employee_on_date(employee_id: str, day: str, reason: str) -> None:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM attendance_logs WHERE employee_id = ? AND timestamp LIKE ?",
            (employee_id, f"{day}%"),
        ).fetchall()
        for row in rows:
            before = dict(row)
            _insert_log_audit(
                conn,
                "manual_absence",
                employee_id,
                before["id"],
                before,
                None,
                reason,
            )
        if not rows:
            _insert_log_audit(
                conn, "manual_absence", employee_id, None, None, None, reason
            )
        conn.execute(
            "DELETE FROM attendance_logs WHERE employee_id = ? AND timestamp LIKE ?",
            (employee_id, f"{day}%"),
        )


def query_log_audit(limit: Optional[int] = 100) -> list[dict[str, Any]]:
    with get_db() as conn:
        sql = (
            "SELECT a.*, e.name, e.department "
            "FROM attendance_log_audit a "
            "LEFT JOIN employees e ON e.id = a.employee_id "
            "ORDER BY a.id DESC"
        )
        if limit is None:
            rows = conn.execute(sql).fetchall()
        else:
            rows = conn.execute(sql + " LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def query_daily_department_summary(day: Optional[str] = None) -> list[dict[str, Any]]:
    selected_day = day or datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT e.department, "
            "COUNT(DISTINCT e.id) AS enrolled, "
            "COUNT(DISTINCT CASE WHEN l.event_type = 'CHECK_IN' THEN e.id END) AS present, "
            "COUNT(DISTINCT CASE WHEN l.event_type = 'CHECK_IN' AND l.status = 'LATE' "
            "THEN e.id END) AS late "
            "FROM employees e "
            "LEFT JOIN attendance_logs l ON l.employee_id = e.id "
            "AND l.timestamp >= ? AND l.timestamp < date(?, '+1 day') "
            "WHERE e.is_active = 1 "
            "GROUP BY e.department ORDER BY e.department",
            (selected_day, selected_day),
        ).fetchall()
    summary = []
    for row in rows:
        department_row = dict(row)
        department_row["absent"] = department_row["enrolled"] - department_row["present"]
        summary.append(department_row)
    return summary


def query_logs(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
) -> list[dict[str, Any]]:
    sql = (
        "SELECT l.*, e.name, e.department "
        "FROM attendance_logs l "
        "JOIN employees e ON e.id = l.employee_id "
        "WHERE 1=1"
    )
    params: list[Any] = []
    if start_date:
        sql += " AND l.timestamp >= ?"
        params.append(f"{start_date} 00:00:00")
    if end_date:
        sql += " AND l.timestamp <= ?"
        params.append(f"{end_date} 23:59:59")
    if department:
        sql += " AND e.department = ?"
        params.append(department)
    if status:
        sql += " AND l.status = ?"
        params.append(status)
    sql += " ORDER BY l.timestamp DESC, l.id DESC"
    with get_db() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def departments() -> list[str]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT department FROM employees ORDER BY department"
        ).fetchall()
    return [row["department"] for row in rows]


def dashboard_metrics(day: Optional[str] = None) -> dict[str, int]:
    day = day or datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        enrolled = conn.execute(
            "SELECT COUNT(*) AS n FROM employees WHERE is_active = 1"
        ).fetchone()["n"]
        present_rows = conn.execute(
            "SELECT DISTINCT employee_id FROM attendance_logs "
            "WHERE timestamp LIKE ? AND event_type = 'CHECK_IN'",
            (f"{day}%",),
        ).fetchall()
        late_rows = conn.execute(
            "SELECT DISTINCT employee_id FROM attendance_logs "
            "WHERE timestamp LIKE ? AND status = 'LATE'",
            (f"{day}%",),
        ).fetchall()
    present = len(present_rows)
    late = len(late_rows)
    absent = max(enrolled - present, 0)
    return {
        "enrolled": enrolled,
        "present": present,
        "late": late,
        "absent": absent,
    }


def present_employee_ids(day: Optional[str] = None) -> set[str]:
    day = day or datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT employee_id FROM attendance_logs "
            "WHERE timestamp LIKE ? AND event_type = 'CHECK_IN'",
            (f"{day}%",),
        ).fetchall()
    return {row["employee_id"] for row in rows}


def serialize_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]
