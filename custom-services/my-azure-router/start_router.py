# my-wiki/labs/my-azure-router/start_router.py
from __future__ import annotations
import os
import signal
import subprocess
import sys
import time
import json
from pathlib import Path

# Import setup (works because start_router.py is one level above /router)
from router.my_router_setup import setup_router_env, PROJECT_ROOT, APP_JSON

# Globals for the controller session
_router_proc: subprocess.Popen | None = None
_python_in_venv: Path | None = None
_heartbeat_file: Path | None = None

def _creationflags_for_windows() -> int:
    """Allow sending CTRL_BREAK_EVENT on Windows by creating a new process group."""
    if os.name == "nt":
        # 0x00000010 CREATE_NEW_CONSOLE or 0x00000200 CREATE_NEW_PROCESS_GROUP
        return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    return 0

def start_router() -> None:
    global _router_proc
    if _router_proc and _router_proc.poll() is None:
        print("[ctl] Router already running.")
        return

    assert _python_in_venv is not None and _heartbeat_file is not None

    router_script = PROJECT_ROOT / "router" / "my_router_process.py"
    if not router_script.exists():
        raise FileNotFoundError(f"Missing router script: {router_script}")

    print("[ctl] Starting router process ...")
    if os.name == "nt":
        _router_proc = subprocess.Popen(
            [str(_python_in_venv), str(router_script), str(_heartbeat_file)],
            creationflags=_creationflags_for_windows()
        )
    else:
        _router_proc = subprocess.Popen(
            [str(_python_in_venv), str(router_script), str(_heartbeat_file)]
        )
    print(f"[ctl] Router PID: {_router_proc.pid}")

def stop_router_soft(timeout: float = 5.0) -> None:
    global _router_proc
    if not _router_proc:
        print("[ctl] Router not running.")
        return

    if os.name == "nt":
        # Best-effort "soft" on Windows: send CTRL_BREAK_EVENT if possible
        try:
            _router_proc.send_signal(signal.CTRL_BREAK_EVENT)
            print("[ctl] Sent CTRL_BREAK_EVENT (soft stop).")
        except Exception:
            _router_proc.terminate()
            print("[ctl] Sent terminate() as fallback.")
    else:
        _router_proc.terminate()
        print("[ctl] Sent SIGTERM (soft stop).")

    try:
        _router_proc.wait(timeout=timeout)
        print("[ctl] Router exited gracefully.")
    except subprocess.TimeoutExpired:
        print("[ctl] Graceful stop timeout exceeded; consider 'kill'.")

def kill_router() -> None:
    global _router_proc
    if not _router_proc:
        print("[ctl] Router not running.")
        return
    print("[ctl] Forcibly killing router ...")
    _router_proc.kill()
    try:
        _router_proc.wait(timeout=3.0)
    except subprocess.TimeoutExpired:
        pass
    print("[ctl] Router killed.")

def restart_router() -> None:
    stop_router_soft(timeout=3.0)
    start_router()

def router_status() -> None:
    # Status from process handle + heartbeat if available
    if not _router_proc or _router_proc.poll() is not None:
        print("[status] Router: NOT RUNNING")
        return

    print(f"[status] Router PID: {_router_proc.pid} (RUNNING)")
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
        "  start              Start the router process\n"
        "  stop               Soft stop (graceful)\n"
        "  kill               Hard kill (immediate)\n"
        "  restart            Restart router\n"
        "  router-status | rs Show router status/health\n"
        "  help               Show this help\n"
        "  q | quit | exit    Exit controller (graceful stop)\n"
    )

def _load_cfg_preview():
    try:
        cfg = json.loads(Path(APP_JSON).read_text(encoding="utf-8"))
        ft = cfg.get("first-time-setup")
        conf = cfg.get("configured")
        host = cfg.get("router", {}).get("host")
        port = cfg.get("router", {}).get("port")
        print(f"[cfg] first-time-setup={ft}, configured={conf}, endpoint={host}:{port}")
    except Exception as e:
        print(f"[cfg] Could not read app.json: {e}")

def main():
    global _python_in_venv, _heartbeat_file

    # Run environment + config setup first
    _python_in_venv, cfg, _heartbeat_file = setup_router_env()

    # Preview config flags for clarity
    _load_cfg_preview()

    # Optionally auto-start after setup; you can comment this out if you prefer manual start
    start_router()

    _print_help()
    # Controller REPL
    try:
        while True:
            cmd = input("router> ").strip().lower()
            if cmd in ("q", "quit", "exit"):
                stop_router_soft(timeout=5.0)
                break
            elif cmd == "start":
                start_router()
            elif cmd == "stop":
                stop_router_soft()
            elif cmd == "kill":
                kill_router()
            elif cmd == "restart":
                restart_router()
            elif cmd in ("router-status", "rs"):
                router_status()
            elif cmd in ("help", "?"):
                _print_help()
            elif cmd == "":
                continue
            else:
                print(f"[ctl] Unknown command: {cmd}. Type 'help'.")
    except (EOFError, KeyboardInterrupt):
        print("\n[ctl] Exiting controller ...")
    finally:
        # Ensure graceful shutdown on exit
        stop_router_soft(timeout=3.0)

if __name__ == "__main__":
    main()