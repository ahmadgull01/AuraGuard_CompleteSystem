from __future__ import annotations

import customtkinter as ctk

from ..theme import COLORS, FONTS


def label(parent, text: str, font=None, color: str | None = None, **kwargs) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=text, font=font or FONTS["body"], text_color=color or COLORS["text"], **kwargs)


def panel(parent, **kwargs) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=22, border_width=1, border_color=COLORS["border_soft"], **kwargs)


def soft_panel(parent, color: str | None = None, **kwargs) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, fg_color=color or COLORS["panel2"], corner_radius=16, border_width=1, border_color=COLORS["border_soft"], **kwargs)


def _stop_animations(widget) -> None:
    if hasattr(widget, "stop_animation"):
        try:
            widget.stop_animation()
        except Exception:
            pass
    for child in list(widget.winfo_children()):
        _stop_animations(child)


def clear_frame(frame) -> None:
    for child in list(frame.winfo_children()):
        _stop_animations(child)
        try:
            child.destroy()
        except Exception:
            pass
