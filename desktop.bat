@echo off
setlocal
cd /d "%~dp0"

set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"

if not exist .venv\Scripts\python.exe (
  echo Project Python environment not found. Running setup first...
  call setup.bat
  if errorlevel 1 exit /b 1
)

.venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
  echo Project Python environment cannot start or is older than Python 3.10.
  echo Running setup so you can choose whether to recreate it...
  call setup.bat
  if errorlevel 1 exit /b 1
)

.venv\Scripts\python.exe -c "import fastapi, uvicorn, jinja2, multipart, cv2, numpy, insightface, onnxruntime, PIL, itsdangerous, openpyxl, webview" >nul 2>&1
if errorlevel 1 (
  echo Installing the optional desktop window dependency...
  .venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
  if errorlevel 1 (
    echo Could not install desktop dependencies. Review the pip output above.
    exit /b 1
  )
)

echo Starting Face Attendance Kiosk desktop app...
.venv\Scripts\python.exe -m backend.desktop
if errorlevel 1 (
  echo The desktop app stopped with an error. Review the output above.
  echo If startup reported OpenBLAS memory allocation errors, close other applications or restart Windows and retry.
  echo A low-memory system may still be unable to load the face-recognition model.
  exit /b 1
)
endlocal
