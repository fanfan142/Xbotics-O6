# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

project_root = Path(SPEC).resolve().parent
prompt_version_dir = project_root / "prompt_version"


datas = [
    (str(project_root / "assets"), "assets"),
    (str(project_root / "runtime"), "runtime"),
    (str(prompt_version_dir), "prompt_version"),
]

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "cv2",
    "mediapipe",
    "numpy",
    "can",
    "linkerbot",
    "serial",
]

excludes = ["PyQt5", "PyQt6", "PySide2"]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Xbotics_O6控制台',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Xbotics_O6控制台',
)
