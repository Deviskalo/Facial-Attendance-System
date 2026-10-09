from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, cast

from backend.config import (
    BACKUPS_DIR,
    DB_PATH,
    EMBEDDING_IDS_PATH,
    EMBEDDINGS_PATH,
    FACES_DIR,
    ROOT_DIR,
)

    _MAX_ARCHIVE_BYTES = 4 * 1024 * 1024 * 1024
    _MAX_DATABASE_BYTES = 1024 * 1024 * 1024
    _MAX_FILE_BYTES = 100 * 1024 * 1024


    def resolve_backup_directory(directory: str | Path | None = None) -> Path:
    selected = Path(directory).expanduser() if directory else BACKUPS_DIR
    if not selected.is_absolute():
        selected = ROOT_DIR / selected
    return selected.resolve()


def _snapshot_database(destination: Path) -> None:
    with closing(sqlite3.connect(DB_PATH)) as source:
        with closing(sqlite3.connect(destination)) as snapshot:
            source.backup(snapshot)
            result = snapshot.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise RuntimeError(f"SQLite backup integrity check failed: {result}")


def create_backup(directory: str | Path | None = None) -> Path:
    backup_dir = resolve_backup_directory(directory)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    final_path = backup_dir / f"attendance-backup-{stamp}.zip"

    with tempfile.TemporaryDirectory(prefix=".attendance-backup-", dir=backup_dir) as temp:
        work_dir = Path(temp)
        database_snapshot = work_dir / "attendance.db"
        archive_path = work_dir / final_path.name
        _snapshot_database(database_snapshot)

        files: list[tuple[Path, str]] = [(database_snapshot, "attendance.db")]
        for path, archive_name in (
            (EMBEDDINGS_PATH, "embeddings.npy"),
            (EMBEDDING_IDS_PATH, "embedding_ids.json"),
        ):
            if path.is_file():
                files.append((path, archive_name))
        if FACES_DIR.exists():
            files.extend(
                (path, (Path("faces") / path.relative_to(FACES_DIR)).as_posix())
                for path in FACES_DIR.rglob("*")
                if path.is_file()
            )

        manifest = {
            "created_at": datetime.now().isoformat(sep=" ", timespec="seconds"),
            "files": [archive_name for _, archive_name in files],
        }
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, archive_name in files:
                archive.write(path, arcname=archive_name)
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))

        with zipfile.ZipFile(archive_path, "r") as archive:
            corrupt_file = archive.testzip()
            if corrupt_file:
                raise RuntimeError(f"Backup archive verification failed: {corrupt_file}")
            if "attendance.db" not in archive.namelist():
                raise RuntimeError("Backup archive does not contain attendance.db.")

        os.replace(archive_path, final_path)

    return final_path


def _safe_archive_name(name: str) -> str:
    if "\\" in name or "\x00" in name:
        raise ValueError("Backup contains an unsafe file path.")
    path = Path(name)
    parts = name.split("/")
    if path.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("Backup contains an unsafe file path.")
    if name in {"attendance.db", "embeddings.npy", "embedding_ids.json", "manifest.json"}:
        return name
    if parts[0] == "faces" and len(parts) >= 2:
        return name
    raise ValueError(f"Backup contains an unsupported file: {name}")


def _validate_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise ValueError(f"Backup database integrity check failed: {result}")
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        required_tables = {"employees", "face_embeddings", "attendance_logs"}
        if not required_tables.issubset(tables):
            raise ValueError("Backup database is missing required attendance tables.")


def _install_staged_file(source: Path, destination: Path, rollback: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    existed = destination.exists()
    if existed:
        os.replace(destination, rollback)
    os.replace(source, destination)
    return existed


def restore_backup(
    uploaded_archive: BinaryIO, directory: str | Path | None = None
) -> Path:
    backup_dir = resolve_backup_directory(directory)
    backup_dir.mkdir(parents=True, exist_ok=True)
    DATA_DIR = DB_PATH.parent
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    safety_backup: Path | None = None
    with tempfile.TemporaryDirectory(prefix=".attendance-restore-", dir=DATA_DIR) as temp:
        work_dir = Path(temp)
        extracted = work_dir / "contents"
        extracted.mkdir()

        uploaded_archive.seek(0)
        try:
            archive = zipfile.ZipFile(uploaded_archive, "r")
        except zipfile.BadZipFile as exc:
            raise ValueError("Uploaded file is not a valid ZIP backup.") from exc

        with archive:
            names: set[str] = set()
            total_size = 0
            database_member = None
            members: list[tuple[zipfile.ZipInfo, str]] = []
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = _safe_archive_name(info.filename)
                if name in names:
                    raise ValueError(f"Backup contains duplicate file: {name}")
                names.add(name)
                if info.file_size > _MAX_FILE_BYTES and name != "attendance.db":
                    raise ValueError(f"Backup file is too large: {name}")
                if name == "attendance.db" and info.file_size > _MAX_DATABASE_BYTES:
                    raise ValueError("Backup database exceeds the 1 GiB restore limit.")
                total_size += info.file_size
                if total_size > _MAX_ARCHIVE_BYTES:
                    raise ValueError("Backup exceeds the 4 GiB restore limit.")
                mode = info.external_attr >> 16
                if mode and (mode & 0o170000) == 0o120000:
                    raise ValueError("Backup contains an unsupported symbolic link.")
                members.append((info, name))
                if name == "attendance.db":
                    database_member = info
            if database_member is None:
                raise ValueError("Backup does not contain attendance.db.")

            for info, name in members:
                destination = extracted.joinpath(*name.split("/"))
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)

        staged_db = extracted / "attendance.db"
        _validate_database(staged_db)
        safety_backup = create_backup(backup_dir)

        rollback_db = work_dir / "current-attendance.db"
        _snapshot_database(rollback_db)
        rollback_faces = work_dir / "current-faces"
        faces_staged = extracted / "faces"
        faces_installed = False
        old_embedding_files: list[tuple[Path, Path | None]] = []
        database_changed = False

        try:
            if FACES_DIR.exists():
                os.replace(FACES_DIR, rollback_faces)
            if faces_staged.exists():
                os.replace(faces_staged, FACES_DIR)
            else:
                FACES_DIR.mkdir(parents=True, exist_ok=True)
            faces_installed = True

            for filename, target in (
                ("embeddings.npy", EMBEDDINGS_PATH),
                ("embedding_ids.json", EMBEDDING_IDS_PATH),
            ):
                source = extracted / filename
                previous = work_dir / f"previous-{filename}"
                if source.exists():
                    existed = _install_staged_file(source, target, previous)
                    old_embedding_files.append((target, previous if existed else None))
                else:
                    existed = target.exists()
                    if existed:
                        os.replace(target, previous)
                    old_embedding_files.append((target, previous if existed else None))

            with closing(sqlite3.connect(staged_db)) as source:
                with closing(sqlite3.connect(DB_PATH)) as destination:
                    source.backup(destination)
                    integrity = destination.execute("PRAGMA integrity_check").fetchone()
                    if not integrity or integrity[0] != "ok":
                        raise RuntimeError(
                            f"Restored database integrity check failed: {integrity}"
                        )
            database_changed = True

            from backend import database
            from backend.face_engine import rebuild_match_cache

            database.init_db()
            rebuild_match_cache()
        except Exception:
            if database_changed:
                with closing(sqlite3.connect(rollback_db)) as source:
                    with closing(sqlite3.connect(DB_PATH)) as destination:
                        source.backup(destination)
            if faces_installed:
                if FACES_DIR.exists():
                    shutil.rmtree(FACES_DIR)
                if rollback_faces.exists():
                    os.replace(rollback_faces, FACES_DIR)
            for target, previous in reversed(old_embedding_files):
                if target.exists():
                    target.unlink()
                if previous and previous.exists():
                    os.replace(previous, target)
            from backend import database
            from backend.face_engine import rebuild_match_cache

            database.init_db()
            rebuild_match_cache()
            raise

    return cast(Path, safety_backup)


def prune_backups(directory: str | Path | None = None, keep: int = 14) -> None:
    if keep < 1:
        raise ValueError("Backup retention must be at least one archive.")
    backup_dir = resolve_backup_directory(directory)
    if not backup_dir.exists():
        return
    archives = sorted(
        backup_dir.glob("attendance-backup-*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for stale_archive in archives[keep:]:
        stale_archive.unlink()


def latest_backup(directory: str | Path | None = None) -> Path | None:
    backup_dir = resolve_backup_directory(directory)
    if not backup_dir.exists():
        return None
    archives = list(backup_dir.glob("attendance-backup-*.zip"))
    if not archives:
        return None
    return max(archives, key=lambda path: path.stat().st_mtime)


def backup_status(directory: str | Path | None = None) -> dict[str, str | None]:
    backup = latest_backup(directory)
    return {
        "directory": str(resolve_backup_directory(directory)),
        "last_backup": datetime.fromtimestamp(backup.stat().st_mtime).isoformat(
            sep=" ", timespec="seconds"
        )
        if backup
        else None,
        "last_backup_file": backup.name if backup else None,
    }
