from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from ctypes.util import find_library
from pathlib import Path
from typing import Any


def configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


configure_stdio()

SCRIPT_PATH = Path(sys.executable).resolve() if getattr(sys, "frozen", False) else Path(__file__).resolve()
BASE_DIR = SCRIPT_PATH.parents[1]
APP_DIR = BASE_DIR.parent
INTERNAL_DIR = APP_DIR / "_internal"
VENDOR_DIR = BASE_DIR / "vendor"
DEFAULT_CONFIG_PATH = BASE_DIR / "o6_openclaw_config.json"
MIN_VENDOR_PYTHON = (3, 12)
BOOTSTRAP_ENV_VAR = "O6_BRIDGE_BOOTSTRAPPED"
JOINTS = ["thumb_flex", "thumb_abd", "index", "middle", "ring", "pinky"]
FINGER_INDEX = {
    "thumb": 0,
    "thumb_flex": 0,
    "thumb_abd": 1,
    "index": 2,
    "middle": 3,
    "ring": 4,
    "pinky": 5,
    "little": 5,
}
HIGH_RISK_PRESETS = {"close_hand", "power_grip", "pinch_heavy", "hold", "fist"}
COLLISION_CHECK_PRESETS = {"close_hand", "pinch_thumb_index", "pinch_medium", "pinch_heavy", "power_grip", "hold"}
COLLISION_CHECK_JOINTS = ("thumb_flex", "index")

DEFAULT_CONFIG = {
    "side": "right",
    "interface_name": "PCAN_USBBUS1",
    "interface_type": "pcan",
    "default_speed": 80,
    "default_acceleration": 60,
    "timeout_ms": 600,
    "force_timeout_ms": 1200,
    "settle_sec": 1.2,
    "fast_timeout_ms": 200,
    "fast_settle_sec": 0.2,
    "collision_threshold_ma": 300,
}

PRESETS: dict[str, dict[str, Any]] = {
    "open_hand": {
        "angles": [100, 100, 100, 100, 100, 100],
        "description": "张开手掌，默认最安全姿态。",
        "keywords": ["张开", "打开", "松开", "open", "release", "paper"],
    },
    "half_open": {
        "angles": [78, 78, 78, 78, 78, 78],
        "description": "半张开，适合过渡。",
        "keywords": ["半开", "放松", "half open", "relax"],
    },
    "close_hand": {
        "angles": [12, 42, 12, 12, 12, 12],
        "description": "基础闭合姿态。",
        "keywords": ["合拢", "握拳", "close", "grab"],
    },
    "thumbs_up": {
        "angles": [100, 80, 12, 12, 12, 12],
        "description": "点赞。",
        "keywords": ["点赞", "thumbs up", "like", "good"],
    },
    "victory": {
        "angles": [35, 65, 100, 100, 15, 15],
        "description": "剪刀手 / V。",
        "keywords": ["剪刀手", "v", "victory", "yeah", "scissors"],
    },
    "pinch_thumb_index": {
        "angles": [22, 38, 20, 100, 100, 100],
        "description": "拇指食指捏合。",
        "keywords": ["捏", "pinch", "拇指食指", "轻捏"],
    },
    "point_index": {
        "angles": [40, 70, 100, 15, 15, 15],
        "description": "食指指向。",
        "keywords": ["指向", "point", "食指"],
    },
    "number_three": {
        "angles": [36, 34, 100, 100, 100, 0],
        "description": "数字三。",
        "keywords": ["数字三", "three", "number 3"],
    },
    "ok_sign": {
        "angles": [45, 25, 25, 100, 100, 100],
        "description": "OK 手势。",
        "keywords": ["ok", "okay", "好的", "👌"],
    },
    "rock": {
        "angles": [100, 100, 15, 100, 15, 100],
        "description": "摇滚手势。",
        "keywords": ["rock", "摇滚", "🤘"],
    },
    "paper": {
        "angles": [100, 100, 100, 100, 100, 100],
        "description": "石头剪刀布里的布。",
        "keywords": ["paper", "布", "平掌"],
    },
    "scissors": {
        "angles": [35, 65, 100, 100, 15, 15],
        "description": "石头剪刀布里的剪刀。",
        "keywords": ["scissors", "剪刀", "✌️"],
    },
    "love_you": {
        "angles": [100, 100, 100, 15, 15, 100],
        "description": "I love you 手势。",
        "keywords": ["love you", "我爱你", "🤟"],
    },
    "pray": {
        "angles": [50, 30, 20, 20, 20, 20],
        "description": "祈祷 / 合掌近似姿态。",
        "keywords": ["pray", "祈祷", "合掌", "🙏"],
    },
    "call_me": {
        "angles": [100, 80, 15, 15, 100, 15],
        "description": "call me 手势。",
        "keywords": ["call me", "打电话", "🤙"],
    },
    "bad": {
        "angles": [12, 20, 100, 100, 100, 100],
        "description": "差评 / 向下手势。",
        "keywords": ["bad", "不好", "差", "👎"],
    },
    "pinch_light": {
        "angles": [25, 35, 25, 100, 100, 100],
        "description": "轻捏。",
        "keywords": ["轻捏", "light pinch"],
    },
    "pinch_medium": {
        "angles": [20, 30, 18, 100, 100, 100],
        "description": "中等力度捏合。",
        "keywords": ["中捏", "medium pinch"],
    },
    "pinch_heavy": {
        "angles": [15, 25, 12, 100, 100, 100],
        "description": "重捏，高风险。",
        "keywords": ["重捏", "heavy pinch", "大力捏"],
    },
    "precision_grip": {
        "angles": [30, 40, 35, 85, 90, 95],
        "description": "精密抓握。",
        "keywords": ["精密抓握", "precision grip"],
    },
    "power_grip": {
        "angles": [25, 45, 20, 25, 30, 35],
        "description": "强力抓握，高风险。",
        "keywords": ["power grip", "强力抓握", "大力抓"],
    },
    "fist": {
        "angles": [15, 40, 15, 15, 15, 15],
        "description": "拳头。",
        "keywords": ["拳头", "fist", "握拳"],
    },
    "wave": {
        "angles": [100, 100, 100, 100, 100, 100],
        "description": "挥手起始姿态。",
        "keywords": ["挥手", "wave", "hello"],
    },
    "count_one": {
        "angles": [40, 70, 100, 15, 15, 15],
        "description": "数字一。",
        "keywords": ["一", "one", "☝️"],
    },
    "count_two": {
        "angles": [35, 65, 100, 100, 15, 15],
        "description": "数字二。",
        "keywords": ["二", "two", "✌️"],
    },
    "count_five": {
        "angles": [100, 100, 100, 100, 100, 100],
        "description": "数字五。",
        "keywords": ["五", "five", "🖐️"],
    },
    "hold": {
        "angles": [50, 55, 50, 50, 50, 50],
        "description": "持物近似姿态，高风险。",
        "keywords": ["握住", "hold", "持握"],
    },
}

PRESET_ALIASES: dict[str, str] = {}
for preset_name, preset in PRESETS.items():
    PRESET_ALIASES[preset_name] = preset_name
    for keyword in preset["keywords"]:
        PRESET_ALIASES[str(keyword).strip().lower()] = preset_name


def iter_python_candidates() -> list[Path]:
    candidates: list[Path] = []
    override = os.environ.get("O6_BRIDGE_PYTHON")
    if override:
        candidates.append(Path(override).expanduser())

    relative_candidates = [
        Path(".venv") / "Scripts" / "python.exe",
        Path(".venv") / "bin" / "python",
        Path("1") / "linkerbot-python-sdk-main" / ".venv" / "Scripts" / "python.exe",
        Path("1") / "linkerbot-python-sdk-main" / ".venv" / "bin" / "python",
        Path("linkerbot-python-sdk-main") / ".venv" / "Scripts" / "python.exe",
        Path("linkerbot-python-sdk-main") / ".venv" / "bin" / "python",
    ]
    for root in [BASE_DIR, APP_DIR, *BASE_DIR.parents]:
        for relative in relative_candidates:
            candidates.append(root / relative)

    current_executable = Path(sys.executable).resolve()
    seen: set[str] = set()
    resolved: list[Path] = []
    for candidate in candidates:
        candidate = candidate.resolve()
        key = str(candidate).lower()
        if key in seen or candidate == current_executable or not candidate.exists():
            continue
        seen.add(key)
        resolved.append(candidate)
    return resolved


def detect_sdk_mode() -> str:
    if INTERNAL_DIR.exists() and (INTERNAL_DIR / "linkerbot").exists():
        return "packaged"
    return "vendor"


def maybe_reexec_with_supported_python(sdk_mode: str) -> None:
    if sdk_mode == "packaged":
        return
    if sys.version_info >= MIN_VENDOR_PYTHON:
        return

    already_bootstrapped = os.environ.get(BOOTSTRAP_ENV_VAR) == "1"
    for candidate in iter_python_candidates():
        env = os.environ.copy()
        env[BOOTSTRAP_ENV_VAR] = "1"
        result = subprocess.run([str(candidate), str(Path(__file__).resolve()), *sys.argv[1:]], env=env)
        if result.returncode == 0:
            raise SystemExit(0)

    version_text = ".".join(str(part) for part in MIN_VENDOR_PYTHON)
    detail = "已尝试自动切换解释器但未成功。" if already_bootstrapped else "未找到可用的兼容解释器。"
    raise RuntimeError(
        f"O6 bridge vendor 模式需要 Python >= {version_text}。"
        f" 当前解释器: {sys.executable} (Python {sys.version.split()[0]})。"
        f" {detail} 请安装兼容版本，或设置 O6_BRIDGE_PYTHON 指向可用解释器。"
    )


SDK_MODE = detect_sdk_mode()
maybe_reexec_with_supported_python(SDK_MODE)

SDK_IMPORT_BASE = INTERNAL_DIR if SDK_MODE == "packaged" else VENDOR_DIR
if str(SDK_IMPORT_BASE) not in sys.path:
    sys.path.insert(0, str(SDK_IMPORT_BASE))

IMPORT_ERROR: Exception | None = None
try:
    from linkerbot import O6
except Exception as exc:  # pragma: no cover - runtime environment dependent
    O6 = None  # type: ignore[assignment]
    IMPORT_ERROR = exc

try:
    import can
except Exception as exc:  # pragma: no cover - runtime environment dependent
    can = None  # type: ignore[assignment]
    if IMPORT_ERROR is None:
        IMPORT_ERROR = exc


def clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def parse_values(raw: str) -> list[float]:
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    if len(parts) == 1:
        return [clamp(float(parts[0]))] * 6
    if len(parts) != 6:
        raise ValueError("需要 1 个或 6 个逗号分隔数值。")
    return [clamp(float(item)) for item in parts]


def to_list(obj: Any) -> list[float]:
    if hasattr(obj, "to_list") and callable(obj.to_list):
        return [float(x) for x in obj.to_list()]
    if isinstance(obj, (list, tuple)):
        return [float(x) for x in obj]
    raise TypeError(f"无法转换为列表: {type(obj).__name__}")


def round_list(values: list[float]) -> list[float]:
    return [round(float(x), 1) for x in values]


def ensure_sdk_available() -> None:
    if IMPORT_ERROR is not None or O6 is None:
        source_hint = "_internal/linkerbot" if SDK_MODE == "packaged" else "vendor/linkerbot"
        raise RuntimeError(
            f"linkerbot SDK 导入失败，请确保 {source_hint} 存在且可用。"
            f" 原始错误: {IMPORT_ERROR}"
        )


def pcan_diagnostics(config: dict[str, Any] | None = None) -> dict[str, Any]:
    interface_name = str((config or {}).get("interface_name", "PCAN_USBBUS1"))
    interface_type = str((config or {}).get("interface_type", "pcan"))
    payload: dict[str, Any] = {
        "can_importable": can is not None,
        "pcanbasic_path": find_library("PCANBasic"),
        "interface_name": interface_name,
        "interface_type": interface_type,
        "available_configs": [],
        "available_channels": [],
        "available_configs_supported": False,
        "raw_bus_open": None,
    }
    if can is None or interface_type != "pcan":
        return payload

    payload["can_version"] = getattr(can, "__version__", "unknown")
    try:
        from can.interfaces.pcan.pcan import PcanBus

        detector = getattr(PcanBus, "_detect_available_configs", None)
        if callable(detector):
            payload["available_configs_supported"] = True
            configs = detector()
            payload["available_configs"] = configs
            channels: list[str] = []
            for item in configs:
                channel = item.get("channel")
                if channel is not None:
                    channels.append(str(channel))
            payload["available_channels"] = channels
        else:
            payload["available_configs_error"] = "python-can 当前版本未暴露 PCAN 通道枚举能力"
    except Exception as exc:
        payload["available_configs_error"] = f"{type(exc).__name__}: {exc}"

    try:
        bus = can.Bus(interface=interface_type, channel=interface_name, bitrate=1_000_000)
        try:
            payload["raw_bus_open"] = True
        finally:
            try:
                bus.shutdown()
            except Exception as exc:
                payload["raw_bus_shutdown_error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        payload["raw_bus_open"] = False
        payload["raw_bus_error"] = f"{type(exc).__name__}: {exc}"
    return payload


def call_with_optional_timeout(method, timeout_ms: float):
    try:
        return method(timeout_ms=timeout_ms)
    except TypeError:
        return method()


def extract_fault_names(code: Any) -> list[str]:
    if code is None:
        return []
    if hasattr(code, "get_fault_names") and callable(code.get_fault_names):
        return list(code.get_fault_names())
    if isinstance(code, int):
        return [] if code == 0 else [str(code)]
    if hasattr(code, "value") and isinstance(code.value, int):
        return [] if code.value == 0 else [str(code.value)]
    return [str(code)]


def extract_device_info(info: Any) -> dict[str, Any]:
    return {
        "serial_number": getattr(info, "serial_number", ""),
        "pcb_version": str(getattr(info, "pcb_version", "")),
        "firmware_version": str(getattr(info, "firmware_version", "")),
        "mechanical_version": str(getattr(info, "mechanical_version", "")),
        "timestamp": getattr(info, "timestamp", None),
    }


def load_config(path: Path) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if path.exists():
        config.update(json.loads(path.read_text(encoding="utf-8")))

    env_overrides = {
        "side": os.environ.get("O6_SIDE"),
        "interface_name": os.environ.get("CAN_INTERFACE"),
        "interface_type": os.environ.get("CAN_INTERFACE_TYPE"),
    }
    for key, value in env_overrides.items():
        if value:
            config[key] = value
    return config


def make_config(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(Path(args.config))
    if args.side:
        config["side"] = args.side
    if args.interface_name:
        config["interface_name"] = args.interface_name
    if args.interface_type:
        config["interface_type"] = args.interface_type

    fast_mode = bool(getattr(args, "fast", False) or os.environ.get("O6_FAST_MODE", "").lower() in {"1", "true", "yes", "on"})
    config["fast_mode"] = fast_mode
    config["skip_state"] = bool(getattr(args, "no_state", False))
    config["timeout_ms"] = float(args.timeout_ms if args.timeout_ms is not None else (config["fast_timeout_ms"] if fast_mode else config["timeout_ms"]))
    config["settle_sec"] = float(args.settle_sec if args.settle_sec is not None else (config["fast_settle_sec"] if fast_mode else config["settle_sec"]))
    return config


def open_hand(config: dict[str, Any]):
    ensure_sdk_available()
    return O6(
        side=config["side"],
        interface_name=config["interface_name"],
        interface_type=config["interface_type"],
    )


def guarded(label: str, fn, out: dict[str, Any]) -> None:
    try:
        out[label] = fn()
    except Exception as exc:  # pragma: no cover - hardware dependent
        out[label] = {"error": f"{type(exc).__name__}: {exc}"}


def read_faults(hand: Any, timeout_ms: float) -> dict[str, Any]:
    fault_reader = getattr(hand.fault, "get_faults_blocking", None) or getattr(hand.fault, "get_blocking", None)
    data = call_with_optional_timeout(fault_reader, timeout_ms)
    faults = data.faults
    detail: dict[str, list[str]] = {}
    has_any_fault = False
    for joint in JOINTS:
        code = getattr(faults, joint, None)
        if code is None:
            continue
        names = extract_fault_names(code)
        detail[joint] = names
        if names:
            has_any_fault = True
    if hasattr(faults, "has_any_fault") and callable(faults.has_any_fault):
        has_any_fault = bool(faults.has_any_fault())
    return {"has_any_fault": has_any_fault, "detail": detail}


def summarize_force_matrix(values: Any) -> dict[str, Any]:
    rows = values.tolist() if hasattr(values, "tolist") else values
    flat = [int(cell) for row in rows for cell in row]
    return {
        "rows": len(rows),
        "cols": len(rows[0]) if rows else 0,
        "min": min(flat) if flat else 0,
        "max": max(flat) if flat else 0,
        "avg": round(sum(flat) / len(flat), 2) if flat else 0.0,
    }


def read_force(hand: Any, timeout_ms: float) -> dict[str, Any]:
    force_reader = getattr(hand.force_sensor, "get_data_blocking", None) or getattr(hand.force_sensor, "get_blocking", None)
    data = call_with_optional_timeout(force_reader, timeout_ms)
    result: dict[str, Any] = {}
    for name in ["thumb", "index", "middle", "ring", "pinky", "palm"]:
        finger = getattr(data, name, None)
        if finger is None:
            continue
        values = getattr(finger, "values", None)
        if values is None:
            continue
        result[name] = summarize_force_matrix(values)
    return result


def collect_state(hand: Any, timeout_ms: float, force_timeout_ms: float | None = None) -> dict[str, Any]:
    state: dict[str, Any] = {}

    angle_reader = getattr(hand.angle, "get_angles_blocking", None) or getattr(hand.angle, "get_blocking", None)
    speed_reader = getattr(hand.speed, "get_speeds_blocking", None) or getattr(hand.speed, "get_blocking", None)
    acceleration_reader = getattr(hand.acceleration, "get_accelerations_blocking", None) or getattr(hand.acceleration, "get_blocking", None)
    torque_reader = getattr(hand.torque, "get_torques_blocking", None) or getattr(hand.torque, "get_blocking", None)
    temperature_reader = getattr(hand.temperature, "get_temperatures_blocking", None) or getattr(hand.temperature, "get_blocking", None)

    guarded("angles", lambda: round_list(to_list(call_with_optional_timeout(angle_reader, timeout_ms).angles)), state)
    guarded("speeds", lambda: round_list(to_list(call_with_optional_timeout(speed_reader, timeout_ms).speeds)), state)
    guarded("accelerations", lambda: round_list(to_list(call_with_optional_timeout(acceleration_reader, timeout_ms).accelerations)), state)
    guarded("torques", lambda: round_list(to_list(call_with_optional_timeout(torque_reader, timeout_ms).torques)), state)
    guarded("temperatures", lambda: round_list(to_list(call_with_optional_timeout(temperature_reader, timeout_ms).temperatures)), state)
    guarded("faults", lambda: read_faults(hand, timeout_ms), state)
    if force_timeout_ms:
        guarded("force_sensor", lambda: read_force(hand, force_timeout_ms), state)
    return state


def pretty_print(obj: Any, indent: int = 0) -> None:
    prefix = " " * indent
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                print(f"{prefix}- {key}:")
                pretty_print(value, indent + 2)
            else:
                print(f"{prefix}- {key}: {value}")
        return
    if isinstance(obj, list):
        print(prefix + json.dumps(obj, ensure_ascii=False))
        return
    print(prefix + str(obj))


def emit_result(title: str, payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)
    pretty_print(payload)


def current_angles_or_default(hand: Any, timeout_ms: float) -> list[float]:
    angle_reader = getattr(hand.angle, "get_angles_blocking", None) or getattr(hand.angle, "get_blocking", None)
    try:
        return to_list(call_with_optional_timeout(angle_reader, timeout_ms).angles)
    except Exception:  # pragma: no cover - hardware dependent
        return [100.0] * 6


def resolve_preset(name_or_keyword: str) -> tuple[str, dict[str, Any]]:
    key = name_or_keyword.strip().lower()
    preset_name = PRESET_ALIASES.get(key)
    if preset_name is None:
        raise KeyError(f"未找到预设或关键词: {name_or_keyword}")
    return preset_name, PRESETS[preset_name]


def motion_values(raw: str | None, default_value: float) -> list[float]:
    return [clamp(default_value)] * 6 if not raw else parse_values(raw)


def state_is_healthy(state: dict[str, Any]) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    faults = state.get("faults")
    if isinstance(faults, dict) and faults.get("has_any_fault"):
        warnings.append("检测到 fault")
    temperatures = state.get("temperatures")
    if isinstance(temperatures, list) and any(float(value) >= 70 for value in temperatures):
        warnings.append("检测到温度偏高(>=70°C)")
    return not warnings, warnings


def detect_collision(hand: Any, timeout_ms: float, threshold_ma: float) -> dict[str, Any]:
    result: dict[str, Any] = {
        "threshold_ma": threshold_ma,
        "baseline_read_success": False,
        "collision_detected": None,
        "all_torques": {},
        "exceeded_joints": [],
    }
    torque_reader = getattr(hand.torque, "get_torques_blocking", None) or getattr(hand.torque, "get_blocking", None)
    try:
        torques = to_list(call_with_optional_timeout(torque_reader, timeout_ms).torques)
        result["baseline_read_success"] = True
        for index, joint in enumerate(JOINTS):
            if index < len(torques):
                result["all_torques"][joint] = round(torques[index], 1)
        for joint in COLLISION_CHECK_JOINTS:
            index = FINGER_INDEX[joint]
            if index >= len(torques):
                continue
            torque_value = abs(torques[index])
            if torque_value > threshold_ma:
                result["exceeded_joints"].append({
                    "joint": joint,
                    "torque": round(torque_value, 1),
                    "threshold_ma": threshold_ma,
                })
        result["collision_detected"] = bool(result["exceeded_joints"])
        return result
    except Exception as exc:  # pragma: no cover - hardware dependent
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result


def run_motion(
    hand: Any,
    config: dict[str, Any],
    label: str,
    angles: list[float],
    speed: list[float],
    acceleration: list[float],
    read_state: bool,
    before_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": True,
        "action": label,
        "fast_mode": bool(config.get("fast_mode", False)),
        "target_angles": round_list(angles),
        "speed": round_list(speed),
        "acceleration": round_list(acceleration),
    }
    if read_state and before_state is not None:
        payload["before"] = before_state
    elif read_state:
        payload["before"] = collect_state(hand, timeout_ms=float(config["timeout_ms"]))
    hand.acceleration.set_accelerations(acceleration)
    hand.speed.set_speeds(speed)
    hand.angle.set_angles(angles)
    time.sleep(float(config["settle_sec"]))
    if read_state:
        payload["after"] = collect_state(hand, timeout_ms=float(config["timeout_ms"]))
    return payload


def cmd_doctor(args: argparse.Namespace, config: dict[str, Any]) -> None:
    payload = {
        "ok": True,
        "cwd": str(Path.cwd()),
        "base_dir": str(BASE_DIR),
        "config_path": str(Path(args.config).resolve()),
        "config_exists": Path(args.config).exists(),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": sys.platform,
        "sdk_mode": SDK_MODE,
        "sdk_import_base": str(SDK_IMPORT_BASE),
        "sdk_importable": IMPORT_ERROR is None,
        "sdk_import_error": None if IMPORT_ERROR is None else f"{type(IMPORT_ERROR).__name__}: {IMPORT_ERROR}",
        "config": config,
        "pcan": pcan_diagnostics(config),
    }
    if args.probe:
        with open_hand(config) as hand:
            try:
                info = call_with_optional_timeout(hand.version.get_device_info, float(config["timeout_ms"]))
                payload["device_info"] = extract_device_info(info)
            except Exception as exc:
                payload["version_probe_error"] = f"{type(exc).__name__}: {exc}"
            payload["state_probe"] = collect_state(
                hand,
                timeout_ms=float(config["timeout_ms"]),
                force_timeout_ms=float(config.get("force_timeout_ms", 0) or 0),
            )
    emit_result("O6 Bridge Doctor", payload, args.json)


def cmd_version(args: argparse.Namespace, config: dict[str, Any]) -> None:
    with open_hand(config) as hand:
        info = call_with_optional_timeout(hand.version.get_device_info, float(config["timeout_ms"]))
    emit_result("O6 设备版本信息", {"ok": True, **extract_device_info(info)}, args.json)


def cmd_state(args: argparse.Namespace, config: dict[str, Any]) -> None:
    with open_hand(config) as hand:
        payload = collect_state(
            hand,
            timeout_ms=float(config["timeout_ms"]),
            force_timeout_ms=float(config.get("force_timeout_ms", 0) or 0),
        )
    emit_result("O6 当前状态", {"ok": True, "state": payload}, args.json)


def cmd_force(args: argparse.Namespace, config: dict[str, Any]) -> None:
    with open_hand(config) as hand:
        payload = read_force(hand, timeout_ms=float(config.get("force_timeout_ms", 1200)))
    emit_result("O6 力传感器快照", {"ok": True, "force": payload}, args.json)


def cmd_list_presets(args: argparse.Namespace) -> None:
    payload = {
        "ok": True,
        "presets": {
            name: {
                "angles": preset["angles"],
                "description": preset["description"],
                "keywords": preset["keywords"],
                "high_risk": name in HIGH_RISK_PRESETS,
            }
            for name, preset in PRESETS.items()
        },
    }
    emit_result("O6 可用预设动作", payload, args.json)


def cmd_keyword_help(args: argparse.Namespace) -> None:
    emit_result("O6 关键词映射", {"ok": True, "keywords": dict(sorted(PRESET_ALIASES.items()))}, args.json)


def cmd_pose(args: argparse.Namespace, config: dict[str, Any]) -> None:
    if args.angles:
        label = "custom_pose"
        angles = parse_values(args.angles)
    else:
        query = args.preset or args.keyword
        if not query:
            raise ValueError("pose 需要 --preset / --keyword / --angles 三者之一。")
        label, preset = resolve_preset(query)
        angles = [float(x) for x in preset["angles"]]

    speed = motion_values(args.speed, float(config["default_speed"]))
    acceleration = motion_values(args.acceleration, float(config["default_acceleration"]))
    read_state = not bool(config.get("skip_state", False))

    with open_hand(config) as hand:
        precheck = collect_state(hand, timeout_ms=float(config["timeout_ms"])) if read_state else {}
        _, warnings = state_is_healthy(precheck) if precheck else (True, [])
        high_risk = label in HIGH_RISK_PRESETS
        if (warnings or high_risk) and not args.allow_risky:
            parts = list(warnings)
            if high_risk:
                parts.append(f"{label} 属于高风险动作")
            raise RuntimeError("；".join(parts) + "。如确认继续，请追加 --allow-risky。")

        collision_result = None
        needs_collision_check = bool(args.collision_check or args.collision_stop or label in COLLISION_CHECK_PRESETS)
        if needs_collision_check:
            collision_result = detect_collision(
                hand,
                timeout_ms=float(config["timeout_ms"]),
                threshold_ma=float(args.collision_threshold or config["collision_threshold_ma"]),
            )
            if args.collision_stop and collision_result.get("collision_detected") is True:
                raise RuntimeError(json.dumps({
                    "action": label,
                    "reason": "collision_detected",
                    "collision": collision_result,
                }, ensure_ascii=False))

        payload = run_motion(
            hand,
            config,
            label=label,
            angles=angles,
            speed=speed,
            acceleration=acceleration,
            read_state=read_state,
            before_state=precheck if precheck else None,
        )
        if collision_result is not None:
            payload["collision"] = collision_result
        payload["high_risk"] = high_risk
        emit_result("O6 动作执行完成", payload, args.json)


def cmd_finger(args: argparse.Namespace, config: dict[str, Any]) -> None:
    finger_key = args.finger.strip().lower()
    if finger_key not in FINGER_INDEX:
        raise KeyError(f"不支持的手指名称: {args.finger}")
    speed = motion_values(args.speed, float(config["default_speed"]))
    acceleration = motion_values(args.acceleration, float(config["default_acceleration"]))
    read_state = not bool(config.get("skip_state", False))

    with open_hand(config) as hand:
        precheck = collect_state(hand, timeout_ms=float(config["timeout_ms"])) if read_state else {}
        _, warnings = state_is_healthy(precheck) if precheck else (True, [])
        if warnings and not args.allow_risky:
            raise RuntimeError("；".join(warnings) + "。如确认继续，请追加 --allow-risky。")

        angles = current_angles_or_default(hand, timeout_ms=float(config["timeout_ms"]))
        index = FINGER_INDEX[finger_key]
        if args.target is not None:
            angles[index] = clamp(float(args.target))
        elif args.delta is not None:
            angles[index] = clamp(angles[index] + float(args.delta))
        else:
            raise ValueError("finger 至少需要 --target 或 --delta。")
        payload = run_motion(
            hand,
            config,
            label=f"finger:{finger_key}",
            angles=angles,
            speed=speed,
            acceleration=acceleration,
            read_state=read_state,
            before_state=precheck if precheck else None,
        )
    emit_result("O6 单指动作执行完成", payload, args.json)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="O6 OpenClaw local bridge")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="配置文件路径")
    parser.add_argument("--side", choices=["left", "right"], help="覆盖配置中的 side")
    parser.add_argument("--interface-name", help="覆盖配置中的 interface_name")
    parser.add_argument("--interface-type", help="覆盖配置中的 interface_type")
    parser.add_argument("--timeout-ms", type=float, help="覆盖 timeout_ms")
    parser.add_argument("--settle-sec", type=float, help="覆盖 settle_sec")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("-f", "--fast", action="store_true", help="启用快速模式")
    parser.add_argument("--no-state", action="store_true", help="跳过动作前后状态读取")

    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="检查环境与配置")
    doctor.add_argument("--probe", action="store_true", help="额外做一次真实设备探测")

    subparsers.add_parser("version", help="读取版本信息")
    subparsers.add_parser("state", help="读取当前状态")
    subparsers.add_parser("read-state", help="state 的兼容别名")
    subparsers.add_parser("force", help="读取力传感器快照")
    subparsers.add_parser("list-presets", help="列出全部预设动作")
    subparsers.add_parser("keyword-help", help="列出关键词映射")

    pose = subparsers.add_parser("pose", help="执行预设动作或自定义姿态")
    pose.add_argument("--preset", help="预设动作名")
    pose.add_argument("--keyword", help="关键词，会映射到预设动作")
    pose.add_argument("--angles", help="1 个或 6 个角度，逗号分隔")
    pose.add_argument("--speed", help="1 个或 6 个速度，逗号分隔")
    pose.add_argument("--acceleration", help="1 个或 6 个加速度，逗号分隔")
    pose.add_argument("--allow-risky", action="store_true", help="允许在 fault/高温等风险场景继续动作")
    pose.add_argument("--collision-check", action="store_true", help="执行前读取扭矩做碰撞检查")
    pose.add_argument("--collision-stop", action="store_true", help="检测到碰撞时取消动作")
    pose.add_argument("--collision-threshold", type=float, help="碰撞阈值，单位 mA")

    finger = subparsers.add_parser("finger", help="控制单指")
    finger.add_argument("--finger", required=True, help="thumb/index/middle/ring/pinky/thumb_abd")
    finger.add_argument("--target", type=float, help="目标值 0-100")
    finger.add_argument("--delta", type=float, help="相对变化量")
    finger.add_argument("--speed", help="1 个或 6 个速度，逗号分隔")
    finger.add_argument("--acceleration", help="1 个或 6 个加速度，逗号分隔")
    finger.add_argument("--allow-risky", action="store_true", help="允许在 fault/高温等风险场景继续动作")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = make_config(args)

    handlers = {
        "doctor": lambda: cmd_doctor(args, config),
        "version": lambda: cmd_version(args, config),
        "state": lambda: cmd_state(args, config),
        "read-state": lambda: cmd_state(args, config),
        "force": lambda: cmd_force(args, config),
        "list-presets": lambda: cmd_list_presets(args),
        "keyword-help": lambda: cmd_keyword_help(args),
        "pose": lambda: cmd_pose(args, config),
        "finger": lambda: cmd_finger(args, config),
    }

    try:
        handlers[args.command]()
        return 0
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        error_text = f"{type(exc).__name__}: {exc}"
        try:
            structured = json.loads(str(exc)) if str(exc).startswith("{") else None
        except json.JSONDecodeError:
            structured = None
        payload = {
            "ok": False,
            "error": error_text,
            "hint": "请检查 Python 版本、requirements.txt、配置文件、CAN 接口、供电、接线与左右手参数。",
        }
        if "PcanCanInitializationError" in error_text:
            payload["pcan"] = pcan_diagnostics(config)
            if payload["pcan"].get("available_channels") == []:
                payload["hint"] = "PCAN 驱动已加载，但当前系统未枚举到任何可用 PCAN 通道。请先确认 PCAN-USB 已插好、驱动/PCAN-View 正常、未被其他进程独占，再重试。"
        if isinstance(structured, dict):
            payload["details"] = structured
        emit_result("O6 Bridge 执行失败", payload, args.json)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
