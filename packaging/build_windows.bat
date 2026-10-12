@echo off
setlocal
cd /d "%~dp0\.."

set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"

if not exist .venv\Scripts\python.exe (
  echo Project Python environment not found. Run setup.bat first.
  exit /b 1
)

.venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
  echo The project Python environment cannot start or is older than Python 3.10.
  echo Run setup.bat and try again.
  exit /b 1
)

echo Installing desktop and Windows packaging dependencies...
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 (
  echo Could not install packaging dependencies.
  exit /b 1
)

if not exist release\windows mkdir release\windows
if not exist release\installer mkdir release\installer

if not exist packaging\FaceAttendanceKiosk.ico (
  echo The application icon was not found at packaging\FaceAttendanceKiosk.ico.
  exit /b 1
)

echo Building the Windows application. Face model weights are intentionally not bundled.
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath release\windows --workpath build\pyinstaller packaging\FaceAttendanceKiosk.spec
if errorlevel 1 (
  echo PyInstaller build failed. Review the output above.
  exit /b 1
)

if not exist release\windows\FaceAttendanceKiosk\_internal\objects\meanshape_68.pkl (
  echo The frozen app is missing InsightFace's required meanshape_68.pkl resource.
  echo Review packaging\FaceAttendanceKiosk.spec and rebuild.
  exit /b 1
)

where ISCC.exe >nul 2>&1
if errorlevel 1 (
  echo.
  echo Application build is ready in release\windows\FaceAttendanceKiosk.
  echo Inno Setup 6 is not installed or ISCC.exe is not on PATH.
  echo Install Inno Setup 6, then compile packaging\FaceAttendanceKiosk.iss to create the installer.
  exit /b 0
)

echo Compiling the Windows installer...
ISCC.exe packaging\FaceAttendanceKiosk.iss
if errorlevel 1 (
  echo Inno Setup failed to compile the installer.
  exit /b 1
)

echo.
echo Installer created under release\installer.
exit /b 0
