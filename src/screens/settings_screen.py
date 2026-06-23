from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from ..gui_components import SectionTitle, panel, primary_button
from ..theme import COLORS, FONTS
from ..widgets.forms import form_entry


class SettingsScreen:
    def page_settings(self) -> None:
        page = self.page_container()
        page.grid_columnconfigure(0, weight=2)
        page.grid_columnconfigure(1, weight=1)
        SectionTitle(page, "Settings", "Change FaceLogin-Dlib recognition, camera, security, and report preferences.", "Save Settings", self.save_settings).grid(row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(22, 18))

        settings = self.db.get_settings()
        self.setting_vars: dict[str, tk.Variable] = {}

        left = ctk.CTkFrame(page, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(24, 10), pady=(0, 24))
        right = ctk.CTkFrame(page, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew", padx=(10, 24), pady=(0, 24))

        self._settings_section(left, "Recognition", COLORS["cyan"], [
            ("recognition_model", "Active model", "readonly", ["facelogin_dlib"]),
            ("threshold", "Face distance threshold", "slider", None),
            ("max_samples", "Registration samples", "number", None),
        ], settings)
        self._settings_section(left, "Security", COLORS["purple"], [
            ("liveness_enabled", "Liveness detection", "switch", None),
            ("two_factor_enabled", "Two factor verification", "switch", None),
            ("snapshot_enabled", "Save unknown snapshots", "switch", None),
            ("min_face_size", "Minimum face size", "number", None),
        ], settings)
        self._settings_section(left, "Session and Device", COLORS["orange"], [
            ("camera_index", "Camera index", "number", None),
            ("frame_rate", "Target frame rate", "number", None),
            ("sound_enabled", "Sound alerts", "switch", None),
            ("voice_feedback", "Voice feedback", "switch", None),
        ], settings)

        self._database_card(right, settings)
        self._active_config_card(right, settings)

    def _settings_section(self, parent, title: str, color: str, items: list[tuple[str, str, str, list[str] | None]], settings: dict[str, str]) -> None:
        card = panel(parent)
        card.pack(fill="x", pady=(0, 14))
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, text_color=color, font=FONTS["h2"]).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))

        for row_no, (key, display, kind, options) in enumerate(items, start=1):
            row = ctk.CTkFrame(card, fg_color=COLORS["panel2"], corner_radius=14)
            row.grid(row=row_no, column=0, sticky="ew", padx=18, pady=6)
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, minsize=190)
            ctk.CTkLabel(row, text=display, text_color=COLORS["white"], font=FONTS["small"]).grid(row=0, column=0, sticky="w", padx=14, pady=(9, 0))
            ctk.CTkLabel(row, text=key, text_color=COLORS["muted2"], font=FONTS["tiny"]).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 9))
            self._setting_control(row, key, kind, options, settings, color).grid(row=0, column=1, rowspan=2, sticky="e", padx=14, pady=8)

    def _setting_control(self, parent, key: str, kind: str, options: list[str] | None, settings: dict[str, str], color: str):
        if kind == "switch":
            var = tk.BooleanVar(value=settings.get(key, "false") == "true")
            self.setting_vars[key] = var
            return ctk.CTkSwitch(parent, text="", variable=var, progress_color=color, button_color=COLORS["white"], fg_color=COLORS["border"], width=72)
        if kind == "option":
            var = tk.StringVar(value=settings.get(key, options[0] if options else ""))
            self.setting_vars[key] = var
            return ctk.CTkOptionMenu(parent, variable=var, values=options or [], fg_color=COLORS["panel3"], button_color=color, button_hover_color=color, width=170)
        if kind == "readonly":
            value = "FaceLogin-Dlib"
            var = tk.StringVar(value="facelogin_dlib")
            self.setting_vars[key] = var
            label = ctk.CTkLabel(parent, text=value, text_color=COLORS["green"], fg_color=COLORS["panel3"], corner_radius=10, width=170, font=FONTS["small"])
            return label
        if kind == "slider":
            raw_value = float(settings.get(key, "0.45"))
            if raw_value > 0.70:
                raw_value = 0.45
            raw_value = max(0.35, min(raw_value, 0.60))
            var = tk.DoubleVar(value=raw_value)
            self.setting_vars[key] = var
            return ctk.CTkSlider(parent, variable=var, from_=0.35, to=0.60, progress_color=color, button_color=color, width=170)
        var = tk.StringVar(value=settings.get(key, ""))
        self.setting_vars[key] = var
        return ctk.CTkEntry(parent, textvariable=var, width=170, fg_color=COLORS["panel3"], border_color=COLORS["border"], corner_radius=10)

    def _database_card(self, parent, settings: dict[str, str]) -> None:
        dbcard = panel(parent)
        dbcard.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(dbcard, text="Database", text_color=COLORS["white"], font=FONTS["h2"]).pack(anchor="w", padx=18, pady=(16, 8))
        stats = self.db.dashboard_stats()
        info = [
            ("Engine", "SQLite"),
            ("Database file", "aura_guard.db"),
            ("Registered users", stats["total_users"]),
            ("Unknown attempts", len(self.db.list_unknown_attempts())),
        ]
        for key, value in info:
            self._info_row(dbcard, key, value)

    def _active_config_card(self, parent, settings: dict[str, str]) -> None:
        active = panel(parent)
        active.pack(fill="x")
        ctk.CTkLabel(active, text="Current Session", text_color=COLORS["white"], font=FONTS["h2"]).pack(anchor="w", padx=18, pady=(16, 8))
        current = dict(settings)
        current["recognition_model"] = "FaceLogin-Dlib"
        if float(current.get("threshold", "0.45") if str(current.get("threshold", "0.45")).replace('.', '', 1).isdigit() else "0.45") > 0.70:
            current["threshold"] = "0.45"
        for key in ["recognition_model", "threshold", "liveness_enabled", "snapshot_enabled", "camera_index"]:
            self._info_row(active, key.replace("_", " ").title(), current.get(key, ""))

    def _info_row(self, parent, label_text: str, value: Any) -> None:
        row = ctk.CTkFrame(parent, fg_color=COLORS["panel2"], corner_radius=12)
        row.pack(fill="x", padx=18, pady=4)
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(row, text=str(label_text), text_color=COLORS["muted"], font=FONTS["tiny"]).grid(row=0, column=0, sticky="w", padx=12, pady=8)
        ctk.CTkLabel(row, text=str(value), text_color=COLORS["text"], font=FONTS["small"]).grid(row=0, column=1, sticky="e", padx=12)

    def save_settings(self) -> None:
        new_settings: dict[str, Any] = {}
        numeric_defaults = {
            "max_samples": 20,
            "camera_index": 0,
            "frame_rate": 24,
            "min_face_size": 80,
        }
        for key, var in self.setting_vars.items():
            value = var.get()
            if isinstance(value, bool):
                value = "true" if value else "false"
            if key == "threshold":
                value = max(0.35, min(float(value), 0.60))
                value = f"{value:.2f}"
            if key == "recognition_model":
                value = "facelogin_dlib"
            if key in numeric_defaults:
                try:
                    value = int(str(value).strip())
                except ValueError:
                    value = numeric_defaults[key]
                if key == "max_samples":
                    value = max(20, min(value, 60))
                if key == "min_face_size":
                    value = max(50, min(value, 180))
                if key == "frame_rate":
                    value = max(10, min(value, 60))
                if key == "camera_index":
                    value = max(0, value)
            new_settings[key] = value
        self.db.update_settings(new_settings)
        self.recognizer.reload_settings()
        messagebox.showinfo("Settings Saved", "Settings saved successfully.")
        self.navigate("settings")
