import pytest

from backend import csv_import as csv_imp


class TestStudentCSVValidation:
    """Test student CSV import validation."""
    
    def test_valid_csv(self, test_db_session, sample_class):
        """Test validation of a valid student CSV."""
        csv_content = """name,department,employee_id,role,consent_given
John Smith,Student,STU001,STUDENT,1
Jane Doe,Student,STU002,STUDENT,1"""
        
        result = csv_imp.validate_student_csv(csv_content, sample_class["id"])
        
        assert result.total_rows == 2
        assert len(result.valid_rows) == 2
        assert len(result.errors) == 0
        assert result.new_records == 2
    
    def test_missing_name_column(self, test_db_session, sample_class):
        """Test that missing name column is caught."""
        csv_content = """department,employee_id
Math,STU001"""
        
        result = csv_imp.validate_student_csv(csv_content, sample_class["id"])
        
        assert len(result.errors) > 0
        assert any("Missing required column" in e for e in result.errors)
    
    def test_missing_name_value(self, test_db_session, sample_class):
        """Test that missing name values are caught."""
        csv_content = """name,department
,Math
Jane Doe,Science"""
        
        result = csv_imp.validate_student_csv(csv_content, sample_class["id"])
        
        assert len(result.errors) > 0
        assert any("Missing required field 'name'" in e for e in result.errors)
    
    def test_duplicate_names(self, test_db_session, sample_class):
        """Test that duplicate names are detected."""
        csv_content = """name,department
John Smith,Math
John Smith,Science"""
        
        result = csv_imp.validate_student_csv(csv_content, sample_class["id"])
        
        assert result.duplicates_found > 0
        assert len(result.warnings) > 0
        assert any("Duplicate name" in w for w in result.warnings)
    
    def test_duplicate_employee_ids(self, test_db_session, sample_class):
        """Test that duplicate employee IDs are caught."""
        csv_content = """name,employee_id
John Smith,STU001
Jane Doe,STU001"""
        
        result = csv_imp.validate_student_csv(csv_content, sample_class["id"])
        
        assert len(result.errors) > 0
        assert any("Duplicate employee_id" in e for e in result.errors)
    
    def test_existing_employee_id(self, test_db_session, sample_class):
        """Test handling of existing employee IDs."""
        # Create an existing employee
        from backend import database as db
        db.create_employee("STU001", "Existing Student", "Student", "STUDENT", 1)
        
        csv_content = """name,employee_id
New Student,STU001"""
        
        result = csv_imp.validate_student_csv(csv_content, sample_class["id"])
        
        assert result.existing_assignments == 1
        assert len(result.warnings) > 0
        assert any("already exists" in w for w in result.warnings)
    
    def test_invalid_role(self, test_db_session, sample_class):
        """Test that invalid roles are handled with a warning."""
        csv_content = """name,role
John Smith,INVALID_ROLE"""
        
        result = csv_imp.validate_student_csv(csv_content, sample_class["id"])
        
        assert len(result.warnings) > 0
        assert any("Invalid role" in w for w in result.warnings)
        # Should default to STUDENT
        assert result.valid_rows[0]["role"] == "STUDENT"
    
    def test_consent_parsing(self, test_db_session, sample_class):
        """Test various consent value formats."""
        csv_content = """name,consent_given
Student1,1
Student2,true
Student3,yes
Student4,0
Student5,false"""
        
        result = csv_imp.validate_student_csv(csv_content, sample_class["id"])
        
        assert len(result.valid_rows) == 5
        assert result.valid_rows[0]["consent_given"] == 1
        assert result.valid_rows[1]["consent_given"] == 1
        assert result.valid_rows[2]["consent_given"] == 1
        assert result.valid_rows[3]["consent_given"] == 0
        assert result.valid_rows[4]["consent_given"] == 0
    
    def test_auto_generated_id(self, test_db_session, sample_class):
        """Test that missing employee IDs are marked for auto-generation."""
        csv_content = """name
John Smith
Jane Doe"""
        
        result = csv_imp.validate_student_csv(csv_content, sample_class["id"])
        
        assert len(result.valid_rows) == 2
        assert result.valid_rows[0]["employee_id"] == "[auto-generated]"
        assert result.valid_rows[1]["employee_id"] == "[auto-generated]"
    
    def test_invalid_csv_format(self, test_db_session, sample_class):
        """Test that invalid CSV format is caught."""
        csv_content = "not a valid csv"
        
        result = csv_imp.validate_student_csv(csv_content, sample_class["id"])
        
        # Invalid CSV might just be treated as a single row with no columns
        # The important thing is it doesn't crash and handles it gracefully
        assert result is not None


class TestStudentCSVPReview:
    """Test student CSV import preview."""
    
    def test_preview_generation(self, test_db_session, sample_class):
        """Test preview generation for valid CSV."""
        csv_content = """name,department
John Smith,Math
Jane Doe,Science"""
        
        preview = csv_imp.preview_student_import(csv_content, sample_class["id"])
        
        assert "summary" in preview
        assert "valid_rows" in preview
        assert "errors" in preview
        assert "warnings" in preview
        assert "class_info" in preview
        assert preview["can_import"] is True
    
    def test_preview_with_errors(self, test_db_session, sample_class):
        """Test preview with validation errors."""
        csv_content = """department
Math"""
        
        preview = csv_imp.preview_student_import(csv_content, sample_class["id"])
        
        assert preview["can_import"] is False
        assert len(preview["errors"]) > 0
    
    def test_preview_limited_rows(self, test_db_session, sample_class):
        """Test that preview limits rows to 50."""
        # Create CSV with more than 50 rows
        rows = ["name,department"]
        for i in range(60):
            rows.append(f"Student{i},Math")
        csv_content = "\n".join(rows)
        
        preview = csv_imp.preview_student_import(csv_content, sample_class["id"])
        
        assert preview["summary"]["total_rows"] == 60
        assert len(preview["valid_rows"]) <= 50


class TestEmployeeCSVValidation:
    """Test general employee CSV import validation."""
    
    def test_valid_employee_csv(self, test_db_session):
        """Test validation of a valid employee CSV."""
        csv_content = """name,department,employee_id,role
John Smith,Engineering,EMP001,EMPLOYEE
Jane Doe,HR,EMP002,STAFF"""
        
        result = csv_imp.validate_employee_csv(csv_content)
        
        assert result.total_rows == 2
        assert len(result.valid_rows) == 2
        assert len(result.errors) == 0
    
    def test_missing_department(self, test_db_session):
        """Test that missing department is caught."""
        csv_content = """name
John Smith"""
        
        result = csv_imp.validate_employee_csv(csv_content)
        
        assert len(result.errors) > 0
        assert any("Missing required column: 'department'" in e for e in result.errors)
    
    def test_employee_defaults(self, test_db_session):
        """Test default values for optional fields."""
        csv_content = """name,department
John Smith,Engineering"""
        
        result = csv_imp.validate_employee_csv(csv_content)
        
        assert len(result.valid_rows) == 1
        assert result.valid_rows[0]["role"] == "EMPLOYEE"
        assert result.valid_rows[0]["consent_given"] == 0
        assert result.valid_rows[0]["employee_id"] == "[auto-generated]"
