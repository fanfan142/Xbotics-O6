from dataclasses import dataclass, field


@dataclass
class O6Config:
    side: str = "right"
    interface_name: str = "PCAN_USBBUS1"
    interface_type: str = "pcan"
    default_speed: int = 80
    default_acceleration: int = 60
    timeout_ms: int = 600
    force_timeout_ms: int = 1200


@dataclass
class UIConfig:
    theme: str = "dark"
    window_title: str = "Xbotics O6 控制台"
    window_width: int = 1440
    window_height: int = 920


@dataclass
class AppConfig:
    o6: O6Config = field(default_factory=O6Config)
    ui: UIConfig = field(default_factory=UIConfig)
