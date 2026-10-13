# Face Attendance Kiosk

A local-first face-recognition attendance system with a live kiosk and a password-protected administration panel. It uses FastAPI, SQLite, OpenCV, InsightFace, and server-rendered HTML/JavaScript.

The application processes camera frames and stores attendance and enrollment data on the machine running the server. It does not require a cloud service for normal operation. Initial setup does need internet access to install Python packages and obtain the face-recognition model.

> **Biometric data notice:** Enrolled face images and embeddings are sensitive personal data. Use this system only with appropriate consent and authorization, restrict access to the host and local network, and establish retention and backup policies suitable for your organization.

## Features

- Live kiosk with camera and attendance-service status, recognition feedback, and check-in/check-out handling.
- Admin setup and password-protected dashboard with live activity, daily attendance metrics, and department summaries.
- Five-pose enrollment workflow with frame quality checks and duplicate-face detection.
- Attendance log filtering and CSV/Excel export.
- Manual attendance corrections with required reasons and a correction audit history.
- Matching threshold calibration with a live preview.
- Downloadable and scheduled local ZIP backups, plus validated restore with a pre-restore safety backup.
- Windows and Unix-like setup/launcher scripts that create and use a project-local `.venv`.

## Requirements

- Python 3.10 or newer.
- A camera connected to the kiosk device, with camera permission granted to the browser.
- Windows, Linux, or macOS with the required Python packages available for that platform.
- Internet access for first-time dependency/model setup. After dependencies and the InsightFace model are installed, face processing runs locally using the CPU execution provider.

The setup scripts can offer to install Python when it is missing (using Winget on Windows or supported system package managers on Linux/macOS). Review any installer prompts before accepting them.

If a project `.venv` already exists, setup checks whether it can run Python 3.10 or newer. For a usable environment, the default is to keep and update it; choose recreate only when you intentionally want a clean environment. If the environment is broken or too old, setup asks before removing it. Recreating `.venv` does not remove the application's `data/` directory. Symbolic links/junctions are handled cautiously to avoid deleting an external target.

## Quick start

Run commands from the project directory.

### Windows

```powershell
.\setup.bat
.\run.bat
```

For the experimental Windows desktop window, use:

```powershell
.\desktop.bat
```

The desktop launcher installs the optional dependency listed in `requirements-desktop.txt` when needed, starts the same application on a loopback-only ephemeral port, and opens the kiosk in a native window. Its launcher limits BLAS/OpenMP worker threads to reduce resource pressure during face-model startup. Close the window to stop its local server. This is an initial wrapper, not a signed installer; camera permission behavior depends on the installed WebView2 runtime and must be verified on the target machine. Use `run.bat` to retain the existing browser/LAN mode.

### Build the Windows installer

The installer is built locally and does not include InsightFace model weights or application data. The Windows executable, installer, and shortcuts use the project's app icon. On a Windows x64 build machine with Python 3.10 or newer, run:

```powershell
.\setup.bat
.\packaging\build_windows.bat
```

The build script installs the optional desktop and PyInstaller requirements into `.venv` and creates the application directory under `release\windows`. Install Inno Setup 6 and ensure `ISCC.exe` is on `PATH` to also create the installer under `release\installer`. Without Inno Setup, the application directory is still produced and can be compiled later using `packaging\FaceAttendanceKiosk.iss`.

The packaged desktop app needs internet access on first launch to download the InsightFace `buffalo_l` model. The download is stored per-user at `%LOCALAPPDATA%\FaceAttendanceKiosk\insightface` and reused on later launches; it is not installed into the application directory. The WebView2 Runtime must also be available on the target computer. The model is third-party software with its own terms; review InsightFace's model license and permitted-use conditions before use or redistribution. The generated installer is not code-signed.

### Linux or macOS

```bash
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

The launcher starts Uvicorn on port `8000`, bound to `0.0.0.0`, and prints kiosk/admin URLs for the local network. Open the printed URL from a device on the same network:

- Kiosk: `http://<host-ip>:8000/kiosk`
- Admin: `http://<host-ip>:8000/admin`

Browsers only allow camera access from secure contexts. The plain-HTTP LAN kiosk URL will not have camera access in a browser on another device. For a browser on the same computer as the server, open `http://localhost:8000/kiosk`; for another device, put the app behind HTTPS with a certificate trusted by that device. The desktop app uses loopback and does not require the LAN HTTP URL.

On first visit, the admin page redirects to setup. Create the administrator password there, then use it to sign in. The current password minimum is six characters; choose a long, unique password instead.

To stop the server, press `Ctrl+C` in the terminal where it is running.

## Using the system

1. **Prepare the kiosk:** Open `/kiosk` in a browser and allow camera access. Keep the server process running.
2. **Set up administration:** Open `/admin`, create the initial administrator password, and sign in.
3. **Enroll people:** Choose **People → Add person**, enter the employee information, and follow the guided five-pose camera capture.
4. **Record attendance:** Keep the kiosk open for people to check in/out. Configure office start time, late margin, cooldown, checkout gap, and recognition threshold in **Settings**.
5. **Review records:** Use **Logs** to filter attendance, export CSV/XLSX, make justified manual corrections, and review/export the correction history.
6. **Protect local data:** Download a backup or configure automatic backup interval, retention, and directory in **Settings**. In the desktop app, the download button opens a Save As dialog for the backup ZIP. To restore, select a backup ZIP there and confirm. Restore replaces the current records and face assets; the application creates a safety backup first.

## Data and privacy

In browser/LAN mode, the application's local data is stored under the project `data/` directory. Desktop mode stores it in the current user's application-data directory (on Windows, `%LOCALAPPDATA%\FaceAttendanceKiosk`).

| Path relative to the data directory | Contents |
| --- | --- |
| `attendance.db` | Employees, attendance logs, audit history, and settings (SQLite) |
| `faces/` | Enrolled face images |
| `embeddings.npy`, `embedding_ids.json` | Cached face-match vectors and their employee IDs |
| `session_secret.txt` | Local session-signing secret |
| `backups/` | Automatic and manually created backup archives by default |

When desktop mode starts and a legacy project database exists but the per-user database does not, it copies missing legacy files into the per-user directory and copies the database last using SQLite's online backup API. Existing per-user databases are left untouched and are not mixed with project-local face files. The source project data is left in place. If both browser/LAN mode and desktop mode are used, they use separate data directories after desktop migration; do not expect changes made in one mode to appear in the other. Close the browser/LAN server before using desktop mode during migration.

In browser/LAN mode, project data files are excluded from version control by `.gitignore`. Desktop-mode data is stored outside the repository. Do not add real employee data, face images, embeddings, database files, session secrets, or backup archives to commits or public issue reports.

Backups contain the attendance database and biometric face assets. Store copies securely, limit access, and periodically verify that backups can be restored. Restore accepts ZIP archives produced for this application and validates their contents before replacement.

## Network and security considerations

- The server listens on every network interface (`0.0.0.0`) so trusted LAN devices can connect. The app uses HTTP by default and is intended for a trusted, access-controlled local network.
- Do not expose port `8000` directly to the public internet. For remote access, use a properly secured VPN or a separately configured HTTPS reverse proxy and firewall.
- Protect the host account, administrator password, database, enrollment images, embeddings, exports, and backups.
- Anyone with physical access to the kiosk browser may be able to interact with its camera. Configure the kiosk device and browser accordingly.
- Follow applicable privacy, biometric-data, employment, and record-retention requirements before deploying.

## Project layout

```text
backend/                 FastAPI routes, SQLite operations, face engine, backups
frontend/templates/      Jinja2 kiosk and admin pages
frontend/static/         CSS and browser JavaScript
data/                    Local database, face assets, cache, and backups (not committed)
models/                  Locally downloaded face-recognition model (not committed)
requirements.txt         Python dependencies
requirements-desktop.txt Optional PyWebView desktop dependency set
setup.bat / setup.sh     Environment and dependency setup
run.bat / run.sh         Application launchers
desktop.bat              Experimental Windows desktop launcher
```

## Development and verification

Create the environment with the setup script, then run focused checks from the project root.

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend
node --check frontend\static\js\SettingsForm.js
```

`node --check` is optional and requires Node.js; there is no Node-based frontend build. The project currently has no configured automated test suite, so changes should also be exercised through the affected admin or kiosk workflow. Avoid testing destructive operations against real attendance data.

See [CHANGELOG.md](./CHANGELOG.md) for documented project milestones, [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution expectations, and [ROADMAP.md](./ROADMAP.md) for suggested future work.

## License

No license file is currently included. Contact the project maintainers before redistributing this project or incorporating it into another product.
