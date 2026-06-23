from __future__ import annotations

"""Single FaceLoginSystem recognition engine for AURA Guard.

This module intentionally keeps one recognition family only: the dlib
128-dimensional face descriptor used by the FaceLoginSystem supplied by the user.

Important design rules:
1. Registration and verification must create the same type of 128D descriptor.
2. The system must never approve the closest stored user unless the distance is
   below a real threshold.
3. GUI/OpenCV face boxes are used directly so registration does not fail just
   because dlib's HOG detector misses a webcam frame.
4. Weak histogram / compatibility descriptors are not used for access decisions.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import cv2
    import numpy as np
except Exception:  # pragma: no cover - handled at runtime on user machine
    cv2 = None
    np = None

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

from ..face_detector import FaceBox


DLIB_MODEL_NAME = "FaceLogin-Dlib-128D"
COMPAT_MODEL_NAME = "DISABLED-Compatibility128"


@dataclass
class EncodingResult:
    model_name: str
    embedding: list[float]
    method: str


def euclidean_distance(a: Iterable[float], b: Iterable[float]) -> float:
    if np is None:
        return 999.0
    va = np.asarray(list(a), dtype="float32")
    vb = np.asarray(list(b), dtype="float32")
    if va.shape != vb.shape or va.size == 0:
        return 999.0
    return float(np.linalg.norm(va - vb))


class FaceLoginDlibEngine:
    """Robust implementation of the attached FaceLoginSystem encoder.

    The attached FaceLoginSystem detects a face, crops it, resizes it to a face
    chip, and creates a dlib 128D descriptor.  In AURA Guard the OpenCV GUI
    already detects a valid face box, so this engine uses that box first instead
    of asking dlib to detect the same face again.  This avoids the repeated
    "No reliable face embeddings" error on webcams where OpenCV detects a face
    but dlib HOG misses it.
    """

    name = DLIB_MODEL_NAME
    compatibility_name = COMPAT_MODEL_NAME

    def __init__(self) -> None:
        self._dlib = None
        self._detector = None
        self._encoder = None
        self._shape5 = None
        self._models_loaded = False
        self._opencv_detector = None
        self.last_error: str | None = None
        self.last_method: str | None = None
        self.last_debug: list[str] = []

    # ------------------------------------------------------------------
    # Loading helpers
    # ------------------------------------------------------------------
    def _load_models(self) -> bool:
        if self._encoder is not None:
            return True
        if self._models_loaded and self._encoder is None:
            return False
        self._models_loaded = True
        try:
            import dlib
            import face_recognition_models

            self._dlib = dlib
            self._detector = dlib.get_frontal_face_detector()
            self._encoder = dlib.face_recognition_model_v1(
                face_recognition_models.face_recognition_model_location()
            )
            try:
                self._shape5 = dlib.shape_predictor(
                    face_recognition_models.pose_predictor_five_point_model_location()
                )
            except Exception as exc:
                self.last_debug.append(f"5-point landmark model not available: {exc}")
                self._shape5 = None
            return True
        except Exception as exc:  # pragma: no cover - Windows env dependent
            self.last_error = (
                "FaceLogin engine could not load dlib or bundled face_recognition_models. "
                f"Install requirements and keep the face_recognition_models folder beside main.py. Details: {exc}"
            )
            return False


    # ------------------------------------------------------------------
    # Image helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_rgb_uint8(image):
        if np is None or image is None:
            return None
        arr = np.asarray(image)
        if arr.ndim != 3 or arr.shape[2] < 3:
            return None
        arr = arr[:, :, :3]
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)
        return np.ascontiguousarray(arr)

    @staticmethod
    def _read_rgb(image_or_path: Any):
        if np is None:
            return None
        if isinstance(image_or_path, (str, Path)):
            path = Path(image_or_path)
            if Image is not None:
                try:
                    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
                except Exception:
                    pass
            if cv2 is not None:
                bgr = cv2.imread(str(path))
                if bgr is not None:
                    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            return None

        if image_or_path is None:
            return None
        frame = np.asarray(image_or_path)
        if frame.ndim != 3 or frame.shape[2] < 3:
            return None
        # AURA Guard camera frames are OpenCV BGR frames.  Saved PIL/numpy RGB
        # paths are handled above, so raw frames are treated as BGR here.
        if cv2 is not None:
            try:
                return cv2.cvtColor(frame[:, :, :3], cv2.COLOR_BGR2RGB)
            except Exception:
                pass
        return frame[:, :, :3]

    @staticmethod
    def _resize_max(rgb, max_side: int = 1000):
        if cv2 is None or rgb is None:
            return rgb
        h, w = rgb.shape[:2]
        longest = max(h, w)
        if longest <= max_side:
            return rgb
        scale = max_side / float(longest)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        return cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)

    @staticmethod
    def _expand_box(face_box: FaceBox, frame_shape, pad_ratio: float = 0.30) -> FaceBox | None:
        if face_box is None:
            return None
        x, y, w, h = [int(v) for v in face_box]
        if w <= 0 or h <= 0:
            return None
        frame_h, frame_w = frame_shape[:2]
        pad = int(max(w, h) * pad_ratio)
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(frame_w, x + w + pad)
        y2 = min(frame_h, y + h + pad)
        new_w = x2 - x1
        new_h = y2 - y1
        if new_w <= 10 or new_h <= 10:
            return None
        return (x1, y1, new_w, new_h)

    @staticmethod
    def _crop(rgb, face_box: FaceBox | None, pad_ratio: float = 0.30):
        if rgb is None or face_box is None or np is None:
            return None
        expanded = FaceLoginDlibEngine._expand_box(face_box, rgb.shape, pad_ratio)
        if expanded is None:
            return None
        x, y, w, h = expanded
        crop = rgb[y : y + h, x : x + w]
        if crop is None or getattr(crop, "size", 0) == 0:
            return None
        return np.ascontiguousarray(crop)

    @staticmethod
    def _whole_image_box(rgb) -> FaceBox | None:
        if rgb is None:
            return None
        h, w = rgb.shape[:2]
        if w < 30 or h < 30:
            return None
        return (0, 0, w, h)


    def _opencv_largest_face(self, rgb) -> FaceBox | None:
        if cv2 is None or rgb is None:
            return None
        try:
            if self._opencv_detector is None:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                detector = cv2.CascadeClassifier(cascade_path)
                if detector.empty():
                    return None
                self._opencv_detector = detector
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            faces = self._opencv_detector.detectMultiScale(
                gray,
                scaleFactor=1.12,
                minNeighbors=4,
                minSize=(40, 40),
            )
            if len(faces) == 0:
                return None
            return max([tuple(map(int, f)) for f in faces], key=lambda b: b[2] * b[3])
        except Exception as exc:
            self.last_debug.append(f"OpenCV detector failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Descriptor builders
    # ------------------------------------------------------------------
    @staticmethod
    def _valid_vector(vector) -> list[float] | None:
        if np is None or vector is None:
            return None
        arr = np.asarray(vector, dtype="float32").reshape(-1)
        if arr.shape[0] != 128:
            return None
        if not np.isfinite(arr).all():
            return None
        if float(np.linalg.norm(arr)) < 1e-6:
            return None
        return [float(x) for x in arr]


    def _descriptor_dlib_landmarks_with_box(self, rgb, face_box: FaceBox | None) -> list[float] | None:
        if np is None or rgb is None or face_box is None:
            return None
        if not self._load_models() or self._shape5 is None:
            return None
        try:
            x, y, w, h = [int(v) for v in face_box]
            x = max(0, x)
            y = max(0, y)
            right = min(rgb.shape[1] - 1, x + w)
            bottom = min(rgb.shape[0] - 1, y + h)
            if right <= x + 10 or bottom <= y + 10:
                return None
            rect = self._dlib.rectangle(int(x), int(y), int(right), int(bottom))
            shape = self._shape5(rgb, rect)
            vec = self._encoder.compute_face_descriptor(rgb, shape, 1)
            return self._valid_vector(vec)
        except Exception as exc:
            self.last_debug.append(f"dlib landmark known-box descriptor failed: {exc}")
            return None

    def _descriptor_facelogin_chip(self, rgb, face_box: FaceBox | None) -> list[float] | None:
        """Exact FaceLoginSystem crop-and-encode idea, using supplied box."""
        if cv2 is None or np is None or rgb is None:
            return None
        if not self._load_models():
            return None
        try:
            crop = self._crop(rgb, face_box, pad_ratio=0.22)
            if crop is None:
                return None
            if crop.shape[0] < 35 or crop.shape[1] < 35:
                return None
            chip = cv2.resize(crop, (150, 150), interpolation=cv2.INTER_AREA)
            chip = np.ascontiguousarray(chip, dtype=np.uint8)
            vec = self._encoder.compute_face_descriptor(chip, 0)
            return self._valid_vector(vec)
        except Exception as exc:
            self.last_debug.append(f"FaceLogin chip descriptor failed: {exc}")
            return None

    def _descriptor_by_internal_detection(self, rgb) -> tuple[list[float] | None, str | None]:
        if rgb is None:
            return None, None
        # Try OpenCV first so a face crop image can still be encoded.
        box = self._opencv_largest_face(rgb) or self._whole_image_box(rgb)
        if box is not None:
            vec = self._descriptor_dlib_landmarks_with_box(rgb, box)
            if vec is not None:
                return vec, "dlib_landmark_internal_or_whole_box"
            vec = self._descriptor_facelogin_chip(rgb, box)
            if vec is not None:
                return vec, "facelogin_chip_internal_or_whole_box"
        return None, None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def encode_all(self, image_or_path: Any, face_box: FaceBox | None = None, include_compatibility: bool = False) -> list[EncodingResult]:
        self.last_error = None
        self.last_method = None
        self.last_debug = []

        rgb = self._read_rgb(image_or_path)
        rgb = self._ensure_rgb_uint8(rgb)
        if rgb is None:
            self.last_error = "No readable RGB image was available for face encoding."
            return []
        rgb = self._resize_max(rgb)

        # If the image is a saved face-chip sample, the caller can pass a whole
        # image box.  If the caller has a live OpenCV face box, use it directly.
        boxes: list[tuple[str, FaceBox]] = []
        if face_box is not None:
            boxes.append(("provided_box", face_box))
        auto_box = self._opencv_largest_face(rgb)
        if auto_box is not None:
            boxes.append(("opencv_box", auto_box))
        whole_box = self._whole_image_box(rgb)
        if whole_box is not None:
            boxes.append(("whole_image_box", whole_box))

        # Deduplicate boxes.
        seen = set()
        unique_boxes: list[tuple[str, FaceBox]] = []
        for name, box in boxes:
            key = tuple(int(v) for v in box)
            if key not in seen:
                seen.add(key)
                unique_boxes.append((name, box))

        # 1) Direct dlib landmark descriptor with the known OpenCV/OpenCV-GUI box.
        for source, box in unique_boxes:
            vec = self._descriptor_dlib_landmarks_with_box(rgb, box)
            if vec is not None:
                self.last_method = f"dlib_landmark_known_box:{source}"
                return [EncodingResult(DLIB_MODEL_NAME, vec, self.last_method)]

        # 2) The user's FaceLoginSystem direct crop descriptor.
        for source, box in unique_boxes:
            vec = self._descriptor_facelogin_chip(rgb, box)
            if vec is not None:
                self.last_method = f"facelogin_chip:{source}"
                return [EncodingResult(DLIB_MODEL_NAME, vec, self.last_method)]

        # 3) Internal detection fallback, but still same 128D descriptor family.
        vec, method = self._descriptor_by_internal_detection(rgb)
        if vec is not None:
            self.last_method = method or "internal_detection"
            return [EncodingResult(DLIB_MODEL_NAME, vec, self.last_method)]

        self.last_error = (
            "Face encoding failed. A face was detected by the GUI, but dlib could not create a 128D descriptor. "
            "Make sure dlib is installed and the bundled face_recognition_models folder exists."
        )
        if self.last_debug:
            self.last_error += " Debug: " + " | ".join(self.last_debug[-3:])
        return []

    def encode(self, image_or_path: Any, face_box: FaceBox | None = None) -> list[float] | None:
        results = self.encode_all(image_or_path, face_box, include_compatibility=False)
        if not results:
            return None
        return results[0].embedding
