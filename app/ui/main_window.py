from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QSizePolicy, QTabWidget,
    QVBoxLayout, QWidget,
)

from app.constants import (
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_TITLE,
    DEFAULT_WINDOW_WIDTH,
    RUNTIME_CONFIG_PATH,
)
from app.services.o6_service import O6Service


APP_STYLE = """
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    background: #f8fafc;
    color: #0f172a;
}
QPushButton {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 14px;
}
QPushButton:hover { background: #f1f5f9; border-color: #94a3b8; }
QPushButton:pressed { background: #e2e8f0; }
QPushButton#GestureBtn {
    min-width: 80px; min-height: 52px;
    font-size: 13px;
    background: #ffffff; color: #0f172a;
    border: 1px solid #cbd5e1;
}
QPushButton#GestureBtn[high_risk="true"] {
    background: #fff7f7; color: #9f1239; border: 1px solid #fecdd3;
}
QPushButton#GestureBtn[high_risk="true"]:hover { background: #fff1f2; }
QPushButton:disabled, QPushButton#GestureBtn:disabled { background: #e2e8f0; color: #94a3b8; }
QFrame#Card {
    background: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 8px;
}
QLabel#SectionTitle { color: #0f172a; font-size: 15px; font-weight: bold; background: transparent; }
QLabel#GestureLabel { color: #0f766e; font-size: 20px; font-weight: bold; background: transparent; }
QTabWidget::pane { border: 1px solid #e2e8f0; background: #ffffff; }
QTabBar::tab { background: #e2e8f0; color: #334155; padding: 8px 14px; border: 1px solid #cbd5e1; }
QTabBar::tab:selected { background: #ffffff; color: #0f172a; }
QComboBox, QPlainTextEdit {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
}
"""


ACTION_REFRESH_INTERVAL_MS = 200
ACTION_REFRESH_TICKS = 5


def _probe_cameras() -> list[dict]:
    results = []
    for idx in range(5):
        try:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                backend = cap.getBackendName()
                cap.release()
                results.append({"index": idx, "name": f"Camera {idx} ({backend})"})
        except Exception:
            pass
    return results


# ── Info Panel ──────────────────────────────────────────────
class InfoPanel(QFrame):
    JOINT_NAMES = [
        "拇指弯曲", "拇指侧摆", "食指", "中指", "无名指", "小指",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        lbl = QLabel("设备信息总览")
        lbl.setObjectName("SectionTitle")
        layout.addWidget(lbl)

        self._joints: dict[str, QLabel] = {}
        for name in self.JOINT_NAMES:
            row = QHBoxLayout()
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet("color: #9ca3af;")
            lbl_val = QLabel("--")
            lbl_val.setStyleSheet("color: #60a5fa; font-weight: bold;")
            row.addWidget(lbl_name)
            row.addStretch(1)
            row.addWidget(lbl_val)
            layout.addLayout(row)
            self._joints[name] = lbl_val

        self._status = QLabel("状态：就绪")
        self._status.setStyleSheet("color: #34d399; font-weight: bold; margin-top: 8px;")
        layout.addWidget(self._status)
        layout.addStretch(1)

    def update_joint(self, name: str, angle: str) -> None:
        if name in self._joints:
            self._joints[name].setText(angle)

    def update_all_joints(self, angles: list[float] | list[str]) -> None:
        for i, name in enumerate(self.JOINT_NAMES):
            if i < len(angles):
                value = angles[i]
                if isinstance(value, str):
                    self._joints[name].setText(value)
                else:
                    self._joints[name].setText(f"{value:.0f}")

    def set_status(self, text: str, ok: bool = True) -> None:
        color = "#34d399" if ok else "#f87171"
        self._status.setStyleSheet(f"color: {color}; font-weight: bold; margin-top: 8px;")
        self._status.setText(f"状态：{text}")


# ── Gesture Grid ────────────────────────────────────────────
class GestureGrid(QFrame):
    def __init__(self, on_gesture) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._on_gesture = on_gesture
        self._active_key: str | None = None

        layout = QVBoxLayout(self)
        lbl = QLabel("手势控制")
        lbl.setObjectName("SectionTitle")
        layout.addWidget(lbl)

        self._btns: dict[str, QPushButton] = {}
        grid = QGridLayout()
        gestures = [
            ("张开", "open_hand", False),
            ("半开", "half_open", False),
            ("轻捏", "pinch_light", False),
            ("点赞", "thumbs_up", False),
            ("剪刀", "victory", False),
            ("指向", "point_index", False),
            ("OK", "ok_sign", False),
            ("我爱你", "love_you", False),
            ("数字三", "number_three", False),
            ("数字一", "count_one", False),
            ("数字二", "count_two", False),
            ("数字五", "count_five", False),
            ("握拳", "close_hand", True),
            ("中捏", "pinch_medium", True),
            ("强力抓", "power_grip", True),
        ]
        for idx, (label, key, high_risk) in enumerate(gestures):
            btn = QPushButton(label)
            btn.setObjectName("GestureBtn")
            btn.setProperty("high_risk", high_risk)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumHeight(52)
            btn.clicked.connect(lambda _, k=key: self._on_click(k))
            self._btns[key] = btn
            grid.addWidget(btn, idx // 3, idx % 3)
        layout.addLayout(grid)

    def _on_click(self, key: str) -> None:
        if self._active_key is not None:
            return
        self._active_key = key
        self._set_buttons_enabled(False)
        self._on_gesture(key)

    def set_loading(self, loading: bool) -> None:
        self._active_key = None
        self._set_buttons_enabled(True)

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for btn in self._btns.values():
            btn.setEnabled(enabled)


# ── Camera Thread ────────────────────────────────────────────
class _CameraThread(QThread):
    frame_ready = Signal(object, object)

    def __init__(self, service, mirrored: bool = False) -> None:
        super().__init__()
        self._service = service
        self._stop = False
        self._mirrored = mirrored

    def run(self) -> None:
        while not self._stop:
            frame_data = self._service.read_frame(mirrored=self._mirrored)
            if frame_data is None:
                time.sleep(0.03)
                continue
            bgr, detection = frame_data
            self.frame_ready.emit(bgr, detection)

    def stop(self) -> None:
        self._stop = True


# ── Camera Panel ────────────────────────────────────────────
class CameraPanel(QFrame):
    def __init__(self, o6_service=None, info_panel=None) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._camera_index = 0
        self._mirror = True
        self._service = None
        self._thread: _CameraThread | None = None
        self._o6 = o6_service
        self._info_panel = info_panel
        self._teleop = None
        self._shared_mode = False

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("摄像头跟随")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)

        self._gesture_lbl = QLabel("手势：--")
        self._gesture_lbl.setObjectName("GestureLabel")
        header.addWidget(self._gesture_lbl, 1)
        layout.addLayout(header)

        calib_row = QHBoxLayout()
        calib_row.addWidget(QLabel("<b>标定：</b>"))
        self._calib_open_btn = QPushButton("张开标定")
        self._calib_open_btn.setMaximumWidth(90)
        self._calib_open_btn.clicked.connect(self._on_calib_open)
        calib_row.addWidget(self._calib_open_btn)

        self._calib_fist_btn = QPushButton("握拳标定")
        self._calib_fist_btn.setMaximumWidth(90)
        self._calib_fist_btn.clicked.connect(self._on_calib_fist)
        calib_row.addWidget(self._calib_fist_btn)

        self._calib_thumb_btn = QPushButton("拇指内收标定")
        self._calib_thumb_btn.setMaximumWidth(120)
        self._calib_thumb_btn.clicked.connect(self._on_calib_thumb)
        calib_row.addWidget(self._calib_thumb_btn)

        self._calib_status_lbl = QLabel("未标定")
        self._calib_status_lbl.setStyleSheet("color: #f87171; font-size: 12px;")
        calib_row.addWidget(self._calib_status_lbl)
        calib_row.addStretch(1)
        layout.addLayout(calib_row)

        teleop_row = QHBoxLayout()
        self._teleop_btn = QPushButton("启动跟随")
        self._teleop_btn.clicked.connect(self._toggle_teleop)
        teleop_row.addWidget(self._teleop_btn)
        teleop_row.addWidget(QLabel("摄像头跟随：实时将手部动作映射到 O6 关节"))
        teleop_row.addStretch(1)
        layout.addLayout(teleop_row)

        self._camera_lbl = QLabel("<center><span style='color:#6b7280'>摄像头画面</span></center>")
        self._camera_lbl.setMinimumHeight(200)
        self._camera_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_lbl.setStyleSheet("background: #0b1220; border: 1px solid #1e3a5f; border-radius: 10px;")
        layout.addWidget(self._camera_lbl)

    def set_shared_camera(self, service, mirror: bool) -> None:
        self._service = service
        self._mirror = mirror
        self._shared_mode = True

    def _on_shared_frame(self, bgr, detection) -> None:
        self._on_frame(bgr, detection)

    def _on_camera_stopped(self) -> None:
        self._stop_teleop()
        self._gesture_lbl.setText("手势：--")
        self._camera_lbl.setText("<center><span style='color:#6b7280'>摄像头已停止</span></center>")

    def _stop_camera(self) -> bool:
        self._stop_teleop()
        if getattr(self, "_shared_mode", False):
            return True
        if self._service is not None:
            self._service.stop()
        if self._thread is not None:
            self._thread.stop()
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
        return True

    def _on_frame(self, bgr, detection) -> None:
        from app.services.camera_service import annotate_hand_overlay

        if self._mirror:
            bgr = cv2.flip(bgr, 1)
        bgr = annotate_hand_overlay(bgr, detection, mirrored=self._mirror)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        from PySide6.QtGui import QImage

        qimage = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage).scaled(
            max(self._camera_lbl.width(), 1) or 640,
            max(self._camera_lbl.height(), 1) or 360,
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        self._camera_lbl.setPixmap(pixmap)

        if self._teleop is not None and self._teleop.is_running:
            teleop_angles = self._teleop.process_detection(detection)
            if teleop_angles and self._info_panel:
                self._info_panel.update_all_joints(teleop_angles)
                self._gesture_lbl.setText("角度：" + " / ".join(f"{int(v):02d}" for v in teleop_angles))
                self._update_calib_status()
                return

        gesture = detection.gesture if detection else None
        if gesture:
            self._gesture_lbl.setText(f"手势：{gesture}")
        else:
            self._gesture_lbl.setText("手势：--")

    def _toggle_teleop(self) -> None:
        if self._teleop is not None and self._teleop.is_running:
            self._stop_teleop()
        else:
            self._start_teleop()

    def _start_teleop(self) -> None:
        if self._o6 is None:
            self._gesture_lbl.setText("O6 未连接")
            return
        if self._service is None or not self._service.is_running:
            self._gesture_lbl.setText("请先启动摄像头")
            return
        if self._teleop is not None:
            self._stop_teleop()

        from app.services.camera_teleop import CameraTeleop
        self._teleop = CameraTeleop(camera_service=self._service, o6_service=self._o6)
        side = getattr(self._o6, "_side", "right")
        self._teleop.set_target_handedness(side)
        self._teleop.start()
        self._teleop_btn.setText("停止跟随")
        self._gesture_lbl.setText("跟随中...")
        self._update_calib_status()

    def _stop_teleop(self) -> None:
        if self._teleop is not None:
            self._teleop.stop()
            self._teleop = None
        self._teleop_btn.setText("启动跟随")
        if self._service and self._service.is_running:
            self._gesture_lbl.setText("手势：--")

    def _on_calib_open(self) -> None:
        if self._teleop is None:
            self._gesture_lbl.setText("请先启动跟随")
            return
        self._teleop.start_calibration("open")
        self._gesture_lbl.setText("标定中：张开...")

    def _on_calib_fist(self) -> None:
        if self._teleop is None:
            self._gesture_lbl.setText("请先启动跟随")
            return
        self._teleop.start_calibration("fist")
        self._gesture_lbl.setText("标定中：握拳...")

    def _on_calib_thumb(self) -> None:
        if self._teleop is None:
            self._gesture_lbl.setText("请先启动跟随")
            return
        self._teleop.start_calibration("thumb_in")
        self._gesture_lbl.setText("标定中：拇指向掌内...")

    def _update_calib_status(self) -> None:
        if self._teleop is None:
            self._calib_status_lbl.setText("未标定")
            self._calib_status_lbl.setStyleSheet("color: #f87171; font-size: 12px;")
            return
        if self._teleop.calibration_ready:
            self._calib_status_lbl.setText("已标定")
            self._calib_status_lbl.setStyleSheet("color: #34d399; font-size: 12px;")
        else:
            self._calib_status_lbl.setText("标定中：请保持当前手势约 1 秒")
            self._calib_status_lbl.setStyleSheet("color: #fbbf24; font-size: 12px;")

    def closeEvent(self, event) -> None:
        if not self._stop_camera():
            event.ignore()
            return
        super().closeEvent(event)


# ── RPS Panel ──────────────────────────────────────────────
class _RPSTask(QThread):
    result_ready = Signal(object, object, object)
    failed = Signal(str)

    def __init__(self, frame_provider) -> None:
        super().__init__()
        self._frame_provider = frame_provider
        self._stop = False

    def run(self) -> None:
        deadline = time.monotonic() + 5.0
        from app.services.camera_service import GestureDebouncer
        debouncer = GestureDebouncer(required_frames=3)
        gesture = None
        while time.monotonic() < deadline and not self._stop:
            frame_data = self._frame_provider()
            if frame_data is None:
                time.sleep(0.03)
                continue
            _, detection = frame_data
            detected = detection.gesture if detection else None
            confirmed = debouncer.push(detected)
            if confirmed in ("Rock", "Paper", "Scissors"):
                gesture = confirmed
                break
            time.sleep(0.03)
        if self._stop:
            return
        if gesture:
            counter_map = {"Rock": "Paper", "Paper": "Scissors", "Scissors": "Rock"}
            computer = counter_map[gesture]
            outcome = "你输了！"
            self.result_ready.emit(gesture, computer, outcome)
            return
        self.failed.emit("5 秒内未识别到稳定手势，请重试")

    def stop(self) -> None:
        self._stop = True


class RSPanel(QFrame):
    def __init__(self, o6_service=None) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._mirror = True
        self._service = None
        self._thread: _RPSTask | None = None
        self._wins = self._losses = self._draws = 0
        self._o6 = o6_service
        self._latest_frame_detection = None

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("猜拳互动")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)

        self._score_lbl = QLabel("胜: 0 | 负: 0 | 平: 0")
        self._start_btn = QPushButton("开始猜拳")
        self._start_btn.clicked.connect(self._toggle_game)
        header.addWidget(self._score_lbl, 1)
        header.addWidget(self._start_btn)
        layout.addLayout(header)

        self._camera_lbl = QLabel("<center><span style='color:#6b7280'>摄像头画面</span></center>")
        self._camera_lbl.setMinimumHeight(140)
        self._camera_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._camera_lbl.setStyleSheet("background: #0b1220; border: 1px solid #1e3a5f; border-radius: 10px;")
        layout.addWidget(self._camera_lbl)

        self._result_lbl = QLabel("做出手势：石头/布/剪刀")
        self._result_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._result_lbl)

        self._detected_lbl = QLabel("检测到手势：--")
        self._detected_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._detected_lbl)

    def set_shared_camera(self, service, mirror: bool) -> None:
        self._service = service
        self._mirror = mirror

    def _current_frame_data(self):
        return self._latest_frame_detection

    def _toggle_game(self) -> None:
        if self._thread and self._thread.isRunning():
            self._stop_game()
        else:
            self._start_game()

    def _start_game(self) -> bool:
        if self._service is None or not self._service.is_running:
            self._result_lbl.setText("请先启动摄像头")
            return False
        self._start_btn.setText("停止猜拳")
        self._start_btn.setEnabled(True)
        self._thread = _RPSTask(self._current_frame_data)
        self._thread.result_ready.connect(self._on_result)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()
        return True

    def _stop_game(self) -> bool:
        if self._thread:
            self._thread.stop()
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
        self._start_btn.setText("开始猜拳")
        self._start_btn.setEnabled(True)
        self._detected_lbl.setText("检测到手势：--")
        self._result_lbl.setText("做出手势：石头/布/剪刀")
        return True

    def _on_shared_frame(self, bgr, detection) -> None:
        self._latest_frame_detection = (bgr, detection)
        self._on_preview_frame(bgr, detection)

    def _on_camera_stopped(self) -> None:
        self._latest_frame_detection = None
        self._camera_lbl.setText("<center><span style='color:#6b7280'>摄像头已停止</span></center>")
        self._detected_lbl.setText("检测到手势：--")
        if self._thread is not None:
            self._stop_game()

    def _on_preview_frame(self, bgr, detection) -> None:
        if self._mirror:
            bgr = cv2.flip(bgr, 1)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        from PySide6.QtGui import QImage

        qimage = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage).scaled(
            max(self._camera_lbl.width(), 1) or 640,
            max(self._camera_lbl.height(), 1) or 360,
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        self._camera_lbl.setPixmap(pixmap)
        gesture = detection.gesture if detection else None
        self._detected_lbl.setText(f"检测到手势：{gesture or '--'}")

    def _on_result(self, player, computer, outcome) -> None:
        self._thread = None

        counter_preset = {
            "Rock": "rps_paper",
            "Paper": "rps_scissors",
            "Scissors": "rps_rock",
        }.get(player)
        if self._o6 is not None and counter_preset is not None:
            self._o6.execute_preset(counter_preset)

        if outcome == "你赢了！":
            self._wins += 1
        elif outcome == "你输了！":
            self._losses += 1
        else:
            self._draws += 1

        self._score_lbl.setText(f"胜: {self._wins} | 负: {self._losses} | 平: {self._draws}")
        self._result_lbl.setText(f"你出：{player} | O6 出：{computer} → {outcome}")
        self._detected_lbl.setText(f"检测到手势：{player}")
        self._start_btn.setText("开始猜拳")
        self._start_btn.setEnabled(True)

    def _on_failed(self, message: str) -> None:
        self._thread = None
        self._start_btn.setText("开始猜拳")
        self._start_btn.setEnabled(True)
        self._result_lbl.setText(message)
        self._detected_lbl.setText("检测到手势：--")

    def closeEvent(self, event) -> None:
        if not self._stop_game():
            event.ignore()
            return
        super().closeEvent(event)


# ── Main Window ─────────────────────────────────────────────
class _ActionTask(QThread):
    finished = Signal(str)

    def __init__(self, fn) -> None:
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        result = self._fn()
        self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(DEFAULT_WINDOW_TITLE)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.setStyleSheet(APP_STYLE)
        self._action_task: _ActionTask | None = None
        self._o6_service = None
        self._camera_service = None
        self._camera_thread: _CameraThread | None = None
        self._camera_index = 0
        self._mirror = True
        self._overview_timer = QTimer(self)
        self._overview_timer.setInterval(300)
        self._overview_timer.timeout.connect(self._refresh_joint_overview)
        self._action_refresh_timer = QTimer(self)
        self._action_refresh_timer.setInterval(ACTION_REFRESH_INTERVAL_MS)
        self._action_refresh_timer.timeout.connect(self._on_action_refresh_tick)
        self._action_refresh_remaining = 0

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        content = QHBoxLayout()
        outer.addLayout(content, 1)

        left = QVBoxLayout()
        right = QVBoxLayout()
        content.addLayout(left, 2)
        content.addLayout(right, 3)

        self._info_panel = InfoPanel()
        self._gesture_grid = GestureGrid(self._on_gesture)
        left.addWidget(self._gesture_grid, 3)
        left.addWidget(self._info_panel, 1)

        camera_bar = QFrame()
        camera_bar.setObjectName("Card")
        camera_bar_layout = QHBoxLayout(camera_bar)
        camera_bar_layout.addWidget(QLabel("共享摄像头"))
        self._camera_combo = QComboBox()
        self._camera_combo.setMinimumWidth(180)
        self._populate_shared_cameras()
        self._camera_combo.currentIndexChanged.connect(self._on_shared_camera_changed)
        camera_bar_layout.addWidget(self._camera_combo)
        self._mirror_check = QCheckBox("镜像翻转")
        self._mirror_check.setChecked(True)
        self._mirror_check.stateChanged.connect(self._on_shared_mirror_changed)
        camera_bar_layout.addWidget(self._mirror_check)
        self._camera_toggle_btn = QPushButton("启动摄像头")
        self._camera_toggle_btn.clicked.connect(self._toggle_shared_camera)
        camera_bar_layout.addWidget(self._camera_toggle_btn)
        self._camera_status_lbl = QLabel("状态：摄像头未启动")
        camera_bar_layout.addWidget(self._camera_status_lbl, 1)
        right.addWidget(camera_bar)

        self._camera_tabs = QTabWidget()
        self._camera_panel = CameraPanel(o6_service=None, info_panel=self._info_panel)
        self._rps_panel = RSPanel(o6_service=None)
        self._camera_tabs.addTab(self._camera_panel, "摄像头跟随")
        self._camera_tabs.addTab(self._rps_panel, "猜拳互动")
        self._camera_tabs.currentChanged.connect(self._on_tab_changed)
        right.addWidget(self._camera_tabs, 3)

        self._camera_panel.set_shared_camera(self._camera_service, self._mirror)
        self._rps_panel.set_shared_camera(self._camera_service, self._mirror)

        self._init_o6()

    def _init_o6(self) -> None:
        o6_cfg: dict = {}
        if RUNTIME_CONFIG_PATH.exists():
            try:
                with open(RUNTIME_CONFIG_PATH, encoding="utf-8") as f:
                    cfg = json.load(f)
                o6_cfg = cfg.get("o6", {})
            except (OSError, json.JSONDecodeError) as exc:
                self._o6_service = None
                self._info_panel.set_status(f"O6 配置读取失败（{exc}）", ok=False)
                return

        try:
            service = O6Service(
                side=o6_cfg.get("side", "right"),
                interface_name=o6_cfg.get("interface_name", "PCAN_USBBUS1"),
                interface_type=o6_cfg.get("interface_type", "pcan"),
            )
            if service.connect():
                self._o6_service = service
                self._info_panel.set_status("O6 已连接", ok=True)
                self._overview_timer.start()
                self._refresh_joint_overview()
                if hasattr(self, '_camera_panel'):
                    self._camera_panel._o6 = service
                if hasattr(self, '_rps_panel'):
                    self._rps_panel._o6 = service
            else:
                self._o6_service = None
                error = getattr(service, "connection_error", None)
                if error:
                    self._info_panel.set_status(f"O6 未连接（{error}）", ok=False)
                else:
                    self._info_panel.set_status("O6 未连接（CAN不可用）", ok=False)
        except Exception as exc:
            self._o6_service = None
            self._info_panel.set_status(f"O6 初始化失败（{exc}）", ok=False)

    def _populate_shared_cameras(self) -> None:
        devices = _probe_cameras()
        self._camera_combo.blockSignals(True)
        self._camera_combo.clear()
        if devices:
            for dev in devices:
                self._camera_combo.addItem(dev["name"], dev["index"])
        else:
            self._camera_combo.addItem("未检测到摄像头", -1)
        self._camera_combo.blockSignals(False)

    def _on_shared_camera_changed(self, index: int) -> None:
        self._camera_index = int(self._camera_combo.currentData() or 0)
        if self._camera_service is not None and self._camera_service.is_running:
            self._stop_shared_camera()
            self._start_shared_camera()

    def _on_shared_mirror_changed(self, state: int) -> None:
        self._mirror = bool(state)
        if self._camera_thread is not None:
            self._camera_thread._mirrored = self._mirror
        self._camera_panel.set_shared_camera(self._camera_service, self._mirror)
        self._rps_panel.set_shared_camera(self._camera_service, self._mirror)

    def _toggle_shared_camera(self) -> None:
        if self._camera_service is not None and self._camera_service.is_running:
            self._stop_shared_camera()
        else:
            self._start_shared_camera()

    def _start_shared_camera(self) -> bool:
        from app.services.camera_service import CameraService

        self._camera_index = int(self._camera_combo.currentData() or 0)
        self._camera_service = CameraService(camera_index=self._camera_index)
        if not self._camera_service.start():
            self._camera_status_lbl.setText("状态：摄像头无法打开")
            return False
        self._camera_thread = _CameraThread(self._camera_service, mirrored=self._mirror)
        self._camera_thread.frame_ready.connect(self._on_shared_frame)
        self._camera_thread.start()
        self._camera_toggle_btn.setText("停止摄像头")
        self._camera_combo.setEnabled(False)
        detector_error = getattr(self._camera_service, "last_error", None)
        if detector_error:
            self._camera_status_lbl.setText(f"状态：摄像头运行中（识别异常：{detector_error}）")
        else:
            self._camera_status_lbl.setText("状态：摄像头运行中")
        self._camera_panel.set_shared_camera(self._camera_service, self._mirror)
        self._rps_panel.set_shared_camera(self._camera_service, self._mirror)
        return True

    def _stop_shared_camera(self) -> bool:
        if self._camera_service is not None:
            self._camera_service.stop()
        if self._camera_thread is not None:
            self._camera_thread.stop()
            self._camera_thread.quit()
            self._camera_thread.wait(2000)
            self._camera_thread = None
        self._camera_toggle_btn.setText("启动摄像头")
        self._camera_combo.setEnabled(True)
        self._camera_status_lbl.setText("状态：摄像头未启动")
        if getattr(self, "_camera_panel", None) is not None:
            self._camera_panel._on_camera_stopped()
        if getattr(self, "_rps_panel", None) is not None:
            self._rps_panel._on_camera_stopped()
        return True

    def _on_shared_frame(self, frame, detection) -> None:
        if getattr(self, "_camera_panel", None) is not None:
            self._camera_panel._on_shared_frame(frame, detection)
        if getattr(self, "_rps_panel", None) is not None:
            self._rps_panel._on_shared_frame(frame, detection)

    def _on_tab_changed(self, index: int) -> None:
        if index != 1:
            return
        camera_panel = getattr(self, "_camera_panel", None)
        teleop = getattr(camera_panel, "_teleop", None) if camera_panel is not None else None
        if teleop is not None and teleop.is_running:
            camera_panel._stop_teleop()
            if self._o6_service is not None:
                self._o6_service.execute_preset("open_hand")
                if hasattr(self, "_info_panel"):
                    self._refresh_joint_overview()

    def _refresh_joint_overview(self) -> None:
        if getattr(self, "_camera_panel", None) is not None:
            teleop = getattr(self._camera_panel, "_teleop", None)
            if teleop is not None and teleop.is_running:
                return
        if self._o6_service is None:
            self._info_panel.update_all_joints(["--", "--", "--", "--", "--", "--"])
            return
        angles = self._o6_service.get_angles()
        if angles is None:
            self._info_panel.update_all_joints(["--", "--", "--", "--", "--", "--"])
            return
        self._info_panel.update_all_joints(angles)

    def _on_gesture(self, preset_key: str) -> None:
        self.setCursor(Qt.CursorShape.WaitCursor)
        self._info_panel.set_status(f"执行 {preset_key}...", ok=True)

        def do_it() -> str:
            if self._o6_service is None:
                return "O6 未连接，无法执行动作"
            try:
                ok = self._o6_service.execute_preset(preset_key)
                if ok:
                    return f"{preset_key} 执行完成"
                return f"{preset_key} 发送失败"
            except Exception as e:
                return f"{preset_key} 错误：{e}"

        self._action_task = _ActionTask(do_it)
        self._action_task.finished.connect(self._on_action_done)
        self._action_task.start()

    def _on_action_done(self, result: str) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._gesture_grid.set_loading(False)
        ok = "失败" not in result and "错误" not in result
        self._info_panel.set_status(result, ok=ok)
        if ok:
            self._refresh_joint_overview()
            self._action_refresh_remaining = ACTION_REFRESH_TICKS
            self._action_refresh_timer.start(ACTION_REFRESH_INTERVAL_MS)
        else:
            self._action_refresh_remaining = 0
            self._action_refresh_timer.stop()
        self._action_task = None

    def _on_action_refresh_tick(self) -> None:
        self._refresh_joint_overview()
        remaining = max(getattr(self, "_action_refresh_remaining", 0) - 1, 0)
        self._action_refresh_remaining = remaining
        if remaining == 0:
            self._action_refresh_timer.stop()

    def closeEvent(self, event) -> None:
        self._overview_timer.stop()
        action_task = getattr(self, "_action_task", None)
        if action_task is not None and action_task.isRunning() and not action_task.wait(2000):
            self._overview_timer.start()
            event.ignore()
            return
        camera_service = getattr(self, "_camera_service", None)
        camera_thread = getattr(self, "_camera_thread", None)
        shared_camera_running = camera_service is not None and getattr(camera_service, "is_running", False)
        camera_stopped = True
        if shared_camera_running or camera_thread is not None:
            camera_stopped = self._stop_shared_camera()
        elif getattr(self, "_camera_panel", None) is not None:
            camera_stopped = self._camera_panel._stop_camera()
        rps_stopped = True
        if getattr(self, "_rps_panel", None) is not None:
            rps_stopped = self._rps_panel._stop_game()
        if not camera_stopped or not rps_stopped:
            self._overview_timer.start()
            event.ignore()
            return
        if self._o6_service is not None:
            self._o6_service.disconnect()
        super().closeEvent(event)
