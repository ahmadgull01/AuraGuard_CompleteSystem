from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import customtkinter as ctk
from tkinter import messagebox
from PIL import Image

try:
    import cv2
except Exception:
    cv2 = None

from ..camera_service import CameraService
from ..config import SNAPSHOTS_DIR
from ..face_detector import FaceDetector
from ..face_quality import FaceQualityChecker
from ..gui_components import clear_frame, ghost_button, panel, primary_button, soft_panel
from ..theme import COLORS, FONTS
from ..widgets.preview import ScannerPlaceholder
from ..widgets.safety import safe_configure, safe_set, widget_alive

USER_VERIFY_FRAME_DELAY_MS = 60
SUCCESS_HOLD_MS = 2800
MATCH_CONFIRMATION_REQUIRED = 3
MATCH_CONFIRMATION_WINDOW_SECONDS = 6.0
MIN_UNKNOWN_RECOGNITION_ATTEMPTS = 5
UNKNOWN_DECISION_TIMEOUT_SECONDS = 16.0



class UserVerificationScreen:
    def show_user_verification(self) -> None:
        try:
            self.unbind("<Return>")
        except Exception:
            pass
        self.stop_camera_loops(reset_preview=False)
        self.logged_in = False
        self.verified_match = None
        self.pending_match = None
        self.last_unknown_attempt_id = None
        self.last_unknown_snapshot = None
        self.last_unknown_confidence = 0.0
        self.registration_request_submitted = False
        self.match_history = []
        self.recognition_attempts = 0
        self.no_match_attempts = 0
        self.verification_stage = "idle"
        clear_frame(self)
        if hasattr(self, "_reset_root_grid"):
            self._reset_root_grid()
        self.configure(fg_color=COLORS["bg"])
        self.grid_columnconfigure(0, weight=1, minsize=0)
        self.grid_rowconfigure(0, weight=1, minsize=0)

        page = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=3)
        page.grid_columnconfigure(1, weight=0, minsize=390)
        page.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(page, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=34, pady=(24, 10))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text="Registered User Verification", text_color=COLORS["white"], font=FONTS["title"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(top, text="First match your registered face, then complete the liveness challenge before access is granted.", text_color=COLORS["muted"], font=FONTS["small"]).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ghost_button(top, "Back to Main Screen", self.show_start_screen, color=COLORS["muted"], width=170).grid(row=0, column=1, rowspan=2, sticky="e")

        scanner_card = panel(page)
        scanner_card.grid(row=1, column=0, sticky="nsew", padx=(34, 12), pady=(10, 28))
        scanner_card.grid_columnconfigure(0, weight=1)
        scanner_card.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(scanner_card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Face Scanner", text_color=COLORS["white"], font=FONTS["h2"]).grid(row=0, column=0, sticky="w")
        self.user_badge = ctk.CTkLabel(header, text=" READY ", text_color=COLORS["cyan"], fg_color=COLORS["cyan_soft"], corner_radius=999, font=FONTS["tiny"])
        self.user_badge.grid(row=0, column=1, sticky="e")

        self.user_preview = ctk.CTkFrame(scanner_card, fg_color=COLORS["panel2"], corner_radius=20, border_width=1, border_color=COLORS["border"])
        self.user_preview.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 14))
        self.user_preview.grid_propagate(False)
        self.user_preview.configure(height=520)
        self._build_user_verify_placeholder()

        self.verify_message = ctk.CTkLabel(scanner_card, text="Press Start Verification when you are ready.", text_color=COLORS["muted"], font=FONTS["small"], wraplength=820, justify="left")
        self.verify_message.grid(row=2, column=0, sticky="w", padx=22, pady=(0, 14))

        result_bar = ctk.CTkFrame(scanner_card, fg_color=COLORS["panel2"], corner_radius=16, border_width=1, border_color=COLORS["border_soft"])
        result_bar.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        result_bar.grid_columnconfigure(0, weight=1)
        self.verify_result_text = ctk.CTkLabel(result_bar, text="Verification result will appear here.", text_color=COLORS["muted"], font=FONTS["body_bold"])
        self.verify_result_text.grid(row=0, column=0, sticky="w", padx=16, pady=14)
        self.request_registration_btn = ghost_button(result_bar, "Request Registration Review", self.submit_registration_request, color=COLORS["orange"], width=230)
        self.request_registration_btn.grid(row=0, column=1, sticky="e", padx=(8, 8), pady=12)
        self.request_registration_btn.configure(state="disabled")
        self.show_card_btn = ghost_button(result_bar, "Show Information Card", self.show_verified_info_card, color=COLORS["green"], width=190)
        self.show_card_btn.grid(row=0, column=2, sticky="e", padx=(8, 16), pady=12)
        self.show_card_btn.configure(state="disabled")

        side = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0, scrollbar_button_color=COLORS["border"], scrollbar_button_hover_color=COLORS["cyan_soft"], width=380)
        side.grid(row=1, column=1, sticky="nsew", padx=(12, 34), pady=(10, 28))
        side.grid_columnconfigure(0, weight=1)

        status = panel(side)
        status.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.user_status = ctk.CTkLabel(status, text="READY", text_color=COLORS["cyan"], font=("Segoe UI", 17, "bold"))
        self.user_status.pack(anchor="w", padx=18, pady=(18, 4))
        self.user_substatus = ctk.CTkLabel(status, text="Your information card will only open if you choose to view it.", text_color=COLORS["muted"], font=FONTS["small"], wraplength=320, justify="left")
        self.user_substatus.pack(anchor="w", padx=18, pady=(0, 16))
        btns = ctk.CTkFrame(status, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=(0, 18))
        btns.grid_columnconfigure((0, 1), weight=1)
        primary_button(btns, "Start Verification", self.start_user_verification).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ghost_button(btns, "Stop", self.stop_user_verification, color=COLORS["red"]).grid(row=0, column=1, sticky="ew", padx=(5, 0))

        flow = panel(side)
        flow.grid(row=1, column=0, sticky="ew", pady=12)
        ctk.CTkLabel(flow, text="Verification Flow", text_color=COLORS["white"], font=FONTS["h2"]).pack(anchor="w", padx=18, pady=(16, 8))
        self.flow_text = ctk.CTkLabel(flow, text="1. Face match\n2. Liveness challenge\n3. Verification result", text_color=COLORS["muted"], font=FONTS["small"], justify="left")
        self.flow_text.pack(anchor="w", padx=18, pady=(0, 16))

        live = panel(side)
        live.grid(row=2, column=0, sticky="ew", pady=12)
        ctk.CTkLabel(live, text="Liveness Challenge", text_color=COLORS["white"], font=FONTS["h2"]).pack(anchor="w", padx=18, pady=(16, 4))
        self.user_challenge = ctk.CTkLabel(live, text="Challenge starts after a registered face is matched.", text_color=COLORS["cyan"], font=("Segoe UI", 14, "bold"), wraplength=320, justify="left")
        self.user_challenge.pack(anchor="w", padx=18, pady=(0, 8))
        self.user_live_progress = ctk.CTkProgressBar(live, progress_color=COLORS["green"], fg_color=COLORS["panel2"])
        self.user_live_progress.pack(fill="x", padx=18, pady=(0, 14))
        self.user_live_progress.set(0)

        checks = panel(side)
        checks.grid(row=3, column=0, sticky="ew", pady=12)
        ctk.CTkLabel(checks, text="Session Checks", text_color=COLORS["white"], font=FONTS["h2"]).pack(anchor="w", padx=18, pady=(16, 6))
        self.user_checks = ctk.CTkLabel(checks, text="Face: --\nQuality: --\nIdentity: --\nLiveness: --", text_color=COLORS["muted"], font=FONTS["small"], justify="left")
        self.user_checks.pack(anchor="w", padx=18, pady=(0, 18))

        note = soft_panel(side)
        note.grid(row=4, column=0, sticky="ew", pady=12)
        ctk.CTkLabel(note, text="Privacy Note", text_color=COLORS["white"], font=FONTS["h2"]).pack(anchor="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(note, text="After verification, click Show Information Card only if you want to display your details.", text_color=COLORS["muted"], font=FONTS["small"], wraplength=320, justify="left").pack(anchor="w", padx=18, pady=(0, 16))

    def _build_user_verify_placeholder(self) -> None:
        if not widget_alive(getattr(self, "user_preview", None)):
            return
        clear_frame(self.user_preview)
        ScannerPlaceholder(
            self.user_preview,
            "SCANNER STANDBY",
            "Live camera preview will appear here while verification is running.",
            width=780,
            height=420,
        ).pack(fill="both", expand=True, padx=10, pady=10)
        self.user_camera_label = None
        self.user_verify_photo = None

    def reset_user_verify_preview(self) -> None:
        self._cancel_user_success_reset()
        self._build_user_verify_placeholder()
        self.verification_stage = "idle"
        self.pending_match = None
        safe_configure(getattr(self, "user_badge", None), text=" READY ", text_color=COLORS["cyan"], fg_color=COLORS["cyan_soft"])
        safe_configure(getattr(self, "user_status", None), text="READY", text_color=COLORS["cyan"])
        safe_configure(getattr(self, "user_substatus", None), text="Press Start Verification to begin.")
        safe_configure(getattr(self, "verify_message", None), text="Press Start Verification when you are ready.", text_color=COLORS["muted"])
        safe_configure(getattr(self, "verify_result_text", None), text="Verification result will appear here.", text_color=COLORS["muted"])
        safe_configure(getattr(self, "user_checks", None), text="Face: --\nQuality: --\nIdentity: --\nLiveness: --")
        safe_configure(getattr(self, "flow_text", None), text="1. Face match\n2. Liveness challenge\n3. Verification result", text_color=COLORS["muted"])
        safe_configure(getattr(self, "user_challenge", None), text="Challenge starts after a registered face is matched.")
        safe_set(getattr(self, "user_live_progress", None), 0)
        if widget_alive(getattr(self, "show_card_btn", None)):
            self.show_card_btn.configure(state="disabled")
        if widget_alive(getattr(self, "request_registration_btn", None)):
            self.request_registration_btn.configure(state="disabled")

    def reset_user_liveness(self) -> None:
        state = self.liveness.reset()
        safe_configure(getattr(self, "user_challenge", None), text=state.challenge)
        safe_set(getattr(self, "user_live_progress", None), 0)

    def start_user_verification(self) -> None:
        if getattr(self, "user_verification_running", False):
            safe_configure(getattr(self, "user_substatus", None), text="Verification is already running. Press Stop before starting again.")
            return

        self._cancel_user_success_reset()
        settings = self.db.get_settings()
        
        try:
            camera_index = int(settings.get("camera_index", "0"))
        except ValueError:
            camera_index = 0
        self.camera = CameraService(camera_index)
        self.recognizer.reload_settings()
        
        try:
            min_face_size = int(settings.get("min_face_size", "80"))
        except ValueError:
            min_face_size = 80
        self.quality_checker = FaceQualityChecker(min_face_size)
        if not self.camera.start():
            safe_configure(self.user_status, text="CAMERA ERROR", text_color=COLORS["red"])
            safe_configure(self.user_substatus, text=self.camera.error or "Could not open camera.")
            return

        clear_frame(self.user_preview)
        self.user_camera_label = ctk.CTkLabel(self.user_preview, text="")
        self.user_camera_label.pack(fill="both", expand=True, padx=10, pady=10)
        self.user_verification_running = True
        self.verified_match = None
        self.pending_match = None
        self.verification_stage = "matching"
        self.verification_started_at = time.time()
        self.last_recognition_time = 0.0
        self.current_match = None
        self.match_history = []
        self.recognition_attempts = 0
        self.no_match_attempts = 0
        self.last_unknown_attempt_id = None
        self.last_unknown_snapshot = None
        self.last_unknown_confidence = 0.0
        self.registration_request_submitted = False
        self.liveness.reset()
        safe_set(self.user_live_progress, 0)
        safe_configure(self.user_badge, text=" MATCHING ", text_color=COLORS["cyan"], fg_color=COLORS["cyan_soft"])
        safe_configure(self.user_status, text="MATCHING FACE", text_color=COLORS["cyan"])
        safe_configure(self.user_substatus, text="Step 1: matching your face with saved registered data.")
        safe_configure(self.verify_message, text="Keep one clear face in the frame. Liveness will start only after your identity is matched.", text_color=COLORS["muted"])
        safe_configure(self.verify_result_text, text="Waiting for registered face match.", text_color=COLORS["muted"])
        safe_configure(self.user_challenge, text="Waiting for face match before starting liveness.")
        safe_configure(self.flow_text, text="1. Face match: running\n2. Liveness challenge: waiting\n3. Verification result: waiting", text_color=COLORS["muted"])
        if widget_alive(self.show_card_btn):
            self.show_card_btn.configure(state="disabled")
        if widget_alive(getattr(self, "request_registration_btn", None)):
            self.request_registration_btn.configure(state="disabled")
        self.user_verification_loop()

    def stop_user_verification(self) -> None:
        self._cancel_user_success_reset()
        self.user_verification_running = False
        if hasattr(self, "camera") and self.camera is not None:
            self.camera.stop()
        self._build_user_verify_placeholder()
        safe_configure(self.user_badge, text=" READY ", text_color=COLORS["cyan"], fg_color=COLORS["cyan_soft"])
        safe_configure(self.user_status, text="STOPPED", text_color=COLORS["orange"])
        safe_configure(self.user_substatus, text="Camera stopped. Start again when needed.")
        safe_configure(self.user_challenge, text="Challenge starts after a registered face is matched.")
        safe_set(self.user_live_progress, 0)

    def user_verification_loop(self) -> None:
        if not self.user_verification_running or not self.camera.is_open:
            return
        ok, frame = self.camera.read()
        if not ok or frame is None:
            safe_configure(self.user_status, text="FRAME ERROR", text_color=COLORS["red"])
            self.after(220, self.user_verification_loop)
            return

        detection = self.detector.detect(frame)
        faces = detection.faces
        face = FaceDetector.largest_face(faces)
        if cv2 is not None:
            for i, (x, y, w, h) in enumerate(faces):
                draw_color = (0, 245, 255) if i == 0 else (245, 158, 11)
                cv2.rectangle(frame, (x, y), (x + w, y + h), draw_color, 2)

        if len(faces) > 1:
            if self.verification_stage == "liveness":
                self._liveness_step(frame, None, "Blocked")
                if self.user_verification_running:
                    self._update_user_status("MULTIPLE FACES", "Liveness requires one clear face only.", COLORS["orange"], len(faces), "Blocked", "Checking", "Match")
                return
            self._update_user_status("MULTIPLE FACES", "Only one face is allowed. Please stand alone.", COLORS["orange"], len(faces), "Blocked", "Waiting", "Waiting")
            self._show_user_frame(frame)
            self.after(USER_VERIFY_FRAME_DELAY_MS, self.user_verification_loop)
            return
        if face is None:
            if self.verification_stage == "liveness":
                self._liveness_step(frame, None, "No face")
                return
            self._update_user_status("SCANNING", "No face detected. Please face the camera.", COLORS["cyan"], 0, "No face", "Waiting", "Waiting")
            self._show_user_frame(frame)
            self.after(USER_VERIFY_FRAME_DELAY_MS, self.user_verification_loop)
            return

        quality = self.quality_checker.evaluate(frame, face)
        quality_text = "Good" if quality.ok else "Needs improvement"
        if not quality.ok:
            if self.verification_stage == "liveness":
                self._liveness_step(frame, None, quality_text)
                if self.user_verification_running:
                    self._update_user_status("QUALITY WARNING", quality.messages[0] if quality.messages else "Improve face quality.", COLORS["orange"], 1, quality_text, "Checking", "Match")
                return
            self._update_user_status("QUALITY WARNING", quality.messages[0] if quality.messages else "Improve face quality.", COLORS["orange"], 1, quality_text, "Waiting", "Waiting")
            self._show_user_frame(frame)
            self.after(USER_VERIFY_FRAME_DELAY_MS, self.user_verification_loop)
            return

        if self.verification_stage == "matching":
            self._match_identity_step(frame, face, quality_text)
            return
        if self.verification_stage == "liveness":
            self._liveness_step(frame, face, quality_text)
            return

    def _match_identity_step(self, frame, face, quality_text: str) -> None:
        now = time.time()
        did_new_recognition = False
        if now - self.last_recognition_time > 0.75:
            self.current_match = self.recognizer.recognize(frame, face)
            self.current_match["recognition_time"] = now
            self.last_recognition_time = now
            self.recognition_attempts += 1
            did_new_recognition = True
        match = self.current_match or {"matched": False, "confidence": 0.0, "reason": "Checking saved users."}

        if match.get("matched") and did_new_recognition:
            confirmed, stable_match, avg_confidence = self._record_match_confirmation(match)
            if not confirmed:
                count = len([m for m in self.match_history if m.get("user_id") == match.get("user_id")])
                self._update_user_status(
                    "CONFIRMING MATCH",
                    f"Possible match found for {match.get('full_name', 'Registered User')}. Confirming identity stability ({count}/{MATCH_CONFIRMATION_REQUIRED}).",
                    COLORS["cyan"],
                    1,
                    quality_text,
                    "Waiting",
                    "Confirming",
                )
                safe_configure(
                    self.verify_result_text,
                    text="Face match found. Confirming with additional frames before liveness starts.",
                    text_color=COLORS["cyan"],
                )
                self._show_user_frame(frame)
                self.after(USER_VERIFY_FRAME_DELAY_MS, self.user_verification_loop)
                return

            stable_match = dict(stable_match)
            stable_match["confidence"] = round(avg_confidence, 2)
            self.pending_match = stable_match
            liveness_enabled = self.db.get_setting("liveness_enabled", "true") == "true"
            if not liveness_enabled:
                self._handle_verified(stable_match, "Disabled")
                return
            self.verification_stage = "liveness"
            self.reset_user_liveness()
            safe_configure(self.user_status, text="FACE MATCHED", text_color=COLORS["green"])
            safe_configure(self.user_substatus, text="Identity confirmed from multiple frames. Liveness will begin after a short preparation delay.")
            safe_configure(self.verify_result_text, text=f"Face confirmed: {stable_match.get('full_name', 'Registered User')}. Preparing liveness test.", text_color=COLORS["green"])
            safe_configure(self.user_badge, text=" PREPARING ", text_color=COLORS["purple"], fg_color=COLORS["purple_soft"])
            safe_configure(self.flow_text, text="1. Face match: confirmed\n2. Liveness challenge: preparing\n3. Verification result: waiting", text_color=COLORS["green"])
            self._update_user_status("PREPARING LIVENESS", self.liveness.state.message, COLORS["purple"], 1, quality_text, "Preparing", "Confirmed")
            self._show_user_frame(frame)
            self.after(USER_VERIFY_FRAME_DELAY_MS, self.user_verification_loop)
            return

        if match.get("matched") and not did_new_recognition:
            count = len([m for m in self.match_history if m.get("user_id") == match.get("user_id")])
            self._update_user_status(
                "CONFIRMING MATCH",
                f"Possible match found for {match.get('full_name', 'Registered User')}. Waiting for next live confirmation ({count}/{MATCH_CONFIRMATION_REQUIRED}).",
                COLORS["cyan"],
                1,
                quality_text,
                "Waiting",
                "Confirming",
            )
            self._show_user_frame(frame)
            self.after(USER_VERIFY_FRAME_DELAY_MS, self.user_verification_loop)
            return

        if did_new_recognition:
            self.match_history = []
            self.no_match_attempts += 1

        if self._should_decide_unknown(match):
            self._handle_unknown(frame, float(match.get("confidence", 0.0)), "Not Started")
            return

        wait_text = match.get("reason", "Checking saved users.")
        if self.recognition_attempts:
            wait_text = f"{wait_text} Recognition checks completed: {self.recognition_attempts}/{MIN_UNKNOWN_RECOGNITION_ATTEMPTS}."
        self._update_user_status("MATCHING FACE", wait_text, COLORS["cyan"], 1, quality_text, "Waiting", "No match yet")
        self._show_user_frame(frame)
        self.after(USER_VERIFY_FRAME_DELAY_MS, self.user_verification_loop)

    def _unknown_timeout_seconds(self) -> float:
        return UNKNOWN_DECISION_TIMEOUT_SECONDS

    def _should_decide_unknown(self, match: dict[str, Any]) -> bool:
        reason = str(match.get("reason", "")).lower()
        if "no registered users" in reason:
            return self.recognition_attempts >= 1
        elapsed = time.time() - float(getattr(self, "verification_started_at", time.time()))
        enough_checks = self.no_match_attempts >= MIN_UNKNOWN_RECOGNITION_ATTEMPTS
        timed_out = elapsed >= self._unknown_timeout_seconds()
        return enough_checks and timed_out

    def _record_match_confirmation(self, match: dict[str, Any]) -> tuple[bool, dict[str, Any], float]:
        now = time.time()
        user_id = match.get("user_id")
        confidence = float(match.get("confidence", 0.0))
        self.match_history = [
            item for item in getattr(self, "match_history", [])
            if now - float(item.get("time", 0.0)) <= MATCH_CONFIRMATION_WINDOW_SECONDS
        ]
        self.match_history.append({"time": now, "user_id": user_id, "confidence": confidence, "match": match})
        same_user = [item for item in self.match_history if item.get("user_id") == user_id]
        if len(same_user) < MATCH_CONFIRMATION_REQUIRED:
            return False, match, confidence
        recent = same_user[-MATCH_CONFIRMATION_REQUIRED:]
        avg_confidence = sum(float(item.get("confidence", 0.0)) for item in recent) / MATCH_CONFIRMATION_REQUIRED
        # This is an additional safety gate before starting liveness.
        if avg_confidence < 72.0:
            return False, match, avg_confidence
        return True, recent[-1]["match"], avg_confidence

    def _liveness_step(self, frame, face, quality_text: str) -> None:
        state = self.liveness.update(face)
        safe_set(self.user_live_progress, state.progress)
        safe_configure(self.user_challenge, text=state.challenge)

        if state.phase == "delay":
            self._update_user_status("PREPARING LIVENESS", state.message, COLORS["purple"], 1, quality_text, "Starting soon", "Match")
            safe_configure(self.flow_text, text="1. Face match: passed\n2. Liveness challenge: starting soon\n3. Verification result: waiting", text_color=COLORS["green"])
            self._show_user_frame(frame)
            self.after(USER_VERIFY_FRAME_DELAY_MS, self.user_verification_loop)
            return

        if state.phase == "calibrate":
            self._update_user_status("CALIBRATING", state.message, COLORS["purple"], 1, quality_text, "Calibrating", "Match")
            safe_configure(self.flow_text, text="1. Face match: passed\n2. Liveness challenge: calibrating center point\n3. Verification result: waiting", text_color=COLORS["green"])
            self._show_user_frame(frame)
            self.after(USER_VERIFY_FRAME_DELAY_MS, self.user_verification_loop)
            return

        if state.phase in {"challenge", "return"}:
            self._update_user_status("LIVENESS CHECK", state.message, COLORS["purple"], 1, quality_text, "Checking", "Match")
            safe_configure(self.flow_text, text="1. Face match: passed\n2. Liveness challenge: running strictly\n3. Verification result: waiting", text_color=COLORS["green"])
            self._show_user_frame(frame)
            self.after(USER_VERIFY_FRAME_DELAY_MS, self.user_verification_loop)
            return

        if state.passed:
            self._show_user_frame(frame)
            if not self._final_identity_recheck(frame, face):
                self._handle_unknown(frame, 0.0, "Identity Changed")
                return
            self._handle_verified(self.pending_match or {}, "Pass")
            return

        if state.failed:
            self._handle_liveness_failed(frame, self.pending_match)
            return

        self._show_user_frame(frame)
        self.after(USER_VERIFY_FRAME_DELAY_MS, self.user_verification_loop)

    def _final_identity_recheck(self, frame, face) -> bool:
        if not self.pending_match or face is None:
            return False
        final_match = self.recognizer.recognize(frame, face)
        if not final_match.get("matched"):
            return False
        if final_match.get("user_id") != self.pending_match.get("user_id"):
            return False
        self.pending_match = dict(final_match)
        return True

    def _update_user_status(self, status: str, sub: str, color: str, face_count: int, quality_text: str, live_text: str, db_text: str) -> None:
        safe_configure(self.user_status, text=status, text_color=color)
        safe_configure(self.user_substatus, text=sub)
        safe_configure(self.user_badge, text=f" {status} ", text_color=color)
        safe_configure(self.user_checks, text=f"Face: {face_count} detected\nQuality: {quality_text}\nIdentity: {db_text}\nLiveness: {live_text}")

    def _handle_verified(self, match: dict[str, Any], liveness_status: str = "Pass") -> None:
        self.user_verification_running = False
        if hasattr(self, "camera") and self.camera is not None:
            self.camera.stop()
        if not match:
            return
        self.verified_match = match
        self.db.add_access_log(match["user_id"], match["full_name"], match["confidence"], liveness_status, "granted")
        safe_configure(self.user_status, text="VERIFIED", text_color=COLORS["green"])
        safe_configure(self.user_substatus, text="Face match and liveness check completed. The scanner will return to standby shortly.")
        safe_configure(self.verify_message, text="You have been verified. Click Show Information Card if you want to view your details.", text_color=COLORS["green"])
        safe_configure(self.verify_result_text, text="You have been verified. Show information card?", text_color=COLORS["green"])
        safe_configure(self.user_badge, text=" VERIFIED ", text_color=COLORS["green"], fg_color=COLORS["green_soft"])
        safe_configure(self.flow_text, text="1. Face match: passed\n2. Liveness challenge: passed\n3. Verification result: granted", text_color=COLORS["green"])
        safe_configure(self.user_checks, text=f"Face: 1 detected\nQuality: Good\nIdentity: Match\nLiveness: {liveness_status}")
        safe_set(self.user_live_progress, 1)
        if widget_alive(self.show_card_btn):
            self.show_card_btn.configure(state="normal")
        self._schedule_user_success_reset()

    def _schedule_user_success_reset(self) -> None:
        self._cancel_user_success_reset()
        if widget_alive(getattr(self, "user_preview", None)):
            self.user_success_after_id = self.after(SUCCESS_HOLD_MS, self._finish_user_success_pause)

    def _finish_user_success_pause(self) -> None:
        self.user_success_after_id = None
        if not widget_alive(getattr(self, "user_preview", None)):
            return
        self._build_user_verify_placeholder()
        self.verification_stage = "complete"
        safe_configure(self.user_badge, text=" COMPLETE ", text_color=COLORS["green"], fg_color=COLORS["green_soft"])
        safe_configure(self.user_substatus, text="Scanner is back to standby. You can view your information card or start again.")

    def _cancel_user_success_reset(self) -> None:
        after_id = getattr(self, "user_success_after_id", None)
        if after_id:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        self.user_success_after_id = None

    def _handle_unknown(self, frame, confidence: float, liveness_status: str) -> None:
        self._cancel_user_success_reset()
        self.user_verification_running = False
        if hasattr(self, "camera") and self.camera is not None:
            self.camera.stop()

        # Unknown attempts are always saved because they may become registration requests.
        snapshot = self._save_snapshot(frame, "unknown")
        self.db.add_access_log("UNKNOWN", "Unknown Person", confidence, liveness_status, "denied", snapshot)
        attempt_id, _alert_id = self.db.add_unknown_attempt(
            confidence,
            liveness_status,
            "Unknown Face",
            snapshot,
            "Unknown person attempted registered-user verification.",
        )
        self.last_unknown_attempt_id = attempt_id
        self.last_unknown_snapshot = snapshot
        self.last_unknown_confidence = confidence
        self.registration_request_submitted = False

        self._build_user_verify_placeholder()
        safe_configure(self.user_status, text="UNKNOWN USER DETECTED", text_color=COLORS["orange"])
        safe_configure(self.user_substatus, text="The face is not registered. The attempt has been captured for admin review.")
        safe_configure(
            self.verify_message,
            text="Unknown user detected. You may submit a registration review request to the administrator.",
            text_color=COLORS["orange"],
        )
        safe_configure(self.verify_result_text, text="Unknown user detected. Access denied.", text_color=COLORS["orange"])
        safe_configure(self.user_badge, text=" UNKNOWN ", text_color=COLORS["orange"], fg_color=COLORS["orange_soft"])
        safe_configure(self.flow_text, text="1. Face match: failed\n2. Liveness challenge: not started\n3. Registration request: optional", text_color=COLORS["orange"])
        if widget_alive(getattr(self, "request_registration_btn", None)):
            self.request_registration_btn.configure(state="normal")

    def submit_registration_request(self) -> None:
        if self.registration_request_submitted:
            messagebox.showinfo("Request Already Submitted", "Your registration request is already waiting for admin review.")
            return
        if not self.last_unknown_snapshot:
            messagebox.showwarning("No Captured Face", "Please scan your face again so the system can capture a clear image for admin review.")
            return

        request_id = self.db.create_registration_request(
            self.last_unknown_attempt_id,
            self.last_unknown_snapshot,
            self.last_unknown_confidence,
            "User requested registration review after unknown face verification.",
        )
        self.registration_request_submitted = True
        if widget_alive(getattr(self, "request_registration_btn", None)):
            self.request_registration_btn.configure(state="disabled")
        safe_configure(self.user_status, text="REQUEST SUBMITTED", text_color=COLORS["green"])
        safe_configure(self.user_substatus, text=f"Request {request_id} has been sent to the administrator for approval.")
        safe_configure(
            self.verify_message,
            text="Your registration request has been submitted successfully. The administrator will review it before creating an account.",
            text_color=COLORS["green"],
        )
        safe_configure(self.verify_result_text, text=f"Registration review request submitted: {request_id}", text_color=COLORS["green"])

    def _handle_liveness_failed(self, frame, match: dict[str, Any] | None = None) -> None:
        self._cancel_user_success_reset()
        self.user_verification_running = False
        if hasattr(self, "camera") and self.camera is not None:
            self.camera.stop()
        snapshot = self._save_snapshot(frame, "liveness_failed") if self.db.get_setting("snapshot_enabled", "true") == "true" else None
        user_id = match.get("user_id") if match else "UNKNOWN"
        full_name = match.get("full_name") if match else "Liveness Failed"
        confidence = float(match.get("confidence", 0.0)) if match else 0.0
        self.db.add_access_log(user_id, full_name, confidence, "Fail", "denied", snapshot)
        self.db.add_unknown_attempt(confidence, "Fail", "Liveness Failed", snapshot, f"Liveness failed after face match for {full_name}.")
        self._build_user_verify_placeholder()
        safe_configure(self.user_status, text="LIVENESS FAILED", text_color=COLORS["red"])
        safe_configure(self.user_substatus, text="Attempt captured because the liveness challenge failed.")
        safe_configure(self.verify_message, text="Liveness failed. The attempt has been stored for admin review.", text_color=COLORS["red"])
        safe_configure(self.verify_result_text, text="Liveness failed. Access denied.", text_color=COLORS["red"])
        safe_configure(self.user_badge, text=" FAILED ", text_color=COLORS["red"], fg_color=COLORS["red_soft"])
        safe_configure(self.flow_text, text="1. Face match: passed\n2. Liveness challenge: failed\n3. Verification result: denied", text_color=COLORS["red"])

    def show_verified_info_card(self) -> None:
        if not self.verified_match:
            return
        match = self.verified_match
        popup = ctk.CTkToplevel(self)
        popup.title("Verified User Information")
        popup.geometry("460x520")
        popup.resizable(False, False)
        popup.configure(fg_color=COLORS["bg"])
        popup.grab_set()
        popup.focus_force()

        card = ctk.CTkFrame(popup, fg_color=COLORS["panel"], corner_radius=26, border_width=1, border_color=COLORS["green"])
        card.pack(fill="both", expand=True, padx=22, pady=22)
        ctk.CTkLabel(card, text="Verified User", text_color=COLORS["green"], font=("Segoe UI", 24, "bold")).pack(anchor="center", pady=(28, 4))
        ctk.CTkLabel(card, text="Access has been granted after face match and liveness check.", text_color=COLORS["muted"], font=FONTS["small"], wraplength=350, justify="center").pack(anchor="center", pady=(0, 22))

        rows = [
            ("User ID", match.get("user_id", "--")),
            ("Full Name", match.get("full_name", "--")),
            ("Role", match.get("role", "--")),
            ("Confidence", f"{float(match.get('confidence', 0.0)):.1f}%"),
            ("Model", match.get("model", self.recognizer.active_model_name)),
        ]
        for label_text, value in rows:
            row = ctk.CTkFrame(card, fg_color=COLORS["panel2"], corner_radius=14)
            row.pack(fill="x", padx=28, pady=6)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=label_text, text_color=COLORS["muted"], font=FONTS["tiny"]).grid(row=0, column=0, sticky="w", padx=14, pady=10)
            ctk.CTkLabel(row, text=str(value), text_color=COLORS["text"], font=FONTS["small"]).grid(row=0, column=1, sticky="e", padx=14)

        ghost_button(card, "Close", popup.destroy, color=COLORS["green"], width=170).pack(anchor="center", pady=(22, 24))

    def _save_snapshot(self, frame, prefix: str) -> str | None:
        if cv2 is None or frame is None:
            return None
        path = SNAPSHOTS_DIR / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        cv2.imwrite(str(path), frame)
        return str(path)

    def _show_user_frame(self, frame) -> None:
        if cv2 is None or not widget_alive(getattr(self, "user_camera_label", None)):
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        image.thumbnail((780, 520))
        self.user_verify_photo = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        self.user_camera_label.configure(image=self.user_verify_photo, text="")
