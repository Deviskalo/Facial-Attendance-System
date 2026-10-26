import pytest
from datetime import date, datetime, timedelta

from backend import calendar as cal


class TestAcademicTerms:
    """Test academic term management."""
    
    def test_create_term(self, test_db_session):
        """Test creating a new academic term."""
        term = cal.create_term(
            name="Fall 2024",
            start_date="2024-09-01",
            end_date="2024-12-20",
            description="Fall semester 2024"
        )
        
        assert term["id"] > 0
        assert term["name"] == "Fall 2024"
        assert term["start_date"] == "2024-09-01"
        assert term["end_date"] == "2024-12-20"
    
    def test_list_terms(self, test_db_session):
        """Test listing all academic terms."""
        cal.create_term("Fall 2024", "2024-09-01", "2024-12-20")
        cal.create_term("Spring 2025", "2025-01-05", "2025-05-30")
        
        terms = cal.list_terms()
        assert len(terms) == 2
        # Should be ordered by start date descending
        assert terms[0]["name"] == "Spring 2025"
        assert terms[1]["name"] == "Fall 2024"
    
    def test_get_active_term(self, test_db_session):
        """Test getting the active term for a specific date."""
        cal.create_term("Fall 2024", "2024-09-01", "2024-12-20")
        
        term = cal.get_active_term("2024-10-15")
        assert term is not None
        assert term["name"] == "Fall 2024"
    
    def test_get_active_term_outside_range(self, test_db_session):
        """Test that dates outside term ranges return None."""
        cal.create_term("Fall 2024", "2024-09-01", "2024-12-20")
        
        term = cal.get_active_term("2024-08-15")
        assert term is None
        
        term = cal.get_active_term("2025-01-15")
        assert term is None
    
    def test_update_term(self, test_db_session):
        """Test updating an academic term."""
        term = cal.create_term("Fall 2024", "2024-09-01", "2024-12-20")
        
        cal.update_term(term["id"], name="Fall Semester 2024")
        
        terms = cal.list_terms()
        updated = next((t for t in terms if t["id"] == term["id"]), None)
        assert updated is not None
        assert updated["name"] == "Fall Semester 2024"
    
    def test_delete_term(self, test_db_session):
        """Test deleting an academic term."""
        term = cal.create_term("Fall 2024", "2024-09-01", "2024-12-20")
        
        cal.delete_term(term["id"])
        
        terms = cal.list_terms()
        assert not any(t["id"] == term["id"] for t in terms)


class TestHolidays:
    """Test holiday management."""
    
    def test_add_holiday(self, test_db_session):
        """Test adding a holiday."""
        holiday = cal.add_holiday(
            name="Christmas",
            holiday_date="2024-12-25",
            description="Christmas Day"
        )
        
        assert holiday["id"] > 0
        assert holiday["name"] == "Christmas"
        assert holiday["date"] == "2024-12-25"
    
    def test_list_holidays(self, test_db_session):
        """Test listing all holidays."""
        cal.add_holiday("Christmas", "2024-12-25")
        cal.add_holiday("New Year", "2025-01-01")
        
        holidays = cal.list_holidays()
        assert len(holidays) == 2
    
    def test_list_holidays_with_date_range(self, test_db_session):
        """Test listing holidays within a date range."""
        cal.add_holiday("Christmas", "2024-12-25")
        cal.add_holiday("New Year", "2025-01-01")
        cal.add_holiday("Independence Day", "2025-07-04")
        
        holidays = cal.list_holidays("2024-12-01", "2025-01-31")
        assert len(holidays) == 2
        names = {h["name"] for h in holidays}
        assert "Christmas" in names
        assert "New Year" in names
        assert "Independence Day" not in names
    
    def test_is_holiday(self, test_db_session):
        """Test checking if a date is a holiday."""
        cal.add_holiday("Christmas", "2024-12-25")
        
        assert cal.is_holiday("2024-12-25") is True
        assert cal.is_holiday("2024-12-24") is False
    
    def test_get_holiday(self, test_db_session):
        """Test getting holiday details for a date."""
        cal.add_holiday("Christmas", "2024-12-25", description="Christmas Day")
        
        holiday = cal.get_holiday("2024-12-25")
        assert holiday is not None
        assert holiday["name"] == "Christmas"
        assert holiday["description"] == "Christmas Day"
    
    def test_delete_holiday(self, test_db_session):
        """Test deleting a holiday."""
        holiday = cal.add_holiday("Christmas", "2024-12-25")
        
        cal.delete_holiday(holiday["id"])
        
        holidays = cal.list_holidays()
        assert not any(h["id"] == holiday["id"] for h in holidays)


class TestSchoolDayLogic:
    """Test school day determination logic."""
    
    def test_is_school_day_weekend(self, test_db_session):
        """Test that weekends are not school days."""
        # Saturday
        assert cal.is_school_day("2024-09-07") is False
        # Sunday
        assert cal.is_school_day("2024-09-08") is False
    
    def test_is_school_day_no_active_term(self, test_db_session):
        """Test that dates without an active term are not school days."""
        # Monday (weekday) but no term defined
        assert cal.is_school_day("2024-09-09") is False
    
    def test_is_school_day_with_term(self, test_db_session):
        """Test that weekdays within a term are school days."""
        cal.create_term("Fall 2024", "2024-09-01", "2024-12-20")
        
        # Monday within term
        assert cal.is_school_day("2024-09-09") is True
        # Tuesday within term
        assert cal.is_school_day("2024-09-10") is True
    
    def test_is_school_day_holiday(self, test_db_session):
        """Test that holidays are not school days even within a term."""
        cal.create_term("Fall 2024", "2024-09-01", "2024-12-20")
        cal.add_holiday("Christmas", "2024-12-25")
        
        # Wednesday (weekday) but it's a holiday
        assert cal.is_school_day("2024-12-25") is False
    
    def test_get_school_days_in_range(self, test_db_session):
        """Test getting all school days within a date range."""
        cal.create_term("Fall 2024", "2024-09-01", "2024-12-20")
        
        # Get school days for a week (Monday-Friday)
        school_days = cal.get_school_days_in_range("2024-09-09", "2024-09-13")
        
        # Should be 5 weekdays (Mon-Fri)
        assert len(school_days) == 5
        assert "2024-09-09" in school_days  # Monday
        assert "2024-09-10" in school_days  # Tuesday
        assert "2024-09-11" in school_days  # Wednesday
        assert "2024-09-12" in school_days  # Thursday
        assert "2024-09-13" in school_days  # Friday
    
    def test_get_school_days_excludes_holidays(self, test_db_session):
        """Test that holidays are excluded from school days."""
        cal.create_term("Fall 2024", "2024-09-01", "2024-12-20")
        cal.add_holiday("Test Holiday", "2024-09-10")
        
        school_days = cal.get_school_days_in_range("2024-09-09", "2024-09-11")
        
        # Should only have Monday and Wednesday (Tuesday is a holiday)
        assert len(school_days) == 2
        assert "2024-09-09" in school_days
        assert "2024-09-10" not in school_days
        assert "2024-09-11" in school_days
