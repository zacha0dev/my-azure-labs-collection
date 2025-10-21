# my-wiki/labs/my-azure-router/router/my_router_process.py
from __future__ import annotations
import json
import os
import signal
import sys
import time
from pathlib import Path

__version__ = "0.1.0"

_running = True

def _handle_sig(signum, frame):
    global _running
    print(f"[router] Received signal {signum}; graceful shutdown requested.")
    _running = False

def _write_heartbeat(hb_path: Path, status: str = "ok"):
    payload = {
        "ts": time.time(),
        "status": status,
        "version": __version__
    }
    hb_path.write_text(json.dumps(payload), encoding="utf-8")

def _remove_heartbeat(hb_path: Path):
    try:
        hb_path.unlink(missing_ok=True)  # Python 3.8+: use try/except if older
    except Exception:
        pass

def main():
    if len(sys.argv) < 2:
        print("[router] Missing heartbeat path argument.")
        sys.exit(2)

    hb_path = Path(sys.argv[1]).resolve()

    # Cross-platform signal handling
    signal.signal(signal.SIGTERM, _handle_sig)
    signal.signal(signal.SIGINT, _handle_sig)   # Ctrl+C
    if hasattr(signal, "SIGBREAK"):             # Windows Ctrl+Break
        signal.signal(signal.SIGBREAK, _handle_sig)

    print("[router] Router process starting ...")
    try:
        while _running:
            _write_heartbeat(hb_path, status="ok")
            time.sleep(1.0)  # <- your main loop work interval
    finally:
        _write_heartbeat(hb_path, status="stopping")
        _remove_heartbeat(hb_path)
        print("[router] Router process stopped.")

if __name__ == "__main__":
    main()