from __future__ import annotations

import threading
from typing import Literal, Optional

from linkerbot import O6
from linkerbot.hand.o6.angle import O6Angle

# ── Preset poses (angles in 0-100 range) ──────────────────────
# [thumb_flex, thumb_abd, index, middle, ring, pinky]
PRESET_POSES: dict[str, list[float]] = {
    "open_hand": [100, 100, 100, 100, 100, 100],
    "half_open": [78, 78, 78, 78, 78, 78],
    "close_hand": [12, 42, 12, 12, 12, 12],
    "rps_paper": [100, 100, 100, 100, 100, 100],
    "rps_rock": [15, 40, 15, 15, 15, 15],
    "rps_scissors": [35, 65, 100, 100, 15, 15],
    "thumbs_up": [100, 80, 12, 12, 12, 12],
    "victory": [35, 65, 100, 100, 15, 15],
    "point_index": [40, 70, 100, 15, 15, 15],
    "ok_sign": [45, 25, 25, 100, 100, 100],
    "love_you": [100, 100, 100, 15, 15, 100],
    "number_three": [36, 34, 100, 100, 100, 0],
    "count_one": [40, 70, 100, 15, 15, 15],
    "count_two": [35, 65, 100, 100, 15, 15],
    "count_five": [100, 100, 100, 100, 100, 100],
    "pinch_light": [25, 35, 25, 100, 100, 100],
    "pinch_medium": [20, 30, 18, 100, 100, 100],
    "power_grip": [25, 45, 20, 25, 30, 35],
}

JOINT_NAMES: list[str] = [
    "拇指弯曲", "拇指侧摆", "食指", "中指", "无名指", "小指",
]


class O6Service:
    """O6 hand CAN control service.

    Holds ONE persistent O6 instance to avoid CAN bus conflicts.
    """

    def __init__(
        self,
        side: Literal["left", "right"] = "right",
        interface_name: str = "PCAN_USBBUS1",
        interface_type: str = "pcan",
    ) -> None:
        self._side = side
        self._interface_name = interface_name
        self._interface_type = interface_type
        self._hand: Optional[O6] = None
        self._lock = threading.Lock()
        self._connected = False
        self._error: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def connection_error(self) -> Optional[str]:
        return self._error

    def connect(self) -> bool:
        if self._hand is not None:
            self._connected = True
            return True
        try:
            self._hand = O6(
                side=self._side,
                interface_name=self._interface_name,
                interface_type=self._interface_type,
            )
            self._connected = True
            self._error = None
            return True
        except Exception as e:
            self._hand = None
            self._connected = False
            self._error = str(e)
            return False

    def disconnect(self) -> None:
        with self._lock:
            if self._hand is not None:
                try:
                    self._hand.close()
                except Exception:
                    pass
                self._hand = None
            self._connected = False

    def set_angles(self, angles: list[float]) -> bool:
        if not self._connected or self._hand is None:
            return False
        try:
            with self._lock:
                self._hand.angle.set_angles(angles)
            return True
        except Exception:
            with self._lock:
                hand = self._hand
                self._hand = None
                self._connected = False
                if hand is not None:
                    try:
                        hand.close()
                    except Exception:
                        pass
            return False

    def execute_preset(self, preset_key: str) -> bool:
        angles = PRESET_POSES.get(preset_key)
        if angles is None:
            return False
        return self.set_angles(angles)

    def get_angles(self) -> Optional[list[float]]:
        if not self._connected or self._hand is None:
            return None
        try:
            with self._lock:
                data = self._hand.angle.get_current_angles()
            if data is not None:
                return data.angles.to_list()
            return None
        except Exception:
            with self._lock:
                hand = self._hand
                self._hand = None
                self._connected = False
                if hand is not None:
                    try:
                        hand.close()
                    except Exception:
                        pass
            return None

    def get_joint_names(self) -> list[str]:
        return list(JOINT_NAMES)
