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

remove_environment() {
  if [[ -L .venv ]]; then
    echo "Removing the .venv symbolic link only; its target will not be deleted."
    rm -- .venv
  elif [[ -e .venv ]]; then
    echo "Removing the existing .venv as requested..."
    rm -rf -- .venv
  fi
  if [[ -e .venv || -L .venv ]]; then
    echo "Could not remove .venv. Close programs using it and check folder permissions, then retry."
    return 1
  fi
}

if [[ -e .venv || -L .venv ]]; then
  env_usable=false
  if [[ -x .venv/bin/python ]]; then
    .venv/bin/python --version || true
    if .venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
      env_usable=true
    fi
  fi

  if [[ "$env_usable" == true ]]; then
    echo "A working Python 3.10+ environment already exists."
    while true; do
      read -r -p "Keep and update this environment, recreate it, or cancel? [K/r/c] " choice || choice=""
      choice="${choice:-K}"
      case "$choice" in
        [Kk]) break ;;
        [Rr]) remove_environment; env_usable=false; break ;;
        [Cc]) echo "Setup cancelled. No environment was changed."; exit 1 ;;
        *) echo "Please enter K, R, or C." ;;
      esac
    done
  else
    echo "The existing .venv is missing, cannot start, or uses Python older than 3.10."
    echo "The environment must be recreated before setup can continue."
    while true; do
      read -r -p "Recreate .venv, or cancel? [r/C] " choice || choice=""
      case "$choice" in
        [Rr]) remove_environment; break ;;
        ""|[Cc]) echo "Setup cancelled. No environment was changed."; exit 1 ;;
        *) echo "Please enter R or C." ;;
      esac
    done
  fi
fi

if [[ ! -e .venv && ! -L .venv ]]; then
  if ! find_python; then
    echo "Python 3.10 or newer was not found."
    if [[ -t 0 ]]; then
      read -r -p "Install Python using this system's package manager? [y/N] " answer || answer=""
    else
      answer=""
    fi
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
  echo "Creating virtual environment..."
  if ! "$python_cmd" -m venv .venv; then
    echo "Could not create .venv. Install the Python venv package for this interpreter."
    exit 1
  fi
fi

if [[ ! -x .venv/bin/python ]] ||
  ! .venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  echo "The .venv Python could not be started after setup."
  echo "Check the selected Python installation and rerun setup.sh."
  exit 1
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
