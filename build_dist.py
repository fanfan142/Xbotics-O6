from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_PATH = PROJECT_ROOT / "xbotics2.spec"
APP_NAME = "Xbotics_O6控制台"
APP_DIR = DIST_DIR / APP_NAME
INTERNAL_DIR = APP_DIR / "_internal"
PROMPT_DIR = APP_DIR / "prompt_version"
BUNDLED_PROMPT_DIR = INTERNAL_DIR / "prompt_version"
PROMPT_TEMPLATE = PROMPT_DIR / "PROMPT.md"
USER_GUIDE = APP_DIR / "README.txt"
ARCHIVE_BASE = DIST_DIR / APP_NAME


def clean() -> None:
    for path in (DIST_DIR, BUILD_DIR):
        if path.exists():
            shutil.rmtree(path)


def run_pyinstaller() -> None:
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC_PATH)],
        cwd=PROJECT_ROOT,
        check=True,
    )


def relocate_prompt_version() -> None:
    if PROMPT_DIR.exists():
        shutil.rmtree(PROMPT_DIR)
    shutil.copytree(BUNDLED_PROMPT_DIR, PROMPT_DIR)


def write_user_guide() -> None:
    src_readme = PROJECT_ROOT / "README.txt"
    if src_readme.exists():
        shutil.copy2(src_readme, USER_GUIDE)


def archive_dist() -> Path:
    archive_path = shutil.make_archive(str(ARCHIVE_BASE), "zip", root_dir=DIST_DIR, base_dir=APP_NAME)
    return Path(archive_path)


def main() -> None:
    clean()
    run_pyinstaller()
    relocate_prompt_version()
    write_user_guide()
    archive_path = archive_dist()
    print(f"Build ready: {APP_DIR}")
    print(f"Archive ready: {archive_path}")


if __name__ == "__main__":
    main()
