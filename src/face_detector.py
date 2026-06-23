"""Face detection helper using OpenCV Haar Cascade for the GUI preview.

The final recognition decision is handled by the FaceLogin-Dlib engine, while
this module provides fast face boxes for camera guidance, quality checks, and
liveness positioning.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

try:
    import cv2
except Exception:  # pragma: no cover - handled gracefully at runtime
    cv2 = None


FaceBox = Tuple[int, int, int, int]


@dataclass
class DetectionResult:
    """Result returned for each processed frame."""

    faces: List[FaceBox]
    error: str | None = None


class FaceDetector:
    """Detect faces from webcam frames."""

    def __init__(self) -> None:
        self.available = cv2 is not None
        self.detector = None
        if self.available:
            # Haar Cascade is included with OpenCV and avoids extra model files.
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.detector = cv2.CascadeClassifier(cascade_path)
            if self.detector.empty():
                self.available = False

    def detect(self, frame) -> DetectionResult:
        """Return face bounding boxes as (x, y, w, h)."""
        if not self.available or frame is None:
            return DetectionResult([], "OpenCV face detector is not available.")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.18, minNeighbors=5, minSize=(55, 55))
        return DetectionResult([tuple(map(int, f)) for f in faces])

    @staticmethod
    def largest_face(faces: List[FaceBox]) -> FaceBox | None:
        """Select the largest face when multiple boxes are present."""
        if not faces:
            return None
        return max(faces, key=lambda b: b[2] * b[3])
