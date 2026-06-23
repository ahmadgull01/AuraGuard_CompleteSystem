from __future__ import annotations

from .face_login_engine import euclidean_distance


def face_distance(a: list[float], b: list[float]) -> float:
    return euclidean_distance(a, b)
