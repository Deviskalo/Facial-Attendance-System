@echo off
setlocal
cd /d "%~dp0"

set "OPENBLAS_NUM_THREADS=1"
set "OMP_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"

if not exist ".venv" goto FIND_PYTHON
if not exist ".venv\Scripts\python.exe" goto BROKEN_VENV

echo Checking the existing virtual environment...
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 goto BROKEN_VENV
goto VALID_VENV

:VALID_VENV
echo A working Python 3.10+ environment already exists.
set "SETUP_CHOICE="
set /p "SETUP_CHOICE=Keep and update this environment, recreate it, or cancel? [K/r/c] "
if not defined SETUP_CHOICE set "SETUP_CHOICE=K"
if /I "%SETUP_CHOICE%"=="K" goto INSTALL_PACKAGES
if /I "%SETUP_CHOICE%"=="R" goto REMOVE_VENV
if /I "%SETUP_CHOICE%"=="C" goto CANCEL_SETUP
echo Please enter K, R, or C.
goto VALID_VENV

:BROKEN_VENV
echo The existing .venv is missing, cannot start, or uses Python older than 3.10.
echo The environment must be recreated before setup can continue.
set "SETUP_CHOICE="
set /p "SETUP_CHOICE=Recreate .venv, or cancel? [r/C] "
if /I "%SETUP_CHOICE%"=="R" goto REMOVE_VENV
if not defined SETUP_CHOICE goto CANCEL_SETUP
if /I "%SETUP_CHOICE%"=="C" goto CANCEL_SETUP
echo Please enter R or C.
goto BROKEN_VENV

:REMOVE_VENV
powershell -NoProfile -NonInteractive -Command "try { $item = Get-Item -LiteralPath '.venv' -Force -ErrorAction Stop; if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { exit 0 }; exit 1 } catch { exit 2 }" >nul 2>&1
if errorlevel 2 (
  echo Could not safely determine whether .venv is a symlink or junction.
  echo No files were removed. Inspect .venv manually, then retry setup.bat.
  exit /b 1
)
if not errorlevel 1 (
  echo .venv is a symlink or junction. It was not removed to avoid affecting its target.
  echo Remove or rename that link yourself, then run setup.bat again.
  exit /b 1
)
echo Removing the existing .venv as requested...
rmdir /s /q .venv
if exist ".venv" (
  echo Could not remove .venv. Close programs using it and check folder permissions, then retry.
  exit /b 1
)

:FIND_PYTHON
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

echo Creating virtual environment...
%PYTHON_CMD% -m venv .venv
if errorlevel 1 (
  echo Could not create .venv. Verify that Python includes the venv module.
  exit /b 1
)

:INSTALL_PACKAGES
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

:CANCEL_SETUP
echo Setup cancelled. No environment was changed.
exit /b 1
