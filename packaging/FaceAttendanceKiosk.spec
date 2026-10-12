from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata

root = Path(SPECPATH).parent
datas = [
    (str(root / "frontend" / "templates"), "frontend/templates"),
    (str(root / "frontend" / "static"), "frontend/static"),
]
binaries = []
hiddenimports = []

for package in (
    "cv2",
    "fastapi",
    "insightface",
    "jinja2",
    "onnxruntime",
    "uvicorn",
    "webview",
):
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports

for package in ("insightface", "pywebview", "uvicorn"):
    datas += copy_metadata(package)

analysis = Analysis(
    [str(root / "backend" / "desktop.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "IPython", "jupyter"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="FaceAttendanceKiosk",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)
COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="FaceAttendanceKiosk",
)
