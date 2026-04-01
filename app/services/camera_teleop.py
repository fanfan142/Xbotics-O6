"""Camera-based hand teleoperation for O6.

Continuously reads MediaPipe hand landmarks from CameraService,
maps them to O6 joint angles using a calibration-based approach,
and streams commands to O6 via CAN.

Calibration requires three poses:
  1. Open (palm open, fingers extended)
  2. Fist (closed)
  3. Thumb-in (thumb adducted toward palm)
"""

from __future__ import annotations

import math
import threading
from pathlib import Path
from typing import Optional

import numpy as np

from app.services.o6_service import JOINT_NAMES


# ── Calibration defaults (middle of 0-100 range) ──────────────
DEFAULT_CALIBRATION = {
    "open_angles": [80.0, 80.0, 80.0, 80.0, 80.0],
    "fist_angles": [20.0, 10.0, 10.0, 10.0, 10.0],
    "open_thumb_swing": 80.0,
    "thumb_in_swing": 20.0,
}


# ── Math helpers ───────────────────────────────────────────────
def _angle_degrees(a, b, c) -> float:
    ba = np.array(a) - np.array(b)
    bc = np.array(c) - np.array(b)
    nba = np.linalg.norm(ba)
    nbc = np.linalg.norm(bc)
    if nba < 1e-8 or nbc < 1e-8:
        return 180.0
    cosang = np.dot(ba, bc) / (nba * nbc)
    cosang = float(np.clip(cosang, -1.0, 1.0))
    return math.degrees(math.acos(cosang))


def _lm_xyz(landmarks, idx):
    lm = landmarks[idx]
    return (lm.x, lm.y, lm.z)


# ── Feature extraction ─────────────────────────────────────────
def compute_bend_angles(landmarks) -> list[float]:
    thumb = _angle_degrees(_lm_xyz(landmarks, 2), _lm_xyz(landmarks, 3), _lm_xyz(landmarks, 4))
    index = _angle_degrees(_lm_xyz(landmarks, 5), _lm_xyz(landmarks, 6), _lm_xyz(landmarks, 7))
    middle = _angle_degrees(_lm_xyz(landmarks, 9), _lm_xyz(landmarks, 10), _lm_xyz(landmarks, 11))
    ring = _angle_degrees(_lm_xyz(landmarks, 13), _lm_xyz(landmarks, 14), _lm_xyz(landmarks, 15))
    pinky = _angle_degrees(_lm_xyz(landmarks, 17), _lm_xyz(landmarks, 18), _lm_xyz(landmarks, 19))
    return [thumb, index, middle, ring, pinky]


def compute_thumb_swing_scalar(landmarks, handedness_label: str) -> float:
    p0 = np.array(_lm_xyz(landmarks, 0))
    pT = np.array(_lm_xyz(landmarks, 2))
    p5 = np.array(_lm_xyz(landmarks, 5))
    p17 = np.array(_lm_xyz(landmarks, 17))

    u = p17 - p5
    nu = np.linalg.norm(u)
    if nu < 1e-8:
        return 0.0
    u = u / nu

    v = pT - p0
    s = float(np.dot(v, u))

    if handedness_label == "Left":
        s = -s
    return s


# ── Mapping ────────────────────────────────────────────────────
def _clamp(x, a, b):
    return max(a, min(b, x))


def map_by_calibration(value, v0, v1) -> int:
    denom = v1 - v0
    if abs(denom) < 1e-8:
        return 128
    t = (value - v0) / denom
    t = _clamp(t, 0.0, 1.0)
    return int(t * 100)


# ── Smoothing ──────────────────────────────────────────────────
SMOOTH_ALPHA = 0.25
DEADBAND = 2


class CameraTeleop:
    """Hand tracking teleoperation for O6 hand."""

    def __init__(
        self,
        camera_service,
        o6_service,
        calib_file: str | Path | None = None,
    ) -> None:
        self._camera = camera_service
        self._o6 = o6_service
        if calib_file:
            self._calib_file = Path(calib_file)
        else:
            new_path = Path.home() / ".xbotics_o6" / "calibration.json"
            old_path = Path.home() / ".xbotics3" / "calibration.json"
            self._calib_file = new_path if new_path.exists() or not old_path.exists() else old_path
        self._calib_file.parent.mkdir(parents=True, exist_ok=True)

        self._calibration = dict(DEFAULT_CALIBRATION)
        self._calibrated_modes: set[str] = set()
        self._calib_mode: Optional[str] = None
        self._calib_samples: list[dict] = []
        self._CALIB_SAMPLE_TARGET = 30

        self._smoothed: list[float] = [50.0] * 6
        self._current_angles: list[float] = [50.0] * 6

        self._running = False
        self._lock = threading.Lock()
        self._target_handedness: str = "Right"

        self._load_calibration()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def calibration_ready(self) -> bool:
        return {"open", "fist", "thumb_in"}.issubset(self._calibrated_modes)

    @property
    def current_angles(self) -> list[float]:
        with self._lock:
            return list(self._current_angles)

    def set_target_handedness(self, side: str) -> None:
        self._target_handedness = "Right" if side == "right" else "Left"

    def start_calibration(self, mode: str) -> None:
        self._calib_mode = mode
        self._calib_samples = []

    def cancel_calibration(self) -> None:
        self._calib_mode = None
        self._calib_samples = []

    def _finalize_calibration(self) -> None:
        if len(self._calib_samples) < 5:
            self._calib_mode = None
            self._calib_samples = []
            return

        angles_mat = np.array([s["angles"] for s in self._calib_samples], dtype=np.float32)
        thumb_arr = np.array([s["thumb_s"] for s in self._calib_samples], dtype=np.float32)
        angles_med = np.median(angles_mat, axis=0).tolist()
        thumb_med = float(np.median(thumb_arr))

        if self._calib_mode == "open":
            self._calibration["open_angles"] = angles_med
            self._calibration["open_thumb_swing"] = thumb_med
            self._calibrated_modes.add("open")
        elif self._calib_mode == "fist":
            self._calibration["fist_angles"] = angles_med
            self._calibrated_modes.add("fist")
        elif self._calib_mode == "thumb_in":
            self._calibration["thumb_in_swing"] = thumb_med
            self._calibrated_modes.add("thumb_in")

        self._calib_mode = None
        self._calib_samples = []
        self._save_calibration()

    def _save_calibration(self) -> None:
        try:
            import json
            with open(self._calib_file, "w", encoding="utf-8") as f:
                json.dump(self._calibration, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_calibration(self) -> None:
        if not self._calib_file.exists():
            return
        try:
            import json
            with open(self._calib_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k in self._calibration:
                if k in data and data[k] is not None:
                    self._calibration[k] = data[k]
            if all(k in data for k in ("open_angles", "open_thumb_swing")):
                self._calibrated_modes.add("open")
            if "fist_angles" in data:
                self._calibrated_modes.add("fist")
            if "thumb_in_swing" in data:
                self._calibrated_modes.add("thumb_in")
        except Exception:
            pass

    def _features_to_joints(self, bend_angles: list[float], thumb_swing_s: float) -> list[int]:
        c = self._calibration
        joints = [0] * 6
        joints[0] = map_by_calibration(bend_angles[0], c["fist_angles"][0], c["open_angles"][0])
        joints[1] = map_by_calibration(thumb_swing_s, c["thumb_in_swing"], c["open_thumb_swing"])
        joints[2] = map_by_calibration(bend_angles[1], c["fist_angles"][1], c["open_angles"][1])
        joints[3] = map_by_calibration(bend_angles[2], c["fist_angles"][2], c["open_angles"][2])
        joints[4] = map_by_calibration(bend_angles[3], c["fist_angles"][3], c["open_angles"][3])
        joints[5] = map_by_calibration(bend_angles[4], c["fist_angles"][4], c["open_angles"][4])
        return joints

    def _apply_smoothing(self, raw_joints: list[int]) -> list[int]:
        out = [0] * 6
        for i in range(6):
            self._smoothed[i] = (1.0 - SMOOTH_ALPHA) * self._smoothed[i] + SMOOTH_ALPHA * float(raw_joints[i])
            candidate = int(round(self._smoothed[i]))
            candidate = int(_clamp(candidate, 0, 100))
            if abs(candidate - self._current_angles[i]) <= DEADBAND:
                out[i] = int(self._current_angles[i])
            else:
                out[i] = candidate
        return out

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def process_detection(self, detection) -> list[float] | None:
        if not self._running or detection is None or detection.landmarks is None:
            return None

        landmarks = detection.landmarks
        handedness = detection.handedness or ""
        if handedness and handedness != self._target_handedness:
            return None

        bend_angles = compute_bend_angles(landmarks)
        thumb_s = compute_thumb_swing_scalar(landmarks, handedness or self._target_handedness)

        if self._calib_mode is not None:
            self._calib_samples.append({"angles": bend_angles, "thumb_s": thumb_s})
            if len(self._calib_samples) >= self._CALIB_SAMPLE_TARGET:
                self._finalize_calibration()

        raw = self._features_to_joints(bend_angles, thumb_s)
        smoothed = self._apply_smoothing(raw)
        with self._lock:
            self._current_angles = smoothed
        self._o6.set_angles(smoothed)
        return list(smoothed)
