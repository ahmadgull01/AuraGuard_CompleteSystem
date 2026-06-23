from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import cv2
    import numpy as np
except Exception:  # pragma: no cover - runtime dependency
    cv2 = None
    np = None

from .config import REGISTERED_FACES_DIR
from .database_manager import DatabaseManager
from .face_detector import FaceBox, FaceDetector
from .recognition.face_login_engine import (
    DLIB_MODEL_NAME,
    FaceLoginDlibEngine,
    EncodingResult,
    euclidean_distance,
)


class FaceRecognizer:
    """FaceLoginSystem-based recognition service for AURA Guard.

    This class fixes the exact failure scenario reported by the user:
    when only one user exists, the system must NOT return that user simply
    because that user is the closest stored face.  A match is accepted only if
    the live face passes strict distance and multi-sample support checks.
    """

    MODEL_NAME = DLIB_MODEL_NAME
    DEFAULT_DISTANCE_THRESHOLD = 0.48
    MIN_REGISTRATION_EMBEDDINGS = 3

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self.settings = db.get_settings()
        self.engine = FaceLoginDlibEngine()
        self.threshold = self._read_threshold(self.settings.get("threshold", str(self.DEFAULT_DISTANCE_THRESHOLD)))
        self._attempted_auto_migration = False

    @property
    def active_model_name(self) -> str:
        return self.MODEL_NAME

    def reload_settings(self) -> None:
        self.settings = self.db.get_settings()
        self.threshold = self._read_threshold(self.settings.get("threshold", str(self.DEFAULT_DISTANCE_THRESHOLD)))

    def _read_threshold(self, value: str | float | int | None) -> float:
        try:
            threshold = float(value if value is not None else self.DEFAULT_DISTANCE_THRESHOLD)
        except (TypeError, ValueError):
            threshold = self.DEFAULT_DISTANCE_THRESHOLD
        # FaceLoginSystem used 0.45.  We allow a small range so genuine users
        # can still verify, but never allow a loose threshold like 0.7/0.9.
        return max(0.40, min(0.52, threshold))

    def embed(self, image_or_path: Any, face_box: FaceBox | None = None) -> list[float] | None:
        return self.engine.encode(image_or_path, face_box)

    def embed_all(self, image_or_path: Any, face_box: FaceBox | None = None) -> list[EncodingResult]:
        return self.engine.encode_all(image_or_path, face_box, include_compatibility=False)

    def _load_rows_for_models(self) -> list[dict[str, Any]]:
        rows = []
        for item in self.db.load_active_embeddings(self.MODEL_NAME):
            emb = item.get("embedding") or []
            if len(emb) == 128:
                rows.append(item)
        return rows

    def _auto_migrate_saved_samples_once(self) -> None:
        if self._attempted_auto_migration:
            return
        self._attempted_auto_migration = True
        try:
            current_rows = self._load_rows_for_models()
            for user in self.db.list_users(status="active"):
                user_id = user.get("user_id")
                if not user_id:
                    continue
                if any(row.get("user_id") == user_id for row in current_rows):
                    continue
                folder = REGISTERED_FACES_DIR / user_id
                if folder.exists():
                    self.register_embeddings_from_folder(user_id, folder)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Matching policy
    # ------------------------------------------------------------------
    def _effective_threshold(self, sample_count: int) -> float:
        # One or two saved samples are risky, so require very tight distance.
        # With 20+ samples, a genuine user can match several samples naturally.
        if sample_count <= 1:
            return min(self.threshold, 0.40)
        if sample_count < 5:
            return min(self.threshold, 0.43)
        if sample_count < 12:
            return min(self.threshold, 0.46)
        return min(self.threshold, 0.48)

    @staticmethod
    def _required_support(sample_count: int) -> int:
        if sample_count <= 1:
            return 1
        if sample_count < 5:
            return 1
        if sample_count < 12:
            return 2
        return max(3, min(6, int(round(sample_count * 0.18))))

    def _support_passed(self, distances: list[float], threshold: float) -> tuple[bool, float, float, int, int]:
        ordered = sorted(float(d) for d in distances if d < 998)
        if not ordered:
            return False, 999.0, 999.0, 0, 0

        sample_count = len(ordered)
        best = ordered[0]
        top_n = min(5, sample_count)
        avg_top = sum(ordered[:top_n]) / float(top_n)
        support_count = sum(1 for d in ordered if d <= threshold)
        required_support = self._required_support(sample_count)

        if sample_count <= 1:
            ok = best <= threshold
        elif sample_count < 5:
            ok = best <= threshold and avg_top <= threshold + 0.025
        else:
            ok = (
                best <= threshold
                and support_count >= required_support
                and avg_top <= threshold + 0.035
            )
        return ok, best, avg_top, support_count, required_support

    @staticmethod
    def _confidence_from_distance(distance: float, threshold: float, matched: bool) -> float:
        if distance >= 998:
            return 0.0
        if matched:
            # High confidence only after the threshold/support gate passes.
            score = 100.0 - (distance / max(threshold, 1e-6)) * 22.0
            return round(max(78.0, min(99.0, score)), 2)
        score = 100.0 - (distance / max(threshold, 1e-6)) * 35.0
        return round(max(0.0, min(70.0, score)), 2)

    def _rank_matches(self, live_embedding: list[float], stored: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_user: dict[str, dict[str, Any]] = {}
        for item in stored:
            emb = item.get("embedding") or []
            if len(emb) != len(live_embedding):
                continue
            dist = euclidean_distance(live_embedding, emb)
            bucket = by_user.setdefault(item["user_id"], {"item": item, "distances": []})
            bucket["distances"].append(dist)

        ranked: list[dict[str, Any]] = []
        for bucket in by_user.values():
            distances = bucket["distances"]
            threshold = self._effective_threshold(len(distances))
            support_ok, best, avg_top, support_count, required_support = self._support_passed(distances, threshold)
            ranked.append({
                "item": bucket["item"],
                "threshold": threshold,
                "support_ok": support_ok,
                "best": best,
                "avg_top": avg_top,
                "final_distance": avg_top,
                "relative_distance": avg_top / max(threshold, 1e-6),
                "samples": len(distances),
                "support_count": support_count,
                "required_support": required_support,
            })
        ranked.sort(key=lambda row: row["relative_distance"])
        return ranked

    def recognize(self, frame, face_box: FaceBox | None = None) -> dict[str, Any]:
        try:
            stored = self._load_rows_for_models()
            if not stored:
                self._auto_migrate_saved_samples_once()
                stored = self._load_rows_for_models()

            if not stored:
                if self.db.list_users(status="active"):
                    return {
                        "matched": False,
                        "user_id": "UNKNOWN",
                        "full_name": "Unknown",
                        "confidence": 0.0,
                        "reason": "Registered users exist, but valid FaceLogin 128D embeddings were not found. Re-register those users.",
                    }
                return {
                    "matched": False,
                    "user_id": "UNKNOWN",
                    "full_name": "Unknown",
                    "confidence": 0.0,
                    "reason": "No registered users found.",
                }

            live_results = self.embed_all(frame, face_box)
            if not live_results:
                return {
                    "matched": False,
                    "user_id": "UNKNOWN",
                    "full_name": "Unknown",
                    "confidence": 0.0,
                    "reason": self.engine.last_error or "Could not generate a FaceLogin 128D encoding from the live face.",
                }

            ranked_all: list[dict[str, Any]] = []
            for live in live_results:
                if live.model_name != self.MODEL_NAME or len(live.embedding) != 128:
                    continue
                ranked_all.extend(self._rank_matches(live.embedding, stored))

            if not ranked_all:
                return {
                    "matched": False,
                    "user_id": "UNKNOWN",
                    "full_name": "Unknown",
                    "confidence": 0.0,
                    "reason": "No compatible FaceLogin 128D data found.",
                }

            ranked_all.sort(key=lambda row: row["relative_distance"])
            best = ranked_all[0]
            second = ranked_all[1] if len(ranked_all) > 1 else None

            # If two users are close, deny instead of guessing.
            margin_ok = True
            if second is not None:
                margin_ok = (second["final_distance"] - best["final_distance"]) >= 0.035

            matched = best["best"] <= best["threshold"] and best["support_ok"] and margin_ok
            if matched:
                item = best["item"]
                return {
                    "matched": True,
                    "user_id": item["user_id"],
                    "full_name": item["full_name"],
                    "role": item["role"],
                    "confidence": self._confidence_from_distance(best["final_distance"], best["threshold"], True),
                    "model": self.MODEL_NAME,
                    "distance": round(best["final_distance"], 4),
                    "best_distance": round(best["best"], 4),
                    "threshold": round(best["threshold"], 4),
                    "samples": best["samples"],
                    "support_count": best["support_count"],
                    "required_support": best["required_support"],
                }

            return {
                "matched": False,
                "user_id": "UNKNOWN",
                "full_name": "Unknown",
                "confidence": self._confidence_from_distance(best["final_distance"], best["threshold"], False),
                "reason": (
                    "Unknown face detected. The closest registered face did not pass "
                    "the distance/support threshold, so access was denied."
                ),
                "model": self.MODEL_NAME,
                "distance": round(best["final_distance"], 4),
                "best_distance": round(best["best"], 4),
                "threshold": round(best["threshold"], 4),
                "support_count": best["support_count"],
                "required_support": best["required_support"],
            }
        except Exception as exc:
            return {
                "matched": False,
                "user_id": "UNKNOWN",
                "full_name": "Unknown",
                "confidence": 0.0,
                "reason": f"Recognition error handled safely: {exc}",
            }

    # ------------------------------------------------------------------
    # Registration processing
    # ------------------------------------------------------------------
    @staticmethod
    def _full_image_box(frame) -> FaceBox | None:
        if frame is None:
            return None
        h, w = frame.shape[:2]
        if w < 30 or h < 30:
            return None
        return (0, 0, w, h)

    def _filter_registration_vectors(self, vectors: list[list[float]]) -> list[list[float]]:
        if np is None or len(vectors) < 8:
            return vectors
        arr = np.asarray(vectors, dtype="float32")
        if arr.ndim != 2 or arr.shape[1] != 128:
            return vectors
        centroid = np.mean(arr, axis=0)
        dists = np.linalg.norm(arr - centroid, axis=1)
        median = float(np.median(dists))
        keep_limit = max(0.18, median + 0.10)
        kept = [vectors[i] for i, dist in enumerate(dists) if float(dist) <= keep_limit]
        # Never let outlier filtering break registration.
        if len(kept) < max(self.MIN_REGISTRATION_EMBEDDINGS, int(len(vectors) * 0.50)):
            return vectors
        return kept

    def register_embeddings_from_folder(self, user_id: str, folder: Path) -> int:
        self.db.delete_embeddings(user_id)
        folder = Path(folder)
        if not folder.exists():
            self.db.update_user_samples_count(user_id, 0)
            return 0

        detector = FaceDetector()
        image_paths = sorted([
            p for p in folder.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
            and not p.name.lower().startswith("request_reference")
        ])
        if not image_paths:
            image_paths = sorted([p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])

        vectors: list[list[float]] = []
        failures: list[str] = []
        for path in image_paths:
            results: list[EncodingResult] = []
            try:
                frame = cv2.imread(str(path)) if cv2 is not None else None
                if frame is not None:
                    detection = detector.detect(frame)
                    if len(detection.faces) > 1:
                        failures.append(f"{path.name}: multiple faces")
                        continue
                    face_box = FaceDetector.largest_face(detection.faces)
                    if face_box is None:
                        # Saved sample may already be a clean face crop.
                        face_box = self._full_image_box(frame)
                    results = self.embed_all(frame, face_box)
                else:
                    results = self.embed_all(path, None)
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")
                results = self.embed_all(path, None)

            found = False
            for result in results:
                if result.model_name == self.MODEL_NAME and len(result.embedding) == 128:
                    vectors.append(result.embedding)
                    found = True
                    break
            if not found:
                failures.append(f"{path.name}: {self.engine.last_error or 'no encoding'}")

        vectors = self._filter_registration_vectors(vectors)
        if len(vectors) < self.MIN_REGISTRATION_EMBEDDINGS:
            self.db.update_user_samples_count(user_id, 0)
            # Leave a useful debug file next to samples so failures can be
            # diagnosed instead of appearing as a mystery popup.
            try:
                (folder / "embedding_debug.txt").write_text(
                    "FaceLogin 128D embedding generation failed.\n"
                    f"Samples found: {len(image_paths)}\n"
                    f"Embeddings generated: {len(vectors)}\n"
                    "Recent failures:\n" + "\n".join(failures[-12:]),
                    encoding="utf-8",
                )
            except Exception:
                pass
            return 0

        for emb in vectors:
            self.db.save_embedding(user_id, emb, self.MODEL_NAME)
        self.db.update_user_samples_count(user_id, len(vectors))
        return len(vectors)
