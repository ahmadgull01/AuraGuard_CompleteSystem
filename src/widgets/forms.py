from __future__ import annotations

import customtkinter as ctk

from ..theme import COLORS, FONTS


def form_label(parent, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text=text,
        text_color=COLORS["muted"],
        font=("Segoe UI", 10, "bold"),
    )


def form_entry(parent, variable, placeholder: str = "", secret: bool = False) -> ctk.CTkEntry:
    return ctk.CTkEntry(
        parent,
        textvariable=variable,
        placeholder_text=placeholder,
        show="*" if secret else "",
        fg_color=COLORS["panel2"],
        border_color=COLORS["border"],
        text_color=COLORS["text"],
        placeholder_text_color=COLORS["muted2"],
        height=44,
        corner_radius=12,
        font=FONTS["body"],
    )
