from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any


class StatsReportsMixin:
    def dashboard_stats(self) -> dict[str, Any]:
        today = date.today().strftime("%Y-%m-%d")
        with self._connect() as conn:
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            granted_today = conn.execute(
                "SELECT COUNT(*) FROM access_logs WHERE access_status = 'granted' AND substr(created_at, 1, 10) = ?",
                (today,),
            ).fetchone()[0]
            denied_today = conn.execute(
                "SELECT COUNT(*) FROM access_logs WHERE access_status = 'denied' AND substr(created_at, 1, 10) = ?",
                (today,),
            ).fetchone()[0]
            unknown_count = conn.execute("SELECT COUNT(*) FROM unknown_attempts WHERE status = 'new'").fetchone()[0]
            total_logs = conn.execute("SELECT COUNT(*) FROM access_logs").fetchone()[0]
            granted_logs = conn.execute("SELECT COUNT(*) FROM access_logs WHERE access_status = 'granted'").fetchone()[0]
        rate = round((granted_logs / total_logs) * 100, 1) if total_logs else 0.0
        return {
            "total_users": total_users,
            "granted_today": granted_today,
            "denied_today": denied_today,
            "unknown_alerts": unknown_count,
            "recognition_rate": rate,
        }

    def recent_activity(self, limit: int = 6) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM access_logs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def export_rows_to_csv(self, rows: list[dict[str, Any]], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not rows:
            output_path.write_text("No data available\n", encoding="utf-8")
            return output_path
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return output_path

    def report_data(self, report_type: str) -> list[dict[str, Any]]:
        if report_type == "access":
            return self.list_access_logs()
        if report_type == "unknown":
            return self.list_unknown_attempts()
        if report_type == "users":
            return self.list_users()
        if report_type == "performance":
            stats = self.dashboard_stats()
            return [{"metric": k, "value": v} for k, v in stats.items()]
        return []
