from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ..theme import COLORS, FONTS
from .buttons import primary_button


class StatCard(ctk.CTkFrame):
    def __init__(self, parent, title: str, value: str, subtitle: str, color: str, label_text: str = "") -> None:
        super().__init__(parent, fg_color=COLORS["panel"], corner_radius=20, border_width=1, border_color=color)
        self.grid_columnconfigure(1, weight=1)
        badge = ctk.CTkFrame(self, fg_color=COLORS["panel2"], corner_radius=14, border_width=1, border_color=color)
        badge.grid(row=0, column=0, rowspan=3, padx=15, pady=15, sticky="n")
        ctk.CTkLabel(badge, text=label_text or title[:2].upper(), text_color=color, font=("Segoe UI", 16, "bold"), width=42, height=42).pack()
        ctk.CTkLabel(self, text=title.upper(), text_color=COLORS["muted"], font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", pady=(15, 0))
        ctk.CTkLabel(self, text=value, text_color=COLORS["white"], font=("Segoe UI", 26, "bold")).grid(row=1, column=1, sticky="w")
        ctk.CTkLabel(self, text=subtitle, text_color=color, font=("Segoe UI", 10)).grid(row=2, column=1, sticky="w", pady=(0, 15))


class StatusPill(ctk.CTkFrame):
    def __init__(self, parent, text: str, color: str) -> None:
        super().__init__(parent, fg_color=COLORS["panel2"], corner_radius=999, border_width=1, border_color=color)
        ctk.CTkLabel(self, text=f"STATUS: {text}", text_color=color, font=("Segoe UI", 9, "bold")).pack(padx=10, pady=5)


class EmptyState(ctk.CTkFrame):
    def __init__(self, parent, title: str, message: str) -> None:
        super().__init__(parent, fg_color="transparent")
        ctk.CTkLabel(self, text=title, text_color=COLORS["white"], font=FONTS["h2"]).pack(pady=(22, 4))
        ctk.CTkLabel(self, text=message, text_color=COLORS["muted"], font=FONTS["small"], wraplength=520, justify="center").pack(pady=(0, 22))


class SectionTitle(ctk.CTkFrame):
    def __init__(self, parent, title: str, subtitle: str, action_text: str | None = None, action_command: Callable | None = None) -> None:
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=title, text_color=COLORS["white"], font=FONTS["h1"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(self, text=subtitle, text_color=COLORS["muted"], font=FONTS["small"]).grid(row=1, column=0, sticky="w", pady=(2, 0))
        if action_text:
            primary_button(self, action_text, action_command, width=155).grid(row=0, column=1, rowspan=2, sticky="e")
