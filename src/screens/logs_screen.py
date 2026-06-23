from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..gui_components import SectionTitle, ghost_button
from ..theme import COLORS
from ..widgets.table import SimpleTable, TableColumn


class LogsScreen:
    def page_logs(self) -> None:
        page = self.page_container()
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)
        SectionTitle(page, "Access Logs", "All successful, denied, unknown, and liveness-failed attempts are saved here.", "Export CSV", self.export_access_logs).grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 18))

        toolbar = ctk.CTkFrame(page, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)
        self.log_search = tk.StringVar()
        self.log_status = tk.StringVar(value="all")
        self.log_date = tk.StringVar(value="")

        search_box = ctk.CTkEntry(toolbar, textvariable=self.log_search, placeholder_text="Search by name, user ID, or log ID", fg_color=COLORS["panel2"], border_color=COLORS["border"], height=40, corner_radius=12)
        search_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        search_box.bind("<KeyRelease>", lambda _e: self.refresh_logs_table())
        ctk.CTkEntry(toolbar, textvariable=self.log_date, placeholder_text="YYYY-MM-DD", fg_color=COLORS["panel2"], border_color=COLORS["border"], width=140, height=40, corner_radius=12).grid(row=0, column=1, padx=8)
        ctk.CTkSegmentedButton(toolbar, values=["all", "granted", "denied"], variable=self.log_status, command=lambda _v: self.refresh_logs_table(), selected_color=COLORS["cyan"]).grid(row=0, column=2, padx=8)
        ghost_button(toolbar, "Apply Date", self.refresh_logs_table).grid(row=0, column=3, padx=(8, 0))

        columns = [
            TableColumn("log_id", "Log ID", 105, 1),
            TableColumn("user_id", "User ID", 105, 1),
            TableColumn("name", "Name", 190, 2),
            TableColumn("date", "Date", 115, 1),
            TableColumn("time", "Time", 100, 1),
            TableColumn("confidence", "Confidence", 115, 1),
            TableColumn("liveness", "Liveness", 105, 1),
            TableColumn("status", "Status", 105, 1),
        ]
        self.logs_table = SimpleTable(page, columns)
        self.logs_table.frame.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 24))
        self.refresh_logs_table()

    def refresh_logs_table(self) -> None:
        self.logs_table.clear()
        rows = self.db.list_access_logs(self.log_search.get(), self.log_status.get(), self.log_date.get())
        if not rows:
            self.logs_table.add_empty("No logs yet", "Registered user verification will create access records automatically.")
            return
        for row in rows:
            date_time = row["created_at"].split(" ")
            values = [
                row["log_id"], row["user_id"] or "-", row["full_name"],
                date_time[0], date_time[1] if len(date_time) > 1 else "",
                f"{row['confidence_score']:.1f}%", row["liveness_status"], row["access_status"],
            ]
            colors = [COLORS["text"]] * len(values)
            if row["liveness_status"] == "Pass":
                colors[6] = COLORS["green"]
            elif row["liveness_status"] == "Fail":
                colors[6] = COLORS["red"]
            colors[7] = COLORS["green"] if row["access_status"] == "granted" else COLORS["red"]
            self.logs_table.add_row(values, colors)

    def export_access_logs(self) -> None:
        rows = self.db.list_access_logs(self.log_search.get(), self.log_status.get(), self.log_date.get())
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile="access_logs.csv")
        if path:
            self.db.export_rows_to_csv(rows, Path(path))
            messagebox.showinfo("Export Complete", f"Access logs exported to:\n{path}")
