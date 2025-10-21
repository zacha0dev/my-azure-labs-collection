# my-wiki/labs/my-azure-router/router/my_router_setup.py
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
APP_JSON = CONFIG_DIR / "app.json"
TEMPLATE_JSON = CONFIG_DIR / "template.app.json"
VENV_DIR = PROJECT_ROOT / ".venv"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
HEARTBEAT_FILE = PROJECT_ROOT / "router" / ".heartbeat"

def _python_in_venv() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    else:
        return VENV_DIR / "bin" / "python"

def _pip_in_venv() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "pip.exe"
    else:
        return VENV_DIR / "bin" / "pip"

def ensure_virtualenv() -> Path:
    """Create .venv if missing and return path to python executable inside it."""
    py = _python_in_venv()
    if not py.exists():
        print("[setup] Creating virtual environment at .venv ...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
    else:
        print("[setup] Virtual environment already present.")
    return py

def install_requirements(python_in_venv: Path) -> None:
    """Install requirements.txt if it exists; allow empty/no-op."""
    if REQUIREMENTS.exists():
        print(f"[setup] Installing dependencies from {REQUIREMENTS.name} ...")
        pip = _pip_in_venv()
        subprocess.check_call([str(pip), "install", "-r", str(REQUIREMENTS)])
    else:
        print("[setup] No requirements.txt found; skipping dependency install.")

def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def _reset_config_from_template() -> dict:
    print("[setup] Resetting configuration from template.app.json ...")
    template = _read_json(TEMPLATE_JSON)
    _write_json(APP_JSON, template)
    return template

def ensure_config() -> dict:
    """Ensure config directory, app.json exist and are valid per your rules."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not TEMPLATE_JSON.exists():
        raise FileNotFoundError(f"Missing template file: {TEMPLATE_JSON}")

    if not APP_JSON.exists():
        print("[setup] app.json not found; creating it from template ...")
        cfg = _reset_config_from_template()
    else:
        cfg = _read_json(APP_JSON)

    # Your stated logic:
    # - if configured == false: reset to template to ensure clean start
    # - elif first-time-setup == true: mark configured true & first-time-setup false
    # - else: leave as-is
    if not cfg.get("configured", False):
        cfg = _reset_config_from_template()
    elif cfg.get("first-time-setup", False):
        print("[setup] First-time setup detected; flipping flags and saving ...")
        cfg["configured"] = True
        cfg["first-time-setup"] = False
        _write_json(APP_JSON, cfg)

    print("[setup] Config ready.")
    return cfg

def setup_router_env() -> Tuple[Path, dict, Path]:
    """Top-level setup:
       - ensure venv
       - install requirements
       - ensure config
       Returns: (python_in_venv, config_dict, heartbeat_file_path)
    """
    python_in_venv = ensure_virtualenv()
    install_requirements(python_in_venv)
    cfg = ensure_config()
    HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    return python_in_venv, cfg, HEARTBEAT_FILE