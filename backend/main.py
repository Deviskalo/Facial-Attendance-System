from __future__ import annotations

import asyncio
import base64
import csv
import io
import json
import logging
import secrets
import threading
import time
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import cv2
from fastapi import (
    FastAPI,
    Form,
    File,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openpyxl import Workbook
from starlette.middleware.sessions import SessionMiddleware

from backend import database as db
from backend import backups
from backend.attendance import evaluate_recognition
from backend.auth import (
    ADMIN_PASSWORD_KEY,
    admin_password_configured,
    check_admin_password,
    is_admin,
    load_or_create_session_secret,
    require_admin_redirect,
    set_admin_password,
)
from backend.config import (
    DESKTOP_MODE,
    FACES_DIR,
    POSE_INSTRUCTIONS,
    POSE_LABELS,
    ROOT_DIR,
    ensure_directories,
)
from backend.face_engine import (
    analyze_frame,
    crop_face,
    decode_image,
    find_duplicate,
    match_embedding,
    preview_matches,
    rebuild_match_cache,
)

ensure_directories()
db.init_db()
rebuild_match_cache()

logger = logging.getLogger(__name__)
backup_operation_lock = asyncio.Lock()
_backup_export_tickets: dict[str, tuple[Path, float]] = {}
_backup_export_tickets_lock = threading.Lock()


def _backup_preferences() -> tuple[bool, int, int, str]:
    settings = db.get_all_settings()
    enabled = settings.get("automatic_backups_enabled", "true").lower() == "true"
    interval_hours = int(settings.get("backup_interval_hours", "24"))
    retention_count = int(settings.get("backup_retention_count", "14"))
    directory = settings.get("backup_directory") or str(backups.BACKUPS_DIR)
    return enabled, interval_hours, retention_count, directory


def consume_desktop_backup_export(ticket: str) -> Path:
    if not DESKTOP_MODE:
        raise RuntimeError("Desktop backup export is not available.")

    now = time.monotonic()
    with _backup_export_tickets_lock:
        expired = [
            key for key, (_, expires_at) in _backup_export_tickets.items()
            if expires_at <= now
        ]
        for key in expired:
            del _backup_export_tickets[key]
        export = _backup_export_tickets.pop(ticket, None)

    if export is None:
        raise ValueError("This backup export request has expired. Please try again.")
    archive, _ = export
    if not archive.is_file():
        raise FileNotFoundError("The backup archive is no longer available.")
    return archive


async def _automatic_backup_loop() -> None:
    while True:
        try:
            enabled, interval_hours, retention_count, directory = _backup_preferences()
            if not enabled:
                await asyncio.sleep(60)
                continue
            latest = backups.latest_backup(directory)
            due = latest is None or (
                datetime.now().timestamp() - latest.stat().st_mtime
                >= interval_hours * 60 * 60
            )
            if due:
                async with backup_operation_lock:
                    archive = await asyncio.to_thread(backups.create_backup, directory)
                    await asyncio.to_thread(
                        backups.prune_backups, directory, retention_count
                    )
                logger.info("Created automatic local backup: %s", archive)
                continue
            remaining = interval_hours * 60 * 60 - (
                datetime.now().timestamp() - latest.stat().st_mtime
            )
            await asyncio.sleep(min(60, max(1, remaining)))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Automatic local backup failed; retrying in 60 seconds.")
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("Starting automatic backups for %s.", app.title)
    backup_task = asyncio.create_task(_automatic_backup_loop())
    try:
        yield
    finally:
        backup_task.cancel()
        try:
            await backup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Face Attendance Kiosk", docs_url=None, redoc_url=None, lifespan=lifespan
)
app.add_middleware(
    SessionMiddleware,
    secret_key=load_or_create_session_secret(),
    session_cookie="kiosk_admin",
    https_only=False,
    same_site="lax",
    max_age=60 * 60 * 12,
)

templates = Jinja2Templates(directory=str(ROOT_DIR / "frontend" / "templates"))
app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "frontend" / "static")), name="static")


class ActivityHub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.recent: list[dict[str, Any]] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)
        await ws.send_json({"type": "history", "events": self.recent[-50:]})

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def broadcast(self, event: dict[str, Any]) -> None:
        event = {**event, "ts": event.get("ts") or datetime.now().isoformat(sep=" ", timespec="seconds")}
        self.recent.append(event)
        self.recent = self.recent[-200:]
        stale = []
        for client in list(self.clients):
            try:
                await client.send_json({"type": "event", "event": event})
            except Exception:
                stale.append(client)
        for client in stale:
            self.clients.discard(client)


hub = ActivityHub()
_last_unknown_broadcast = 0.0


def _render(request: Request, name: str, extra: Optional[dict[str, Any]] = None) -> HTMLResponse:
    ctx = extra or {}
    return templates.TemplateResponse(request, name, ctx)


def _deny_api(request: Request) -> Optional[JSONResponse]:
    if not is_admin(request):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return None


def _decode_data_url(image: str) -> bytes:
    if "," in image:
        image = image.split(",", 1)[1]
    return base64.b64decode(image)


def _face_payload(faces: list, color: str, extra: Optional[dict] = None) -> list[dict]:
    packed = []
    for face in faces:
        item = {"bbox": face["bbox"], "color": color, **(extra or {})}
        packed.append(item)
    return packed


def _public_settings() -> dict[str, str]:
    data = db.get_all_settings()
    data.pop(ADMIN_PASSWORD_KEY, None)
    return data


async def _require_ws_admin(ws: WebSocket) -> bool:
    try:
        admin = bool(ws.session.get("admin"))
    except Exception:
        admin = False
    if not admin:
        await ws.close(code=1008)
        return False
    return True


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    return _render(request, "public/home.html")


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request) -> HTMLResponse:
    return _render(request, "public/about.html")


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request) -> HTMLResponse:
    return _render(request, "public/privacy.html")


@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request) -> HTMLResponse:
    return _render(request, "public/terms.html")


@app.get("/download", response_class=HTMLResponse)
async def download(request: Request) -> HTMLResponse:
    return _render(request, "public/download.html")


@app.get("/kiosk", response_class=HTMLResponse)
async def kiosk(request: Request) -> HTMLResponse:
    return _render(request, "kiosk.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_home(request: Request):
    redirect = require_admin_redirect(request)
    if redirect:
        return redirect
    metrics = db.dashboard_metrics()
    return _render(
        request,
        "admin/dashboard.html",
        {
            "metrics": metrics,
            "class_summary": db.query_daily_class_summary(),
            "backup_status": backups.backup_status(
                db.get_setting("backup_directory")
            ),
            "backup_settings": _backup_preferences(),
            "active": "dashboard",
        },
    )


@app.get("/admin/setup", response_class=HTMLResponse)
async def admin_setup(request: Request):
    if admin_password_configured():
        return RedirectResponse("/admin/login", status_code=302)
    return _render(request, "admin/setup.html")


@app.post("/admin/setup")
async def admin_setup_post(request: Request, password: str = Form(...), confirm: str = Form(...)):
    if admin_password_configured():
        return RedirectResponse("/admin/login", status_code=302)
    if len(password) < 6:
        return _render(
            request,
            "admin/setup.html",
            {"error": "Password must be at least 6 characters."},
        )
    if password != confirm:
        return _render(request, "admin/setup.html", {"error": "Passwords do not match."})
    set_admin_password(password)
    request.session["admin"] = True
    return RedirectResponse("/admin", status_code=302)


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    if not admin_password_configured():
        return RedirectResponse("/admin/setup", status_code=302)
    if is_admin(request):
        return RedirectResponse("/admin", status_code=302)
    return _render(request, "admin/login.html")


@app.post("/admin/login")
async def admin_login_post(request: Request, password: str = Form(...)):
    if not check_admin_password(password):
        return _render(request, "admin/login.html", {"error": "Invalid password."})
    request.session["admin"] = True
    return RedirectResponse("/admin", status_code=302)


@app.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=302)


@app.get("/admin/people", response_class=HTMLResponse)
async def admin_people(request: Request, role: Optional[str] = None):
    redirect = require_admin_redirect(request)
    if redirect:
        return redirect
    role_filter = (role or "").strip().upper()
    role_paths = {
        "STUDENT": "Students",
        "TEACHER": "Teachers",
        "STAFF": "Staff",
        "EMPLOYEE": "Employees",
    }
    if role_filter not in role_paths:
        if role_filter:
            raise HTTPException(404, "Role directory not found.")
        return RedirectResponse("/students", status_code=307)
    return await role_directory(request, role_filter)


async def role_directory(request: Request, role_filter: str):
    redirect = require_admin_redirect(request)
    if redirect:
        return redirect
    role_titles = {
        "STUDENT": "Students",
        "TEACHER": "Teachers",
        "STAFF": "Staff",
        "EMPLOYEE": "Employees",
    }
    people = db.list_people_by_role(role_filter)
    enriched = []
    for p in people:
        classes = (
            db.get_student_classes(p["id"])
            if p["role"].upper() == "STUDENT"
            else db.get_teacher_classes(p["id"])
            if p["role"].upper() in {"TEACHER", "STAFF", "EMPLOYEE"}
            else []
        )
        p_copy = dict(p)
        p_copy["classes"] = ", ".join([c["name"] for c in classes]) if classes else ""
        enriched.append(p_copy)
    return _render(
        request,
        "admin/people.html",
        {
            "people": enriched,
            "active": "people",
            "role_filter": role_filter,
            "page_title": role_titles[role_filter],
            "nav_active": role_filter.lower(),
            "directory_path": f"/{role_filter.lower() + 's' if role_filter != 'STAFF' else 'staff'}",
        },
    )


@app.get("/students", response_class=HTMLResponse)
async def student_directory(request: Request):
    return await role_directory(request, "STUDENT")


@app.get("/teachers", response_class=HTMLResponse)
async def teacher_directory(request: Request):
    return await role_directory(request, "TEACHER")


@app.get("/staff", response_class=HTMLResponse)
async def staff_directory(request: Request):
    return await role_directory(request, "STAFF")


@app.get("/employees", response_class=HTMLResponse)
async def employee_directory(request: Request):
    return await role_directory(request, "EMPLOYEE")


@app.get("/students/add", response_class=HTMLResponse)
async def add_student(request: Request):
    return await admin_people_add(request, "STUDENT")


@app.get("/teachers/add", response_class=HTMLResponse)
async def add_teacher(request: Request):
    return await admin_people_add(request, "TEACHER")


@app.get("/staff/add", response_class=HTMLResponse)
async def add_staff(request: Request):
    return await admin_people_add(request, "STAFF")


@app.get("/employees/add", response_class=HTMLResponse)
async def add_employee(request: Request):
    return await admin_people_add(request, "EMPLOYEE")


@app.get('/admin/people/{emp_id}/edit', response_class=HTMLResponse)
async def admin_people_edit(request: Request, emp_id: str):
    redirect = require_admin_redirect(request)
    if redirect:
        return redirect
    person = db.get_employee(emp_id)
    if not person:
        raise HTTPException(404, 'Person not found.')
    classes = db.list_classes()
    role = person["role"].upper()
    assigned = [
        cls["id"]
        for cls in (
            db.get_student_classes(emp_id)
            if role == "STUDENT"
            else db.get_teacher_classes(emp_id)
            if role in {"TEACHER", "STAFF", "EMPLOYEE"}
            else []
        )
    ]
    return _render(
        request,
        'admin/people_edit.html',
        {
            'person': person,
            'classes': classes,
            'assigned_ids': assigned,
            'roles': ["STUDENT", "TEACHER", "STAFF", "EMPLOYEE"],
            'active': 'people',
            'nav_active': role.lower(),
            'directory_path': f"/{role.lower() + 's' if role != 'STAFF' else 'staff'}",
        },
    )


@app.post("/admin/people/{emp_id}/edit")
async def admin_people_edit_post(request: Request, emp_id: str):
    redirect = require_admin_redirect(request)
    if redirect:
        return redirect
    person = db.get_employee(emp_id)
    if not person:
        raise HTTPException(404, "Person not found.")
    form = await request.form()
    name = str(form.get("name") or "").strip()
    department = str(form.get("department") or "").strip()
    role = str(form.get("role") or "").strip().upper()
    if not name:
        raise HTTPException(400, "Name is required.")
    if role not in {"STUDENT", "TEACHER", "STAFF", "EMPLOYEE"}:
        raise HTTPException(400, "Choose a valid role.")
    if role != "STUDENT" and not department:
        raise HTTPException(400, "Department is required for staff and employees.")
    if role == "STUDENT" and not department:
        department = "Student"
    try:
        class_ids = [int(value) for value in form.getlist("class_ids")]
    except ValueError as exc:
        raise HTTPException(400, "Invalid class selection.") from exc
    available_class_ids = {cls["id"] for cls in db.list_classes()}
    if len(class_ids) != len(set(class_ids)) or not set(class_ids).issubset(available_class_ids):
        raise HTTPException(400, "One or more selected classes do not exist.")
    was_active = bool(person["is_active"])
    is_active = form.get("is_active") == "1"
    db.update_employee(
        emp_id,
        name=name,
        department=department,
        role=role,
        is_active=int(is_active),
        consent_given=int(form.get("consent_given") == "1"),
    )
    db.set_student_classes(emp_id, class_ids if role == "STUDENT" else [])
    db.set_teacher_classes(
        emp_id,
        class_ids if role in {"TEACHER", "STAFF", "EMPLOYEE"} else [],
    )
    if was_active != is_active:
        rebuild_match_cache()
    return RedirectResponse(f"/admin/people/{emp_id}", status_code=303)


@app.get("/admin/people/add", response_class=HTMLResponse)
async def admin_people_add(request: Request, role: str = "STUDENT"):
    redirect = require_admin_redirect(request)
    if redirect:
        return redirect
    role = role.strip().upper()
    if role not in {"STUDENT", "TEACHER", "EMPLOYEE", "STAFF"}:
        role = "STUDENT"
    return _render(
        request,
        "admin/people_add.html",
        {
            "active": "people",
            "poses": [
                {"id": pose, "label": pose.title(), "hint": POSE_INSTRUCTIONS[pose]}
                for pose in POSE_LABELS
            ],
            "next_id": db.next_employee_id(),
            "classes": db.list_classes(),
            "initial_role": role,
        },
    )


@app.get("/admin/people/{emp_id}", response_class=HTMLResponse)
async def admin_person_detail(request: Request, emp_id: str):
    redirect = require_admin_redirect(request)
    if redirect:
        return redirect
    person = db.get_employee(emp_id)
    if not person:
        raise HTTPException(404, "Person not found.")
    role = person["role"].upper()
    classes = (
        db.get_student_classes(emp_id)
        if role == "STUDENT"
        else db.get_teacher_classes(emp_id)
        if role in {"TEACHER", "STAFF", "EMPLOYEE"}
        else []
    )
    return _render(
        request,
        "admin/person_detail.html",
        {
            "person": person,
            "classes": classes,
            "attendance": db.get_employee_attendance(emp_id),
            "active": "people",
            "nav_active": role.lower(),
            "directory_path": f"/{role.lower() + 's' if role != 'STAFF' else 'staff'}",
        },
    )


@app.get("/admin/logs", response_class=HTMLResponse)
async def admin_logs(request: Request):
    redirect = require_admin_redirect(request)
    if redirect:
        return redirect
    return _render(
        request,
        "admin/logs.html",
        {"active": "logs", "departments": db.departments()},
    )


@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request):
    redirect = require_admin_redirect(request)
    if redirect:
        return redirect
    settings = _public_settings()
    return _render(request, "admin/settings.html", {"active": "settings", "settings": settings})


@app.get("/admin/classes", response_class=HTMLResponse)
async def admin_classes(request: Request):
    redirect = require_admin_redirect(request)
    if redirect:
        return redirect
    classes = db.list_classes()
    return _render(request, "admin/classes.html", {"classes": classes, "active": "classes"})


@app.post("/api/classes")
async def api_create_class(request: Request):
    if denied := _deny_api(request):
        return denied
    payload = await request.json()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "Class name is required.")
    cls = db.create_class(name)
    return cls


@app.patch("/api/classes/{class_id}")
async def api_update_class(request: Request, class_id: int):
    if denied := _deny_api(request):
        return denied
    payload = await request.json()
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "Class name is required.")
    db.update_class(class_id, name)
    return {"ok": True}


@app.delete("/api/classes/{class_id}")
async def api_delete_class(request: Request, class_id: int):
    if denied := _deny_api(request):
        return denied
    # delete class and any associations
    db.delete_class(class_id)
    return {"ok": True}


@app.get("/api/dashboard")
async def api_dashboard(request: Request):
    if denied := _deny_api(request):
        return denied
    return db.dashboard_metrics()


@app.get("/api/employees")
async def api_employees(request: Request):
    if denied := _deny_api(request):
        return denied
    return db.list_employees()


@app.patch("/api/employees/{emp_id}")
async def api_employee_update(request: Request, emp_id: str):
    if denied := _deny_api(request):
        return denied
    if not db.get_employee(emp_id):
        raise HTTPException(404, "Employee not found")
    payload = await request.json()
    fields = {}
    if "name" in payload:
        fields["name"] = str(payload["name"]).strip()
    if "department" in payload:
        fields["department"] = str(payload["department"]).strip()
    if "is_active" in payload:
        fields["is_active"] = 1 if payload["is_active"] else 0
    db.update_employee(emp_id, **fields)
    if "is_active" in fields:
        rebuild_match_cache()
    return db.get_employee(emp_id)


@app.delete("/api/employees/{emp_id}")
async def api_employee_delete(request: Request, emp_id: str):
    if denied := _deny_api(request):
        return denied
    if not db.get_employee(emp_id):
        raise HTTPException(404, "Employee not found")
    db.delete_employee(emp_id)
    face_dir = FACES_DIR / emp_id
    if face_dir.exists():
        for path in face_dir.glob("*"):
            path.unlink()
        face_dir.rmdir()
    rebuild_match_cache()
    return {"ok": True}


@app.get("/media/faces/{emp_id}/{pose}")
async def media_face(request: Request, emp_id: str, pose: str):
    redirect = require_admin_redirect(request)
    if redirect:
        raise HTTPException(401, "Unauthorized")
    path = FACES_DIR / emp_id / f"{pose}.jpg"
    if not path.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(path)


@app.get("/api/logs")
async def api_logs(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    department: Optional[str] = None,
    status_filter: Optional[str] = None,
):
    if denied := _deny_api(request):
        return denied
    return db.query_logs(start_date, end_date, department or None, status_filter or None)


@app.post("/api/logs/manual")
async def api_manual_log(request: Request):
    if denied := _deny_api(request):
        return denied
    payload = await request.json()
    emp_id = payload.get("employee_id")
    if not emp_id or not db.get_employee(emp_id):
        raise HTTPException(400, "Unknown employee")
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise HTTPException(400, "A reason is required for attendance corrections.")
    if len(reason) > 500:
        raise HTTPException(400, "Correction reason must be 500 characters or fewer.")
    action = payload.get("action")
    day = payload.get("date") or datetime.now().strftime("%Y-%m-%d")
    if action == "absent":
        db.delete_logs_for_employee_on_date(emp_id, day, reason)
        return {"ok": True, "action": "absent"}
    event_type = payload.get("event_type") or "CHECK_IN"
    status_value = payload.get("status") or "MANUAL"
    timestamp = payload.get("timestamp")
    record = db.insert_manual_log(emp_id, event_type, status_value, reason, timestamp)
    return record


@app.get('/admin/classes/{class_id}', response_class=HTMLResponse)
async def admin_class_detail(request: Request, class_id: int):
    redirect = require_admin_redirect(request)
    if redirect:
        return redirect
    cls_row = None
    for c in db.list_classes():
        if c['id'] == class_id:
            cls_row = c
            break
    if not cls_row:
        raise HTTPException(404, 'Class not found')
    students = db.get_students_in_class(class_id)
    sponsors = db.get_class_sponsors(class_id)
    sponsor_ids = {teacher["id"] for teacher in sponsors}
    sponsor_candidates = db.list_class_sponsor_candidates()
    return _render(
        request,
        'admin/class_detail.html',
        {
            'class': cls_row,
            'students': students,
            'sponsors': sponsors,
            'sponsor_candidates': sponsor_candidates,
            'sponsor_ids': sponsor_ids,
            'active': 'classes',
        },
    )


@app.put('/api/classes/{class_id}/sponsors')
async def api_set_class_sponsors(request: Request, class_id: int):
    if denied := _deny_api(request):
        return denied
    if not any(cls["id"] == class_id for cls in db.list_classes()):
        raise HTTPException(404, 'Class not found.')
    payload = await request.json()
    teacher_ids = payload.get("teacher_ids")
    if not isinstance(teacher_ids, list) or any(not isinstance(item, str) for item in teacher_ids):
        raise HTTPException(400, 'teacher_ids must be a list of employee IDs.')
    teacher_ids = list(dict.fromkeys(item.strip() for item in teacher_ids))
    eligible_ids = {teacher["id"] for teacher in db.list_class_sponsor_candidates()}
    invalid_ids = set(teacher_ids) - eligible_ids
    if invalid_ids:
        raise HTTPException(400, 'Sponsors must be active teachers, staff, or employees.')
    db.set_class_sponsors(class_id, teacher_ids)
    return {"ok": True, "sponsors": db.get_class_sponsors(class_id)}


@app.post('/admin/classes/{class_id}/import')
async def admin_class_import(request: Request, class_id: int, file: UploadFile = File(...)):
    redirect = require_admin_redirect(request)
    if redirect:
        return redirect
    # basic CSV import without images — creates employees and assigns them to this class
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except Exception:
        raise HTTPException(400, 'Could not read uploaded file as UTF-8')
    reader = csv.DictReader(io.StringIO(text))
    imported_new = 0
    assigned_existing = 0
    errors: list[str] = []
    max_rows = 2000
    for i, row in enumerate(reader, start=1):
        if i > max_rows:
            errors.append(f'Import aborted: exceeds maximum of {max_rows} rows')
            break
        name = (row.get('name') or '').strip()
        dept = (row.get('department') or '').strip() or 'Unassigned'
        emp_id = (row.get('employee_id') or '').strip()
        role = (row.get('role') or 'STUDENT').upper()
        consent = 1 if str(row.get('consent_given') or '').strip().lower() in ('1', 'true', 'yes') else 0
        if not name:
            errors.append(f'Row {i}: missing name')
            continue
        if emp_id:
            existing = db.get_employee(emp_id)
            if existing:
                try:
                    db.assign_student_to_class(emp_id, class_id)
                    assigned_existing += 1
                except Exception as exc:
                    errors.append(f'Row {i}: could not assign existing {emp_id}: {exc}')
                continue
        # create new employee with a generated ID
        if not emp_id:
            emp_id = db.next_employee_id()
        # ensure emp_id is unique (append suffix if needed)
        base = emp_id
        suffix = 1
        while db.get_employee(emp_id):
            emp_id = f"{base}-{suffix}"
            suffix += 1
        try:
            db.create_employee(emp_id, name, dept, role=role, consent_given=consent)
            db.assign_student_to_class(emp_id, class_id)
            imported_new += 1
        except Exception as exc:
            errors.append(f'Row {i}: {exc}')
    return JSONResponse({'imported_new': imported_new, 'assigned_existing': assigned_existing, 'errors': errors})


@app.post('/api/employees/{emp_id}/classes')
async def api_set_employee_classes(request: Request, emp_id: str):
    if denied := _deny_api(request):
        return denied
    if not db.get_employee(emp_id):
        raise HTTPException(404, 'Employee not found')
    payload = await request.json()
    class_ids = payload.get('class_ids') or []
    try:
        ids = [int(x) for x in class_ids]
    except Exception:
        raise HTTPException(400, 'class_ids must be a list of integers')
    db.set_student_classes(emp_id, ids)
    return {'ok': True}


@app.get("/api/logs/audit")
async def api_log_audit(request: Request):
    if denied := _deny_api(request):
        return denied
    return db.query_log_audit()


@app.get("/api/logs/audit/export")
async def api_export_log_audit(request: Request, fmt: str = "csv"):
    if denied := _deny_api(request):
        return denied
    if fmt not in {"csv", "xlsx"}:
        raise HTTPException(400, "Format must be csv or xlsx.")
    rows = db.query_log_audit(limit=None)
    headers = [
        "changed_at",
        "action",
        "employee_id",
        "name",
        "department",
        "actor",
        "reason",
        "attendance_log_id",
        "before_data",
        "after_data",
    ]
    if fmt == "xlsx":
        wb = Workbook()
        ws = wb.active
        ws.title = "Correction history"
        ws.append(headers)
        for row in rows:
            ws.append([row.get(header) for header in headers])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=attendance-corrections.xlsx"},
        )
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({header: row.get(header) for header in headers})
    data = io.BytesIO(buf.getvalue().encode("utf-8"))
    return StreamingResponse(
        data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance-corrections.csv"},
    )


@app.patch("/api/logs/{log_id}")
async def api_edit_log(request: Request, log_id: int):
    if denied := _deny_api(request):
        return denied
    payload = await request.json()
    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise HTTPException(400, "A reason is required for attendance corrections.")
    if len(reason) > 500:
        raise HTTPException(400, "Correction reason must be 500 characters or fewer.")
    fields = {}
    for key in ("timestamp", "event_type", "status"):
        if key in payload:
            fields[key] = payload[key]
    if not fields:
        raise HTTPException(400, "At least one attendance field is required.")
    if not db.get_log(log_id):
        raise HTTPException(404, "Attendance record not found.")
    db.update_log(log_id, reason=reason, **fields)
    return {"ok": True}


@app.get("/api/logs/export")
async def api_export_logs(
    request: Request,
    fmt: str = "csv",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    department: Optional[str] = None,
    status_filter: Optional[str] = None,
):
    if denied := _deny_api(request):
        return denied
    rows = db.query_logs(start_date, end_date, department or None, status_filter or None)
    headers = ["id", "employee_id", "name", "department", "timestamp", "event_type", "status", "confidence_score"]
    if fmt == "xlsx":
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance"
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h) for h in headers])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=attendance.xlsx"},
        )
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({h: row.get(h) for h in headers})
    data = io.BytesIO(buf.getvalue().encode("utf-8"))
    return StreamingResponse(
        data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance.csv"},
    )


@app.get("/api/settings")
async def api_get_settings(request: Request):
    if denied := _deny_api(request):
        return denied
    return _public_settings()


@app.post("/api/settings")
async def api_save_settings(request: Request):
    if denied := _deny_api(request):
        return denied
    payload = await request.json()
    allowed = {
        "office_start_time",
        "late_margin_minutes",
        "detection_cooldown_seconds",
        "checkout_gap_minutes",
        "matching_threshold",
        "automatic_backups_enabled",
        "backup_interval_hours",
        "backup_retention_count",
        "backup_directory",
    }
    updates = {k: str(v) for k, v in payload.items() if k in allowed}
    if "automatic_backups_enabled" in updates:
        enabled = updates["automatic_backups_enabled"].lower()
        if enabled not in {"true", "false"}:
            raise HTTPException(400, "Automatic backups must be enabled or disabled.")
        updates["automatic_backups_enabled"] = enabled
    if "backup_interval_hours" in updates:
        try:
            interval = int(updates["backup_interval_hours"])
        except ValueError as exc:
            raise HTTPException(400, "Backup interval must be a whole number of hours.") from exc
        if not 1 <= interval <= 720:
            raise HTTPException(400, "Backup interval must be between 1 and 720 hours.")
        updates["backup_interval_hours"] = str(interval)
    if "backup_retention_count" in updates:
        try:
            retention = int(updates["backup_retention_count"])
        except ValueError as exc:
            raise HTTPException(400, "Backup retention must be a whole number.") from exc
        if not 1 <= retention <= 365:
            raise HTTPException(400, "Backup retention must be between 1 and 365 archives.")
        updates["backup_retention_count"] = str(retention)
    if "backup_directory" in updates:
        directory = updates["backup_directory"].strip()
        if not directory or len(directory) > 500:
            raise HTTPException(400, "Enter a backup folder path up to 500 characters.")
        try:
            backups.resolve_backup_directory(directory).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise HTTPException(400, f"Cannot use backup folder: {exc}") from exc
        updates["backup_directory"] = directory
    db.set_settings(updates)
    return _public_settings()


@app.get("/api/backup")
async def api_backup(request: Request):
    if denied := _deny_api(request):
        return denied
    _, _, retention_count, directory = _backup_preferences()
    async with backup_operation_lock:
        archive = await asyncio.to_thread(backups.create_backup, directory)
        await asyncio.to_thread(
            backups.prune_backups, directory, retention_count
        )
    return FileResponse(
        archive,
        media_type="application/zip",
        filename=archive.name,
    )


@app.get("/api/backup/export")
async def api_backup_export(request: Request):
    if not DESKTOP_MODE:
        raise HTTPException(404, "Desktop backup export is not available.")
    if denied := _deny_api(request):
        return denied
    _, _, retention_count, directory = _backup_preferences()
    async with backup_operation_lock:
        archive = await asyncio.to_thread(backups.create_backup, directory)
        await asyncio.to_thread(
            backups.prune_backups, directory, retention_count
        )

    ticket = secrets.token_urlsafe(32)
    now = time.monotonic()
    with _backup_export_tickets_lock:
        expired = [
            key for key, (_, expires_at) in _backup_export_tickets.items()
            if expires_at <= now
        ]
        for key in expired:
            del _backup_export_tickets[key]
        _backup_export_tickets[ticket] = (archive, now + 300)
    return {"ticket": ticket, "filename": archive.name}


@app.post("/api/backup/restore")
async def api_restore_backup(request: Request, file: UploadFile = File(...)):
    if denied := _deny_api(request):
        return denied
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "Select a ZIP backup file.")
    if file.size is not None and file.size > backups.MAX_ARCHIVE_BYTES:
        raise HTTPException(413, "Backup file exceeds the 4 GiB restore limit.")
    _, _, _, directory = _backup_preferences()
    try:
        async with backup_operation_lock:
            safety_backup = await asyncio.to_thread(
                backups.restore_backup, file.file, directory
            )
    except (ValueError, zipfile.BadZipFile) as exc:
        raise HTTPException(400, str(exc)) from exc
    except OSError as exc:
        logger.exception("Could not restore the uploaded attendance backup.")
        raise HTTPException(500, f"Could not restore backup: {exc}") from exc
    except Exception as exc:
        logger.exception("Could not restore the uploaded attendance backup.")
        raise HTTPException(500, "Restore failed. The pre-restore safety backup was retained.") from exc
    finally:
        await file.close()
    return {
        "ok": True,
        "message": "Backup restored successfully.",
        "safety_backup": safety_backup.name,
    }


@app.post("/api/preview-match")
async def api_preview_match(request: Request):
    if denied := _deny_api(request):
        return denied
    payload = await request.json()
    raw = _decode_data_url(payload.get("image", ""))
    frame = decode_image(raw)
    if frame is None:
        raise HTTPException(400, "Invalid image")
    analysis = analyze_frame(frame)
    quality = analysis["quality"]
    if quality["face_count"] != 1:
        return {"quality": quality, "matches": []}
    embedding = analysis["faces"][0]["embedding"]
    matches = preview_matches(embedding)
    for item in matches:
        emp = db.get_employee(item["employee_id"])
        item["name"] = emp["name"] if emp else item["employee_id"]
    return {
        "quality": quality,
        "matches": matches,
        "threshold": float(db.get_all_settings().get("matching_threshold", "0.36")),
        "bbox": analysis["faces"][0]["bbox"],
        "frame_size": analysis["frame_size"],
    }


def _jpeg_bytes_from_ws_payload(message: Any) -> Optional[bytes]:
    if isinstance(message, bytes):
        return message
    if isinstance(message, str):
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            return None
        image = payload.get("image")
        if image:
            return _decode_data_url(image)
    return None


@app.websocket("/ws/kiosk")
async def ws_kiosk(ws: WebSocket) -> None:
    global _last_unknown_broadcast
    await ws.accept()
    try:
        while True:
            message = await ws.receive()
            if message.get("type") == "websocket.disconnect":
                break
            raw = message.get("bytes") or None
            if raw is None and message.get("text"):
                raw = _jpeg_bytes_from_ws_payload(message["text"])
            if not raw:
                continue
            frame = decode_image(raw)
            if frame is None:
                await ws.send_json({"faces": [], "error": "Could not decode frame", "toast": None})
                continue
            try:
                analysis = await asyncio.to_thread(analyze_frame, frame)
            except Exception as exc:
                await ws.send_json(
                    {
                        "faces": [],
                        "error": f"Face engine error: {exc}",
                        "toast": None,
                        "frame_size": [frame.shape[1], frame.shape[0]],
                    }
                )
                continue

            quality = analysis["quality"]
            faces = analysis["faces"]
            toast = None
            color = "yellow"
            extras: dict[str, Any] = {}

            if quality["face_count"] > 1 or (quality["face_count"] == 0 and quality["issues"]):
                payload_faces = _face_payload(
                    faces,
                    "red" if quality["face_count"] > 1 else "yellow",
                )
                if quality["face_count"] > 1 and time.time() - _last_unknown_broadcast > 5:
                    _last_unknown_broadcast = time.time()
                    await hub.broadcast(
                        {"kind": "error", "name": None, "message": "Multiple faces detected"}
                    )
                await ws.send_json(
                    {
                        "faces": payload_faces,
                        "frame_size": analysis["frame_size"],
                        "quality": quality,
                        "toast": None,
                        "error": "; ".join(quality["issues"]) if quality["face_count"] != 1 else None,
                    }
                )
                continue

            if quality["face_count"] == 1:
                face = faces[0]
                match = await asyncio.to_thread(match_embedding, face["embedding"])
                if match["matched"]:
                    color = "green"
                    employee = db.get_employee(match["employee_id"])
                    extras = {
                        "name": employee["name"] if employee else match["employee_id"],
                        "employee_id": match["employee_id"],
                        "distance": match["distance"],
                    }
                    result = await asyncio.to_thread(
                        evaluate_recognition, match["employee_id"], match["confidence"]
                    )
                    name = extras["name"]
                    if result["action"] == "ALREADY_MARKED":
                        toast = {"type": "info", "message": f"Already marked — {name}"}
                    elif result["action"] == "CHECK_OUT":
                        toast = {"type": "success", "message": f"Goodbye, {name}! Status: Checkout"}
                        await hub.broadcast(
                            {
                                "kind": "known",
                                "name": name,
                                "employee_id": match["employee_id"],
                                "message": "Checkout",
                            }
                        )
                    else:
                        label = "On Time" if result["status"] == "ON_TIME" else "Late"
                        toast = {
                            "type": "late" if result["status"] == "LATE" else "success",
                            "message": f"Welcome, {name}! Status: {label}",
                        }
                        await hub.broadcast(
                            {
                                "kind": "known",
                                "name": name,
                                "employee_id": match["employee_id"],
                                "message": f"Check-in ({label})",
                            }
                        )
                else:
                    color = "yellow"
                    extras = {"name": "Unknown", "distance": match["distance"]}
                    if time.time() - _last_unknown_broadcast > 5:
                        _last_unknown_broadcast = time.time()
                        await hub.broadcast(
                            {"kind": "unknown", "name": "Unknown", "message": "Unrecognized face"}
                        )

            await ws.send_json(
                {
                    "faces": _face_payload(
                        faces,
                        color,
                        extras,
                    ),
                    "frame_size": analysis["frame_size"],
                    "quality": quality,
                    "toast": toast,
                    "error": None,
                }
            )
    except WebSocketDisconnect:
        return


@app.websocket("/ws/activity")
async def ws_activity(ws: WebSocket) -> None:
    if not await _require_ws_admin(ws):
        return
    await hub.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(ws)


@app.websocket("/ws/enroll")
async def ws_enroll(ws: WebSocket) -> None:
    if not await _require_ws_admin(ws):
        return
    await ws.accept()
    captured: dict[str, dict[str, Any]] = {}
    try:
        while True:
            raw = await ws.receive_text()
            payload = json.loads(raw)
            action = payload.get("type") or payload.get("action")
            if action == "analyze":
                frame = decode_image(_decode_data_url(payload.get("image", "")))
                if frame is None:
                    await ws.send_json({"ok": False, "type": "analyze", "error": "Invalid image"})
                    continue
                try:
                    analysis = await asyncio.to_thread(analyze_frame, frame)
                except Exception as exc:
                    await ws.send_json({"ok": False, "type": "analyze", "error": str(exc)})
                    continue
                face_info = None
                if analysis["faces"]:
                    face_info = {
                        "bbox": analysis["faces"][0]["bbox"],
                    }
                await ws.send_json(
                    {
                        "ok": True,
                        "type": "analyze",
                        "quality": analysis["quality"],
                        "frame_size": analysis["frame_size"],
                        "face": face_info,
                        "captured": list(captured.keys()),
                    }
                )
            elif action == "capture":
                pose = payload.get("pose")
                if pose not in POSE_LABELS:
                    await ws.send_json({"ok": False, "type": "capture", "error": "Unknown pose"})
                    continue
                frame = decode_image(_decode_data_url(payload.get("image", "")))
                if frame is None:
                    await ws.send_json({"ok": False, "type": "capture", "error": "Invalid image"})
                    continue
                try:
                    analysis = await asyncio.to_thread(analyze_frame, frame)
                except Exception as exc:
                    await ws.send_json({"ok": False, "type": "capture", "error": str(exc)})
                    continue
                quality = analysis["quality"]
                if not quality["ok"] or quality["face_count"] != 1:
                    await ws.send_json(
                        {
                            "ok": False,
                            "type": "capture",
                            "error": "; ".join(quality["issues"]) or "Quality check failed",
                            "quality": quality,
                        }
                    )
                    continue
                embedding = analysis["faces"][0]["embedding"]
                duplicate = await asyncio.to_thread(find_duplicate, embedding)
                if duplicate:
                    emp = db.get_employee(duplicate)
                    label = emp["name"] if emp else duplicate
                    await ws.send_json(
                        {
                            "ok": False,
                            "type": "capture",
                            "error": f"This face already matches enrolled user {label} ({duplicate}).",
                            "duplicate_id": duplicate,
                        }
                    )
                    continue
                crop = crop_face(frame, analysis["faces"][0]["bbox"])
                ok, buf = cv2.imencode(".jpg", crop)
                if not ok:
                    await ws.send_json(
                        {"ok": False, "type": "capture", "error": "Could not encode crop"}
                    )
                    continue
                captured[pose] = {
                    "embedding": embedding,
                    "jpeg": buf.tobytes(),
                }
                await ws.send_json(
                    {
                        "ok": True,
                        "type": "capture",
                        "pose": pose,
                        "captured": list(captured.keys()),
                    }
                )
            elif action == "finalize":
                missing = [p for p in POSE_LABELS if p not in captured]
                if missing:
                    await ws.send_json(
                        {
                            "ok": False,
                            "error": f"Missing poses: {', '.join(missing)}",
                            "captured": list(captured.keys()),
                        }
                    )
                    continue
                name = str(payload.get("name") or "").strip()
                role = str(payload.get("role") or "STUDENT").strip().upper()
                if role not in {"STUDENT", "TEACHER", "EMPLOYEE", "STAFF"}:
                    await ws.send_json({"ok": False, "error": "Choose Student, Teacher, Employee, or Staff."})
                    continue
                department = str(payload.get("department") or "").strip()
                if role == "STUDENT":
                    department = department or "Student"
                elif not department:
                    await ws.send_json({"ok": False, "error": "Department is required for employees and staff."})
                    continue
                emp_id = str(payload.get("employee_id") or "").strip()
                if not emp_id:
                    prefix = {"STUDENT": "STU", "TEACHER": "TEACHER", "EMPLOYEE": "EMP", "STAFF": "STAFF"}[role]
                    emp_id = db.next_person_id(prefix)
                try:
                    consent = 1 if int(payload.get("consent_given") or 0) else 0
                    requested_class_ids = payload.get("class_ids") or []
                    if not isinstance(requested_class_ids, list):
                        raise ValueError
                    class_ids = [int(class_id) for class_id in requested_class_ids]
                except (TypeError, ValueError):
                    await ws.send_json({"ok": False, "error": "Invalid consent or class selection."})
                    continue
                if role != "STUDENT" and class_ids:
                    await ws.send_json({"ok": False, "error": "Only students can be assigned to grade classes."})
                    continue
                available_class_ids = {item["id"] for item in db.list_classes()}
                if any(class_id not in available_class_ids for class_id in class_ids):
                    await ws.send_json({"ok": False, "error": "One or more selected classes no longer exist."})
                    continue
                if not name:
                    await ws.send_json({"ok": False, "error": "Full name is required."})
                    continue
                if db.get_employee(emp_id):
                    await ws.send_json({"ok": False, "error": f"Employee ID {emp_id} already exists."})
                    continue
                for pose, item in captured.items():
                    dup = find_duplicate(item["embedding"])
                    if dup:
                        emp = db.get_employee(dup)
                        label = emp["name"] if emp else dup
                        await ws.send_json(
                            {
                                "ok": False,
                                "error": f"Duplicate face matches {label} ({dup}). Enrollment blocked.",
                            }
                        )
                        captured.clear()
                        break
                else:
                    employee = db.create_employee(emp_id, name, department, role=role, consent_given=consent)
                    face_dir = FACES_DIR / emp_id
                    face_dir.mkdir(parents=True, exist_ok=True)
                    for pose, item in captured.items():
                        (face_dir / f"{pose}.jpg").write_bytes(item["jpeg"])
                        db.add_embedding(emp_id, item["embedding"], pose)
                    if class_ids:
                        db.assign_student_to_classes(emp_id, class_ids)
                    rebuild_match_cache()
                    await ws.send_json({"ok": True, "type": "finalize", "employee": employee})
                    captured.clear()
            else:
                await ws.send_json({"ok": False, "error": f"Unknown action {action}"})
    except WebSocketDisconnect:
        return


if __name__ == "__main__":
    import uvicorn

    from backend.config import HOST, PORT, print_access_urls

    print_access_urls()
    uvicorn.run("backend.main:app", host=HOST, port=PORT)
