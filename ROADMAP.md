# Roadmap

This document is a proposed direction for the project, not a release schedule or a promise that every item will be implemented. Priorities should be revisited with maintainers and users. The roadmap favors reliability and responsible handling of local biometric data.

## Current capabilities

- Local FastAPI/Jinja2 application with kiosk and admin interfaces.
- Guided five-pose employee enrollment with image-quality checks and duplicate detection.
- SQLite attendance storage, daily dashboard, department summary, filtering, and CSV/Excel exports.
- Manual attendance correction with required reason and correction-history audit.
- Matching calibration preview and kiosk service/camera status.
- Downloadable and scheduled local backups, retention, and validated restore with a pre-restore safety archive.
- Windows and Unix-like setup and run scripts.

## Near term: reliability and operator experience

- Establish a repeatable automated test suite for attendance rules, admin authorization, backup validation, restore rollback, and route behavior.
- Add deployment and recovery smoke-check guidance so operators can verify camera, database, model, and backup readiness.
- Improve camera/device selection and provide clearer actionable messages for browser permission, camera-busy, and reconnect failures.
- Add a backup verification workflow that lets an admin check archive integrity without restoring it.
- Make backup status and restore outcomes more discoverable, including clear timestamps and the location of safety archives.

## Medium term: administration and data lifecycle

- Add configurable retention and safe archival/deletion workflows for attendance records and biometric enrollment data.
- Improve employee lifecycle management, including edit/deactivate flows and clearer handling of associated images and embeddings.
- Add import tools for employee rosters with preview, validation, and duplicate detection before writing changes.
- Expand audit coverage for sensitive administrative actions while keeping audit records useful and privacy-conscious.
- Provide a documented, least-privilege deployment approach for serving the app over HTTPS on a managed local network.

## Longer term: deployment and maintainability

- Evaluate support for multiple kiosks sharing one managed local installation, with explicit concurrency and device ownership rules.
- Improve platform-specific dependency installation and provide a verified compatibility matrix for supported Python and operating-system versions.
- Add accessibility and usability reviews for kiosk placement, keyboard navigation, readable status messaging, and localization readiness.
- Define a migration/versioning strategy for the SQLite schema and backup format before introducing incompatible changes.
- Document operational monitoring and upgrade procedures without adding cloud dependencies by default.

## Principles for prioritization

1. **Reliability first:** Attendance capture, database integrity, and recovery take precedence over new features.
2. **Local by default:** No cloud dependency or external transfer of biometric data without explicit user and maintainer approval.
3. **Safe data operations:** Destructive changes need validation, clear confirmation, and a recovery path.
4. **Operator clarity:** Errors and system status should be understandable to administrators who do not develop software.
5. **Compatibility:** Changes should preserve supported Windows and Unix-like setup workflows where feasible.

## Proposing roadmap work

When proposing an item, describe the user problem, the expected outcome, privacy and data-retention implications, and how success could be verified. Discuss significant scope or behavior changes before implementation.
