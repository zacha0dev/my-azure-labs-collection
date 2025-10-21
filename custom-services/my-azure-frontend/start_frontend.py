# my-azure-frontend/start_frontend.py
from __future__ import annotations
import os
import signal
import subprocess
import sys
import time
import json
from pathlib import Path

from config.my_frontend_setup import setup_frontend_env, PROJECT_ROOT, APP_JSON

_frontend_proc: subprocess.Popen | None = None
_python_in_venv: Path | None = None
_heartbeat_file: Path | None = None

def _creationflags_for_windows() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    return 0

def start_frontend() -> None:
    global _frontend_proc
    if _frontend_proc and _frontend_proc.poll() is None:
        print("[ctl] Frontend already running.")
        return

    assert _python_in_venv is not None and _heartbeat_file is not None

    frontend_script = PROJECT_ROOT / "app" / "my_frontend_process.py"
    if not frontend_script.exists():
        raise FileNotFoundError(f"Missing frontend script: {frontend_script}")

    print("[ctl] Starting frontend process ...")
    if os.name == "nt":
        _frontend_proc = subprocess.Popen(
            [str(_python_in_venv), str(frontend_script), str(_heartbeat_file)],
            creationflags=_creationflags_for_windows()
        )
    else:
        _frontend_proc = subprocess.Popen(
            [str(_python_in_venv), str(frontend_script), str(_heartbeat_file)]
        )
    print(f"[ctl] Frontend PID: {_frontend_proc.pid}")

def stop_frontend_soft(timeout: float = 5.0) -> None:
    global _frontend_proc
    if not _frontend_proc:
        print("[ctl] Frontend not running.")
        return

    if os.name == "nt":
        try:
            _frontend_proc.send_signal(signal.CTRL_BREAK_EVENT)
            print("[ctl] Sent CTRL_BREAK_EVENT (soft stop).")
        except Exception:
            _frontend_proc.terminate()
            print("[ctl] Sent terminate() as fallback.")
    else:
        _frontend_proc.terminate()
        print("[ctl] Sent SIGTERM (soft stop).")

    try:
        _frontend_proc.wait(timeout=timeout)
        print("[ctl] Frontend exited gracefully.")
    except subprocess.TimeoutExpired:
        print("[ctl] Graceful stop timeout exceeded; consider 'kill'.")

def kill_frontend() -> None:
    global _frontend_proc
    if not _frontend_proc:
        print("[ctl] Frontend not running.")
        return
    print("[ctl] Forcibly killing frontend ...")
    _frontend_proc.kill()
    try:
        _frontend_proc.wait(timeout=3.0)
    except subprocess.TimeoutExpired:
        pass
    print("[ctl] Frontend killed.")

def restart_frontend() -> None:
    stop_frontend_soft(timeout=3.0)
    start_frontend()

def frontend_status() -> None:
    if not _frontend_proc or _frontend_proc.poll() is not None:
        print("[status] Frontend: NOT RUNNING")
        return

    print(f"[status] Frontend PID: {_frontend_proc.pid} (RUNNING)")
    if _heartbeat_file and _heartbeat_file.exists():
        try:
            hb = json.loads(_heartbeat_file.read_text(encoding="utf-8"))
            age = time.time() - float(hb.get("ts", 0))
            st = hb.get("status", "unknown")
            ver = hb.get("version", "?")
            freshness = "fresh" if age < 5 else f"stale ~{int(age)}s"
            print(f"[status] Heartbeat: {st}, v{ver}, {freshness}")
        except Exception as e:
            print(f"[status] Heartbeat unreadable: {e}")
    else:
        print("[status] No heartbeat file found.")

def _print_help() -> None:
    print(
        "Commands:\n"
        "  start                   Start the frontend process\n"
        "  stop                    Soft stop (graceful)\n"
        "  kill                    Hard kill (immediate)\n"
        "  restart                 Restart frontend\n"
        "  frontend-status | fs    Show frontend status/health\n"
        "  help                    Show this help\n"
        "  q | quit | exit         Exit controller (graceful stop)\n"
    )

def _load_cfg_preview():
    try:
        cfg = json.loads(Path(APP_JSON).read_text(encoding="utf-8"))
        ft = cfg.get("first-time-setup")
        conf = cfg.get("configured")
        host = cfg.get("frontend", {}).get("host")
        port = cfg.get("frontend", {}).get("port")
        print(f"[cfg] first-time-setup={ft}, configured={conf}, frontend={host}:{port}")
    except Exception as e:
        print(f"[cfg] Could not read app.json: {e}")

def main():
    global _python_in_venv, _heartbeat_file
    _python_in_venv, cfg, _heartbeat_file = setup_frontend_env()
    _load_cfg_preview()
    start_frontend()
    _print_help()

    try:
        while True:
            cmd = input("frontend> ").strip().lower()
            if cmd in ("q", "quit", "exit"):
                stop_frontend_soft(timeout=5.0)
                break
            elif cmd == "start":
                start_frontend()
            elif cmd == "stop":
                stop_frontend_soft()
            elif cmd == "kill":
                kill_frontend()
            elif cmd == "restart":
                restart_frontend()
            elif cmd in ("frontend-status", "fs"):
                frontend_status()
            elif cmd in ("help", "?"):
                _print_help()
            elif cmd == "":
                continue
            else:
                print(f"[ctl] Unknown command: {cmd}. Type 'help'.")
    except (EOFError, KeyboardInterrupt):
        print("\n[ctl] Exiting controller ...")
    finally:
        stop_frontend_soft(timeout=3.0)

if __name__ == "__main__":
    main()