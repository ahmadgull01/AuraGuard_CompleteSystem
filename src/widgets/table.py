from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

import customtkinter as ctk

from ..theme import COLORS, FONTS


@dataclass(frozen=True)
class TableColumn:
    key: str
    title: str
    min_width: int
    weight: int = 1
    anchor: str = "w"


class SimpleTable:
    def __init__(self, parent, columns: Sequence[TableColumn]) -> None:
        self.columns = list(columns)
        self.frame = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=18, border_width=1, border_color=COLORS["border"])
        self.frame.grid_columnconfigure(0, weight=1)
        self.header = ctk.CTkFrame(self.frame, fg_color=COLORS["panel"], corner_radius=14)
        self.header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        self.body = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.frame.grid_rowconfigure(1, weight=1)
        self._configure_columns(self.header)
        self._draw_header()

    def _configure_columns(self, container) -> None:
        for index, col in enumerate(self.columns):
            container.grid_columnconfigure(index, weight=col.weight, minsize=col.min_width, uniform="aura_table")

    def _draw_header(self) -> None:
        for index, col in enumerate(self.columns):
            ctk.CTkLabel(
                self.header,
                text=col.title.upper(),
                text_color=COLORS["cyan"],
                font=("Segoe UI", 9, "bold"),
                anchor=col.anchor,
            ).grid(row=0, column=index, sticky="ew", padx=10, pady=10)

    def clear(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()

    def add_row(self, values: Sequence[str], colors: Sequence[str] | None = None, actions: Callable[[ctk.CTkFrame], None] | None = None) -> None:
        row_no = len(self.body.winfo_children())
        bg = COLORS["panel2"] if row_no % 2 == 0 else COLORS["panel3"]
        row = ctk.CTkFrame(self.body, fg_color=bg, corner_radius=14)
        row.pack(fill="x", padx=2, pady=5)
        self._configure_columns(row)
        for index, col in enumerate(self.columns):
            value = values[index] if index < len(values) else ""
            color = colors[index] if colors and index < len(colors) else COLORS["text"]
            if actions and index == len(self.columns) - 1:
                holder = ctk.CTkFrame(row, fg_color="transparent")
                holder.grid(row=0, column=index, sticky="w", padx=8, pady=8)
                actions(holder)
            else:
                ctk.CTkLabel(
                    row,
                    text=str(value),
                    text_color=color,
                    font=FONTS["small"],
                    anchor=col.anchor,
                ).grid(row=0, column=index, sticky="ew", padx=10, pady=12)

    def add_empty(self, title: str, message: str) -> None:
        box = ctk.CTkFrame(self.body, fg_color=COLORS["panel2"], corner_radius=16, border_width=1, border_color=COLORS["border_soft"])
        box.pack(fill="x", padx=2, pady=14)
        ctk.CTkLabel(box, text=title, text_color=COLORS["white"], font=FONTS["h2"]).pack(anchor="w", padx=18, pady=(16, 3))
        ctk.CTkLabel(box, text=message, text_color=COLORS["muted"], font=FONTS["small"], justify="left").pack(anchor="w", padx=18, pady=(0, 16))
