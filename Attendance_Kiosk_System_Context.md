# Context & Objective
Build a complete, 100% offline, local-first Face Recognition Attendance System with dual interfaces:
1. **Kiosk Mode**: Interactive display for live facial recognition check-ins/check-outs with instant visual feedback.
2. **Admin Panel**: Password-protected dashboard for employee enrollment, real-time activity tracking, attendance logs, threshold calibration, and database backups.

The entire system must run on a local network (LAN/Wi-Fi) without relying on any cloud services or third-party APIs. It must include auto-installer scripts for one-click setup (`setup.bat`/`setup.sh`) and execution (`run.bat`/`run.sh`).

---

## Tech Stack & Architecture
- **Backend Framework**: Python (FastAPI with Uvicorn, WebSockets, and Pydantic)
- **Computer Vision & AI Engine**: OpenCV, NumPy, and `insightface` or `face_recognition` (dlib) for 128D/512D face embeddings.
- **Frontend Framework**: Next.js (React + Tailwind CSS + Lucide Icons) OR FastAPI Jinja2 + HTML5 WebSockets + Tailwind CSS.
- **Database**: SQLite (Local file-based storage for logs, settings, and user metadata) + NumPy binary (`.npy`) or SQLite BLOB for vector embeddings.
- **Network Scope**: Bound to `0.0.0.0:8000` so any device on the local Wi-Fi/LAN can access the Kiosk or Admin UI.

---

## Key System Modules & Technical Requirements

### 1. Auto-Setup & Execution Scripts
Provide setup and launcher scripts that handle environment configuration automatically:
- `setup.bat` (Windows) & `setup.sh` (Linux/macOS):
  - Checks for Python 3.10 or newer; if unavailable, offers to install Python using winget on Windows or a supported system package manager on Linux/macOS.
  - Creates a local Python virtual environment (`.venv`).
  - Upgrades `pip`, installs `requirements.txt`, and checks for dependency conflicts.
  - Downloads required local ONNX/Dlib face detection models into a `/models` folder.
- `run.bat` (Windows) & `run.sh` (Linux/macOS):
  - Uses the `.venv` Python directly and runs setup automatically if the environment is missing.
  - Verifies the required Python version, server package, and face-recognition models before launch.
  - Boots the FastAPI server on `http://0.0.0.0:8000`.
  - Prints local IP links for Kiosk (`/kiosk`) and Admin (`/admin`).

---

### 2. Smart Face Enrollment Wizard (5-Angle Capture)
Inside the Admin Panel (`/admin/people/add`), build a guided 5-shot photo capture system:
1. **Guided Angles**:
   - Step 1: Frontal view
   - Step 2: Turn head slightly left
   - Step 3: Turn head slightly right
   - Step 4: Tilt chin slightly up
   - Step 5: Tilt chin slightly down
2. **Quality Auditing Engine**:
   - **Lighting Check**: Reject frames that are too dark or severely overexposed (mean brightness score thresholding).
   - **Blur Check**: Compute Laplacian variance; flag images below a crispness threshold.
   - **Multi-Face Prevention**: Ensure exactly one face is present in frame.
   - **Duplicate Detection**: Compare candidate face embeddings against existing enrolled faces. If cosine/Euclidean distance matches an existing user, block enrollment and alert the admin.
3. **Storage**: Crop the bounding box, save original reference images to `/data/faces/{employee_id}/`, and extract/average the embeddings into the embedding store.

---

### 3. Interactive Kiosk View (`/kiosk`)
A clean screen suited for a dedicated wall tablet or secondary display:
- **Live Stream**: HTML5 Canvas rendering WebSocket frames from the backend or processing client-side video frames.
- **Real-Time Bounding Boxes**: Overlays face detection boxes on stream with color coding:
  - **Green**: Recognized member.
  - **Yellow**: Unrecognized / Unknown person.
  - **Red**: Detection error / Multiple faces.
- **Attendance Rules & State Machine**:
  - **Check-in Logic**: Marks employee "On Time" or "Late" based on configured `office_start_time` and `late_margin_minutes`.
  - **Cooldown Period**: Once recognized, the user enters a cooldown (e.g., 60 seconds default) to prevent spamming logs.
  - **Checkout Window**: If an employee is detected again after `checkout_gap_minutes` (e.g., 120 minutes), flag the log entry as "Checkout".
  - **Audio/Visual Banners**: Displays a temporary toast notification ("Welcome, [Name]! Status: On Time", "Already Marked", or "Late").

---

### 4. Admin Panel & Control Center (`/admin`)
Password-protected section (prompt for admin password setup on initial startup):
- **Live Activity Feed**: Stream of all detections in real time (known vs. unknown face logs).
- **Today's Attendance Overview**: Summary metrics (Total Enrolled, Present Today, Late Count, Absent Count).
- **Attendance Records Table**:
  - Filterable by Date Range, Department, or Status (On Time, Late, Manual Entry).
  - Manual Overrides: Ability to mark employees absent, present, or edit timestamps.
  - Export Options: Export logs to CSV/Excel formats.
- **System Settings & Calibration**:
  - `office_start_time` (e.g., `09:00`)
  - `late_margin_minutes` (e.g., `15`)
  - `detection_cooldown_seconds` (e.g., `60`)
  - `checkout_gap_minutes` (e.g., `120`)
  - `matching_threshold` (Slider to calibrate facial distance tolerance; default `0.36`). Includes a visual calibration preview tool.
- **Database Backup**: One-click "Download Database Backup" button that packages SQLite tables and stored face vectors into a timestamped `.zip` file.
- **Automatic Local Backups**: While the server is running, create verified timestamped archives locally using SQLite's online backup API; package the database snapshot, embeddings, and enrolled face images, and prune archives to the configured retention count.

---

## Database Schema (SQLite)

```sql
-- Employees Table
CREATE TABLE employees (
    id TEXT PRIMARY KEY, -- e.g., EMP-101
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Embeddings Table
CREATE TABLE face_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    embedding_data BLOB NOT NULL, -- Serialized 128D/512D vector array
    pose_label TEXT NOT NULL, -- 'center', 'left', 'right', 'up', 'down'
    FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
);

-- Attendance Logs Table
CREATE TABLE attendance_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL, -- 'CHECK_IN', 'CHECK_OUT'
    status TEXT NOT NULL, -- 'ON_TIME', 'LATE', 'MANUAL'
    confidence_score REAL,
    FOREIGN KEY(employee_id) REFERENCES employees(id)
);

-- System Configuration Table
CREATE TABLE system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);