# my-azure-frontend/app/main.py
from __future__ import annotations
import json
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Tuple

import requests
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, jsonify
)

# -----------------------------
# Config helpers
# -----------------------------

def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]

def _config_paths() -> Tuple[Path, Path]:
    cfg_dir = _project_root() / "config"
    return cfg_dir / "app.json", cfg_dir / "template.app.json"

def load_config() -> dict:
    app_json, _ = _config_paths()
    with open(app_json, "r", encoding="utf-8") as f:
        return json.load(f)

# -----------------------------
# In-memory auth store
# -----------------------------

# Runtime-only user dictionary; resets when the process restarts.
# Populated on startup from config.auth.users (if present) and ensures a default admin/admin.
users_store: Dict[str, str] = {}
_users_initialized = False

def _ensure_users_initialized(cfg: dict) -> None:
    """Hydrate in-memory users from config once per process and guarantee a default admin/admin."""
    global _users_initialized
    if _users_initialized:
        return

    # Load from config.auth.users (optional)
    for u in cfg.get("auth", {}).get("users", []):
        uname = (u or {}).get("username")
        pwd = (u or {}).get("password")
        if isinstance(uname, str) and uname and isinstance(pwd, str) and pwd:
            users_store.setdefault(uname, pwd)

    # Ensure a default dev user is available
    users_store.setdefault("admin", "admin")

    _users_initialized = True

def _check_credentials(username: str, password: str) -> bool:
    return users_store.get(username) == password

def _username_exists(username: str) -> bool:
    return username in users_store

# -----------------------------
# Decorators
# -----------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

# -----------------------------
# Health / integration helpers
# -----------------------------

def _read_router_heartbeat(cfg: dict) -> Dict[str, Any]:
    hb_path = cfg.get("integrations", {}).get("router", {}).get("heartbeat_path")
    try:
        if not hb_path:
            return {"status": "unknown", "note": "No heartbeat_path configured"}
        p = (_project_root() / hb_path).resolve()
        if not p.exists():
            return {"status": "down", "note": f"Heartbeat not found at {p}"}
        payload = json.loads(p.read_text(encoding="utf-8"))
        return {"status": payload.get("status", "unknown"), "raw": payload}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def _query_api_health(cfg: dict) -> Dict[str, Any]:
    url = cfg.get("integrations", {}).get("api", {}).get("health_url")
    try:
        if not url:
            return {"status": "unknown", "note": "No api.health_url configured"}
        r = requests.get(url, timeout=2)
        if r.ok:
            try:
                return {"status": "ok", "raw": r.json()}
            except Exception:
                return {"status": "ok", "raw": r.text}
        return {"status": "down", "code": r.status_code, "raw": r.text}
    except requests.exceptions.RequestException as e:
        return {"status": "down", "error": str(e)}

def _post_route_update(cfg: dict, data: dict) -> Dict[str, Any]:
    url = cfg.get("integrations", {}).get("api", {}).get("routes_url")
    if not url:
        return {"ok": False, "error": "No api.routes_url configured"}
    try:
        r = requests.post(url, json=data, timeout=3)
        return {"ok": r.ok, "status_code": r.status_code, "response": try_json(r)}
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": str(e)}

def try_json(r: requests.Response):
    try:
        return r.json()
    except Exception:
        return r.text

# -----------------------------
# Flask app factory
# -----------------------------

def create_app(cfg: dict) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.secret_key = cfg.get("auth", {}).get("secret_key", "dev-only-change-me")

    # Initialize in-memory users once per process
    _ensure_users_initialized(cfg)

    # ---- Routes ----

    @app.route("/healthz")
    def healthz():
        return jsonify({"status": "ok", "service": "frontend"})

    # --- Auth ---

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = (request.form.get("password") or "").strip()
            if _check_credentials(username, password):
                session["user"] = username
                return redirect(url_for("dashboard"))
            flash("Invalid credentials", "error")
        return render_template("login.html", title="Login")


    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            password = (request.form.get("password") or "").strip()

            if not username or not password:
                flash("Username and password are required.", "error")
            elif username in users_store:
                flash("Username already exists.", "error")
            else:
                users_store[username] = password
                flash("Account created successfully! Please log in.", "success")
                return redirect(url_for("login"))

        return render_template("register.html", title="Register")


    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # --- App pages ---

    @app.route("/")
    @login_required
    def dashboard():
        router = _read_router_heartbeat(cfg)
        api = _query_api_health(cfg)
        theme = cfg.get("frontend", {}).get("theme", "light")
        return render_template(
            "dashboard.html",
            title="Dashboard",
            theme=theme,
            router=router,
            api=api
        )

    @app.route("/routes", methods=["GET", "POST"])
    @login_required
    def routes():
        result = None
        if request.method == "POST":
            payload = {
                "destination": request.form.get("destination"),
                "next_hop": request.form.get("next_hop"),
                "metric": int(request.form.get("metric") or 0),
            }
            result = _post_route_update(cfg, payload)
            if result.get("ok"):
                flash("Route update submitted", "success")
            else:
                flash(f"Route update failed: {result.get('error') or result.get('status_code')}", "error")

        theme = cfg.get("frontend", {}).get("theme", "light")
        return render_template("routes.html", title="Routes", theme=theme, result=result)

    return app