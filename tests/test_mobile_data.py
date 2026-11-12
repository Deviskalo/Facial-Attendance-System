from backend import database as db


def test_mobile_people_pagination_search_and_class_filter(test_db):
    first = db.create_employee("STU-101", "Avery Student", "Grade 8", "STUDENT", 1)
    db.create_employee("STU-102", "Jordan Student", "Grade 8", "STUDENT", 1)
    db.create_employee("TCH-101", "Morgan Teacher", "Grade 8", "TEACHER", 1)
    class_record = db.create_class("8th Grade")
    db.assign_student_to_class(first["id"], class_record["id"])
    db.assign_student_to_class("STU-102", class_record["id"])
    db.set_teacher_classes("TCH-101", [class_record["id"]])

    people, total = db.query_mobile_people("STUDENT", "Avery", None, True, 50, 0)
    assert total == 1
    assert people[0]["id"] == "STU-101"
    assert people[0]["classes"] == [class_record]
    assert "consent_given" not in people[0]

    people, total = db.query_mobile_people(None, None, None, True, 1, 1)
    assert total == 3
    assert len(people) == 1
    assert people[0]["name"] == "Jordan Student"

    people, total = db.query_mobile_people(
        None, None, class_record["id"], True, 50, 0
    )
    assert total == 2
    assert {person["id"] for person in people} == {"STU-101", "STU-102"}


def test_mobile_attendance_filters_and_omits_recognition_confidence(test_db):
    db.create_employee("STU-201", "Taylor Student", "Grade 9", "STUDENT", 1)
    db.create_employee("TCH-201", "Casey Teacher", "Grade 9", "TEACHER", 1)
    class_record = db.create_class("9th Grade")
    db.assign_student_to_class("STU-201", class_record["id"])
    db.insert_log(
        "STU-201",
        "CHECK_IN",
        "LATE",
        confidence_score=0.93,
        timestamp="2026-11-11 09:20:00",
    )
    db.insert_log(
        "TCH-201",
        "CHECK_IN",
        "ON_TIME",
        timestamp="2026-11-11 08:40:00",
    )
    db.insert_log(
        "STU-201",
        "CHECK_OUT",
        "ON_TIME",
        timestamp="2026-11-10 15:00:00",
    )

    records, total = db.query_mobile_attendance(
        "2026-11-11",
        "2026-11-11",
        None,
        "STUDENT",
        "CHECK_IN",
        "LATE",
        class_record["id"],
        50,
        0,
    )
    assert total == 1
    assert records[0]["employee_id"] == "STU-201"
    assert records[0]["status"] == "LATE"
    assert "confidence_score" not in records[0]

    records, total = db.query_mobile_attendance(
        None, None, None, None, None, None, None, 1, 1
    )
    assert total == 3
    assert len(records) == 1
