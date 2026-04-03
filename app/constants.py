import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

if getattr(sys, "frozen", False):
    APP_BASE_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DATA_DIR = APP_BASE_DIR / "_internal"
else:
    APP_BASE_DIR = PROJECT_ROOT
    BUNDLE_DATA_DIR = PROJECT_ROOT

RUNTIME_DIR = BUNDLE_DATA_DIR / "runtime"
ASSETS_DIR = BUNDLE_DATA_DIR / "assets"
RUNTIME_CONFIG_PATH = RUNTIME_DIR / "config.json"
MODEL_PATH = ASSETS_DIR / "hand_landmarker.task"

PROMPT_VERSION_SOURCE_DIR = PROJECT_ROOT / "prompt_version"
PROMPT_VERSION_DIST_DIR = APP_BASE_DIR / "prompt_version"

DEFAULT_WINDOW_TITLE = "Xbotics_O6控制台"
DEFAULT_WINDOW_WIDTH = 1440
DEFAULT_WINDOW_HEIGHT = 920
