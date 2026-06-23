from __future__ import annotations

import random
import time
from dataclasses import dataclass
from statistics import mean
from typing import Literal, Tuple

FaceBox = Tuple[int, int, int, int]

# The detector uses movement challenges because they are fast and do not need
# extra landmark models. The thresholds are based on face size, so the test stays
# usable when the user is closer or farther from the camera.
CHALLENGES = [
    {
        "name": "Turn your head left",
        "instruction": "Slowly move your face toward the left, then return to center.",
        "axis": "x",
        "direction": -1,
    },
    {
        "name": "Turn your head right",
        "instruction": "Slowly move your face toward the right, then return to center.",
        "axis": "x",
        "direction": 1,
    },
    {
        "name": "Nod your head up or down",
        "instruction": "Move your face slightly up or down, then return to center.",
        "axis": "y",
        "direction": 0,
    },
]


@dataclass
class LivenessState:
    challenge: str
    phase: Literal["delay", "calibrate", "challenge", "return", "passed", "failed"] = "delay"
    passed: bool = False
    failed: bool = False
    progress: float = 0.0
    message: str = "Preparing liveness test..."
    countdown: float = 0.0


class LivenessDetector:
    """Small state machine for a stricter and smoother liveness check.

    The user must wait briefly after face matching, hold still for calibration,
    perform the requested movement for a few continuous frames, and then return
    to the center. This makes the test harder to pass by accident while keeping
    it light enough for normal laptops.
    """

    def __init__(self) -> None:
        self.delay_seconds = 3.5
        self.calibration_frames_needed = 8
        self.action_frames_needed = 7
        self.return_frames_needed = 5
        self.calibration_timeout = 8.0
        self.challenge_timeout = 12.0
        self.reset()

    def reset(self) -> LivenessState:
        self.challenge_data = random.choice(CHALLENGES)
        self.state = LivenessState(
            challenge="Preparing liveness test",
            phase="delay",
            message="Face matched. Starting liveness test shortly. Keep looking at the camera.",
            countdown=self.delay_seconds,
        )
        now = time.time()
        self.started_at = now
        self.phase_started_at = now
        self.baseline_center: tuple[float, float] | None = None
        self.smoothed_center: tuple[float, float] | None = None
        self.face_size: tuple[float, float] | None = None
        self.calibration_samples: list[tuple[float, float]] = []
        self.action_frames = 0
        self.return_frames = 0
        self.lost_frames = 0
        return self.state

    def update(self, face: FaceBox | None) -> LivenessState:
        now = time.time()
        if face is None:
            self.lost_frames += 1
            self.state.message = "Keep your face visible during the liveness test."
            self.state.progress = max(0.0, self.state.progress - 0.02)
            if self.lost_frames > 18:
                self._fail("Face was lost during the liveness test.")
            return self.state

        self.lost_frames = 0
        center, size = self._smooth_face(face)
        self.face_size = size

        if self.state.phase == "delay":
            remaining = max(0.0, self.delay_seconds - (now - self.phase_started_at))
            self.state.countdown = remaining
            if self.delay_seconds > 0:
                self.state.progress = min(0.22, (self.delay_seconds - remaining) / self.delay_seconds * 0.22)
            else:
                self.state.progress = 0.22
            if remaining > 0:
                self.state.challenge = "Preparing liveness test"
                self.state.message = f"Face verified. Liveness starts in {remaining:.1f} seconds. Stay steady."
                return self.state
            self._change_phase("calibrate")

        if self.state.phase == "calibrate":
            return self._calibration_step(center)

        if self.state.phase == "challenge":
            return self._challenge_step(center, size)

        if self.state.phase == "return":
            return self._return_step(center, size)

        return self.state

    def _smooth_face(self, face: FaceBox) -> tuple[tuple[float, float], tuple[float, float]]:
        x, y, w, h = face
        center = (x + w / 2.0, y + h / 2.0)
        if self.smoothed_center is None:
            self.smoothed_center = center
        else:
            # A small smoothing factor removes jitter without making the test feel slow.
            alpha = 0.35
            self.smoothed_center = (
                self.smoothed_center[0] * (1 - alpha) + center[0] * alpha,
                self.smoothed_center[1] * (1 - alpha) + center[1] * alpha,
            )
        return self.smoothed_center, (float(w), float(h))

    def _calibration_step(self, center: tuple[float, float]) -> LivenessState:
        if time.time() - self.phase_started_at > self.calibration_timeout:
            self._fail("Center calibration timed out. Keep one clear face steady in front of the camera.")
            return self.state

        self.state.challenge = "Hold still for calibration"
        self.state.message = "Hold your face steady. The system is setting a center point."
        self.state.progress = 0.25
        self.calibration_samples.append(center)
        if len(self.calibration_samples) > self.calibration_frames_needed:
            self.calibration_samples.pop(0)

        if len(self.calibration_samples) < self.calibration_frames_needed:
            return self.state

        xs = [p[0] for p in self.calibration_samples]
        ys = [p[1] for p in self.calibration_samples]
        steady_x = max(xs) - min(xs) < 16
        steady_y = max(ys) - min(ys) < 16
        if not (steady_x and steady_y):
            # User moved during calibration, so start calibration again.
            self.calibration_samples.clear()
            self.state.message = "Too much movement. Hold still for one moment."
            self.state.progress = 0.20
            return self.state

        self.baseline_center = (mean(xs), mean(ys))
        self._change_phase("challenge")
        self.state.challenge = self.challenge_data["name"]
        self.state.message = self.challenge_data["instruction"]
        self.state.progress = 0.35
        return self.state

    def _challenge_step(self, center: tuple[float, float], size: tuple[float, float]) -> LivenessState:
        if self.baseline_center is None:
            self._change_phase("calibrate")
            return self.state

        if time.time() - self.phase_started_at > self.challenge_timeout:
            self._fail("Liveness challenge timed out.")
            return self.state

        self.state.challenge = self.challenge_data["name"]
        dx = center[0] - self.baseline_center[0]
        dy = center[1] - self.baseline_center[1]
        threshold_x = max(24.0, size[0] * 0.16)
        threshold_y = max(20.0, size[1] * 0.13)

        axis = self.challenge_data["axis"]
        direction = self.challenge_data["direction"]
        if axis == "x" and direction == -1:
            correct = dx < -threshold_x
            opposite = dx > threshold_x * 0.65
        elif axis == "x" and direction == 1:
            correct = dx > threshold_x
            opposite = dx < -threshold_x * 0.65
        else:
            correct = abs(dy) > threshold_y
            opposite = False

        if correct:
            self.action_frames += 1
            self.state.message = "Good. Hold that movement for a moment."
        else:
            if opposite:
                self.state.message = "That is the wrong direction. Follow the instruction shown above."
            else:
                self.state.message = self.challenge_data["instruction"]
            self.action_frames = max(0, self.action_frames - 1)

        action_ratio = min(1.0, self.action_frames / self.action_frames_needed)
        self.state.progress = 0.35 + action_ratio * 0.38
        if self.action_frames >= self.action_frames_needed:
            self._change_phase("return")
            self.state.challenge = "Return to center"
            self.state.message = "Now return your face to the center to finish the test."
            self.state.progress = 0.78
        return self.state

    def _return_step(self, center: tuple[float, float], size: tuple[float, float]) -> LivenessState:
        if self.baseline_center is None:
            self._change_phase("calibrate")
            return self.state

        dx = abs(center[0] - self.baseline_center[0])
        dy = abs(center[1] - self.baseline_center[1])
        center_x_ok = dx < max(18.0, size[0] * 0.10)
        center_y_ok = dy < max(16.0, size[1] * 0.10)
        self.state.challenge = "Return to center"
        if center_x_ok and center_y_ok:
            self.return_frames += 1
            self.state.message = "Center confirmed. Finishing liveness test."
        else:
            self.return_frames = max(0, self.return_frames - 1)
            self.state.message = "Bring your face back to the center."

        return_ratio = min(1.0, self.return_frames / self.return_frames_needed)
        self.state.progress = 0.78 + return_ratio * 0.22
        if self.return_frames >= self.return_frames_needed:
            self.state.phase = "passed"
            self.state.passed = True
            self.state.progress = 1.0
            self.state.challenge = "Liveness passed"
            self.state.message = "Liveness challenge completed successfully."
        return self.state

    def _change_phase(self, phase: Literal["delay", "calibrate", "challenge", "return", "passed", "failed"]) -> None:
        self.state.phase = phase
        self.phase_started_at = time.time()

    def _fail(self, message: str) -> None:
        self.state.phase = "failed"
        self.state.failed = True
        self.state.passed = False
        self.state.message = message
        self.state.progress = 0.0
