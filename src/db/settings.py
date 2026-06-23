from __future__ import annotations

from typing import Any


class SettingsMixin:
    def verify_admin(self, username: str, password: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT password_hash FROM admins WHERE username = ?", (username,)).fetchone()
        return bool(row and row["password_hash"] == self.hash_secret(password))

    def get_settings(self) -> dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT setting_name, setting_value FROM settings").fetchall()
        return {row["setting_name"]: row["setting_value"] for row in rows}

    def get_setting(self, name: str, default: str = "") -> str:
        return self.get_settings().get(name, default)

    def update_settings(self, settings: dict[str, Any]) -> None:
        with self._connect() as conn:
            for name, value in settings.items():
                conn.execute("INSERT OR REPLACE INTO settings(setting_name, setting_value) VALUES (?, ?)", (name, str(value)))
            conn.commit()
