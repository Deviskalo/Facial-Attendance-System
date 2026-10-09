from __future__ import annotations

import socket
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
FACES_DIR = DATA_DIR / "faces"
BACKUPS_DIR = DATA_DIR / "backups"
MODELS_ROOT = ROOT_DIR  # InsightFace stores weights in {root}/models/buffalo_l
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


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
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
