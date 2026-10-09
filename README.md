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

## Quick start

Run commands from the project directory.

### Windows

```powershell
.\setup.bat
.\run.bat
```

### Linux or macOS

```bash
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

The launcher starts Uvicorn on port `8000`, bound to `0.0.0.0`, and prints kiosk/admin URLs for the local network. Open the printed URL from a device on the same network:

- Kiosk: `http://<host-ip>:8000/kiosk`
- Admin: `http://<host-ip>:8000/admin`

On first visit, the admin page redirects to setup. Create the administrator password there, then use it to sign in. The current password minimum is six characters; choose a long, unique password instead.

To stop the server, press `Ctrl+C` in the terminal where it is running.

## Using the system

1. **Prepare the kiosk:** Open `/kiosk` in a browser and allow camera access. Keep the server process running.
2. **Set up administration:** Open `/admin`, create the initial administrator password, and sign in.
3. **Enroll people:** Choose **People → Add person**, enter the employee information, and follow the guided five-pose camera capture.
4. **Record attendance:** Keep the kiosk open for people to check in/out. Configure office start time, late margin, cooldown, checkout gap, and recognition threshold in **Settings**.
5. **Review records:** Use **Logs** to filter attendance, export CSV/XLSX, make justified manual corrections, and review/export the correction history.
6. **Protect local data:** Download a backup or configure automatic backup interval, retention, and directory in **Settings**. To restore, select a backup ZIP there and confirm. Restore replaces the current records and face assets; the application creates a safety backup first.

## Data and privacy

The application's default local data is stored under `data/`:

| Path | Contents |
| --- | --- |
| `data/attendance.db` | Employees, attendance logs, audit history, and settings (SQLite) |
| `data/faces/` | Enrolled face images |
| `data/embeddings.npy`, `data/embedding_ids.json` | Cached face-match vectors and their employee IDs |
| `data/session_secret.txt` | Local session-signing secret |
| `data/backups/` | Automatic and manually created backup archives by default |

These files are excluded from version control by `.gitignore`. Do not add real employee data, face images, embeddings, database files, session secrets, or backup archives to commits or public issue reports.

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
setup.bat / setup.sh     Environment and dependency setup
run.bat / run.sh         Application launchers
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
