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
- **Changed:** Setup scripts now test whether an existing `.venv` interpreter actually runs. They prompt before reusing/updating a working environment or recreating it; broken or too-old environments are not replaced without confirmation. Recreating a symlinked Unix `.venv` removes only the link, not its target.
- **Changed:** Run scripts route broken or unsupported environments through setup and report that the interpreter cannot start or is too old, instead of implying the version check alone proves the cause.
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

## Initial Windows desktop wrapper — current development

- **Added:** Optional `pywebview` desktop entry point and `desktop.bat`; the existing browser/LAN run scripts remain available.
- **Changed:** Desktop startup launches the existing FastAPI application on loopback (`127.0.0.1`) using an available local port, opens the kiosk in an app window, and requests a server shutdown when the window closes.
- **Not yet verified:** Camera permission and capture behavior across WebView2 installations, native window close behavior on target devices, and packaged installer/update flows. This wrapper is a development entry point, not a production installer.

## Kiosk recognition overlay — current development

- **Changed:** Kiosk face boxes and labels are HTML overlays positioned above the mirrored video canvas rather than canvas strokes, to address the missing recognition box observed in WebView.
- **Changed:** Overlay positions account for the cover-cropped kiosk preview, and kiosk asset URLs include a cache-busting version.
- **Verified by user:** The green recognition box now appears in the WebView after the overlay change.

## Desktop data persistence — current development

- **Changed:** Desktop mode stores the database, face images, embeddings, session secret, and default backups in a stable per-user application-data directory. Browser/LAN mode continues to use project-local `data/`.
- **Added:** First desktop startup copies missing legacy data into the per-user directory only when a legacy project database exists and the per-user database is absent. The database is copied last with SQLite's online backup API; existing per-user databases are not mixed with project-local face files. Source project data is left in place, and the saved default backup path is updated for the new location.
- **Not yet verified:** Migration against a real existing installation and behavior when the target per-user folder is not writable.

## Startup resource limits — current development

- **Changed:** Windows and Unix-like setup/run scripts limit OpenBLAS, OpenMP, MKL, and NumExpr worker threads to one before importing the face-recognition stack.
- **Changed:** The desktop Python entry point applies the same limits before loading numerical or face-recognition packages.
- **Reason:** Desktop startup reported OpenBLAS memory-allocation retries; the affected Windows host also reported very low free physical memory. The thread cap reduces thread-related memory overhead but cannot compensate for insufficient overall system memory.

## Documentation — current project state

- **Added:** A user-facing `README.md` covering setup, use, local data locations, backup/restore, and deployment/privacy cautions.
- **Added:** `CONTRIBUTING.md` describing development setup, validation, privacy, and contribution expectations.
- **Added:** `ROADMAP.md` separating implemented capabilities from proposed future work.
- **Added:** This changelog to record the documented project milestones and their verification limits.

## Windows installer preparation — current development

- **Added:** A PyInstaller onedir spec and a Windows build script that can produce the application directory and, when Inno Setup 6 is installed, a per-user installer.
- **Changed:** Desktop-mode InsightFace model storage is under the per-user application-data directory so first-run model downloads do not target the install directory.
- **Changed:** The frozen app now explicitly bundles InsightFace's landmark pickle at the extraction-root path its loader expects and includes the ASGI entry module loaded by Uvicorn from a module string. The build script checks the required pickle is present.
- **Documented behavior:** Model weights and user attendance data are intentionally excluded from the installer. The model downloads on first app launch and is reused from the per-user model cache.
- **Not yet verified:** PyInstaller build, Inno Setup compilation, first-run model download from the packaged app, and installer behavior on a clean Windows profile. The build was not run because the available Windows host had very little free physical memory and lacked the packaging tools.

## Current state

The current project is a local FastAPI/Jinja2 face-attendance application with Windows and Unix-like setup/launch scripts, a kiosk, password-protected admin pages, five-pose enrollment, SQLite attendance and correction auditing, CSV/Excel exports, local scheduled/manual backups, and admin backup restore.

No release version or release date is assigned here. The project currently has no configured automated test suite documented in the README. Validation of individual changes has been performed during development, but that is not equivalent to a continuously maintained test suite.
