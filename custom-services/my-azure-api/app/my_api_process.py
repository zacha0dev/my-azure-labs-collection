# my-azure-labs-collection/custom-services/my-azure-api/app/my_api_process.py
from __future__ import annotations
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path
import uvicorn

__version__ = "0.1.0"
_running = True

def _handle_sig(signum, frame):
    global _running
    print(f"[api] Received signal {signum}; graceful shutdown requested.")
    _running = False

def _heartbeat_worker(hb_path: Path, interval_sec: float = 1.0):
    while _running:
        payload = {"ts": time.time(), "status": "ok", "version": __version__}
        try:
            hb_path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            pass
        time.sleep(interval_sec)
    # mark stopping + cleanup
    try:
        hb_path.write_text(json.dumps({"ts": time.time(), "status": "stopping", "version": __version__}), encoding="utf-8")
        hb_path.unlink(missing_ok=True)
    except Exception:
        pass

def main():
    if len(sys.argv) < 4:
        print("Usage: my_api_process.py <heartbeat_path> <host> <port> [interval_sec]")
        sys.exit(2)

    hb_path = Path(sys.argv[1]).resolve()
    host = sys.argv[2]
    port = int(sys.argv[3])
    interval = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0

    # --- Ensure we can import the local package reliably ---
    # Change CWD to the service root and put it on sys.path[0]
    SERVICE_ROOT = Path(__file__).resolve().parents[1]  # .../my-azure-api/
    os.chdir(SERVICE_ROOT)
    if str(SERVICE_ROOT) not in sys.path:
        sys.path.insert(0, str(SERVICE_ROOT))

    # Import the FastAPI app object directly (avoids string-based import issues)
    try:
        from app.main import app as fastapi_app
    except Exception as e:
        print(f"[api] Failed to import FastAPI app from app.main: {e}")
        sys.exit(3)

    # Signals
    signal.signal(signal.SIGTERM, _handle_sig)
    signal.signal(signal.SIGINT, _handle_sig)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _handle_sig)

    # Heartbeat thread
    t = threading.Thread(target=_heartbeat_worker, args=(hb_path, interval), daemon=True)
    t.start()

    print(f"[api] Starting FastAPI on {host}:{port}")
    # Pass the app object directly to Uvicorn:
    config = uvicorn.Config(fastapi_app, host=host, port=port, reload=False, log_level="info")
    server = uvicorn.Server(config)

    try:
        server.run()
    finally:
        global _running
        _running = False
        t.join(timeout=2.0)
        print("[api] API process stopped.")

if __name__ == "__main__":
    main()