from __future__ import annotations

import math
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from app.constants import MODEL_PATH

RPS_ANGLE_THRESHOLD = 160.0


@dataclass
class HandDetection:
    """Result of hand detection from one camera frame."""
    landmarks: list
    handedness: str
    gesture: Optional[str]


def _landmark_xyz(landmarks, idx: int) -> tuple[float, float, float]:
    lm = landmarks[idx]
    return (lm.x, lm.y, lm.z)


def _joint_angle(a, b, c) -> float:
    ba = np.array(a) - np.array(b)
    bc = np.array(c) - np.array(b)
    nba = np.linalg.norm(ba)
    nbc = np.linalg.norm(bc)
    if nba < 1e-8 or nbc < 1e-8:
        return 180.0
    cosang = float(np.dot(ba, bc) / (nba * nbc))
    cosang = float(np.clip(cosang, -1.0, 1.0))
    return math.degrees(math.acos(cosang))


def _is_finger_extended(landmarks, mcp: int, pip: int, dip: int, tip: int, angle_threshold: float = RPS_ANGLE_THRESHOLD) -> bool:
    pip_angle = _joint_angle(_landmark_xyz(landmarks, mcp), _landmark_xyz(landmarks, pip), _landmark_xyz(landmarks, dip))
    dip_angle = _joint_angle(_landmark_xyz(landmarks, pip), _landmark_xyz(landmarks, dip), _landmark_xyz(landmarks, tip))
    return pip_angle > angle_threshold and dip_angle > angle_threshold


def _is_thumb_extended(landmarks, angle_threshold: float = RPS_ANGLE_THRESHOLD) -> bool:
    mcp_angle = _joint_angle(_landmark_xyz(landmarks, 1), _landmark_xyz(landmarks, 2), _landmark_xyz(landmarks, 3))
    ip_angle = _joint_angle(_landmark_xyz(landmarks, 2), _landmark_xyz(landmarks, 3), _landmark_xyz(landmarks, 4))
    return mcp_angle > angle_threshold and ip_angle > angle_threshold


def classify_rps_gesture(landmarks) -> str:
    thumb = _is_thumb_extended(landmarks)
    index = _is_finger_extended(landmarks, 5, 6, 7, 8)
    middle = _is_finger_extended(landmarks, 9, 10, 11, 12)
    ring = _is_finger_extended(landmarks, 13, 14, 15, 16)
    pinky = _is_finger_extended(landmarks, 17, 18, 19, 20)

    if index and middle and not ring and not pinky:
        return "Scissors"

    num_extended = sum([thumb, index, middle, ring, pinky])
    if num_extended >= 4:
        return "Paper"
    if num_extended <= 1:
        return "Rock"
    return "Unknown"


def annotate_hand_overlay(frame: np.ndarray, detection: HandDetection | None, mirrored: bool = False) -> np.ndarray:
    annotated = frame.copy()
    if detection is None or detection.landmarks is None:
        return annotated

    h, w = annotated.shape[:2]
    connections = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (5, 9), (9, 10), (10, 11), (11, 12),
        (9, 13), (13, 14), (14, 15), (15, 16),
        (13, 17), (17, 18), (18, 19), (19, 20),
        (0, 17),
    ]

    points: list[tuple[int, int]] = []
    for lm in detection.landmarks:
        raw_x = int(np.clip(lm.x * w, 0, w - 1))
        x = (w - 1 - raw_x) if mirrored else raw_x
        y = int(np.clip(lm.y * h, 0, h - 1))
        points.append((x, y))

    for start, end in connections:
        cv2.line(annotated, points[start], points[end], (0, 255, 0), 2)

    for point in points:
        cv2.circle(annotated, point, 4, (255, 180, 0), -1)
        cv2.circle(annotated, point, 6, (20, 20, 20), 1)

    label = detection.handedness or "Hand"
    if detection.gesture:
        label = f"{label} | {detection.gesture}"
    cv2.putText(annotated, label, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 220, 120), 2, cv2.LINE_AA)
    return annotated


class GestureDebouncer:
    def __init__(self, required_frames: int = 3) -> None:
        self._required_frames = required_frames
        self._last_seen: str | None = None
        self._count = 0
        self._confirmed: str | None = None

    def push(self, gesture: str | None) -> str | None:
        if gesture not in {"Rock", "Paper", "Scissors"}:
            self._last_seen = None
            self._count = 0
            return None

        if gesture == self._last_seen:
            self._count += 1
        else:
            self._last_seen = gesture
            self._count = 1

        if self._count >= self._required_frames and gesture != self._confirmed:
            self._confirmed = gesture
            return gesture
        return None


class CameraService:
    """摄像头服务：捕获画面 + MediaPipe 手势检测"""

    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self._cap: Optional[cv2.VideoCapture] = None
        self._hand_landmarker = None
        self._running = False
        self._lock = threading.Lock()
        self.last_error: Optional[str] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        if self._running:
            return True
        self.last_error = None
        self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            self._cap.release()
            self._cap = None
            self.last_error = "camera open failed"
            return False

        if MODEL_PATH.exists():
            try:
                from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
                from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode
                from mediapipe.tasks.python.core.base_options import BaseOptions

                options = HandLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
                    running_mode=VisionTaskRunningMode.IMAGE,
                    num_hands=1,
                )
                self._hand_landmarker = HandLandmarker.create_from_options(options)
            except Exception as exc:
                self._hand_landmarker = None
                self.last_error = str(exc)
        else:
            self._hand_landmarker = None
            self.last_error = f"hand model missing: {MODEL_PATH.as_posix()}"

        self._running = True
        return True

    def stop(self) -> None:
        with self._lock:
            self._running = False
            if self._cap:
                self._cap.release()
                self._cap = None
            if self._hand_landmarker:
                close = getattr(self._hand_landmarker, "close", None)
                if callable(close):
                    close()
                self._hand_landmarker = None

    def read_frame(self, mirrored: bool = False) -> Optional[tuple[np.ndarray, HandDetection | None]]:
        with self._lock:
            if not self._cap or not self._running:
                return None
            ret, frame = self._cap.read()
            if not ret:
                return None
            detection = self._detect_hand(frame, mirrored)
            return frame, detection

    def _detect_hand(self, frame: np.ndarray, mirrored: bool = False) -> HandDetection | None:
        if self._hand_landmarker is None:
            return None
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            from mediapipe import Image as MPImage, ImageFormat

            mp_image = MPImage(image_format=ImageFormat.SRGB, data=rgb)
            result = self._hand_landmarker.detect(mp_image)
            if result.hand_landmarks and result.hand_landmarks[0]:
                landmarks = result.hand_landmarks[0]
                handedness = ""
                if result.handedness and result.handedness[0]:
                    handedness = result.handedness[0][0].category_name
                gesture = classify_rps_gesture(landmarks)
                self.last_error = None
                return HandDetection(landmarks=landmarks, handedness=handedness, gesture=gesture)
        except Exception as exc:
            self.last_error = str(exc)
        return None

    def __del__(self) -> None:
        self.stop()
