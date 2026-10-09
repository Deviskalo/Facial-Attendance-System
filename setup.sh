#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python_cmd=""
find_python() {
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
      "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
      python_cmd="$(command -v "$candidate")"
      return 0
    fi
  done
  return 1
}

install_python() {
  local os_name
  os_name="$(uname -s)"
  case "$os_name" in
    Darwin)
      if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew is required to install Python automatically."
        echo "Install Python 3.10 or newer from https://www.python.org/downloads/ and rerun setup.sh."
        return 1
      fi
      brew install python@3.12
      ;;
    Linux*)
      if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-venv python3-pip
      elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y python3 python3-pip
      elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --needed python python-pip
      else
        echo "No supported package manager (apt, dnf, or pacman) was found."
        echo "Install Python 3.10 or newer and its venv module, then rerun setup.sh."
        return 1
      fi
      ;;
    *)
      echo "Automatic Python installation is not supported on $os_name."
      echo "Install Python 3.10 or newer and rerun setup.sh."
      return 1
      ;;
  esac
}

if ! find_python; then
  echo "Python 3.10 or newer was not found."
  read -r -p "Install Python using this system's package manager? [y/N] " answer
  case "$answer" in
    y|Y|yes|YES|Yes)
      install_python
      if ! find_python; then
        echo "Python was installed or updated, but Python 3.10+ is still not on PATH."
        echo "Open a new terminal or install Python 3.10 or newer manually, then rerun setup.sh."
        exit 1
      fi
      ;;
    *)
      echo "Setup cancelled. Install Python 3.10 or newer and rerun setup.sh."
      exit 1
      ;;
  esac
fi

echo "Using $("$python_cmd" --version) at $python_cmd"

if [[ -x .venv/bin/python ]]; then
  if ! .venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    echo "The existing .venv uses Python older than 3.10."
    echo "Rename or remove .venv manually, then rerun setup.sh."
    exit 1
  fi
else
  echo "Creating virtual environment..."
  if ! "$python_cmd" -m venv .venv; then
    echo "Could not create .venv. Install the Python venv package for this interpreter."
    exit 1
  fi
fi

echo "Installing Python packages..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check

mkdir -p data/faces models

echo "Downloading or verifying InsightFace buffalo_l models..."
.venv/bin/python -c "from backend.face_engine import ensure_models; ensure_models(); print('Models ready.')"

echo
echo "Setup complete. Run ./run.sh to start the kiosk."
