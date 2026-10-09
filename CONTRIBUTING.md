# Contributing

Thanks for helping improve Face Attendance Kiosk. Contributions should preserve its local-first design, protect biometric and attendance data, and keep setup practical for non-developer administrators.

## Before starting

- Search existing code and documentation for established behavior and helpers before adding a new implementation.
- For substantial or behavior-changing work, open an issue or discussion first to agree on the expected user experience.
- Keep changes focused. Update relevant documentation when setup, workflows, configuration, or user-visible behavior changes.
- Do not include real names, face images, embeddings, databases, session secrets, backup archives, or other personal data in commits, screenshots, or issue reports.

## Development setup

Use the setup script for your platform from the repository root:

```powershell
.\setup.bat
```

```bash
./setup.sh
```

The scripts create `.venv`, install `requirements.txt`, check dependency consistency, and obtain the InsightFace model if needed. Initial setup requires internet access. Run the app with `.\run.bat` on Windows or `./run.sh` on Linux/macOS.

## Making a change

1. Create a focused branch from the project’s current main development branch.
2. Reproduce the issue or verify the expected behavior before editing where practical.
3. Make the smallest complete change that addresses the task. Follow nearby naming, formatting, and error-handling patterns.
4. Add or update tests when a test harness exists or the change can be covered with a focused test. Use temporary directories/databases for database or backup checks.
5. Update user or developer documentation affected by the change.
6. Run the applicable checks below and manually verify relevant UI flows.
7. Submit a pull request explaining the problem, the solution, the validation performed, and any operational or data-impacting behavior.

## Validation

At minimum, run Python syntax compilation after Python changes:

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend
```

For browser JavaScript changes, run `node --check` on the edited file if Node.js is installed. Also run any focused tests available for the affected code.

For user-facing changes, verify the relevant workflow, including camera permissions and graceful error feedback when applicable. For backup/restore changes, use a disposable database and verify both the successful path and invalid archive handling. Never run a restore or destructive test against a real deployment database.

## Design and implementation guidelines

- Keep recognition, attendance records, and face-data handling on the local machine; do not introduce cloud uploads or external analytics without explicit project approval.
- Treat face imagery and embeddings as sensitive data. Minimize copies, avoid logging their contents, and use temporary test fixtures.
- Keep SQLite access consistent with the existing database helpers and use SQLite's online backup API for live database snapshots.
- Validate uploaded files and user-controlled values at the server boundary; return clear errors without success-shaped fallbacks.
- Preserve admin authentication on administrative pages and APIs.
- Maintain Windows and Unix-like script support when changing setup or launch behavior. Do not assume a shell, path separator, or package manager is universal.
- Avoid adding dependencies unless they are necessary and documented in `requirements.txt`.

## Pull request checklist

- [ ] The change has a clear scope and explanation.
- [ ] Related documentation is updated.
- [ ] Relevant syntax checks and focused tests pass, or limitations are stated.
- [ ] User-facing behavior is manually verified where practical.
- [ ] No personal data, secrets, local database files, model weights, or backup archives are included.
- [ ] Any changes to restore, attendance correction, or retention behavior clearly describe their data impact.

## Reporting a problem

Include the affected page or command, steps to reproduce, expected and actual behavior, and relevant sanitized logs. Remove names, employee IDs where identifying, face data, session cookies, secrets, and local filesystem details before sharing. State the operating system and Python version; do not attach a live database or backup.
