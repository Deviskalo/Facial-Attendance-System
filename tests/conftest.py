import pytest
import sqlite3
import tempfile
from pathlib import Path
from typing import Generator

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import database as db
from backend.config import DB_PATH


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def test_db(temp_db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Create a test database connection with a temporary file."""
    # Override the DB_PATH for this test
    original_db_path = DB_PATH
    db.DB_PATH = str(temp_db_path)
    
    # Initialize the test database
    db.init_db()
    
    # Get a connection
    conn = db.connect()
    
    yield conn
    
    # Cleanup
    conn.close()
    db.DB_PATH = original_db_path


@pytest.fixture
def test_db_session(test_db: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    """Create a test database session with automatic rollback."""
    conn = test_db
    conn.execute("BEGIN TRANSACTION")
    
    yield conn
    
    conn.rollback()


@pytest.fixture
def sample_employee(test_db: sqlite3.Connection) -> dict:
    """Create a sample employee for testing."""
    emp = db.create_employee(
        emp_id="TEST001",
        name="Test User",
        department="Test Department",
        role="EMPLOYEE",
        consent_given=1
    )
    return emp


@pytest.fixture
def sample_student(test_db: sqlite3.Connection) -> dict:
    """Create a sample student for testing."""
    student = db.create_employee(
        emp_id="STU001",
        name="Test Student",
        department="Student",
        role="STUDENT",
        consent_given=1
    )
    return student


@pytest.fixture
def sample_class(test_db: sqlite3.Connection) -> dict:
    """Create a sample class for testing."""
    cls = db.create_class("Test Class")
    return cls
