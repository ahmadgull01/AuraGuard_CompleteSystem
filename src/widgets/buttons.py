from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from ..theme import COLORS


def primary_button(parent, text: str, command: Callable | None = None, **kwargs) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=COLORS["cyan"],
        hover_color=COLORS["cyan_dark"],
        text_color=COLORS["black"],
        font=("Segoe UI", 12, "bold"),
        corner_radius=14,
        height=42,
        **kwargs,
    )


def danger_button(parent, text: str, command: Callable | None = None, **kwargs) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=COLORS["red"],
        hover_color="#c81e45",
        text_color=COLORS["white"],
        font=("Segoe UI", 12, "bold"),
        corner_radius=14,
        height=42,
        **kwargs,
    )


def ghost_button(parent, text: str, command: Callable | None = None, color: str | None = None, **kwargs) -> ctk.CTkButton:
    accent = color or COLORS["cyan"]
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=COLORS["panel2"],
        hover_color=COLORS["panel3"],
        text_color=accent,
        font=("Segoe UI", 11, "bold"),
        corner_radius=12,
        border_width=1,
        border_color=accent,
        height=36,
        **kwargs,
    )
