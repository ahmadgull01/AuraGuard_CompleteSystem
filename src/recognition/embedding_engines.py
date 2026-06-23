from __future__ import annotations

"""Compatibility module.

DeepFace, InsightFace, ONNXRuntime, and the previous OpenCV fallback model were
removed from the project.  The active recognition engine is now implemented in
``face_login_engine.py`` using the FaceLoginSystem dlib descriptor.
"""

from .face_login_engine import FaceLoginDlibEngine, euclidean_distance

__all__ = ["FaceLoginDlibEngine", "euclidean_distance"]
