from __future__ import annotations

import shutil
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

try:
    import cv2
except Exception:
    cv2 = None

from ..camera_service import CameraService
from ..config import REGISTERED_FACES_DIR
from ..face_detector import FaceDetector
from ..face_quality import FaceQualityChecker
from ..gui_components import ScannerCanvas, SectionTitle, clear_frame, ghost_button, panel, primary_button, soft_panel
from ..theme import COLORS, FONTS
from ..widgets.safety import safe_configure, safe_set, widget_alive


class RegistrationScreen:
    def page_register(self) -> None:
        page = self.page_container()
        page.grid_columnconfigure(0, weight=0, minsize=410)
        page.grid_columnconfigure(1, weight=1, minsize=520)
        SectionTitle(page, "Register User", "Add a user and capture clear face samples.").grid(row=0, column=0, columnspan=2, sticky="ew", padx=24, pady=(22, 18))

        form = panel(page)
        form.grid(row=1, column=0, sticky="new", padx=(24, 10), pady=(0, 24))
        form.configure(width=410)
        form.grid_propagate(True)
        form.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(form, text="User Details", text_color=COLORS["white"], font=FONTS["h2"]).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 12))
        self.reg_name = tk.StringVar()
        self.reg_id = tk.StringVar(value=self.db.next_user_id())
        self.reg_role = tk.StringVar()
        self.reg_pin = tk.StringVar()
        fields = [
            ("Full Name *", self.reg_name, "Enter full name", False),
            ("User ID *", self.reg_id, "Example: USR-001", False),
            ("Role / Designation *", self.reg_role, "Example: Engineer", False),
            ("PIN / Password (Optional)", self.reg_pin, "Optional", True),
        ]
        for i, (title, var, ph, secret) in enumerate(fields, start=1):
            ctk.CTkLabel(form, text=title.upper(), text_color=COLORS["muted"], font=("Segoe UI", 9, "bold")).grid(row=i * 2 - 1, column=0, sticky="w", padx=18, pady=(8, 3))
            ctk.CTkEntry(form, textvariable=var, placeholder_text=ph, show="*" if secret else "", fg_color=COLORS["panel2"], border_color=COLORS["border"], height=42, corner_radius=12).grid(row=i * 2, column=0, sticky="ew", padx=18)

        self.reg_status = tk.StringVar(value="active")
        ctk.CTkSegmentedButton(form, values=["active", "inactive"], variable=self.reg_status, selected_color=COLORS["cyan"], selected_hover_color=COLORS["cyan_dark"]).grid(row=9, column=0, sticky="ew", padx=18, pady=16)
        primary_button(form, "Start Guided Face Capture", self.start_registration_capture).grid(row=10, column=0, sticky="ew", padx=18, pady=(4, 8))
        ghost_button(form, "Generate Embeddings From Saved Samples", self.generate_embeddings_for_registered, color=COLORS["green"]).grid(row=11, column=0, sticky="ew", padx=18, pady=(0, 8))
        ghost_button(form, "Clear Form", self.page_register, color=COLORS["orange"]).grid(row=12, column=0, sticky="ew", padx=18, pady=(0, 18))

        tips = soft_panel(form)
        tips.grid(row=13, column=0, sticky="ew", padx=18, pady=(0, 18))
        ctk.CTkLabel(tips, text="Capture Tips", text_color=COLORS["cyan"], font=FONTS["small"]).pack(anchor="w", padx=14, pady=(10, 0))
        ctk.CTkLabel(tips, text="Use bright light, keep one face in frame, and follow the movement prompts.", text_color=COLORS["muted"], font=FONTS["tiny"], wraplength=440, justify="left").pack(anchor="w", padx=14, pady=(2, 10))

        capture = panel(page)
        capture.grid(row=1, column=1, sticky="new", padx=(10, 24), pady=(0, 24))
        capture.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(capture, text="Face Capture", text_color=COLORS["white"], font=FONTS["h2"]).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 6))
        self.reg_instruction = ctk.CTkLabel(capture, text="Look straight at the camera", text_color=COLORS["cyan"], font=("Segoe UI", 14, "bold"), wraplength=520, justify="left")
        self.reg_instruction.grid(row=1, column=0, sticky="w", padx=18)
        self.reg_preview = ctk.CTkFrame(capture, fg_color=COLORS["panel2"], corner_radius=20, border_width=1, border_color=COLORS["border"])
        self.reg_preview.grid(row=2, column=0, sticky="ew", padx=18, pady=14)
        self.reg_preview.grid_propagate(False)
        self.reg_preview.configure(height=340)
        self._build_registration_placeholder()
        self.reg_progress = ctk.CTkProgressBar(capture, progress_color=COLORS["green"], fg_color=COLORS["panel2"])
        self.reg_progress.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.reg_progress.set(0)
        self.reg_message = ctk.CTkLabel(capture, text="Capture 15 to 30 clear samples for better recognition.", text_color=COLORS["muted"], font=FONTS["small"], wraplength=520, justify="left")
        self.reg_message.grid(row=4, column=0, sticky="w", padx=18, pady=(0, 12))
        self.quality_box = ctk.CTkFrame(capture, fg_color="transparent")
        self.quality_box.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 18))
        self._build_quality_checks({})

    def _build_registration_placeholder(self) -> None:
        clear_frame(self.reg_preview)
        self.reg_scanner = ScannerCanvas(self.reg_preview, width=560, height=340)
        self.reg_scanner.pack(fill="both", expand=True)
        self.reg_camera_label = ctk.CTkLabel(self.reg_preview, text="")
        self.reg_camera_photo = None

    def reset_registration_preview(self) -> None:
        if widget_alive(getattr(self, "reg_preview", None)):
            self._build_registration_placeholder()
        safe_set(getattr(self, "reg_progress", None), 0)
        safe_configure(getattr(self, "reg_instruction", None), text="Look straight at the camera")
        safe_configure(getattr(self, "reg_message", None), text="Capture 15 to 30 clear samples for better recognition.", text_color=COLORS["muted"])
        if widget_alive(getattr(self, "quality_box", None)):
            self._build_quality_checks({})

    def _build_quality_checks(self, checks: dict[str, bool]) -> None:
        if not widget_alive(getattr(self, "quality_box", None)):
            return
        for child in self.quality_box.winfo_children():
            child.destroy()
        names = ["Face Detected", "Face Centered", "Good Lighting", "Not Blurry", "Face Size OK"]
        for i, name in enumerate(names):
            ok = checks.get(name, False)
            chip = ctk.CTkFrame(self.quality_box, fg_color=COLORS["green_soft"] if ok else COLORS["panel2"], corner_radius=14, border_width=1, border_color=COLORS["green"] if ok else COLORS["border"])
            chip.grid(row=i // 2, column=i % 2, sticky="ew", padx=4, pady=4)
            ctk.CTkLabel(chip, text=("OK  " if ok else "--  ") + name, text_color=COLORS["green"] if ok else COLORS["muted"], font=FONTS["tiny"]).pack(padx=12, pady=7)
        self.quality_box.grid_columnconfigure((0, 1), weight=1)

    def validate_registration_form(self) -> tuple[bool, str]:
        uid = self.reg_id.get().strip()
        if not self.reg_name.get().strip() or not uid or not self.reg_role.get().strip():
            return False, "Please fill all required fields."
        if not self.db.is_valid_user_id(uid):
            return False, "User ID must not contain spaces or special path characters."
        if self.db.user_exists(uid):
            return False, "This User ID already exists. Use another ID or delete the old user first."
        return True, "OK"

    def start_registration_capture(self) -> None:
        if getattr(self, "registration_running", False):
            safe_configure(getattr(self, "reg_message", None), text="Face capture is already running. Wait until it finishes or move to another tab to stop it.", text_color=COLORS["orange"])
            return

        ok, msg = self.validate_registration_form()
        if not ok:
            messagebox.showerror("Registration Error", msg)
            return
        settings = self.db.get_settings()
        
        try:
            self.max_samples = max(20, int(settings.get("max_samples", "20")))
        except ValueError:
            self.max_samples = 20
        
        try:
            camera_index = int(settings.get("camera_index", "0"))
        except ValueError:
            camera_index = 0
        self.camera = CameraService(camera_index)
        
        try:
            min_face_size = int(settings.get("min_face_size", "80"))
        except ValueError:
            min_face_size = 80
        self.quality_checker = FaceQualityChecker(min_face_size)
        if not self.camera.start():
            self.reg_message.configure(text=self.camera.error or "Camera could not start.", text_color=COLORS["red"])
            return
        clear_frame(self.reg_preview)
        self.reg_camera_label = ctk.CTkLabel(self.reg_preview, text="")
        self.reg_camera_label.pack(fill="both", expand=True, padx=10, pady=10)
        self.register_samples = 0
        self.last_capture_time = 0.0
        safe_user = self.reg_id.get().strip().replace("/", "_").replace("\\", "_")
        self.register_folder = REGISTERED_FACES_DIR / safe_user
        if self.register_folder.exists():
            shutil.rmtree(self.register_folder)
        self.register_folder.mkdir(parents=True, exist_ok=True)
        self.registration_running = True
        self.registration_loop()

    def registration_loop(self) -> None:
        if not self.registration_running or not self.camera.is_open:
            return
        ok, frame = self.camera.read()
        if not ok or frame is None:
            self.after(100, self.registration_loop)
            return
        detection = self.detector.detect(frame)
        if len(detection.faces) > 1:
            safe_configure(self.reg_message, text="Only one face is allowed during registration. Please keep the background clear.", text_color=COLORS["orange"])
            self._show_registration_frame(frame)
            self.after(80, self.registration_loop)
            return
        face = FaceDetector.largest_face(detection.faces)
        quality = self.quality_checker.evaluate(frame, face)
        self._build_quality_checks(quality.checks)
        clean_frame = frame.copy() if cv2 is not None else frame
        if cv2 is not None and face:
            x, y, w, h = face
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 245, 255), 2)
        now = time.time()
        if quality.ok and self.register_folder and self.register_samples < self.max_samples and now - self.last_capture_time >= 0.35:
            self.register_samples += 1
            self.last_capture_time = now
            path = self.register_folder / f"sample_{self.register_samples:03d}.jpg"
            saved = self._save_clean_face_sample(clean_frame, face, path)
            if not saved and cv2 is not None:
                cv2.imwrite(str(path), clean_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 96])
            instructions = ["Look straight at the camera", "Turn head slightly left", "Turn head slightly right", "Tilt head up slightly", "Tilt head down slightly", "Move slightly forward"]
            safe_configure(self.reg_instruction, text=instructions[self.register_samples % len(instructions)])
            safe_configure(self.reg_message, text=f"Captured {self.register_samples}/{self.max_samples} samples.", text_color=COLORS["green"])
            safe_set(self.reg_progress, self.register_samples / self.max_samples)
        elif not quality.ok:
            safe_configure(self.reg_message, text=" | ".join(quality.messages) if quality.messages else "Improve face quality.", text_color=COLORS["orange"])
        self._show_registration_frame(frame)
        if self.register_samples >= self.max_samples:
            self.finish_registration()
            return
        self.after(80, self.registration_loop)


    def _save_clean_face_sample(self, frame, face, path: Path) -> bool:
        """Save a clean face crop for the FaceLogin encoder.

        Earlier versions saved the whole camera frame and later tried to detect
        the face again from that saved image.  That made registration fail on
        some webcams.  This method saves the already validated face region with
        some padding, so embedding generation receives a clean face sample.
        """
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

    def _show_registration_frame(self, frame) -> None:
        if cv2 is None or self.reg_camera_label is None:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        image.thumbnail((560, 340))
        self.reg_camera_photo = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        if widget_alive(self.reg_camera_label):
            self.reg_camera_label.configure(image=self.reg_camera_photo, text="")

    def finish_registration(self) -> None:
        self.registration_running = False
        self.camera.stop()
        user_id = self.reg_id.get().strip()
        try:
            self.db.add_user(user_id, self.reg_name.get().strip(), self.reg_role.get().strip(), self.reg_pin.get().strip() or None, self.reg_status.get())
            count = self.recognizer.register_embeddings_from_folder(user_id, self.register_folder or Path())
            if count <= 0:
                self.db.delete_user(user_id)
                raise RuntimeError("No reliable face embeddings could be generated. Please capture the user again in better lighting.")
            self.reset_registration_preview()
            self.reg_message.configure(text=f"Registration complete. {count} sample image(s) processed for recognition.", text_color=COLORS["green"])
            messagebox.showinfo("Registration Complete", f"User {user_id} registered successfully with {count} processed sample image(s).")
        except Exception as exc:
            self.reg_message.configure(text=f"Registration failed: {exc}", text_color=COLORS["red"])
            messagebox.showerror("Registration Failed", str(exc))

    def generate_embeddings_for_registered(self) -> None:
        user_id = self.reg_id.get().strip()
        folder = REGISTERED_FACES_DIR / user_id
        if not self.db.user_exists(user_id):
            messagebox.showerror("User Missing", "User ID must already exist in the database.")
            return
        if not folder.exists():
            messagebox.showerror("Samples Missing", f"No sample folder found: {folder}")
            return
        count = self.recognizer.register_embeddings_from_folder(user_id, folder)
        if count <= 0:
            messagebox.showerror("Embedding Failed", "No reliable embeddings were generated. Capture clearer samples and try again.")
            return
        messagebox.showinfo("Embeddings Generated", f"Processed {count} sample image(s) for {user_id}.")
