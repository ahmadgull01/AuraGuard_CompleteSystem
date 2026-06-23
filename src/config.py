from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
REGISTERED_FACES_DIR = DATA_DIR / "registered_faces"
UNKNOWN_FACES_DIR = DATA_DIR / "unknown_faces"
REGISTRATION_REQUESTS_DIR = DATA_DIR / "registration_requests"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
LOGS_DIR = DATA_DIR / "logs"
DATABASE_DIR = ROOT_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "aura_guard.db"

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

DEFAULT_SETTINGS = {
    "recognition_model": "facelogin_dlib",
    "threshold": "0.48",
    "auto_threshold": "false",
    "max_samples": "24",
    "camera_index": "0",
    "liveness_enabled": "true",
    "two_factor_enabled": "false",
    "snapshot_enabled": "true",
    "sound_enabled": "true",
    "voice_feedback": "false",
    "email_alerts": "false",
    "min_face_size": "80",
    "frame_rate": "24",
    "language": "English",
}


def ensure_directories() -> None:
    for path in [
        DATA_DIR,
        REGISTERED_FACES_DIR,
        UNKNOWN_FACES_DIR,
        REGISTRATION_REQUESTS_DIR,
        SNAPSHOTS_DIR,
        LOGS_DIR,
        DATABASE_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
