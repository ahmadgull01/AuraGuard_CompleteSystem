from __future__ import annotations

from typing import Any
from pathlib import Path

import customtkinter as ctk

from .camera_service import CameraService
from .config import ensure_directories
from .database_manager import DatabaseManager
from .face_detector import FaceDetector
from .face_quality import FaceQualityChecker
from .face_recognizer import FaceRecognizer
from .liveness_detection import LivenessDetector
from .report_generator import ReportGenerator
from .theme import COLORS
from .shell import ShellMixin
from .screens.dashboard_screen import DashboardScreen
from .screens.registration_screen import RegistrationScreen
from .screens.user_verification_screen import UserVerificationScreen
from .screens.users_screen import UsersScreen
from .screens.logs_screen import LogsScreen
from .screens.alerts_screen import AlertsScreen
from .screens.settings_screen import SettingsScreen
from .screens.reports_screen import ReportsScreen
from .screens.registration_requests_screen import RegistrationRequestsScreen


class AURAGuardApp(
    ctk.CTk,
    ShellMixin,
    UserVerificationScreen,
    DashboardScreen,
    RegistrationScreen,
    UsersScreen,
    LogsScreen,
    AlertsScreen,
    SettingsScreen,
    ReportsScreen,
    RegistrationRequestsScreen,
):
    def __init__(self) -> None:
        super().__init__()
        ensure_directories()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("AURA Guard")
        self.configure(fg_color=COLORS["bg"])
        self.minsize(1180, 720)
        self.resizable(True, True)

        # Build the first screen while hidden to avoid the small-window startup flicker.
        self.withdraw()

        self.db = DatabaseManager()
        self.recognizer = FaceRecognizer(self.db)
        self.detector = FaceDetector()
        
        try:
            min_face_size = int(self.db.get_setting("min_face_size", "80"))
        except ValueError:
            min_face_size = 80
        self.quality_checker = FaceQualityChecker(min_face_size)
        self.reporter = ReportGenerator(self.db)
        
        try:
            camera_index = int(self.db.get_setting("camera_index", "0"))
        except ValueError:
            camera_index = 0
        self.camera = CameraService(camera_index)
        self.liveness = LivenessDetector()

        self.current_page = "dashboard"
        self.logged_in = False
        self.sidebar: ctk.CTkFrame | None = None
        self.content: ctk.CTkFrame | None = None
        self.camera_photo = None
        self.reg_camera_photo = None
        self.user_verify_photo = None
        self.recognition_running = False
        self.registration_running = False
        self.user_verification_running = False
        self.last_log_time = 0.0
        self.last_recognition_time = 0.0
        self.current_match: dict[str, Any] | None = None
        self.verified_match: dict[str, Any] | None = None
        self.register_samples = 0
        self.register_folder: Path | None = None

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.show_start_screen()
        self.after(10, self._show_maximized_window)

    def _show_maximized_window(self) -> None:
        self._apply_maximized_state()
        self.deiconify()
        self.lift()
        self.focus_force()
        self.after(100, self._apply_maximized_state)
        self.after(350, self._apply_maximized_state)
        self.after(900, self._apply_maximized_state)

    def _apply_maximized_state(self) -> None:
        try:
            self.state("zoomed")
            return
        except Exception:
            pass
        try:
            self.attributes("-zoomed", True)
            return
        except Exception:
            pass
        try:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            self.geometry(f"{screen_width}x{screen_height}+0+0")
        except Exception:
            pass

    def on_close(self) -> None:
        try:
            self.stop_camera_loops()
        except Exception:
            pass
        self.destroy()
