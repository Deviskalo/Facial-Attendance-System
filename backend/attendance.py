from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from backend.database import get_all_settings, insert_log, last_log_for_employee


def _parse_dt(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(value)


def classify_punctuality(now: Optional[datetime] = None) -> str:
    now = now or datetime.now()
    settings = get_all_settings()
    start_raw = settings.get("office_start_time", "09:00")
    try:
        hour, minute = [int(p) for p in start_raw.split(":")[:2]]
    except ValueError:
        hour, minute = 9, 0
    try:
        margin = int(settings.get("late_margin_minutes", "15"))
    except ValueError:
        margin = 15
    threshold = datetime.combine(now.date(), datetime.min.time()).replace(
        hour=hour, minute=minute
    ) + timedelta(minutes=margin)
    return "ON_TIME" if now <= threshold else "LATE"


def evaluate_recognition(
    employee_id: str, confidence: Optional[float] = None
) -> dict[str, Any]:
    settings = get_all_settings()
    try:
        cooldown = int(settings.get("detection_cooldown_seconds", "60"))
    except ValueError:
        cooldown = 60
    try:
        checkout_gap = int(settings.get("checkout_gap_minutes", "120"))
    except ValueError:
        checkout_gap = 120

    now = datetime.now()
    last = last_log_for_employee(employee_id)
    if last:
        last_dt = _parse_dt(str(last["timestamp"]))
        elapsed = (now - last_dt).total_seconds()
        if elapsed < cooldown:
            return {
                "action": "ALREADY_MARKED",
                "logged": False,
                "event_type": last["event_type"],
                "status": last["status"],
                "message": "Already marked",
            }
        if last["event_type"] == "CHECK_IN" and elapsed >= checkout_gap * 60:
            record = insert_log(employee_id, "CHECK_OUT", "ON_TIME", confidence)
            return {
                "action": "CHECK_OUT",
                "logged": True,
                "event_type": "CHECK_OUT",
                "status": "ON_TIME",
                "record": record,
                "message": "Checked out",
            }

    status = classify_punctuality(now)
    record = insert_log(employee_id, "CHECK_IN", status, confidence)
    label = "On Time" if status == "ON_TIME" else "Late"
    return {
        "action": "CHECK_IN",
        "logged": True,
        "event_type": "CHECK_IN",
        "status": status,
        "record": record,
        "message": label,
    }
