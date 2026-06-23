from __future__ import annotations

from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database_manager import DatabaseManager
from src.face_recognizer import FaceRecognizer
from src.report_generator import ReportGenerator
from src.liveness_detection import LivenessDetector


def _vector(value: float, size: int = 128) -> list[float]:
    return [float(value)] * size


def _slightly_shifted(base: float, index: int, size: int = 128) -> list[float]:
    return [float(base + ((index % 5) * 0.002))] * size


def database_checks(tmp: Path) -> None:
    db = DatabaseManager(tmp / "test.db")
    assert db.verify_admin("admin", "admin123")
    assert db.list_users() == []
    stats = db.dashboard_stats()
    assert stats["total_users"] == 0
    assert db.next_user_id() == "USR-001"
    assert db.is_valid_user_id("USR-001")
    assert not db.is_valid_user_id("USR 001")

    request_id = db.create_registration_request("ATT-1001", None, 0.0, "test request")
    assert db.list_registration_requests("pending")[0]["request_id"] == request_id
    db.update_registration_request_status(request_id, "ignored", "test decision")
    assert db.list_registration_requests("ignored")[0]["request_status"] == "ignored"

    report = ReportGenerator(db, tmp).export("performance")
    assert report.exists()


def migration_checks(tmp: Path) -> None:
    old_db = tmp / "old_schema.db"
    conn = sqlite3.connect(old_db)
    cur = conn.cursor()
    cur.execute("CREATE TABLE admins(username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)")
    cur.execute("CREATE TABLE users(user_id TEXT PRIMARY KEY, full_name TEXT NOT NULL, role TEXT NOT NULL, registered_at TEXT NOT NULL)")
    cur.execute("CREATE TABLE face_embeddings(embedding_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, embedding_data TEXT NOT NULL, model_name TEXT NOT NULL, created_at TEXT NOT NULL)")
    cur.execute("CREATE TABLE access_logs(log_id TEXT PRIMARY KEY, user_id TEXT, full_name TEXT NOT NULL, confidence_score REAL NOT NULL, liveness_status TEXT NOT NULL, access_status TEXT NOT NULL, created_at TEXT NOT NULL)")
    cur.execute("CREATE TABLE unknown_attempts(attempt_id TEXT PRIMARY KEY, alert_id TEXT NOT NULL, confidence_score REAL NOT NULL, liveness_status TEXT NOT NULL, detection_status TEXT NOT NULL, snapshot_path TEXT, created_at TEXT NOT NULL)")
    cur.execute("CREATE TABLE registration_requests(request_id TEXT PRIMARY KEY, created_at TEXT NOT NULL)")
    cur.execute("CREATE TABLE settings(setting_name TEXT PRIMARY KEY, setting_value TEXT NOT NULL)")
    conn.commit()
    conn.close()

    db = DatabaseManager(old_db)
    with db._connect() as conn2:
        user_cols = {row[1] for row in conn2.execute("PRAGMA table_info(users)").fetchall()}
        req_cols = {row[1] for row in conn2.execute("PRAGMA table_info(registration_requests)").fetchall()}
        unknown_cols = {row[1] for row in conn2.execute("PRAGMA table_info(unknown_attempts)").fetchall()}
    assert "samples_count" in user_cols
    assert "sample_folder" in req_cols
    assert "status" in unknown_cols


def recognition_checks(tmp: Path) -> None:
    db = DatabaseManager(tmp / "recognition.db")
    db.add_user("USR-001", "Known User", "Student", None, "active")
    for i in range(24):
        db.save_embedding("USR-001", _slightly_shifted(0.010, i), FaceRecognizer.MODEL_NAME)
    db.update_user_samples_count("USR-001", 24)

    recognizer = FaceRecognizer(db)
    from src.recognition.face_login_engine import EncodingResult
    recognizer.embed_all = lambda frame, face_box=None: [EncodingResult(FaceRecognizer.MODEL_NAME, frame, "test")]  # type: ignore[method-assign]

    known = recognizer.recognize(_vector(0.018), None)
    assert known["matched"] is True
    assert known["user_id"] == "USR-001"

    unknown = recognizer.recognize(_vector(0.900), None)
    assert unknown["matched"] is False
    assert unknown["user_id"] == "UNKNOWN"

    weak_lookalike = recognizer.recognize(_vector(0.180), None)
    assert weak_lookalike["matched"] is False


def liveness_checks() -> None:
    live = LivenessDetector()
    live.delay_seconds = 0
    live.calibration_frames_needed = 3
    live.action_frames_needed = 2
    live.return_frames_needed = 2
    steady_face = (100, 100, 100, 100)
    state = live.state
    for _ in range(6):
        state = live.update(steady_face)
    if live.challenge_data["axis"] == "x":
        shift = -45 if live.challenge_data["direction"] == -1 else 45
        moved_face = (100 + shift, 100, 100, 100)
    else:
        moved_face = (100, 145, 100, 100)
    for _ in range(6):
        state = live.update(moved_face)
    for _ in range(6):
        state = live.update(steady_face)
    assert state.passed and not state.failed


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        database_checks(tmp)
        migration_checks(tmp)
        recognition_checks(tmp)
        liveness_checks()
    print("All core validation checks passed.")


if __name__ == "__main__":
    main()
