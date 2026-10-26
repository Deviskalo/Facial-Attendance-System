"""
School calendar module for managing term dates and holidays.

This module provides functionality to:
- Define academic terms with start and end dates
- Mark holidays and non-school days
- Check if a given date is a school day
- Calculate attendance periods considering holidays
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from backend import database as db


def create_term(
    name: str,
    start_date: str,
    end_date: str,
    description: Optional[str] = None
) -> dict[str, Any]:
    """
    Create a new academic term.
    
    Args:
        name: Term name (e.g., "Fall 2024", "Spring 2025")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        description: Optional description of the term
    
    Returns:
        Dictionary with term details
    """
    with db.get_db() as conn:
        cur = conn.execute(
            """INSERT INTO academic_terms (name, start_date, end_date, description)
            VALUES (?, ?, ?, ?)""",
            (name, start_date, end_date, description or "")
        )
        term_id = cur.lastrowid
    
    return {
        "id": term_id,
        "name": name,
        "start_date": start_date,
        "end_date": end_date,
        "description": description or ""
    }


def list_terms() -> list[dict[str, Any]]:
    """List all academic terms ordered by start date."""
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM academic_terms ORDER BY start_date DESC"
        ).fetchall()
    
    return [dict(row) for row in rows]


def get_active_term(target_date: Optional[str] = None) -> Optional[dict[str, Any]]:
    """
    Get the active academic term for a given date.
    
    Args:
        target_date: Date to check in YYYY-MM-DD format (defaults to today)
    
    Returns:
        Term dictionary if date falls within a term, None otherwise
    """
    check_date = target_date or date.today().isoformat()
    
    with db.get_db() as conn:
        row = conn.execute(
            """SELECT * FROM academic_terms 
            WHERE start_date <= ? AND end_date >= ?""",
            (check_date, check_date)
        ).fetchone()
    
    return dict(row) if row else None


def add_holiday(
    name: str,
    holiday_date: str,
    description: Optional[str] = None
) -> dict[str, Any]:
    """
    Add a holiday to the calendar.
    
    Args:
        name: Holiday name (e.g., "Christmas", "Spring Break")
        holiday_date: Date in YYYY-MM-DD format
        description: Optional description
    
    Returns:
        Dictionary with holiday details
    """
    with db.get_db() as conn:
        cur = conn.execute(
            """INSERT INTO holidays (name, date, description)
            VALUES (?, ?, ?)""",
            (name, holiday_date, description or "")
        )
        holiday_id = cur.lastrowid
    
    return {
        "id": holiday_id,
        "name": name,
        "date": holiday_date,
        "description": description or ""
    }


def list_holidays(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> list[dict[str, Any]]:
    """
    List holidays, optionally filtered by date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
    
    Returns:
        List of holiday dictionaries
    """
    with db.get_db() as conn:
        if start_date and end_date:
            rows = conn.execute(
                """SELECT * FROM holidays 
                WHERE date >= ? AND date <= ? 
                ORDER BY date""",
                (start_date, end_date)
            ).fetchall()
        elif start_date:
            rows = conn.execute(
                """SELECT * FROM holidays 
                WHERE date >= ? 
                ORDER BY date""",
                (start_date,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM holidays ORDER BY date"
            ).fetchall()
    
    return [dict(row) for row in rows]


def is_school_day(check_date: Optional[str] = None) -> bool:
    """
    Check if a given date is a school day.
    
    A date is considered a school day if:
    - It falls within an active academic term
    - It is not a holiday
    - It is not a weekend (Saturday/Sunday)
    
    Args:
        check_date: Date to check in YYYY-MM-DD format (defaults to today)
    
    Returns:
        True if it's a school day, False otherwise
    """
    target_date = check_date or date.today().isoformat()
    
    # Check if it's a weekend
    dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    if dt.weekday() >= 5:  # Saturday (5) or Sunday (6)
        return False
    
    # Check if it's within an active term
    term = get_active_term(target_date)
    if not term:
        return False
    
    # Check if it's a holiday
    with db.get_db() as conn:
        holiday = conn.execute(
            "SELECT * FROM holidays WHERE date = ?",
            (target_date,)
        ).fetchone()
    
    return holiday is None


def is_holiday(check_date: Optional[str] = None) -> bool:
    """
    Check if a given date is a holiday.
    
    Args:
        check_date: Date to check in YYYY-MM-DD format (defaults to today)
    
    Returns:
        True if it's a holiday, False otherwise
    """
    target_date = check_date or date.today().isoformat()
    
    with db.get_db() as conn:
        holiday = conn.execute(
            "SELECT * FROM holidays WHERE date = ?",
            (target_date,)
        ).fetchone()
    
    return holiday is not None


def get_holiday(check_date: Optional[str] = None) -> Optional[dict[str, Any]]:
    """
    Get holiday details for a given date.
    
    Args:
        check_date: Date to check in YYYY-MM-DD format (defaults to today)
    
    Returns:
        Holiday dictionary if it's a holiday, None otherwise
    """
    target_date = check_date or date.today().isoformat()
    
    with db.get_db() as conn:
        row = conn.execute(
            "SELECT * FROM holidays WHERE date = ?",
            (target_date,)
        ).fetchone()
    
    return dict(row) if row else None


def get_school_days_in_range(
    start_date: str,
    end_date: str
) -> list[str]:
    """
    Get all school days within a date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        List of date strings (YYYY-MM-DD format) that are school days
    """
    school_days = []
    current = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    while current <= end:
        if is_school_day(current.isoformat()):
            school_days.append(current.isoformat())
        current = date.fromordinal(current.toordinal() + 1)
    
    return school_days


def update_term(
    term_id: int,
    name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    description: Optional[str] = None
) -> None:
    """
    Update an academic term.
    
    Args:
        term_id: ID of the term to update
        name: New name (optional)
        start_date: New start date (optional)
        end_date: New end date (optional)
        description: New description (optional)
    """
    updates = []
    values = []
    
    if name is not None:
        updates.append("name = ?")
        values.append(name)
    if start_date is not None:
        updates.append("start_date = ?")
        values.append(start_date)
    if end_date is not None:
        updates.append("end_date = ?")
        values.append(end_date)
    if description is not None:
        updates.append("description = ?")
        values.append(description)
    
    if not updates:
        return
    
    values.append(term_id)
    
    with db.get_db() as conn:
        conn.execute(
            f"UPDATE academic_terms SET {', '.join(updates)} WHERE id = ?",
            values
        )


def delete_term(term_id: int) -> None:
    """Delete an academic term."""
    with db.get_db() as conn:
        conn.execute("DELETE FROM academic_terms WHERE id = ?", (term_id,))


def delete_holiday(holiday_id: int) -> None:
    """Delete a holiday."""
    with db.get_db() as conn:
        conn.execute("DELETE FROM holidays WHERE id = ?", (holiday_id,))
