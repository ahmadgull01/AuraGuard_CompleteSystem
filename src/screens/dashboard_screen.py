from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from ..gui_components import EmptyState, SectionTitle, StatCard, ghost_button, panel
from ..theme import COLORS, FONTS


class DashboardScreen:
    def page_dashboard(self) -> None:
        page = self.page_container()
        page.grid_columnconfigure((0, 1, 2, 3), weight=1)
        SectionTitle(page, "System Dashboard", "Overview of users, registered face data, logs, alerts, and reports.").grid(row=0, column=0, columnspan=4, sticky="ew", padx=24, pady=(22, 18))

        stats = self.db.dashboard_stats()
        cards = [
            ("Registered Users", str(stats["total_users"]), "stored profiles", COLORS["cyan"], "US"),
            ("Access Granted", str(stats["granted_today"]), "today", COLORS["green"], "OK"),
            ("Unknown Alerts", str(stats["unknown_alerts"]), "new alerts", COLORS["orange"], "AL"),
            ("Recognition Rate", f"{stats['recognition_rate']}%", "all logs", COLORS["purple"], "RT"),
        ]
        for i, args in enumerate(cards):
            StatCard(page, *args).grid(row=1, column=i, sticky="ew", padx=(24 if i == 0 else 8, 24 if i == 3 else 8), pady=(0, 16))

        timeline = panel(page)
        timeline.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(24, 8), pady=8)
        ctk.CTkLabel(timeline, text="Access Timeline", text_color=COLORS["white"], font=FONTS["h2"]).pack(anchor="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(timeline, text="Activity will appear after real scans.", text_color=COLORS["muted"], font=FONTS["small"]).pack(anchor="w", padx=18)
        if self.db.recent_activity(1):
            self._draw_timeline(timeline)
        else:
            EmptyState(timeline, "No activity yet", "User verification attempts will create access logs here.").pack(fill="x", padx=18, pady=18)

        summary = panel(page)
        summary.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=(8, 24), pady=8)
        ctk.CTkLabel(summary, text="Decision Summary", text_color=COLORS["white"], font=FONTS["h2"]).pack(anchor="w", padx=18, pady=(16, 4))
        self._draw_decision_summary(summary, stats)

        recent = panel(page)
        recent.grid(row=3, column=0, columnspan=4, sticky="ew", padx=24, pady=(8, 24))
        recent.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(recent, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(head, text="Recent Activity", text_color=COLORS["white"], font=FONTS["h2"]).grid(row=0, column=0, sticky="w")
        ghost_button(head, "View All", lambda: self.navigate("logs"), width=105).grid(row=0, column=1, sticky="e")
        rows = self.db.recent_activity(6)
        if not rows:
            EmptyState(recent, "No records found", "Access logs will be listed here after user verification starts.").grid(row=1, column=0, sticky="ew", padx=14, pady=8)
        for r, log_row in enumerate(rows, start=1):
            self._activity_row(recent, log_row).grid(row=r, column=0, sticky="ew", padx=14, pady=3)

    def _draw_timeline(self, parent) -> None:
        canvas = tk.Canvas(parent, height=220, bg=COLORS["panel"], highlightthickness=0)
        canvas.pack(fill="x", padx=18, pady=18)
        labels = ["08", "10", "12", "14", "16", "18"]
        values = [1, 2, 1, 3, 2, 1]
        max_v = max(values) or 1
        for i, val in enumerate(values):
            x = 55 + i * 92
            bar_h = int((val / max_v) * 130)
            canvas.create_rectangle(x, 170 - bar_h, x + 42, 170, fill=COLORS["cyan"], outline="")
            canvas.create_text(x + 21, 195, text=labels[i], fill=COLORS["muted"], font=("Segoe UI", 9))

    def _draw_decision_summary(self, parent, stats: dict) -> None:
        rows = [
            ("Users", stats["total_users"], COLORS["cyan"]),
            ("Granted Today", stats["granted_today"], COLORS["green"]),
            ("Denied Today", stats["denied_today"], COLORS["red"]),
            ("New Unknown Alerts", stats["unknown_alerts"], COLORS["orange"]),
        ]
        for label, value, color in rows:
            row = ctk.CTkFrame(parent, fg_color=COLORS["panel2"], corner_radius=14)
            row.pack(fill="x", padx=18, pady=6)
            ctk.CTkLabel(row, text=label, text_color=COLORS["muted"], font=FONTS["small"]).pack(side="left", padx=14, pady=10)
            ctk.CTkLabel(row, text=str(value), text_color=color, font=("Segoe UI", 17, "bold")).pack(side="right", padx=14)

    def _activity_row(self, parent, row: dict) -> ctk.CTkFrame:
        box = ctk.CTkFrame(parent, fg_color=COLORS["panel2"], corner_radius=12)
        box.grid_columnconfigure(1, weight=1)
        status = row["access_status"]
        color = COLORS["green"] if status == "granted" else COLORS["red"]
        ctk.CTkLabel(box, text="OK" if status == "granted" else "NO", text_color=color, font=("Segoe UI", 13, "bold"), width=42).grid(row=0, column=0, padx=14, pady=10)
        ctk.CTkLabel(box, text=row["full_name"], text_color=COLORS["white"], font=FONTS["body_bold"]).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(box, text=f"{row['created_at']}  |  {row['confidence_score']:.1f}%", text_color=COLORS["muted"], font=FONTS["tiny"]).grid(row=1, column=1, sticky="w", pady=(0, 9))
        ctk.CTkLabel(box, text=status.upper(), text_color=color, font=FONTS["tiny"]).grid(row=0, column=2, rowspan=2, padx=14)
        return box
