from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

RUNTIME_DIR = PROJECT_ROOT / "runtime"
ASSETS_DIR = PROJECT_ROOT / "assets"
RUNTIME_CONFIG_PATH = RUNTIME_DIR / "config.json"
MODEL_PATH = ASSETS_DIR / "hand_landmarker.task"

DEFAULT_WINDOW_TITLE = "Xbotics O6 控制台"
DEFAULT_WINDOW_WIDTH = 1440
DEFAULT_WINDOW_HEIGHT = 920
