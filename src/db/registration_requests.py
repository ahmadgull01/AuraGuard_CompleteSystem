from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ..config import REGISTRATION_REQUESTS_DIR


class RegistrationRequestsMixin:
    def _next_request_id(self) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT request_id FROM registration_requests ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        if not row:
            return "REQ-1001"
        digits = "".join(ch for ch in row["request_id"] if ch.isdigit())
        return f"REQ-{int(digits or 1000) + 1:04d}"

    def create_registration_request(
        self,
        attempt_id: str | None,
        snapshot_path: str | None,
        confidence_score: float,
        remarks: str,
    ) -> str:
        request_id = self._next_request_id()
        request_folder = REGISTRATION_REQUESTS_DIR / request_id
        request_folder.mkdir(parents=True, exist_ok=True)

        saved_snapshot = snapshot_path
        if snapshot_path and Path(snapshot_path).exists():
            target = request_folder / f"{request_id}_sample_001{Path(snapshot_path).suffix or '.jpg'}"
            shutil.copy2(snapshot_path, target)
            saved_snapshot = str(target)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO registration_requests(
                    request_id, attempt_id, snapshot_path, sample_folder,
                    confidence_score, request_status, admin_decision,
                    remarks, created_at, decided_at
                )
                VALUES (?, ?, ?, ?, ?, 'pending', NULL, ?, ?, NULL)
                """,
                (request_id, attempt_id, saved_snapshot, str(request_folder), float(confidence_score), remarks, self.now()),
            )
            conn.commit()
        return request_id

    def list_registration_requests(self, status: str = "all") -> list[dict[str, Any]]:
        query = "SELECT * FROM registration_requests"
        params: list[Any] = []
        if status != "all":
            query += " WHERE request_status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_registration_request(self, request_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM registration_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
        return dict(row) if row else None

    def update_registration_request_status(self, request_id: str, status: str, decision: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE registration_requests
                SET request_status = ?, admin_decision = ?, decided_at = ?
                WHERE request_id = ?
                """,
                (status, decision, self.now(), request_id),
            )
            conn.commit()

    def complete_registration_request(self, request_id: str, user_id: str) -> None:
        self.update_registration_request_status(request_id, "registered", f"Registered as {user_id}")
