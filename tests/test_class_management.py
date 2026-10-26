import pytest

from backend import database as db


class TestClassOperations:
    """Test class creation, management, and student assignment."""
    
    def test_create_class(self, test_db_session):
        """Test creating a new class."""
        cls = db.create_class("10th Grade")
        
        assert cls["id"] > 0
        assert cls["name"] == "10th Grade"
    
    def test_create_duplicate_class(self, test_db_session):
        """Test that duplicate class names are handled gracefully."""
        db.create_class("10th Grade")
        cls2 = db.create_class("10th Grade")
        
        # Should return existing class
        assert cls2["name"] == "10th Grade"
    
    def test_list_classes(self, test_db_session):
        """Test listing all classes."""
        # Database is initialized with default classes (1st-12th Grade)
        classes = db.list_classes()
        assert len(classes) >= 12  # At least the default grades
        assert any(c["name"] == "1st Grade" for c in classes)
        assert any(c["name"] == "12th Grade" for c in classes)
    
    def test_list_classes_sorted(self, test_db_session):
        """Test that classes are sorted by grade order."""
        db.create_class("Kindergarten")
        db.create_class("Advanced Math")
        
        classes = db.list_classes()
        # Should be sorted by grade order first, then alphabetically
        # 1st, 2nd, 3rd, etc., then custom classes
        grade_names = [c["name"] for c in classes if "Grade" in c["name"]]
        assert grade_names[0] == "1st Grade"
        assert grade_names[1] == "2nd Grade"
    
    def test_update_class(self, test_db_session, sample_class):
        """Test updating a class name."""
        db.update_class(sample_class["id"], "Updated Class Name")
        
        classes = db.list_classes()
        updated = next((c for c in classes if c["id"] == sample_class["id"]), None)
        assert updated is not None
        assert updated["name"] == "Updated Class Name"
    
    def test_delete_class(self, test_db_session, sample_class):
        """Test deleting a class."""
        db.delete_class(sample_class["id"])
        
        classes = db.list_classes()
        assert not any(c["id"] == sample_class["id"] for c in classes)


class TestStudentClassAssignment:
    """Test student-to-class assignment operations."""
    
    def test_assign_student_to_class(self, test_db_session, sample_student, sample_class):
        """Test assigning a student to a class."""
        db.assign_student_to_class(sample_student["id"], sample_class["id"])
        
        classes = db.get_student_classes(sample_student["id"])
        assert len(classes) == 1
        assert classes[0]["id"] == sample_class["id"]
    
    def test_assign_student_to_multiple_classes(self, test_db_session, sample_student):
        """Test assigning a student to multiple classes."""
        class1 = db.create_class("1st Grade")
        class2 = db.create_class("2nd Grade")
        
        db.assign_student_to_classes(sample_student["id"], [class1["id"], class2["id"]])
        
        classes = db.get_student_classes(sample_student["id"])
        assert len(classes) == 2
    
    def test_set_student_classes(self, test_db_session, sample_student):
        """Test replacing all student class assignments."""
        class1 = db.create_class("1st Grade")
        class2 = db.create_class("2nd Grade")
        class3 = db.create_class("3rd Grade")
        
        # Initially assign to class1
        db.assign_student_to_class(sample_student["id"], class1["id"])
        
        # Replace with class2 and class3
        db.set_student_classes(sample_student["id"], [class2["id"], class3["id"]])
        
        classes = db.get_student_classes(sample_student["id"])
        assert len(classes) == 2
        class_ids = {c["id"] for c in classes}
        assert class1["id"] not in class_ids
        assert class2["id"] in class_ids
        assert class3["id"] in class_ids
    
    def test_remove_student_from_class(self, test_db_session, sample_student, sample_class):
        """Test removing a student from a class."""
        db.assign_student_to_class(sample_student["id"], sample_class["id"])
        db.remove_student_from_class(sample_student["id"], sample_class["id"])
        
        classes = db.get_student_classes(sample_student["id"])
        assert len(classes) == 0
    
    def test_get_students_in_class(self, test_db_session, sample_class):
        """Test retrieving all students in a class."""
        student1 = db.create_employee("STU001", "Alice", "Student", "STUDENT", 1)
        student2 = db.create_employee("STU002", "Bob", "Student", "STUDENT", 1)
        
        db.assign_student_to_class(student1["id"], sample_class["id"])
        db.assign_student_to_class(student2["id"], sample_class["id"])
        
        students = db.get_students_in_class(sample_class["id"])
        assert len(students) == 2
        names = {s["name"] for s in students}
        assert "Alice" in names
        assert "Bob" in names


class TestTeacherClassSponsorship:
    """Test teacher/staff class sponsorship operations."""
    
    def test_set_teacher_classes(self, test_db_session):
        """Test assigning a teacher to multiple classes."""
        teacher = db.create_employee("TEA001", "Prof. Smith", "Math", "TEACHER", 1)
        class1 = db.create_class("1st Grade")
        class2 = db.create_class("2nd Grade")
        
        db.set_teacher_classes(teacher["id"], [class1["id"], class2["id"]])
        
        classes = db.get_teacher_classes(teacher["id"])
        assert len(classes) == 2
    
    def test_get_teacher_classes(self, test_db_session):
        """Test retrieving classes sponsored by a teacher."""
        teacher = db.create_employee("TEA001", "Prof. Smith", "Math", "TEACHER", 1)
        class1 = db.create_class("1st Grade")
        
        db.set_teacher_classes(teacher["id"], [class1["id"]])
        
        classes = db.get_teacher_classes(teacher["id"])
        assert len(classes) == 1
        assert classes[0]["id"] == class1["id"]
    
    def test_get_class_sponsors(self, test_db_session, sample_class):
        """Test retrieving sponsors for a class."""
        teacher1 = db.create_employee("TEA001", "Prof. Smith", "Math", "TEACHER", 1)
        teacher2 = db.create_employee("TEA002", "Prof. Johnson", "Science", "TEACHER", 1)
        
        db.set_class_sponsors(sample_class["id"], [teacher1["id"], teacher2["id"]])
        
        sponsors = db.get_class_sponsors(sample_class["id"])
        assert len(sponsors) == 2
        names = {s["name"] for s in sponsors}
        assert "Prof. Smith" in names
        assert "Prof. Johnson" in names
    
    def test_list_class_sponsor_candidates(self, test_db_session):
        """Test listing eligible class sponsors."""
        teacher = db.create_employee("TEA001", "Prof. Smith", "Math", "TEACHER", 1)
        staff = db.create_employee("STA001", "Admin", "Office", "STAFF", 1)
        student = db.create_employee("STU001", "Alice", "Student", "STUDENT", 1)
        
        candidates = db.list_class_sponsor_candidates()
        candidate_ids = {c["id"] for c in candidates}
        
        assert teacher["id"] in candidate_ids
        assert staff["id"] in candidate_ids
        assert student["id"] not in candidate_ids  # Students cannot be sponsors


class TestClassAttendance:
    """Test class-level attendance summaries."""
    
    def test_query_daily_class_summary(self, test_db_session):
        """Test daily attendance summary by class."""
        class1 = db.create_class("1st Grade")
        class2 = db.create_class("2nd Grade")
        
        student1 = db.create_employee("STU001", "Alice", "Student", "STUDENT", 1)
        student2 = db.create_employee("STU002", "Bob", "Student", "STUDENT", 1)
        student3 = db.create_employee("STU003", "Charlie", "Student", "STUDENT", 1)
        
        db.assign_student_to_class(student1["id"], class1["id"])
        db.assign_student_to_class(student2["id"], class1["id"])
        db.assign_student_to_class(student3["id"], class2["id"])
        
        # Mark attendance
        db.insert_log(student1["id"], "CHECK_IN", "ON_TIME")
        db.insert_log(student2["id"], "CHECK_IN", "LATE")
        
        summary = db.query_daily_class_summary()
        
        class1_summary = next((s for s in summary if s["class_name"] == "1st Grade"), None)
        assert class1_summary is not None
        assert class1_summary["enrolled"] == 2
        assert class1_summary["present"] == 2
        assert class1_summary["late"] == 1
    
    def test_query_student_attendance_metrics(self, test_db_session):
        """Test student-specific attendance metrics via dashboard_metrics."""
        db.create_employee("STU001", "Alice", "Student", "STUDENT", 1)
        db.create_employee("STU002", "Bob", "Student", "STUDENT", 1)
        
        db.insert_log("STU001", "CHECK_IN", "ON_TIME")
        
        metrics = db.dashboard_metrics()
        
        assert metrics["enrolled"] == 2
        assert metrics["present"] == 1
        assert metrics["absent"] == 1
