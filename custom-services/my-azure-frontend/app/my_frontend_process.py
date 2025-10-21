# my-azure-frontend/app/my_frontend_process.py
from __future__ import annotations
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path

from main import create_app, load_config  # local imports from app/main.py

__version__ = "0.1.1"

_running = True
_httpd = None  # will hold the werkzeug server
_srv_thread: threading.Thread | None = None

def _set_console_title():
    if os.name == "nt":
        try:
            import ctypes  # type: ignore
            ctypes.windll.kernel32.SetConsoleTitleW(f"MyAzureFrontend [{os.getpid()}]")
        except Exception:
            pass

def _maybe_set_proc_title():
    # Optional: if setproctitle is installed, set a friendlier process title
    try:
        import setproctitle  # type: ignore
        setproctitle.setproctitle(f"my-azure-frontend [{os.getpid()}]")
    except Exception:
        pass

def _handle_sig(signum, frame):
    """Make shutdown deterministic across SIGTERM (Linux), SIGBREAK (Windows soft), SIGINT."""
    global _running
    print(f"[frontend] Received signal {signum}; graceful shutdown requested.")
    _running = False
    # If the HTTP server is running, ask it to stop accepting new requests
    try:
        if _httpd:
            _httpd.shutdown()
    except Exception:
        pass

def _write_heartbeat(hb_path: Path, status: str = "ok"):
    payload = {"ts": time.time(), "status": status, "version": __version__}
    hb_path.write_text(json.dumps(payload), encoding="utf-8")

def _remove_heartbeat(hb_path: Path):
    try:
        hb_path.unlink(missing_ok=True)
    except Exception:
        pass

def _write_pid(pid_path: Path):
    try:
        pid_path.write_text(json.dumps({"pid": os.getpid(), "ts": time.time()}), encoding="utf-8")
    except Exception:
        pass

def _remove_pid(pid_path: Path):
    try:
        pid_path.unlink(missing_ok=True)
    except Exception:
        pass

def main():
    if len(sys.argv) < 2:
        print("[frontend] Missing heartbeat path argument.")
        sys.exit(2)

    hb_path = Path(sys.argv[1]).resolve()
    pid_path = hb_path.parent / ".pid"

    # Signals — do NOT override SIGINT; Werkzeug handles Ctrl+C. We handle SIGTERM/SIGBREAK.
    signal.signal(signal.SIGTERM, _handle_sig)
    if hasattr(signal, "SIGBREAK"):  # Windows Ctrl+Break
        signal.signal(signal.SIGBREAK, _handle_sig)

    # Visual/process identification helpers
    _set_console_title()
    _maybe_set_proc_title()

    # Config + app
    cfg = load_config()
    host = cfg.get("frontend", {}).get("host", "127.0.0.1")
    port = int(cfg.get("frontend", {}).get("port", 8501))
    debug = bool(cfg.get("frontend", {}).get("debug", False))
    hb_interval = float(cfg.get("heartbeat", {}).get("interval_sec", 1.0))

    app = create_app(cfg)

    # Heartbeat thread
    def _heartbeat_worker():
        while _running:
            try:
                _write_heartbeat(hb_path, status="ok")
            except Exception as e:
                print(f"[frontend] Heartbeat write failed: {e}")
            time.sleep(hb_interval)
        try:
            _write_heartbeat(hb_path, status="stopping")
            _remove_heartbeat(hb_path)
        except Exception:
            pass

    hb_thread = threading.Thread(target=_heartbeat_worker, daemon=True)
    hb_thread.start()
    _write_pid(pid_path)

    # Start HTTP server in a thread using werkzeug.make_server so we can shut it down cleanly
    from werkzeug.serving import make_server
    global _httpd, _srv_thread
    _httpd = make_server(host, port, app)
    _srv_thread = threading.Thread(target=_httpd.serve_forever, daemon=True)

    print(f"[frontend] Flask starting on http://{host}:{port} ...")
    _srv_thread.start()

    # Main loop waits for shutdown signal
    try:
        while _running:
            time.sleep(0.2)
    finally:
        # Ask server to stop and join
        try:
            if _httpd:
                _httpd.shutdown()
        except Exception:
            pass
        if _srv_thread:
            _srv_thread.join(timeout=5.0)

        # Cleanup
        _remove_pid(pid_path)
        print("[frontend] Frontend process stopped.")

if __name__ == "__main__":
    main()