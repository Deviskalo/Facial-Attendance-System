"""
CSV import validation and preview module.

This module provides functionality to:
- Validate CSV structure and data
- Preview import changes before committing
- Check for duplicates and data conflicts
- Generate detailed error reports
"""

from __future__ import annotations

import csv
import io
from typing import Any, Optional

from backend import database as db


class CSVImportResult:
    """Result of a CSV import validation/preview."""
    
    def __init__(self):
        self.valid_rows: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.duplicates_found: int = 0
        self.new_records: int = 0
        self.existing_assignments: int = 0
        self.total_rows: int = 0


def validate_student_csv(csv_content: str, class_id: int) -> CSVImportResult:
    """
    Validate a student CSV file for class import.
    
    Expected columns:
    - name (required): Full name of the student
    - department (optional): Department, defaults to "Student"
    - employee_id (optional): Custom employee ID
    - role (optional): Role, defaults to "STUDENT"
    - consent_given (optional): 0/1, defaults to 0
    
    Args:
        csv_content: CSV file content as string
        class_id: ID of the class to assign students to
    
    Returns:
        CSVImportResult with validation details
    """
    result = CSVImportResult()
    
    try:
        reader = csv.DictReader(io.StringIO(csv_content))
    except Exception as e:
        result.errors.append(f"Invalid CSV format: {e}")
        return result
    
    # Check for required columns
    if not reader.fieldnames:
        result.errors.append("CSV has no headers")
        return result
    
    if 'name' not in reader.fieldnames:
        result.errors.append("Missing required column: 'name'")
        return result
    
    # Process each row
    seen_employee_ids = set()
    seen_names = set()
    
    for i, row in enumerate(reader, start=1):
        result.total_rows += 1
        
        # Validate required fields
        name = (row.get('name') or '').strip()
        if not name:
            result.errors.append(f"Row {i}: Missing required field 'name'")
            continue
        
        # Check for duplicate names in the same import
        if name.lower() in seen_names:
            result.warnings.append(f"Row {i}: Duplicate name '{name}' in import file")
            result.duplicates_found += 1
        seen_names.add(name.lower())
        
        # Extract and validate optional fields
        dept = (row.get('department') or '').strip() or 'Student'
        emp_id = (row.get('employee_id') or '').strip()
        role = (row.get('role') or 'STUDENT').strip().upper()
        consent_str = (row.get('consent_given') or '').strip().lower()
        
        # Validate role
        valid_roles = {'STUDENT', 'TEACHER', 'EMPLOYEE', 'STAFF'}
        if role not in valid_roles:
            result.warnings.append(
                f"Row {i}: Invalid role '{role}', defaulting to STUDENT"
            )
            role = 'STUDENT'
        
        # Validate consent
        if consent_str in ('1', 'true', 'yes', 'on'):
            consent = 1
        else:
            consent = 0
        
        # Check for duplicate employee IDs in the same import
        if emp_id:
            if emp_id in seen_employee_ids:
                result.errors.append(f"Row {i}: Duplicate employee_id '{emp_id}' in import file")
                continue
            seen_employee_ids.add(emp_id)
            
            # Check if employee ID already exists in database
            existing = db.get_employee(emp_id)
            if existing:
                result.existing_assignments += 1
                result.warnings.append(
                    f"Row {i}: Employee ID '{emp_id}' already exists, will assign to class"
                )
            else:
                result.new_records += 1
        else:
            result.new_records += 1
        
        # Add to valid rows
        result.valid_rows.append({
            'row': i,
            'name': name,
            'department': dept,
            'employee_id': emp_id or '[auto-generated]',
            'role': role,
            'consent_given': consent,
            'action': 'assign_existing' if emp_id and db.get_employee(emp_id) else 'create_new'
        })
    
    return result


def preview_student_import(csv_content: str, class_id: int) -> dict[str, Any]:
    """
    Generate a preview of student import changes.
    
    Args:
        csv_content: CSV file content as string
        class_id: ID of the class to assign students to
    
    Returns:
        Dictionary with preview information including:
        - summary: Overall statistics
        - valid_rows: List of rows that will be processed
        - errors: List of validation errors
        - warnings: List of validation warnings
        - class_info: Information about the target class
    """
    validation = validate_student_csv(csv_content, class_id)
    
    # Get class information
    class_info = None
    try:
        classes = db.list_classes()
        class_info = next((c for c in classes if c['id'] == class_id), None)
    except Exception:
        pass
    
    return {
        'summary': {
            'total_rows': validation.total_rows,
            'valid_rows': len(validation.valid_rows),
            'new_records': validation.new_records,
            'existing_assignments': validation.existing_assignments,
            'errors_count': len(validation.errors),
            'warnings_count': len(validation.warnings),
            'duplicates_found': validation.duplicates_found
        },
        'valid_rows': validation.valid_rows[:50],  # Limit preview to first 50 rows
        'errors': validation.errors,
        'warnings': validation.warnings,
        'class_info': class_info,
        'can_import': len(validation.errors) == 0
    }


def validate_employee_csv(csv_content: str) -> CSVImportResult:
    """
    Validate a general employee CSV file for import.
    
    Expected columns:
    - name (required): Full name
    - department (required): Department
    - employee_id (optional): Custom employee ID
    - role (optional): Role, defaults to "EMPLOYEE"
    - consent_given (optional): 0/1, defaults to 0
    
    Args:
        csv_content: CSV file content as string
    
    Returns:
        CSVImportResult with validation details
    """
    result = CSVImportResult()
    
    try:
        reader = csv.DictReader(io.StringIO(csv_content))
    except Exception as e:
        result.errors.append(f"Invalid CSV format: {e}")
        return result
    
    if not reader.fieldnames:
        result.errors.append("CSV has no headers")
        return result
    
    if 'name' not in reader.fieldnames:
        result.errors.append("Missing required column: 'name'")
        return result
    
    if 'department' not in reader.fieldnames:
        result.errors.append("Missing required column: 'department'")
        return result
    
    seen_employee_ids = set()
    seen_names = set()
    
    for i, row in enumerate(reader, start=1):
        result.total_rows += 1
        
        name = (row.get('name') or '').strip()
        dept = (row.get('department') or '').strip()
        
        if not name:
            result.errors.append(f"Row {i}: Missing required field 'name'")
            continue
        
        if not dept:
            result.errors.append(f"Row {i}: Missing required field 'department'")
            continue
        
        if name.lower() in seen_names:
            result.warnings.append(f"Row {i}: Duplicate name '{name}' in import file")
            result.duplicates_found += 1
        seen_names.add(name.lower())
        
        emp_id = (row.get('employee_id') or '').strip()
        role = (row.get('role') or 'EMPLOYEE').strip().upper()
        consent_str = (row.get('consent_given') or '').strip().lower()
        
        valid_roles = {'STUDENT', 'TEACHER', 'EMPLOYEE', 'STAFF'}
        if role not in valid_roles:
            result.warnings.append(
                f"Row {i}: Invalid role '{role}', defaulting to EMPLOYEE"
            )
            role = 'EMPLOYEE'
        
        consent = 1 if consent_str in ('1', 'true', 'yes', 'on') else 0
        
        if emp_id:
            if emp_id in seen_employee_ids:
                result.errors.append(f"Row {i}: Duplicate employee_id '{emp_id}' in import file")
                continue
            seen_employee_ids.add(emp_id)
            
            if db.get_employee(emp_id):
                result.warnings.append(f"Row {i}: Employee ID '{emp_id}' already exists, will skip")
                continue
        
        result.new_records += 1
        result.valid_rows.append({
            'row': i,
            'name': name,
            'department': dept,
            'employee_id': emp_id or '[auto-generated]',
            'role': role,
            'consent_given': consent
        })
    
    return result
