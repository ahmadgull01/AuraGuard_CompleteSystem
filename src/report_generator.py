"""Report export helper."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config import LOGS_DIR
from .database_manager import DatabaseManager


class ReportGenerator:
    """Generate CSV reports for access logs, unknown attempts, users, and metrics."""

    def __init__(self, db: DatabaseManager, output_dir: Path | None = None) -> None:
        self.db = db
        self.output_dir = output_dir or LOGS_DIR

    def export(self, report_type: str) -> Path:
        """Export the selected report type and return the generated file path."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = report_type.replace(" ", "_").lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"{safe_name}_report_{timestamp}.csv"
        rows = self.db.report_data(report_type)
        return self.db.export_rows_to_csv(rows, output_path)
