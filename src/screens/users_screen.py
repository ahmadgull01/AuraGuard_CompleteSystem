from __future__ import annotations

import shutil
import tkinter as tk
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from ..config import REGISTERED_FACES_DIR
from ..gui_components import EmptyState, SectionTitle, clear_frame, ghost_button, panel, primary_button
from ..theme import COLORS, FONTS
from ..widgets.table import SimpleTable, TableColumn


class UsersScreen:
    def page_users(self) -> None:
        page = self.page_container()
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)
        SectionTitle(page, "User Management", "Manage registered users, roles, status, and saved face samples.", "Add User", self.open_add_user_dialog).grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 18))

        toolbar = ctk.CTkFrame(page, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)
        self.user_search = tk.StringVar()
        self.user_filter = tk.StringVar(value="all")
        search = ctk.CTkEntry(toolbar, textvariable=self.user_search, placeholder_text="Search by name or user ID", fg_color=COLORS["panel2"], border_color=COLORS["border"], height=40, corner_radius=12)
        search.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        search.bind("<KeyRelease>", lambda _e: self.refresh_users_table())
        seg = ctk.CTkSegmentedButton(toolbar, values=["all", "active", "inactive"], variable=self.user_filter, command=lambda _v: self.refresh_users_table(), selected_color=COLORS["cyan"])
        seg.grid(row=0, column=1, padx=8)

        columns = [
            TableColumn("user_id", "User ID", 105, 1),
            TableColumn("name", "Name", 180, 2),
            TableColumn("role", "Role", 145, 2),
            TableColumn("status", "Status", 100, 1),
            TableColumn("samples", "Samples", 90, 1),
            TableColumn("last", "Last Access", 165, 2),
            TableColumn("actions", "Actions", 180, 2),
        ]
        self.users_table = SimpleTable(page, columns)
        self.users_table.frame.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 24))
        self.refresh_users_table()

    def refresh_users_table(self) -> None:
        self.users_table.clear()
        users = self.db.list_users(self.user_search.get() if hasattr(self, "user_search") else "", self.user_filter.get() if hasattr(self, "user_filter") else "all")
        if not users:
            self.users_table.add_empty("No users found", "Register a user from the Register Face Data tab or use Add User for a manual profile.")
            return
        for user in users:
            self._user_row(user)

    def _user_row(self, user: dict[str, Any]) -> None:
        values = [
            user["user_id"],
            user["full_name"],
            user["role"],
            user["status"],
            str(user["samples_count"]),
            user.get("last_access") or "Never",
            "",
        ]
        colors = [
            COLORS["text"], COLORS["text"], COLORS["text"],
            COLORS["green"] if user["status"] == "active" else COLORS["red"],
            COLORS["text"], COLORS["text"], COLORS["text"],
        ]

        def actions(holder) -> None:
            ghost_button(holder, "Edit", lambda uid=user["user_id"]: self.open_edit_user_dialog(uid), width=72, color=COLORS["cyan"]).pack(side="left", padx=(0, 6))
            ghost_button(holder, "Delete", lambda uid=user["user_id"]: self.delete_user_confirm(uid), width=82, color=COLORS["red"]).pack(side="left")

        self.users_table.add_row(values, colors, actions)

    def open_add_user_dialog(self) -> None:
        self._user_dialog("Add User")

    def open_edit_user_dialog(self, user_id: str) -> None:
        users = [u for u in self.db.list_users() if u["user_id"] == user_id]
        if users:
            self._user_dialog("Edit User", users[0])

    def _user_dialog(self, title: str, user: dict[str, Any] | None = None) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("430x440")
        dialog.configure(fg_color=COLORS["bg"])
        dialog.grab_set()
        dialog.focus_force()

        box = panel(dialog)
        box.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(box, text=title, text_color=COLORS["white"], font=FONTS["h1"]).pack(anchor="w", padx=18, pady=(18, 12))

        user_id = tk.StringVar(value=user["user_id"] if user else f"USR-{len(self.db.list_users()) + 1:03d}")
        name = tk.StringVar(value=user["full_name"] if user else "")
        role = tk.StringVar(value=user["role"] if user else "")
        status = tk.StringVar(value=user["status"] if user else "active")
        pin = tk.StringVar()

        fields = [("User ID", user_id, bool(user)), ("Full Name", name, False), ("Role", role, False), ("PIN Optional", pin, False)]
        for text, var, disabled in fields:
            ctk.CTkLabel(box, text=text.upper(), text_color=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=18, pady=(8, 2))
            ctk.CTkEntry(box, textvariable=var, state="disabled" if disabled else "normal", fg_color=COLORS["panel2"], border_color=COLORS["border"], height=36).pack(fill="x", padx=18)

        ctk.CTkLabel(box, text="STATUS", text_color=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=18, pady=(8, 2))
        ctk.CTkSegmentedButton(box, values=["active", "inactive"], variable=status, selected_color=COLORS["cyan"]).pack(fill="x", padx=18)

        def save() -> None:
            if not user_id.get().strip() or not name.get().strip() or not role.get().strip():
                messagebox.showwarning("Missing Data", "User ID, name, and role are required.")
                return
            if user:
                self.db.update_user(user_id.get().strip(), name.get().strip(), role.get().strip(), status.get())
            else:
                if self.db.user_exists(user_id.get().strip()):
                    messagebox.showerror("Duplicate User", "This user ID already exists.")
                    return
                self.db.add_user(user_id.get().strip(), name.get().strip(), role.get().strip(), pin.get().strip() or None, status.get())
            dialog.destroy()
            self.refresh_users_table()

        primary_button(box, "Save User", save).pack(fill="x", padx=18, pady=(18, 18))

    def delete_user_confirm(self, user_id: str) -> None:
        if not messagebox.askyesno("Delete User", f"Delete {user_id} and all related face embeddings?"):
            return
        self.db.delete_user(user_id)
        folder = REGISTERED_FACES_DIR / user_id
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
        self.refresh_users_table()
