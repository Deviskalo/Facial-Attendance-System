import pytest
from datetime import datetime

from backend import database as db


class TestEmployeeOperations:
    """Test employee creation, retrieval, and role-based operations."""
    
    def test_create_employee(self, test_db_session):
        """Test creating a new employee."""
        emp = db.create_employee(
            emp_id="EMP001",
            name="John Doe",
            department="Engineering",
            role="EMPLOYEE",
            consent_given=1
        )
        
        assert emp["id"] == "EMP001"
        assert emp["name"] == "John Doe"
        assert emp["department"] == "Engineering"
        assert emp["role"] == "EMPLOYEE"
        assert emp["consent_given"] == 1
        assert emp["is_active"] == 1
    
    def test_create_student(self, test_db_session):
        """Test creating a student."""
        student = db.create_employee(
            emp_id="STU001",
            name="Jane Smith",
            department="Student",
            role="STUDENT",
            consent_given=1
        )
        
        assert student["role"] == "STUDENT"
        assert student["department"] == "Student"
    
    def test_create_teacher(self, test_db_session):
        """Test creating a teacher."""
        teacher = db.create_employee(
            emp_id="TEA001",
            name="Prof. Johnson",
            department="Mathematics",
            role="TEACHER",
            consent_given=1
        )
        
        assert teacher["role"] == "TEACHER"
    
    def test_get_employee(self, test_db_session, sample_employee):
        """Test retrieving an employee by ID."""
        emp = db.get_employee(sample_employee["id"])
        
        assert emp is not None
        assert emp["id"] == sample_employee["id"]
        assert emp["name"] == sample_employee["name"]
    
    def test_get_nonexistent_employee(self, test_db_session):
        """Test retrieving a non-existent employee."""
        emp = db.get_employee("NONEXISTENT")
        assert emp is None
    
    def test_list_employees(self, test_db_session):
        """Test listing all employees."""
        db.create_employee("EMP001", "Alice", "HR", "EMPLOYEE", 1)
        db.create_employee("EMP002", "Bob", "IT", "EMPLOYEE", 1)
        db.create_employee("STU001", "Charlie", "Student", "STUDENT", 1)
        
        employees = db.list_employees()
        assert len(employees) == 3
    
    def test_list_employees_by_role(self, test_db_session):
        """Test filtering employees by role."""
        db.create_employee("EMP001", "Alice", "HR", "EMPLOYEE", 1)
        db.create_employee("TEA001", "Bob", "Math", "TEACHER", 1)
        db.create_employee("STU001", "Charlie", "Student", "STUDENT", 1)
        
        students = db.list_people_by_role("STUDENT")
        assert len(students) == 1
        assert students[0]["role"] == "STUDENT"
    
    def test_update_employee(self, test_db_session, sample_employee):
        """Test updating employee details."""
        db.update_employee(
            sample_employee["id"],
            name="Updated Name",
            department="Updated Department",
            role="TEACHER",
            consent_given=0
        )
        
        updated = db.get_employee(sample_employee["id"])
        assert updated["name"] == "Updated Name"
        assert updated["department"] == "Updated Department"
        assert updated["role"] == "TEACHER"
        assert updated["consent_given"] == 0
    
    def test_deactivate_employee(self, test_db_session, sample_employee):
        """Test deactivating an employee."""
        db.update_employee(sample_employee["id"], is_active=0)
        
        emp = db.get_employee(sample_employee["id"])
        assert emp["is_active"] == 0
    
    def test_activate_employee(self, test_db_session, sample_employee):
        """Test activating an employee."""
        db.update_employee(sample_employee["id"], is_active=0)
        db.update_employee(sample_employee["id"], is_active=1)
        
        emp = db.get_employee(sample_employee["id"])
        assert emp["is_active"] == 1
    
    def test_duplicate_employee_id(self, test_db_session):
        """Test that duplicate employee IDs are prevented."""
        db.create_employee("EMP001", "Alice", "HR", "EMPLOYEE", 1)
        
        with pytest.raises(Exception):  # SQLite integrity error
            db.create_employee("EMP001", "Bob", "IT", "EMPLOYEE", 1)
    
    def test_next_person_id(self, test_db_session):
        """Test auto-generation of employee IDs."""
        # Create an employee with the generated ID first
        id1 = db.next_person_id("STU")
        db.create_employee(id1, "Student1", "Student", "STUDENT", 1)
        
        # Next ID should be different
        id2 = db.next_person_id("STU")
        
        assert id1 != id2
        assert id1.startswith("STU")
        assert id2.startswith("STU")


class TestAttendanceOperations:
    """Test attendance logging and querying."""
    
    def test_log_attendance(self, test_db_session, sample_employee):
        """Test logging an attendance event."""
        log = db.insert_log(
            employee_id=sample_employee["id"],
            event_type="CHECK_IN",
            status="ON_TIME"
        )
        
        assert log["employee_id"] == sample_employee["id"]
        assert log["event_type"] == "CHECK_IN"
        assert log["status"] == "ON_TIME"
    
    def test_get_attendance_logs(self, test_db_session, sample_employee):
        """Test retrieving attendance logs for an employee."""
        db.insert_log(sample_employee["id"], "CHECK_IN", "ON_TIME")
        db.insert_log(sample_employee["id"], "CHECK_OUT", "")
        
        logs = db.get_employee_attendance(sample_employee["id"])
        assert len(logs) == 2
    
    def test_dashboard_metrics(self, test_db_session):
        """Test dashboard metrics calculation."""
        db.create_employee("STU001", "Student1", "Student", "STUDENT", 1)
        db.create_employee("STU002", "Student2", "Student", "STUDENT", 1)
        
        today = datetime.now().strftime("%Y-%m-%d")
        db.insert_log("STU001", "CHECK_IN", "ON_TIME")
        
        metrics = db.dashboard_metrics()
        assert metrics["enrolled"] >= 2
        assert metrics["present"] >= 1


class TestEmbeddingOperations:
    """Test face embedding storage and retrieval."""
    
    def test_add_embedding(self, test_db_session, sample_employee):
        """Test adding a face embedding."""
        import numpy as np
        
        embedding = np.random.rand(512).astype(np.float32)
        db.add_embedding(sample_employee["id"], embedding, "front")
        
        # Embedding should be stored successfully
        assert True  # If no exception, test passes
    
    def test_get_embeddings(self, test_db_session, sample_employee):
        """Test retrieving embeddings for an employee."""
        import numpy as np
        
        embedding1 = np.random.rand(512).astype(np.float32)
        embedding2 = np.random.rand(512).astype(np.float32)
        
        db.add_embedding(sample_employee["id"], embedding1, "front")
        db.add_embedding(sample_employee["id"], embedding2, "left")
        
        embeddings = db.all_embeddings()
        # all_embeddings returns a list of (employee_id, embedding) tuples
        employee_embeddings = [emb for emp_id, emb in embeddings if emp_id == sample_employee["id"]]
        assert len(employee_embeddings) == 2


class TestSettingsOperations:
    """Test settings storage and retrieval."""
    
    def test_set_and_get_setting(self, test_db_session):
        """Test setting and retrieving a setting."""
        db.set_setting("test_key", "test_value")
        
        value = db.get_setting("test_key")
        assert value == "test_value"
    
    def test_get_all_settings(self, test_db_session):
        """Test retrieving all settings."""
        db.set_setting("key1", "value1")
        db.set_setting("key2", "value2")
        
        settings = db.get_all_settings()
        assert "key1" in settings
        assert "key2" in settings
        assert settings["key1"] == "value1"
