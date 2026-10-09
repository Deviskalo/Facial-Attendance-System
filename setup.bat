@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
where py >nul 2>&1
if not errorlevel 1 (
  for %%V in (3.14 3.13 3.12 3.11 3.10) do (
    py -%%V -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if not errorlevel 1 if not defined PYTHON_CMD set "PYTHON_CMD=py -%%V"
  )
)

if not defined PYTHON_CMD (
  for %%C in (python python3) do (
    where %%C >nul 2>&1
    if not errorlevel 1 (
      %%C -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
      if not errorlevel 1 if not defined PYTHON_CMD set "PYTHON_CMD=%%C"
    )
  )
)

if not defined PYTHON_CMD (
  echo Python 3.10 or newer was not found.
  where winget >nul 2>&1
  if errorlevel 1 (
    echo Install Python 3.12 from https://www.python.org/downloads/ and run setup.bat again.
    exit /b 1
  )
  choice /M "Install Python 3.12 for your Windows user using winget"
  if errorlevel 2 (
    echo Setup cancelled. Install Python 3.10 or newer and run setup.bat again.
    exit /b 1
  )
  winget install --id Python.Python.3.12 --exact --scope user --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo Python installation failed. Install Python 3.10 or newer and run setup.bat again.
    exit /b 1
  )
  set "PYTHON_CMD=py -3.12"
  %PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
  if errorlevel 1 (
    echo Python was installed, but this terminal cannot find it yet.
    echo Close this window, open a new one, and run setup.bat again.
    exit /b 1
  )
)

echo Using:
%PYTHON_CMD% --version
if errorlevel 1 (
  echo Could not run the selected Python interpreter.
  exit /b 1
)

if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
  if errorlevel 1 (
    echo The existing .venv uses Python older than 3.10.
    echo Rename or remove .venv manually, then run setup.bat again.
    exit /b 1
  )
) else (
  echo Creating virtual environment...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 (
    echo Could not create .venv. Verify that Python includes the venv module.
    exit /b 1
  )
)

echo Installing Python packages...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 (
  echo Could not upgrade pip. Check your internet connection and try again.
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Package installation failed. Check your internet connection and requirements.txt.
  exit /b 1
)
.venv\Scripts\python.exe -m pip check
if errorlevel 1 (
  echo Installed packages have dependency conflicts. Review the pip output above.
  exit /b 1
)

if not exist data\faces mkdir data\faces
if not exist models mkdir models

echo Downloading or verifying InsightFace buffalo_l models...
.venv\Scripts\python.exe -c "from backend.face_engine import ensure_models; ensure_models(); print('Models ready.')"
if errorlevel 1 (
  echo Model setup failed. Check your internet connection and try setup.bat again.
  exit /b 1
)

echo.
echo Setup complete. Run run.bat to start the kiosk.
exit /b 0
