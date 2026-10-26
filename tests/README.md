# Test Suite

This directory contains automated tests for the School Attendance System.

## Running Tests

From the project root:

```powershell
# Run all tests
.\.venv\Scripts\python.exe -m pytest

# Run with coverage
.\.venv\Scripts\python.exe -m pytest --cov=backend --cov=frontend

# Run specific test file
.\.venv\Scripts\python.exe -m pytest tests/test_database.py

# Run specific test
.\.venv\Scripts\python.exe -m pytest tests/test_database.py::TestEmployeeOperations::test_create_employee
```

## Test Structure

- `conftest.py` - Shared fixtures and test configuration
- `test_database.py` - Database operations tests (employees, attendance, embeddings, settings)
- `test_class_management.py` - Class management tests (creation, student assignment, sponsorship)

## Fixtures

- `temp_db_path` - Creates a temporary database file
- `test_db` - Initializes a test database
- `test_db_session` - Creates a database session with automatic rollback
- `sample_employee` - Creates a sample employee for testing
- `sample_student` - Creates a sample student for testing
- `sample_class` - Creates a sample class for testing

## Adding New Tests

1. Create a new test file in the `tests/` directory
2. Name it `test_<module>.py`
3. Create test classes with names starting with `Test`
4. Create test methods with names starting with `test_`
5. Use fixtures from `conftest.py` as needed

## Test Coverage Goals

- Database operations (employees, classes, attendance)
- Role-based enrollment (students, teachers, staff, employees)
- Class management (creation, assignment, sponsorship)
- Attendance rules and validation
- CSV import validation
- School calendar integration
