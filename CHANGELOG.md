# Changelog

This file records the project milestones documented in the available conversation history and checked against the current project where possible.

**Record limits:** Git history could not be inspected in this environment because the `git` command is unavailable. Earlier work has no verified commit dates, release tags, or version numbers. Entries are therefore kept in chronological order without invented dates or versions. This is not a claim that every development change is represented.

## Project foundation — initial project, date not recorded

The project was established as a local-first face-attendance application with a kiosk and an administrator interface.

- **Added:** FastAPI application with Jinja2/HTML pages and browser JavaScript.
- **Added:** SQLite-backed employee, face-embedding, attendance-log, and settings storage.
- **Added:** InsightFace/OpenCV face processing, five-pose enrollment, and attendance recognition workflows.
- **Added:** Initial administrator setup/login, dashboard, people management, attendance logs, and recognition settings.
- **Added:** Windows and Unix-like setup and run scripts.

These items describe the project foundation and current architecture; their original implementation dates and exact order are not recorded.

## Enrollment and kiosk reliability — subsequent improvements, dates not recorded

- **Changed:** Enrollment capture now reports camera/connection readiness and failures instead of silently ignoring unavailable capture requests.
- **Changed:** Enrollment preview draws locally from the video, limits analysis to one in-flight request, and uses a reduced 640×480 camera request to reduce lag.
- **Changed:** Kiosk preview mirroring was corrected to match the user's requested left/right orientation; face overlays were adjusted to stay aligned and text remains readable.
- **Added:** Separate kiosk camera and attendance-service status indicators, including startup, error, and reconnect states.
- **Added:** Enrollment progress and live image-quality guidance.

## Attendance administration and audit history — subsequent improvements, dates not recorded

- **Added:** Attendance correction audit records with before/after snapshots for manual entries, removals, and edits.
- **Changed:** Manual attendance corrections require a reason; reasons are recorded with the audit history.
- **Added:** Admin Logs view and CSV/Excel export for correction history.
- **Added:** Daily attendance summaries grouped by department.
- **Confirmed:** Attendance-log CSV/Excel export was already present before these additions; it was not introduced as part of the correction-audit work.

## Setup and local backup — subsequent improvements, dates not recorded

- **Changed:** Setup scripts check for Python 3.10 or newer, offer supported OS-specific installation paths when Python is unavailable, create/reuse `.venv`, install requirements, and check dependency consistency.
- **Changed:** Run scripts use the local virtual environment, check application dependencies and face-model availability, and print LAN access URLs.
- **Added:** Configurable automatic local backups with an interval and retention count. Backups use SQLite's online backup API and include the database snapshot and associated face assets/cache files.
- **Added:** Manual backup download and dashboard status for local backups.
- **Changed:** Backup output is verified, and older archives are pruned according to the configured retention setting.
- **Documented behavior:** Automatic backups run while the application process is running; they are not an independent operating-system service.

## Admin backup restore — latest application feature, dates not recorded

- **Added:** Admin Settings workflow to upload and restore a backup ZIP.
- **Added:** Archive path, duplicate-entry, file-type, encryption, size, and data-integrity validation before restore.
- **Changed:** Restore makes a safety backup before replacing current data, restores the SQLite database through SQLite's backup API, replaces associated face files/cache data, and rebuilds the face-match cache.
- **Added:** Rollback handling for failures during the restore operation and clear success/error feedback in the Settings page.
- **Documented behavior:** Restore replaces current attendance/enrollment data. The safety backup is retained locally; the admin should verify the configured backup folder and available disk space.

## Documentation — current project state

- **Added:** A user-facing `README.md` covering setup, use, local data locations, backup/restore, and deployment/privacy cautions.
- **Added:** `CONTRIBUTING.md` describing development setup, validation, privacy, and contribution expectations.
- **Added:** `ROADMAP.md` separating implemented capabilities from proposed future work.
- **Added:** This changelog to record the documented project milestones and their verification limits.

## Current state

The current project is a local FastAPI/Jinja2 face-attendance application with Windows and Unix-like setup/launch scripts, a kiosk, password-protected admin pages, five-pose enrollment, SQLite attendance and correction auditing, CSV/Excel exports, local scheduled/manual backups, and admin backup restore.

No release version or release date is assigned here. The project currently has no configured automated test suite documented in the README. Validation of individual changes has been performed during development, but that is not equivalent to a continuously maintained test suite.
