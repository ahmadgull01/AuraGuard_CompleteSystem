"""SQLite entry point for AURA Guard.

The old version had every query in one long file.  This version keeps the
public class name the same, but moves the actual work into small feature
mixins under ``src/db``.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

from .config import DATABASE_PATH, ensure_directories
from .db.schema import SchemaMixin
from .db.settings import SettingsMixin
from .db.users import UsersMixin
from .db.embeddings import EmbeddingsMixin
from .db.logs import LogsMixin
from .db.stats_reports import StatsReportsMixin
from .db.registration_requests import RegistrationRequestsMixin


class DatabaseManager(
    SchemaMixin,
    SettingsMixin,
    UsersMixin,
    EmbeddingsMixin,
    LogsMixin,
    StatsReportsMixin,
    RegistrationRequestsMixin,
):
    """Small public wrapper around all SQLite operations."""

    def __init__(self, db_path: Path = DATABASE_PATH) -> None:
        ensure_directories()
        self.db_path = Path(db_path)
        self._create_schema()
        self._seed_defaults()

    def _connect(self) -> sqlite3.Connection:
        # Every query uses this helper so row results behave like dictionaries.
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def hash_secret(value: str) -> str:
        # A simple SHA-256 hash is enough for this academic/local project.
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
