from __future__ import annotations

from ..config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, DEFAULT_SETTINGS


class SchemaMixin:
    def _create_schema(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    pin_hash TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    samples_count INTEGER NOT NULL DEFAULT 0,
                    last_access TEXT,
                    registered_at TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS face_embeddings (
                    embedding_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    embedding_data TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS access_logs (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    full_name TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    liveness_status TEXT NOT NULL,
                    access_status TEXT NOT NULL,
                    snapshot_path TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS unknown_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    alert_id TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    liveness_status TEXT NOT NULL,
                    detection_status TEXT NOT NULL,
                    snapshot_path TEXT,
                    remarks TEXT,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS registration_requests (
                    request_id TEXT PRIMARY KEY,
                    attempt_id TEXT,
                    snapshot_path TEXT,
                    sample_folder TEXT,
                    confidence_score REAL NOT NULL DEFAULT 0,
                    request_status TEXT NOT NULL DEFAULT 'pending',
                    admin_decision TEXT,
                    remarks TEXT,
                    created_at TEXT NOT NULL,
                    decided_at TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    setting_name TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL
                )
            """)
            self._migrate_schema(cur)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_user_model ON face_embeddings(user_id, model_name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_created_at ON access_logs(created_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_unknown_status ON unknown_attempts(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON registration_requests(request_status)")
            conn.commit()

    def _migrate_schema(self, cur) -> None:
        """Keep old local databases compatible with the latest project files."""
        def columns(table: str) -> set[str]:
            return {row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}

        migrations = {
            "users": {
                "pin_hash": "TEXT",
                "status": "TEXT NOT NULL DEFAULT 'active'",
                "samples_count": "INTEGER NOT NULL DEFAULT 0",
                "last_access": "TEXT",
                "registered_at": "TEXT NOT NULL DEFAULT 'Unknown'",
            },
            "access_logs": {
                "snapshot_path": "TEXT",
            },
            "unknown_attempts": {
                "remarks": "TEXT",
                "status": "TEXT NOT NULL DEFAULT 'new'",
            },
            "registration_requests": {
                "attempt_id": "TEXT",
                "snapshot_path": "TEXT",
                "sample_folder": "TEXT",
                "confidence_score": "REAL NOT NULL DEFAULT 0",
                "request_status": "TEXT NOT NULL DEFAULT 'pending'",
                "admin_decision": "TEXT",
                "remarks": "TEXT",
                "decided_at": "TEXT",
            },
        }
        for table, required in migrations.items():
            existing = columns(table)
            for name, definition in required.items():
                if name not in existing:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def _seed_defaults(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM admins")
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO admins(username, password_hash, created_at) VALUES (?, ?, ?)",
                    (DEFAULT_ADMIN_USERNAME, self.hash_secret(DEFAULT_ADMIN_PASSWORD), self.now()),
                )
            for name, value in DEFAULT_SETTINGS.items():
                cur.execute(
                    "INSERT OR IGNORE INTO settings(setting_name, setting_value) VALUES (?, ?)",
                    (name, value),
                )
            # The final project uses only the FaceLoginSystem dlib engine. If an
            # older database still says DeepFace, InsightFace, or OpenCV fallback,
            # migrate the setting so the UI and recognizer stay consistent.
            cur.execute(
                """
                UPDATE settings
                SET setting_value = 'facelogin_dlib'
                WHERE setting_name = 'recognition_model'
                  AND setting_value != 'facelogin_dlib'
                """
            )
            cur.execute(
                """
                UPDATE settings
                SET setting_value = '0.48'
                WHERE setting_name = 'threshold'
                  AND (setting_value IS NULL OR CAST(setting_value AS REAL) > 0.70 OR CAST(setting_value AS REAL) < 0.40)
                """
            )
            conn.commit()
