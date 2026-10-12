from __future__ import annotations

import os
import platform
import shutil
import socket
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
LEGACY_DATA_DIR = ROOT_DIR / "data"


def _desktop_data_directory() -> Path:
    current_platform = platform.system()
    if current_platform == "Windows":
        base = Path(
            os.environ.get("LOCALAPPDATA")
            or Path.home() / "AppData" / "Local"
        )
    elif current_platform == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(
            os.environ.get("XDG_DATA_HOME")
            or Path.home() / ".local" / "share"
        )
    return base / "FaceAttendanceKiosk"


DESKTOP_MODE = os.environ.get("ATTENDANCE_DESKTOP") == "1"
DATA_DIR = _desktop_data_directory() if DESKTOP_MODE else LEGACY_DATA_DIR
FACES_DIR = DATA_DIR / "faces"
BACKUPS_DIR = DATA_DIR / "backups"
MODELS_ROOT = DATA_DIR / "insightface" if DESKTOP_MODE else ROOT_DIR
DB_PATH = DATA_DIR / "attendance.db"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"
EMBEDDING_IDS_PATH = DATA_DIR / "embedding_ids.json"
SESSION_SECRET_PATH = DATA_DIR / "session_secret.txt"

HOST = "0.0.0.0"
PORT = 8000
INSIGHTFACE_MODEL = "buffalo_l"
INSIGHTFACE_PROVIDERS = ["CPUExecutionProvider"]
DET_SIZE = (640, 640)

BRIGHTNESS_MIN = 40.0
BRIGHTNESS_MAX = 220.0
BLUR_MIN_VARIANCE = 60.0

DEFAULT_SETTINGS = {
    "office_start_time": "09:00",
    "late_margin_minutes": "15",
    "detection_cooldown_seconds": "60",
    "checkout_gap_minutes": "120",
    "matching_threshold": "0.36",
    "automatic_backups_enabled": "true",
    "backup_interval_hours": "24",
    "backup_retention_count": "14",
    "backup_directory": str(BACKUPS_DIR),
}

POSE_LABELS = ("center", "left", "right", "up", "down")
POSE_INSTRUCTIONS = {
    "center": "Look straight at the camera",
    "left": "Turn your head slightly left",
    "right": "Turn your head slightly right",
    "up": "Tilt your chin slightly up",
    "down": "Tilt your chin slightly down",
}


def _copy_file_if_missing(source: Path, destination: Path) -> bool:
    if destination.exists() or not source.is_file() or source.is_symlink():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.migration-",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            with source.open("rb") as original:
                shutil.copyfileobj(original, temporary)
        try:
            os.link(temporary_path, destination)
        except FileExistsError:
            return False
        return True
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def _copy_database_if_missing(source: Path, destination: Path) -> bool:
    if destination.exists() or not source.is_file() or source.is_symlink():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.migration-",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        with closing(sqlite3.connect(source)) as original:
            with closing(sqlite3.connect(temporary_path)) as migrated:
                original.backup(migrated)
                integrity = migrated.execute("PRAGMA integrity_check").fetchone()
                if not integrity or integrity[0] != "ok":
                    raise RuntimeError(
                        f"Legacy database migration failed integrity check: {integrity}"
                    )
        try:
            os.link(temporary_path, destination)
        except FileExistsError:
            return False
        return True
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def _copy_tree_files_if_missing(source: Path, destination: Path) -> int:
    if not source.is_dir() or source.is_symlink():
        return 0
    copied = 0
    for current, directories, filenames in os.walk(source, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if not (current_path / name).is_symlink()
        ]
        for filename in filenames:
            source_file = current_path / filename
            if source_file.is_symlink():
                continue
            relative_path = source_file.relative_to(source)
            if _copy_file_if_missing(source_file, destination / relative_path):
                copied += 1
    return copied


def _update_migrated_backup_setting(legacy_data_dir: Path) -> None:
    if not DB_PATH.is_file():
        return
    try:
        with closing(sqlite3.connect(DB_PATH)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if "system_settings" not in tables:
                return
            row = connection.execute(
                "SELECT value FROM system_settings WHERE key = 'backup_directory'"
            ).fetchone()
            if not row:
                return
            configured = Path(row[0]).expanduser()
            if not configured.is_absolute():
                configured = ROOT_DIR / configured
            if configured.resolve() != (legacy_data_dir / "backups").resolve():
                return
            connection.execute(
                "UPDATE system_settings SET value = ? WHERE key = 'backup_directory'",
                (str(BACKUPS_DIR),),
            )
            connection.commit()
    except sqlite3.DatabaseError as exc:
        raise RuntimeError(
            "Could not update the default backup folder while migrating desktop data."
        ) from exc


def migrate_legacy_data(
    legacy_data_dir: Path = LEGACY_DATA_DIR,
    destination_data_dir: Path = DATA_DIR,
) -> int:
    if not DESKTOP_MODE or legacy_data_dir.resolve() == destination_data_dir.resolve():
        return 0

    legacy_database = legacy_data_dir / "attendance.db"
    destination_database = destination_data_dir / "attendance.db"
    if destination_database.exists() or not legacy_database.is_file():
        return 0

    copied = 0
    for filename in ("embeddings.npy", "embedding_ids.json", "session_secret.txt"):
        if _copy_file_if_missing(
            legacy_data_dir / filename, destination_data_dir / filename
        ):
            copied += 1

    for dirname in ("faces", "backups"):
        copied += _copy_tree_files_if_missing(
            legacy_data_dir / dirname, destination_data_dir / dirname
        )

    if _copy_database_if_missing(legacy_database, destination_database):
        copied += 1
        _update_migrated_backup_setting(legacy_data_dir)
    return copied


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DESKTOP_MODE:
        migrated_count = migrate_legacy_data()
        if migrated_count:
            print(
                f"Migrated {migrated_count} existing data file(s) to {DATA_DIR}"
            )
    FACES_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT_DIR / "models").mkdir(parents=True, exist_ok=True)


def local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def print_access_urls() -> None:
    ip = local_ip()
    print(f"Kiosk  http://{ip}:{PORT}/kiosk")
    print(f"Admin  http://{ip}:{PORT}/admin")
    print(f"Local  http://127.0.0.1:{PORT}/kiosk")
