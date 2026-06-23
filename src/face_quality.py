"""Face quality checks for registration and recognition.

The SRS requires warnings for low light, blur, face size, and positioning. This
module performs those checks and returns human-readable messages for the GUI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

try:
    import cv2
    import numpy as np
except Exception:  # pragma: no cover
    cv2 = None
    np = None

FaceBox = Tuple[int, int, int, int]


@dataclass
class QualityReport:
    ok: bool
    score: float
    checks: dict[str, bool] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)


class FaceQualityChecker:
    """Analyze brightness, blur, size, and centering of a detected face."""

    def __init__(self, min_face_size: int = 80) -> None:
        self.min_face_size = min_face_size

    def evaluate(self, frame, face: FaceBox | None) -> QualityReport:
        """Return a full quality report for the current camera frame."""
        if frame is None or face is None:
            return QualityReport(False, 0.0, messages=["No face detected."])
        if cv2 is None or np is None:
            return QualityReport(True, 0.70, messages=["Quality module running in limited mode."])

        x, y, w, h = face
        height, width = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_gray = gray[max(y, 0): max(y + h, 0), max(x, 0): max(x + w, 0)]

        brightness = float(np.mean(face_gray)) if face_gray.size else 0.0
        blur_score = float(cv2.Laplacian(face_gray, cv2.CV_64F).var()) if face_gray.size else 0.0
        face_size_ok = w >= self.min_face_size and h >= self.min_face_size
        center_x = x + w / 2
        center_y = y + h / 2
        centered = abs(center_x - width / 2) < width * 0.28 and abs(center_y - height / 2) < height * 0.28
        lighting_ok = brightness >= 55
        blur_ok = blur_score >= 45

        checks = {
            "Face Detected": True,
            "Face Centered": centered,
            "Good Lighting": lighting_ok,
            "Not Blurry": blur_ok,
            "Face Size OK": face_size_ok,
        }
        messages = []
        if not centered:
            messages.append("Please center your face in the frame.")
        if not lighting_ok:
            messages.append("Low light detected. Move to a brighter place.")
        if not blur_ok:
            messages.append("Face is blurry. Hold still for a clearer capture.")
        if not face_size_ok:
            messages.append("Move closer to the camera.")

        passed = sum(1 for v in checks.values() if v)
        score = passed / len(checks)
        return QualityReport(score >= 0.80, score, checks, messages)
