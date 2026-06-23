from __future__ import annotations

from typing import Any


class UsersMixin:
    def add_user(self, user_id: str, full_name: str, role: str, pin: str | None = None, status: str = "active") -> None:
        pin_hash = self.hash_secret(pin) if pin else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users(user_id, full_name, role, pin_hash, status, samples_count, last_access, registered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, full_name, role, pin_hash, status, 0, "Never", self.now()),
            )
            conn.commit()

    def update_user(self, user_id: str, full_name: str, role: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE users SET full_name = ?, role = ?, status = ? WHERE user_id = ?", (full_name, role, status, user_id))
            conn.commit()

    def delete_user(self, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM face_embeddings WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()

    def update_user_samples_count(self, user_id: str, count: int) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE users SET samples_count = ? WHERE user_id = ?", (count, user_id))
            conn.commit()

    def list_users(self, search: str = "", status: str = "all") -> list[dict[str, Any]]:
        query = "SELECT * FROM users WHERE 1=1"
        params: list[Any] = []
        if search:
            term = f"%{search.lower()}%"
            query += " AND (LOWER(full_name) LIKE ? OR LOWER(user_id) LIKE ?)"
            params.extend([term, term])
        if status != "all":
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY registered_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


    def next_user_id(self) -> str:
        with self._connect() as conn:
            rows = conn.execute("SELECT user_id FROM users WHERE user_id LIKE 'USR-%'").fetchall()
        highest = 0
        for row in rows:
            digits = ''.join(ch for ch in row['user_id'] if ch.isdigit())
            if digits:
                highest = max(highest, int(digits))
        return f"USR-{highest + 1:03d}"

    @staticmethod
    def is_valid_user_id(user_id: str) -> bool:
        if not user_id or len(user_id) > 32:
            return False
        blocked = set('\\/:*?"<>| ')
        return not any(ch in blocked for ch in user_id)

    def user_exists(self, user_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row is not None

    def verify_user_pin(self, user_id: str, pin: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT pin_hash FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return bool(row and row["pin_hash"] and row["pin_hash"] == self.hash_secret(pin))
