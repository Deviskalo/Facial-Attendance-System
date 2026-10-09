@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo Virtual environment not found. Running setup first...
  call setup.bat
  if errorlevel 1 exit /b 1
)

.venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
  echo The existing .venv does not use Python 3.10 or newer.
  echo Rename or remove .venv manually, then run setup.bat.
  exit /b 1
)

.venv\Scripts\python.exe -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
  echo The server dependencies are missing. Running setup first...
  call setup.bat
  if errorlevel 1 exit /b 1
)

.venv\Scripts\python.exe -c "import fastapi, uvicorn, jinja2, multipart, cv2, numpy, insightface, onnxruntime, PIL, itsdangerous, openpyxl" >nul 2>&1
if errorlevel 1 (
  echo One or more application packages are missing. Running setup first...
  call setup.bat
  if errorlevel 1 exit /b 1
  .venv\Scripts\python.exe -c "import fastapi, uvicorn, jinja2, multipart, cv2, numpy, insightface, onnxruntime, PIL, itsdangerous, openpyxl" >nul 2>&1
  if errorlevel 1 (
    echo Application dependencies are still unavailable. Review the setup output above.
    exit /b 1
  )
)

.venv\Scripts\python.exe -c "from backend.face_engine import ensure_models; ensure_models()"
if errorlevel 1 (
  echo Face recognition models are unavailable. Check your internet connection and run setup.bat.
  exit /b 1
)

echo Starting Face Attendance Kiosk on port 8000...
.venv\Scripts\python.exe -c "from backend.config import print_access_urls; print_access_urls()"
if errorlevel 1 (
  echo Could not load the application configuration.
  exit /b 1
)
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
if errorlevel 1 (
  echo The server stopped with an error. Check whether port 8000 is already in use.
  exit /b 1
)
endlocal
