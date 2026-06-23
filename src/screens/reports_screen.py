from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from ..gui_components import EmptyState, SectionTitle, panel, primary_button
from ..theme import COLORS, FONTS


class ReportsScreen:
    def page_reports(self) -> None:
        page = self.page_container()
        page.grid_columnconfigure((0, 1, 2, 3), weight=1)
        SectionTitle(page, "Export Reports", "Create CSV files for review or submission.").grid(row=0, column=0, columnspan=4, sticky="ew", padx=24, pady=(22, 18))
        reports = [
            ("access", "Access Log Report", "Authentication attempts with confidence and liveness status", COLORS["cyan"]),
            ("unknown", "Unknown Attempts Report", "Unauthorized attempts with snapshot references", COLORS["orange"]),
            ("users", "User Summary Report", "Registered users and account status", COLORS["purple"]),
            ("performance", "System Performance Report", "Counts, recognition rate, and metrics", COLORS["green"]),
        ]
        for i, (rtype, title, desc, color) in enumerate(reports):
            card = panel(page)
            card.grid(row=1, column=i, sticky="nsew", padx=(24 if i == 0 else 8, 24 if i == 3 else 8), pady=(0, 18))
            ctk.CTkLabel(card, text=title, text_color=color, font=FONTS["h2"], wraplength=210).pack(anchor="w", padx=16, pady=(16, 8))
            ctk.CTkLabel(card, text=desc, text_color=COLORS["muted"], font=FONTS["small"], wraplength=220, justify="left").pack(anchor="w", padx=16)
            primary_button(card, "Export CSV", lambda rt=rtype: self.export_report(rt)).pack(fill="x", padx=16, pady=16)
        preview = panel(page)
        preview.grid(row=2, column=0, columnspan=4, sticky="ew", padx=24, pady=(0, 24))
        ctk.CTkLabel(preview, text="Report Preview", text_color=COLORS["white"], font=FONTS["h2"]).pack(anchor="w", padx=18, pady=(16, 8))
        rows = self.db.recent_activity(5)
        if not rows:
            EmptyState(preview, "No preview available", "Scan a face or register users to create report data.").pack(fill="x", padx=18, pady=12)
        for row in rows:
            ctk.CTkLabel(preview, text=f"{row['log_id']} | {row['full_name']} | {row['confidence_score']:.1f}% | {row['access_status']}", text_color=COLORS["muted"], font=FONTS["small"]).pack(anchor="w", padx=18, pady=3)

    def export_report(self, report_type: str) -> None:
        path = self.reporter.export(report_type)
        messagebox.showinfo("Report Exported", f"Saved to:\n{path}")
