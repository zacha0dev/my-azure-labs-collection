# my-azure-labs-collection/custom-services/my-azure-api/start_api.py
from __future__ import annotations
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from config.my_api_setup import setup_api_env, PROJECT_ROOT, APP_JSON

_api_proc: subprocess.Popen | None = None
_python_in_venv: Path | None = None
_heartbeat_file: Path | None = None
_cfg: dict | None = None

def _creationflags_for_windows() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    return 0

def _load_cfg_preview():
    try:
        cfg = json.loads(Path(APP_JSON).read_text(encoding="utf-8"))
        api = cfg.get("api", {})
        hb = cfg.get("heartbeat", {})
        print(f"[cfg] host={api.get('host')} port={api.get('port')} heartbeat={hb.get('path')}")
    except Exception as e:
        print(f"[cfg] Could not read app.json: {e}")

def start_api() -> None:
    global _api_proc
    if _api_proc and _api_proc.poll() is None:
        print("[ctl] API already running.")
        return

    assert _python_in_venv is not None and _heartbeat_file is not None and _cfg is not None

    proc_script = PROJECT_ROOT / "app" / "my_api_process.py"
    if not proc_script.exists():
        raise FileNotFoundError(f"Missing API process script: {proc_script}")

    host = _cfg["api"]["host"]
    port = str(_cfg["api"]["port"])
    hb_interval = str(_cfg["heartbeat"].get("interval_sec", 1))
    hb_path = str(_heartbeat_file)

    print("[ctl] Starting API process ...")
    if os.name == "nt":
        _api_proc = subprocess.Popen(
            [str(_python_in_venv), str(proc_script), hb_path, host, port, hb_interval],
            creationflags=_creationflags_for_windows()
        )
    else:
        _api_proc = subprocess.Popen(
            [str(_python_in_venv), str(proc_script), hb_path, host, port, hb_interval]
        )
    print(f"[ctl] API PID: {_api_proc.pid}")

def stop_api_soft(timeout: float = 5.0) -> None:
    global _api_proc
    if not _api_proc:
        print("[ctl] API not running.")
        return

    if os.name == "nt":
        try:
            _api_proc.send_signal(signal.CTRL_BREAK_EVENT)
            print("[ctl] Sent CTRL_BREAK_EVENT (soft stop).")
        except Exception:
            _api_proc.terminate()
            print("[ctl] Sent terminate() as fallback.")
    else:
        _api_proc.terminate()
        print("[ctl] Sent SIGTERM (soft stop).")

    try:
        _api_proc.wait(timeout=timeout)
        print("[ctl] API exited gracefully.")
    except subprocess.TimeoutExpired:
        print("[ctl] Graceful stop timeout exceeded; consider 'kill'.")

def kill_api() -> None:
    global _api_proc
    if not _api_proc:
        print("[ctl] API not running.")
        return
    print("[ctl] Forcibly killing API ...")
    _api_proc.kill()
    try:
        _api_proc.wait(timeout=3.0)
    except subprocess.TimeoutExpired:
        pass
    print("[ctl] API killed.")

def restart_api() -> None:
    stop_api_soft(timeout=3.0)
    start_api()

def api_status() -> None:
    if not _api_proc or _api_proc.poll() is not None:
        print("[status] API: NOT RUNNING")
        return
    print(f"[status] API PID: {_api_proc.pid} (RUNNING)")
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

def _print_help():
    print(
        "Commands:\n"
        "  start              Start the API process\n"
        "  stop               Soft stop (graceful)\n"
        "  kill               Hard kill (immediate)\n"
        "  restart            Restart API\n"
        "  api-status | as    Show API status/health\n"
        "  help               Show this help\n"
        "  q | quit | exit    Exit controller (graceful stop)\n"
    )

def main():
    global _python_in_venv, _heartbeat_file, _cfg
    _python_in_venv, _cfg, _heartbeat_file = setup_api_env()
    _load_cfg_preview()

    # Auto-start; comment out if you prefer manual start
    start_api()
    _print_help()

    try:
        while True:
            cmd = input("api> ").strip().lower()
            if cmd in ("q", "quit", "exit"):
                stop_api_soft(timeout=5.0)
                break
            elif cmd == "start":
                start_api()
            elif cmd == "stop":
                stop_api_soft()
            elif cmd == "kill":
                kill_api()
            elif cmd == "restart":
                restart_api()
            elif cmd in ("api-status", "as"):
                api_status()
            elif cmd in ("help", "?"):
                _print_help()
            elif cmd == "":
                continue
            else:
                print(f"[ctl] Unknown command: {cmd}. Type 'help'.")
    except (EOFError, KeyboardInterrupt):
        print("\n[ctl] Exiting controller ...")
    finally:
        stop_api_soft(timeout=3.0)

if __name__ == "__main__":
    main()