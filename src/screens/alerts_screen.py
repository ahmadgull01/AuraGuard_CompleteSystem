from __future__ import annotations

import tkinter as tk
from typing import Any

import customtkinter as ctk

from ..gui_components import EmptyState, SectionTitle, clear_frame, ghost_button, panel
from ..theme import COLORS, FONTS


class AlertsScreen:
    def page_alerts(self) -> None:
        page = self.page_container()
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=1)
        SectionTitle(page, "Unknown Alerts", "Review unauthorized or unknown face attempts.").grid(row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(22, 18))
        left = panel(page)
        left.grid(row=1, column=0, sticky="nsew", padx=(24, 10), pady=(0, 24))
        right = panel(page)
        right.grid(row=1, column=1, sticky="nsew", padx=(10, 24), pady=(0, 24))
        self.alert_filter = tk.StringVar(value="all")
        ctk.CTkSegmentedButton(left, values=["all", "new", "reviewed", "resolved"], variable=self.alert_filter, command=lambda _v: self.refresh_alerts(), selected_color=COLORS["orange"]).pack(fill="x", padx=16, pady=16)
        self.alerts_list = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.alerts_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.alert_detail = right
        self.refresh_alerts()

    def refresh_alerts(self) -> None:
        clear_frame(self.alerts_list)
        rows = self.db.list_unknown_attempts(self.alert_filter.get())
        if not rows:
            EmptyState(self.alerts_list, "No alerts", "Unknown face alerts will appear here.").pack(fill="x", padx=12, pady=24)
            clear_frame(self.alert_detail)
            EmptyState(self.alert_detail, "Nothing selected", "Select an alert to review details.").pack(fill="x", padx=18, pady=35)
            return
        for row in rows:
            color = COLORS["red"] if row["status"] == "new" else COLORS["orange"] if row["status"] == "reviewed" else COLORS["green"]
            card = ctk.CTkFrame(self.alerts_list, fg_color=COLORS["panel2"], corner_radius=16, border_width=1, border_color=color)
            card.pack(fill="x", padx=4, pady=6)
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(card, text=f"{row['alert_id']} - {row['attempt_id']}", text_color=color, font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
            ctk.CTkLabel(card, text=row["created_at"], text_color=COLORS["muted"], font=FONTS["tiny"]).grid(row=1, column=0, sticky="w", padx=14)
            ctk.CTkLabel(card, text=row["remarks"], text_color=COLORS["text"], font=FONTS["small"], wraplength=360).grid(row=2, column=0, sticky="w", padx=14, pady=(2, 12))
            card.bind("<Button-1>", lambda _e, r=row: self.show_alert_detail(r))
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda _e, r=row: self.show_alert_detail(r))
        self.show_alert_detail(rows[0])

    def show_alert_detail(self, row: dict[str, Any]) -> None:
        clear_frame(self.alert_detail)
        ctk.CTkLabel(self.alert_detail, text="ALERT DETAIL", text_color=COLORS["orange"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=18, pady=(18, 6))
        ctk.CTkLabel(self.alert_detail, text=row["snapshot_path"] or "No snapshot saved", text_color=COLORS["white"], font=FONTS["h2"]).pack(anchor="w", padx=18)
        details = [
            ("Alert ID", row["alert_id"]),
            ("Attempt ID", row["attempt_id"]),
            ("Date and Time", row["created_at"]),
            ("Confidence", f"{row['confidence_score']:.1f}%"),
            ("Liveness", row["liveness_status"]),
            ("Detection", row["detection_status"]),
            ("Decision", "DENIED"),
            ("Status", row["status"].upper()),
        ]
        for k, v in details:
            line = ctk.CTkFrame(self.alert_detail, fg_color=COLORS["panel2"], corner_radius=12)
            line.pack(fill="x", padx=18, pady=5)
            ctk.CTkLabel(line, text=k, text_color=COLORS["muted"], font=FONTS["tiny"]).pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(line, text=str(v), text_color=COLORS["text"], font=FONTS["small"]).pack(side="right", padx=12)
        ctk.CTkLabel(self.alert_detail, text="Remarks", text_color=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=18, pady=(12, 2))
        ctk.CTkLabel(self.alert_detail, text=row["remarks"], text_color=COLORS["text"], font=FONTS["small"], wraplength=450, justify="left").pack(anchor="w", padx=18)
        btnrow = ctk.CTkFrame(self.alert_detail, fg_color="transparent")
        btnrow.pack(fill="x", padx=18, pady=18)
        ghost_button(btnrow, "Mark Reviewed", lambda: self._set_alert_status(row["attempt_id"], "reviewed"), color=COLORS["orange"], width=140).pack(side="left", padx=(0, 8))
        ghost_button(btnrow, "Resolve", lambda: self._set_alert_status(row["attempt_id"], "resolved"), color=COLORS["green"], width=120).pack(side="left")

    def _set_alert_status(self, attempt_id: str, status: str) -> None:
        self.db.update_unknown_status(attempt_id, status)
        self.refresh_alerts()
