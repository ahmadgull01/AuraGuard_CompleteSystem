from __future__ import annotations

import tkinter as tk
import customtkinter as ctk

from .gui_components import StatusPill, clear_frame, ghost_button, panel, primary_button, soft_panel
from .theme import COLORS, FONTS, SIDEBAR_WIDTH
from .widgets.forms import form_entry, form_label
from .widgets.preview import ScannerPlaceholder
from .widgets.safety import widget_alive


class ShellMixin:
    def _reset_root_grid(self) -> None:
        # Tk keeps old grid weights after changing screens.
        # Clearing them keeps the admin sidebar fixed instead of stretching.
        for index in range(6):
            self.grid_columnconfigure(index, weight=0, minsize=0)
            self.grid_rowconfigure(index, weight=0, minsize=0)

    def show_start_screen(self) -> None:
        try:
            self.unbind("<Return>")
        except Exception:
            pass
        self.stop_camera_loops(reset_preview=False)
        self.logged_in = False
        clear_frame(self)
        self._reset_root_grid()
        self.configure(fg_color=COLORS["bg"])
        self.grid_columnconfigure(0, weight=1, minsize=0)
        self.grid_columnconfigure(1, weight=0, minsize=0)
        self.grid_rowconfigure(0, weight=1, minsize=0)

        outer = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        outer.grid(row=0, column=0, sticky="nsew")
        outer.grid_columnconfigure(0, weight=3)
        outer.grid_columnconfigure(1, weight=2)
        outer.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(outer, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(70, 35), pady=55)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        hero = panel(left)
        hero.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        hero.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hero, text="AURA Guard", text_color=COLORS["white"], font=FONTS["display"]).grid(row=0, column=0, sticky="w", padx=24, pady=(24, 2))
        ctk.CTkLabel(hero, text="Face recognition with liveness-based access control", text_color=COLORS["cyan"], font=FONTS["body_bold"]).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 22))
        StatusPill(hero, "LOCAL SYSTEM", COLORS["green"]).grid(row=0, column=1, rowspan=2, sticky="e", padx=24)

        visual = panel(left)
        visual.grid(row=1, column=0, sticky="nsew")
        visual.grid_columnconfigure(0, weight=1)
        visual.grid_rowconfigure(0, weight=1)
        ScannerPlaceholder(
            visual,
            "FACE VERIFICATION AREA",
            "Choose a mode from the right side. User verification opens a live scanner. Admin login opens the control panel.",
            width=650,
            height=380,
        ).grid(row=0, column=0, sticky="nsew", padx=22, pady=22)

        right = ctk.CTkFrame(outer, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(35, 80), pady=70)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure((0, 3), weight=1)

        choose = panel(right)
        choose.grid(row=1, column=0, sticky="ew")
        choose.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(choose, text="Select Login Mode", text_color=COLORS["white"], font=("Segoe UI", 26, "bold")).grid(row=0, column=0, sticky="w", padx=26, pady=(28, 4))
        ctk.CTkLabel(choose, text="Use admin login for management. Use registered user verification for face-based access.", text_color=COLORS["muted"], font=FONTS["small"], wraplength=360, justify="left").grid(row=1, column=0, sticky="w", padx=26, pady=(0, 20))

        self._choice_card(choose, 2, "Admin Login", "Manage users, registration, logs, alerts, reports, and settings.", COLORS["cyan"], self.show_admin_login)
        self._choice_card(choose, 3, "Verify as Registered User", "Scan your face, pass liveness, and verify your identity.", COLORS["green"], self.show_user_verification)

        footer = soft_panel(choose)
        footer.grid(row=4, column=0, sticky="ew", padx=26, pady=(12, 26))
        ctk.CTkLabel(footer, text="No face data is shown until verification is completed and the user chooses to view it.", text_color=COLORS["muted"], font=FONTS["tiny"], wraplength=330, justify="left").pack(anchor="w", padx=14, pady=10)

    def _choice_card(self, parent, row: int, title: str, message: str, color: str, command) -> None:
        card = ctk.CTkFrame(parent, fg_color=COLORS["panel2"], corner_radius=18, border_width=1, border_color=COLORS["border_soft"])
        card.grid(row=row, column=0, sticky="ew", padx=26, pady=7)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, text_color=color, font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(card, text=message, text_color=COLORS["muted"], font=FONTS["small"], wraplength=270, justify="left").grid(row=1, column=0, sticky="w", padx=16, pady=(0, 14))
        ghost_button(card, "Open", command, color=color, width=92).grid(row=0, column=1, rowspan=2, padx=16)

    def show_admin_login(self) -> None:
        self.stop_camera_loops(reset_preview=False)
        clear_frame(self)
        self._reset_root_grid()
        self.configure(fg_color=COLORS["bg"])
        self.grid_columnconfigure(0, weight=1, minsize=0)
        self.grid_rowconfigure(0, weight=1, minsize=0)

        wrapper = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        wrapper.grid(row=0, column=0, sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure((0, 2), weight=1)

        card = panel(wrapper)
        card.grid(row=1, column=0, sticky="n", padx=30, pady=30)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="Admin Login", text_color=COLORS["white"], font=("Segoe UI", 28, "bold")).grid(row=0, column=0, sticky="w", padx=34, pady=(30, 4))
        ctk.CTkLabel(card, text="Enter your admin username and password.", text_color=COLORS["muted"], font=FONTS["small"], wraplength=390, justify="left").grid(row=1, column=0, sticky="w", padx=34, pady=(0, 18))

        self.login_error = ctk.CTkLabel(card, text="", text_color=COLORS["red"], font=FONTS["small"])
        self.login_error.grid(row=2, column=0, sticky="w", padx=34, pady=(0, 8))
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        form_label(card, "Username").grid(row=3, column=0, sticky="w", padx=34, pady=(4, 4))
        user_entry = form_entry(card, self.username_var, "Type username")
        user_entry.grid(row=4, column=0, sticky="ew", padx=34)
        form_label(card, "Password").grid(row=5, column=0, sticky="w", padx=34, pady=(14, 4))
        pass_entry = form_entry(card, self.password_var, "Type password", secret=True)
        pass_entry.grid(row=6, column=0, sticky="ew", padx=34)

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.grid(row=7, column=0, sticky="ew", padx=34, pady=(22, 32))
        buttons.grid_columnconfigure((0, 1), weight=1)
        ghost_button(buttons, "Back", self.show_start_screen, color=COLORS["muted"]).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        primary_button(buttons, "Login", self.do_login).grid(row=0, column=1, sticky="ew", padx=(6, 0))
        user_entry.focus_set()
        self.bind("<Return>", lambda _e: self.do_login())

    def do_login(self) -> None:
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        if self.db.verify_admin(username, password):
            self.unbind("<Return>")
            self.logged_in = True
            self.build_shell()
        else:
            self.login_error.configure(text="Invalid username or password.")

    def build_shell(self) -> None:
        clear_frame(self)
        self._reset_root_grid()
        self.grid_columnconfigure(0, weight=0, minsize=SIDEBAR_WIDTH)
        self.grid_columnconfigure(1, weight=1, minsize=0)
        self.grid_rowconfigure(0, weight=1, minsize=0)
        self.sidebar = ctk.CTkFrame(self, width=SIDEBAR_WIDTH, corner_radius=0, fg_color="#050a16", border_width=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.content = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self.navigate("dashboard")

    def build_sidebar(self) -> None:
        if not widget_alive(self.sidebar):
            return
        clear_frame(self.sidebar)
        top = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(22, 18))
        ctk.CTkLabel(top, text="AURA", text_color=COLORS["cyan"], font=("Segoe UI", 26, "bold")).pack(anchor="w")
        ctk.CTkLabel(top, text="GUARD ADMIN", text_color=COLORS["white"], font=("Segoe UI", 12, "bold")).pack(anchor="w")
        StatusPill(top, "ADMIN SESSION", COLORS["green"]).pack(anchor="w", pady=(14, 0))

        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=12, pady=(8, 0))
        nav_items = [
            ("dashboard", "Dashboard"),
            ("register", "Register Face Data"),
            ("users", "User Management"),
            ("logs", "Access Logs"),
            ("alerts", "Unknown Alerts"),
            ("requests", "Registration Requests"),
            ("reports", "Export Reports"),
            ("settings", "Settings"),
        ]
        for page, text in nav_items:
            active = page == self.current_page
            btn = ctk.CTkButton(
                nav_frame,
                text=text,
                anchor="w",
                command=lambda p=page: self.navigate(p),
                fg_color=COLORS["panel2"] if active else "transparent",
                hover_color=COLORS["panel2"],
                text_color=COLORS["cyan"] if active else COLORS["muted"],
                font=("Segoe UI", 12, "bold" if active else "normal"),
                corner_radius=14,
                border_width=1,
                border_color=COLORS["cyan"] if active else "#050a16",
                height=42,
            )
            btn.pack(fill="x", pady=4)

        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=16, pady=18)
        admin = soft_panel(bottom)
        admin.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(admin, text="Administrator", text_color=COLORS["white"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 0))
        ctk.CTkLabel(admin, text="Control panel access", text_color=COLORS["muted"], font=FONTS["tiny"]).pack(anchor="w", padx=14, pady=(0, 12))
        ghost_button(bottom, "Logout", self.show_start_screen, color=COLORS["red"]).pack(fill="x")

    def navigate(self, page: str) -> None:
        if page != self.current_page:
            self.stop_camera_loops(reset_preview=False)
        self.current_page = page
        self.build_sidebar()
        if not widget_alive(self.content):
            return
        clear_frame(self.content)
        pages = {
            "dashboard": self.page_dashboard,
            "register": self.page_register,
            "users": self.page_users,
            "logs": self.page_logs,
            "alerts": self.page_alerts,
            "requests": self.page_registration_requests,
            "reports": self.page_reports,
            "settings": self.page_settings,
        }
        pages[page]()

    def page_container(self) -> ctk.CTkScrollableFrame:
        page = ctk.CTkScrollableFrame(self.content, fg_color=COLORS["bg"], corner_radius=0)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        return page

    def stop_camera_loops(self, reset_preview: bool = True) -> None:
        self.recognition_running = False
        self.registration_running = False
        self.user_verification_running = False
        if hasattr(self, "camera") and self.camera is not None:
            self.camera.stop()
        if reset_preview:
            if hasattr(self, "reset_user_verify_preview"):
                self.reset_user_verify_preview()
            if hasattr(self, "reset_registration_preview"):
                self.reset_registration_preview()
