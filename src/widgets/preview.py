from __future__ import annotations

import customtkinter as ctk

from ..theme import COLORS, FONTS
from .scanner import ScannerCanvas


class ScannerPlaceholder(ctk.CTkFrame):
    def __init__(self, parent, title: str, message: str, width: int = 700, height: int = 440) -> None:
        super().__init__(parent, fg_color=COLORS["panel2"], corner_radius=20, border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text=title, text_color=COLORS["cyan"], font=("Segoe UI", 12, "bold")).grid(row=0, column=0, pady=(18, 4))
        self.scanner = ScannerCanvas(self, width=width, height=height)
        self.scanner.grid(row=1, column=0, sticky="nsew", padx=18, pady=(4, 12))
        ctk.CTkLabel(self, text=message, text_color=COLORS["muted"], font=FONTS["small"], wraplength=width).grid(row=2, column=0, padx=18, pady=(0, 18))
