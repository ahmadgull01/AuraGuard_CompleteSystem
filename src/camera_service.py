"""Small webcam wrapper used by registration and user verification screens."""
from __future__ import annotations

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


class CameraService:
    """Open, read, and release a camera safely."""

    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self.capture = None
        self.error: str | None = None

    @property
    def is_open(self) -> bool:
        """Return True if a camera stream is currently active."""
        return bool(self.capture is not None and self.capture.isOpened())

    def start(self) -> bool:
        """Start the webcam stream using lightweight settings for smoother UI."""
        if cv2 is None:
            self.error = "opencv-python is not installed. Install requirements.txt first."
            return False
        self.stop()
        self.capture = cv2.VideoCapture(self.camera_index)
        if not self.capture.isOpened():
            self.error = f"Camera {self.camera_index} was not found or is busy."
            self.capture = None
            return False

        # These values reduce camera buffering and keep live preview responsive.
        # They are safe to ignore if a webcam driver does not support them.
        try:
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
            self.capture.set(cv2.CAP_PROP_FPS, 24)
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        self.error = None
        return True

    def read(self):
        """Read one frame from the camera."""
        if not self.is_open:
            return False, None
        return self.capture.read()

    def stop(self) -> None:
        """Release the camera resource."""
        if self.capture is not None:
            self.capture.release()
        self.capture = None
