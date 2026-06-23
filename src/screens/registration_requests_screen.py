from __future__ import annotations

import shutil
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Any

import customtkinter as ctk
from PIL import Image

try:
    import cv2
except Exception:
    cv2 = None

from ..camera_service import CameraService
from ..config import REGISTERED_FACES_DIR, REGISTRATION_REQUESTS_DIR
from ..face_detector import FaceDetector
from ..face_quality import FaceQualityChecker
from ..gui_components import ScannerCanvas, SectionTitle, clear_frame, ghost_button, panel, primary_button
from ..theme import COLORS, FONTS
from ..widgets.table import SimpleTable, TableColumn


class RegistrationRequestsScreen:
    def page_registration_requests(self) -> None:
        page = self.page_container()
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)
        SectionTitle(
            page,
            "Registration Requests",
            "Review unknown users who requested face registration approval.",
        ).grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 18))

        toolbar = ctk.CTkFrame(page, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)
        self.request_filter = tk.StringVar(value="pending")
        ctk.CTkLabel(
            toolbar,
            text="Approved requests require a full fresh face-sample capture before registration.",
            text_color=COLORS["muted"],
            font=FONTS["small"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkSegmentedButton(
            toolbar,
            values=["all", "pending", "registered", "ignored"],
            variable=self.request_filter,
            command=lambda _v: self.refresh_registration_requests(),
            selected_color=COLORS["orange"],
        ).grid(row=0, column=1, sticky="e")

        columns = [
            TableColumn("request_id", "Request ID", 115, 1),
            TableColumn("attempt", "Attempt", 120, 1),
            TableColumn("confidence", "Confidence", 105, 1),
            TableColumn("status", "Status", 110, 1),
            TableColumn("created", "Created At", 170, 2),
            TableColumn("actions", "Actions", 250, 2),
        ]
        self.requests_table = SimpleTable(page, columns)
        self.requests_table.frame.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 24))
        self.refresh_registration_requests()

    def refresh_registration_requests(self) -> None:
        self.requests_table.clear()
        rows = self.db.list_registration_requests(self.request_filter.get() if hasattr(self, "request_filter") else "pending")
        if not rows:
            self.requests_table.add_empty(
                "No registration requests found",
                "When an unknown user requests registration review, the request will appear here.",
            )
            return
        for row in rows:
            self._registration_request_row(row)

    def _registration_request_row(self, row: dict[str, Any]) -> None:
        status = row["request_status"]
        status_color = COLORS["orange"] if status == "pending" else COLORS["green"] if status == "registered" else COLORS["red"]
        values = [
            row["request_id"],
            row.get("attempt_id") or "--",
            f"{float(row.get('confidence_score') or 0):.1f}%",
            status,
            row.get("created_at") or "--",
            "",
        ]
        colors = [COLORS["text"], COLORS["text"], COLORS["text"], status_color, COLORS["text"], COLORS["text"]]

        def actions(holder) -> None:
            ghost_button(holder, "View", lambda rid=row["request_id"]: self.open_request_detail(rid), width=70, color=COLORS["cyan"]).pack(side="left", padx=(0, 6))
            if status == "pending":
                ghost_button(holder, "Register", lambda rid=row["request_id"]: self.open_request_register_dialog(rid), width=88, color=COLORS["green"]).pack(side="left", padx=(0, 6))
                ghost_button(holder, "Ignore", lambda rid=row["request_id"]: self.ignore_registration_request(rid), width=78, color=COLORS["red"]).pack(side="left")
            else:
                ctk.CTkLabel(holder, text="Decision saved", text_color=COLORS["muted"], font=FONTS["tiny"]).pack(side="left")

        self.requests_table.add_row(values, colors, actions)

    def open_request_detail(self, request_id: str) -> None:
        request = self.db.get_registration_request(request_id)
        if not request:
            messagebox.showerror("Request Missing", "This registration request could not be found.")
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Registration Request Detail")
        dialog.geometry("540x500")
        dialog.configure(fg_color=COLORS["bg"])
        dialog.grab_set()
        dialog.focus_force()

        box = panel(dialog)
        box.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(box, text="Registration Request", text_color=COLORS["orange"], font=FONTS["h1"]).pack(anchor="w", padx=18, pady=(18, 6))
        details = [
            ("Request ID", request["request_id"]),
            ("Attempt ID", request.get("attempt_id") or "--"),
            ("Status", request["request_status"]),
            ("Confidence", f"{float(request.get('confidence_score') or 0):.1f}%"),
            ("Snapshot", request.get("snapshot_path") or "No snapshot"),
            ("Created At", request.get("created_at") or "--"),
            ("Remarks", request.get("remarks") or "--"),
        ]
        for key, value in details:
            row = ctk.CTkFrame(box, fg_color=COLORS["panel2"], corner_radius=12)
            row.pack(fill="x", padx=18, pady=5)
            ctk.CTkLabel(row, text=key, text_color=COLORS["muted"], font=FONTS["tiny"]).pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(row, text=str(value), text_color=COLORS["text"], font=FONTS["small"], wraplength=330, justify="right").pack(side="right", padx=12)

        btns = ctk.CTkFrame(box, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=(18, 16))
        if request["request_status"] == "pending":
            primary_button(btns, "Register This User", lambda: (dialog.destroy(), self.open_request_register_dialog(request_id))).pack(side="left", fill="x", expand=True, padx=(0, 8))
            ghost_button(btns, "Ignore", lambda: (dialog.destroy(), self.ignore_registration_request(request_id)), color=COLORS["red"]).pack(side="left", fill="x", expand=True)
        else:
            ghost_button(btns, "Close", dialog.destroy, color=COLORS["cyan"]).pack(fill="x")

    def open_request_register_dialog(self, request_id: str) -> None:
        request = self.db.get_registration_request(request_id)
        if not request:
            messagebox.showerror("Request Missing", "This registration request could not be found.")
            return
        if request["request_status"] != "pending":
            messagebox.showinfo("Decision Already Saved", "This request has already been handled.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Approve Registration Request")
        dialog.geometry("980x740")
        dialog.minsize(900, 680)
        dialog.configure(fg_color=COLORS["bg"])
        dialog.grab_set()
        dialog.focus_force()

        # Dialog state is kept local so it does not disturb normal registration.
        capture_camera: CameraService | None = None
        capture_running = False
        captured_samples = 0
        last_capture_time = 0.0
        request_photo = None
        
        try:
            sample_target = max(20, int(self.db.get_setting("max_samples", "20")))
        except ValueError:
            sample_target = 20
        capture_folder = REGISTRATION_REQUESTS_DIR / request_id / "fresh_admin_samples"

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        outer = panel(dialog)
        outer.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        outer.grid_columnconfigure(0, weight=1, minsize=380)
        outer.grid_columnconfigure(1, weight=1, minsize=470)
        outer.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(18, 10))
        ctk.CTkLabel(header, text="Approve Registration", text_color=COLORS["green"], font=FONTS["h1"]).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text=f"Enter user details, then capture at least {sample_target} fresh face samples before approval.",
            text_color=COLORS["muted"],
            font=FONTS["small"],
            wraplength=820,
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        form = ctk.CTkFrame(
            outer,
            fg_color=COLORS["panel"],
            corner_radius=18,
            border_width=1,
            border_color=COLORS["border"],
        )
        form.grid(row=1, column=0, sticky="nsew", padx=(18, 9), pady=(0, 12))
        form.grid_columnconfigure(0, weight=1)

        user_id = tk.StringVar(value=self.db.next_user_id())
        name = tk.StringVar()
        role = tk.StringVar()
        status = tk.StringVar(value="active")
        pin = tk.StringVar()

        fields = [
            ("User ID", user_id),
            ("Full Name", name),
            ("Role / Designation", role),
            ("PIN Optional", pin),
        ]
        for row_no, (label_text, var) in enumerate(fields):
            ctk.CTkLabel(form, text=label_text.upper(), text_color=COLORS["muted"], font=FONTS["tiny"]).grid(
                row=row_no * 2, column=0, sticky="w", padx=18, pady=(16 if row_no == 0 else 10, 3)
            )
            entry = ctk.CTkEntry(form, textvariable=var, fg_color=COLORS["panel2"], border_color=COLORS["border"], height=42)
            entry.grid(row=row_no * 2 + 1, column=0, sticky="ew", padx=18)

        status_row = len(fields) * 2
        ctk.CTkLabel(form, text="STATUS", text_color=COLORS["muted"], font=FONTS["tiny"]).grid(
            row=status_row, column=0, sticky="w", padx=18, pady=(14, 3)
        )
        ctk.CTkSegmentedButton(form, values=["active", "inactive"], variable=status, selected_color=COLORS["cyan"]).grid(
            row=status_row + 1, column=0, sticky="ew", padx=18, pady=(0, 14)
        )

        note = ctk.CTkFrame(form, fg_color=COLORS["panel2"], corner_radius=14, border_width=1, border_color=COLORS["border_soft"])
        note.grid(row=status_row + 2, column=0, sticky="ew", padx=18, pady=(0, 14))
        ctk.CTkLabel(
            note,
            text=(
                "The original request snapshot is kept as a reference only. "
                "Reliable registration needs a fresh multi-sample capture."
            ),
            text_color=COLORS["muted"],
            font=FONTS["small"],
            wraplength=330,
            justify="left",
        ).pack(anchor="w", padx=12, pady=10)

        right = ctk.CTkFrame(
            outer,
            fg_color=COLORS["panel"],
            corner_radius=18,
            border_width=1,
            border_color=COLORS["border"],
        )
        right.grid(row=1, column=1, sticky="nsew", padx=(9, 18), pady=(0, 12))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(right, text="Fresh Face Sample Capture", text_color=COLORS["white"], font=FONTS["h2"]).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 4)
        )
        capture_msg = ctk.CTkLabel(
            right,
            text="Click Start Capture and keep the same person in front of the camera.",
            text_color=COLORS["muted"],
            font=FONTS["small"],
            wraplength=430,
            justify="left",
        )
        capture_msg.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 8))

        preview = ctk.CTkFrame(right, fg_color=COLORS["panel2"], corner_radius=18, border_width=1, border_color=COLORS["border"])
        preview.grid(row=2, column=0, sticky="nsew", padx=18, pady=(4, 12))
        preview.grid_propagate(False)
        preview.configure(height=320)
        scanner = ScannerCanvas(preview, width=460, height=320)
        scanner.pack(fill="both", expand=True)
        camera_label: ctk.CTkLabel | None = None

        progress = ctk.CTkProgressBar(right, progress_color=COLORS["green"], fg_color=COLORS["panel2"])
        progress.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 10))
        progress.set(0)

        count_label = ctk.CTkLabel(
            right,
            text=f"Samples captured: 0/{sample_target}",
            text_color=COLORS["muted"],
            font=FONTS["small"],
        )
        count_label.grid(row=4, column=0, sticky="w", padx=18, pady=(0, 10))

        actions = ctk.CTkFrame(outer, fg_color="transparent")
        actions.grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 18))
        actions.grid_columnconfigure((0, 1, 2), weight=1)

        start_btn = primary_button(actions, "Start 20+ Sample Capture", lambda: start_capture())
        start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        approve_btn = primary_button(actions, "Approve and Register User", lambda: approve())
        approve_btn.grid(row=0, column=1, sticky="ew", padx=8)
        approve_btn.configure(state="disabled")
        ghost_button(actions, "Cancel", lambda: close_dialog(), color=COLORS["muted"]).grid(row=0, column=2, sticky="ew", padx=(8, 0))

        def reset_preview() -> None:
            nonlocal camera_label, request_photo
            clear_frame(preview)
            placeholder = ScannerCanvas(preview, width=460, height=320)
            placeholder.pack(fill="both", expand=True)
            camera_label = None
            request_photo = None

        def validate_form() -> tuple[bool, str]:
            uid = user_id.get().strip()
            fullname = name.get().strip()
            user_role = role.get().strip()
            if not uid or not fullname or not user_role:
                return False, "User ID, full name, and role are required."
            if not self.db.is_valid_user_id(uid):
                return False, "User ID must not contain spaces or special path characters."
            if self.db.user_exists(uid):
                return False, "This user ID already exists. Please choose another user ID."
            return True, "OK"

        def start_capture() -> None:
            nonlocal capture_camera, capture_running, captured_samples, last_capture_time, camera_label
            valid, message = validate_form()
            if not valid:
                messagebox.showwarning("Missing Data", message, parent=dialog)
                return
            if cv2 is None:
                messagebox.showerror("OpenCV Missing", "OpenCV is required for camera capture.", parent=dialog)
                return
            if capture_running:
                capture_msg.configure(text="Capture is already running. Please wait until it completes.", text_color=COLORS["orange"])
                return

            if capture_folder.exists():
                shutil.rmtree(capture_folder)
            capture_folder.mkdir(parents=True, exist_ok=True)
            captured_samples = 0
            last_capture_time = 0.0
            progress.set(0)
            count_label.configure(text=f"Samples captured: 0/{sample_target}", text_color=COLORS["muted"])
            approve_btn.configure(state="disabled")

            settings = self.db.get_settings()
            
            try:
                camera_index = int(settings.get("camera_index", "0"))
            except ValueError:
                camera_index = 0
            capture_camera = CameraService(camera_index)
            if not capture_camera.start():
                capture_msg.configure(text=capture_camera.error or "Camera could not start.", text_color=COLORS["red"])
                return

            clear_frame(preview)
            camera_label = ctk.CTkLabel(preview, text="")
            camera_label.pack(fill="both", expand=True, padx=8, pady=8)
            capture_running = True
            start_btn.configure(state="disabled")
            capture_msg.configure(
                text="Capturing fresh samples. Slowly change your face angle as guided.",
                text_color=COLORS["cyan"],
            )
            capture_loop()

        def capture_loop() -> None:
            nonlocal captured_samples, last_capture_time, request_photo, capture_running
            if not capture_running or capture_camera is None or not capture_camera.is_open:
                return
            ok, frame = capture_camera.read()
            if not ok or frame is None:
                dialog.after(100, capture_loop)
                return

            detector = FaceDetector()
            
            try:
                min_face_size = int(self.db.get_setting("min_face_size", "80"))
            except ValueError:
                min_face_size = 80
            quality_checker = FaceQualityChecker(min_face_size)
            detection = detector.detect(frame)
            if len(detection.faces) > 1:
                capture_msg.configure(text="Only one face is allowed during approval capture. Please keep the background clear.", text_color=COLORS["orange"])
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(rgb)
                image.thumbnail((460, 320))
                request_photo = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
                if camera_label is not None and camera_label.winfo_exists():
                    camera_label.configure(image=request_photo, text="")
                dialog.after(80, capture_loop)
                return
            face = FaceDetector.largest_face(detection.faces)
            quality = quality_checker.evaluate(frame, face)
            clean_frame = frame.copy() if cv2 is not None else frame
            if cv2 is not None and face:
                x, y, w, h = face
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 245, 255), 2)

            now = time.time()
            if quality.ok and captured_samples < sample_target and now - last_capture_time >= 0.35:
                captured_samples += 1
                last_capture_time = now
                sample_path = capture_folder / f"sample_{captured_samples:03d}.jpg"
                saved = self._save_request_face_sample(clean_frame, face, sample_path)
                if not saved:
                    cv2.imwrite(str(sample_path), clean_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 96])
                tips = [
                    "Look straight at the camera",
                    "Turn your head slightly left",
                    "Turn your head slightly right",
                    "Tilt your head slightly upward",
                    "Tilt your head slightly downward",
                    "Move slightly closer, then stay centered",
                ]
                capture_msg.configure(text=tips[captured_samples % len(tips)], text_color=COLORS["green"])
                count_label.configure(text=f"Samples captured: {captured_samples}/{sample_target}", text_color=COLORS["green"])
                progress.set(captured_samples / sample_target)
            elif not quality.ok:
                text = " | ".join(quality.messages) if quality.messages else "Keep one clear face in the frame."
                capture_msg.configure(text=text, text_color=COLORS["orange"])

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            image.thumbnail((460, 320))
            request_photo = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
            if camera_label is not None and camera_label.winfo_exists():
                camera_label.configure(image=request_photo, text="")

            if captured_samples >= sample_target:
                finish_capture()
                return
            dialog.after(80, capture_loop)

        def finish_capture() -> None:
            nonlocal capture_running
            capture_running = False
            if capture_camera is not None:
                capture_camera.stop()
            start_btn.configure(state="normal")
            approve_btn.configure(state="normal")
            capture_msg.configure(
                text=f"Fresh sample capture complete. {captured_samples} samples are ready for registration.",
                text_color=COLORS["green"],
            )
            count_label.configure(text=f"Samples captured: {captured_samples}/{sample_target}", text_color=COLORS["green"])
            dialog.after(900, reset_preview)

        def close_dialog() -> None:
            nonlocal capture_running
            capture_running = False
            if capture_camera is not None:
                capture_camera.stop()
            dialog.destroy()

        def approve() -> None:
            valid, message = validate_form()
            if not valid:
                messagebox.showwarning("Missing Data", message, parent=dialog)
                return
            fresh_samples = list(capture_folder.glob("*.jpg")) if capture_folder.exists() else []
            if len(fresh_samples) < sample_target:
                messagebox.showwarning(
                    "Fresh Samples Required",
                    f"Please capture at least {sample_target} fresh face samples before approving this request.",
                    parent=dialog,
                )
                return

            uid = user_id.get().strip()
            try:
                self.db.add_user(uid, name.get().strip(), role.get().strip(), pin.get().strip() or None, status.get())
                sample_count = self._copy_request_samples_to_user(request, uid, fresh_capture_folder=capture_folder)
                count = self.recognizer.register_embeddings_from_folder(uid, REGISTERED_FACES_DIR / uid)
                if count <= 0:
                    self.db.delete_user(uid)
                    raise RuntimeError("No reliable face embeddings could be generated. Capture the samples again in better lighting.")
                self.db.complete_registration_request(request_id, uid)
                if request.get("attempt_id"):
                    self.db.update_unknown_status(request["attempt_id"], "resolved")
                close_dialog()
                messagebox.showinfo(
                    "Request Approved",
                    f"Registration request approved. User {uid} was created with {count} embedding(s) from {sample_count} saved sample(s).",
                )
                self.refresh_registration_requests()
            except Exception as exc:
                messagebox.showerror("Registration Failed", str(exc), parent=dialog)

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)

        try:
            dialog.update_idletasks()
            screen_w = dialog.winfo_screenwidth()
            screen_h = dialog.winfo_screenheight()
            win_w = dialog.winfo_width()
            win_h = dialog.winfo_height()
            x = max(30, int(screen_w * 0.03))
            y = max(20, (screen_h - win_h) // 2)
            dialog.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _save_request_face_sample(self, frame, face, path: Path) -> bool:
        """Save the already validated face area for approval registration."""
        if cv2 is None or frame is None or face is None:
            return False
        try:
            x, y, w, h = [int(v) for v in face]
            frame_h, frame_w = frame.shape[:2]
            pad = int(max(w, h) * 0.35)
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(frame_w, x + w + pad)
            y2 = min(frame_h, y + h + pad)
            crop = frame[y1:y2, x1:x2]
            if crop is None or crop.size == 0 or crop.shape[0] < 40 or crop.shape[1] < 40:
                crop = frame.copy()
            cv2.imwrite(str(path), crop, [int(cv2.IMWRITE_JPEG_QUALITY), 96])
            return True
        except Exception:
            return False

    def _copy_request_samples_to_user(
        self,
        request: dict[str, Any],
        user_id: str,
        fresh_capture_folder: Path | None = None,
    ) -> int:
        user_folder = REGISTERED_FACES_DIR / user_id
        user_folder.mkdir(parents=True, exist_ok=True)
        copied = 0

        # Fresh approval samples are the main registration source.
        if fresh_capture_folder and fresh_capture_folder.exists():
            for path in sorted(fresh_capture_folder.glob("*.jpg")):
                copied += 1
                shutil.copy2(path, user_folder / f"sample_{copied:03d}.jpg")

        # The original unknown snapshot is kept as a reference image only.
        # It is copied after the fresh samples so registration is never based on one photo.
        sample_folder = Path(request.get("sample_folder") or "")
        if sample_folder.exists():
            for path in sorted(sample_folder.glob("*.jpg")):
                copied += 1
                shutil.copy2(path, user_folder / f"request_reference_{copied:03d}.jpg")
        elif request.get("snapshot_path") and Path(request["snapshot_path"]).exists():
            copied += 1
            shutil.copy2(request["snapshot_path"], user_folder / f"request_reference_{copied:03d}.jpg")
        return copied

    def ignore_registration_request(self, request_id: str) -> None:
        if not messagebox.askyesno("Ignore Request", "Ignore this registration request? The captured attempt will remain in alerts for record keeping."):
            return
        request = self.db.get_registration_request(request_id)
        self.db.update_registration_request_status(request_id, "ignored", "Ignored by admin")
        if request and request.get("attempt_id"):
            self.db.update_unknown_status(request["attempt_id"], "reviewed")
        self.refresh_registration_requests()
