from __future__ import annotations

from typing import Any


class LogsMixin:
    def _next_id(self, table: str, column: str, prefix: str) -> str:
        with self._connect() as conn:
            row = conn.execute(f"SELECT {column} FROM {table} ORDER BY created_at DESC LIMIT 1").fetchone()
        if not row:
            return f"{prefix}-1001"
        digits = "".join(ch for ch in row[column] if ch.isdigit())
        return f"{prefix}-{int(digits or 1000) + 1:04d}"

    def add_access_log(self, user_id: str | None, full_name: str, confidence_score: float, liveness_status: str, access_status: str, snapshot_path: str | None = None) -> str:
        log_id = self._next_id("access_logs", "log_id", "LOG")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO access_logs(log_id, user_id, full_name, confidence_score, liveness_status, access_status, snapshot_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (log_id, user_id, full_name, float(confidence_score), liveness_status, access_status, snapshot_path, self.now()),
            )
            if user_id and user_id != "UNKNOWN":
                conn.execute("UPDATE users SET last_access = ? WHERE user_id = ?", (self.now(), user_id))
            conn.commit()
        return log_id

    def add_unknown_attempt(self, confidence_score: float, liveness_status: str, detection_status: str, snapshot_path: str | None, remarks: str, status: str = "new") -> tuple[str, str]:
        attempt_id = self._next_id("unknown_attempts", "attempt_id", "ATT")
        alert_id = "ALT-" + attempt_id.split("-")[-1]
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO unknown_attempts(attempt_id, alert_id, confidence_score, liveness_status, detection_status, snapshot_path, remarks, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (attempt_id, alert_id, float(confidence_score), liveness_status, detection_status, snapshot_path, remarks, status, self.now()),
            )
            conn.commit()
        return attempt_id, alert_id

    def list_access_logs(self, search: str = "", status: str = "all", date_filter: str = "") -> list[dict[str, Any]]:
        query = "SELECT * FROM access_logs WHERE 1=1"
        params: list[Any] = []
        if search:
            term = f"%{search.lower()}%"
            query += " AND (LOWER(log_id) LIKE ? OR LOWER(user_id) LIKE ? OR LOWER(full_name) LIKE ?)"
            params.extend([term, term, term])
        if status != "all":
            query += " AND access_status = ?"
            params.append(status)
        if date_filter:
            query += " AND substr(created_at, 1, 10) = ?"
            params.append(date_filter)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def list_unknown_attempts(self, status: str = "all") -> list[dict[str, Any]]:
        query = "SELECT * FROM unknown_attempts"
        params: list[Any] = []
        if status != "all":
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def update_unknown_status(self, attempt_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE unknown_attempts SET status = ? WHERE attempt_id = ?", (status, attempt_id))
            conn.commit()
