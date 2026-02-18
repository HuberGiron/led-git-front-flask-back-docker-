from __future__ import annotations
import json
import os
import re
import tempfile
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_cors import CORS

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ En Render conviene usar un path persistente (ej. /var/data) con un Disk montado.
DATA_DIR = os.getenv("DATA_DIR", os.path.join(APP_DIR, "data"))

STATE_FILE = os.path.join(DATA_DIR, "state.json")

# Posibles nombres anteriores (por si existieran)
LEGACY_FILES = [
    os.path.join(DATA_DIR, "state.jsonq"),
    os.path.join(DATA_DIR, "state.txt"),
]

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
LED_MIN, LED_MAX = 0, 8

app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": "*"}})

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix="state_", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, path)  # escritura atómica
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def default_state() -> dict:
    return {"color": "#ff0000", "count": 8, "rev": 1, "updated_at": now_iso()}


def migrate_legacy_if_needed() -> None:
    """
    Si no existe state.json pero existe algún legacy, lo migra a state.json.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(STATE_FILE):
        return

    for legacy in LEGACY_FILES:
        if os.path.exists(legacy):
            try:
                os.replace(legacy, STATE_FILE)
                return
            except Exception:
                try:
                    with open(legacy, "r", encoding="utf-8") as f:
                        content = f.read()
                    atomic_write_text(STATE_FILE, content)
                    return
                except Exception:
                    pass


def load_state() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    migrate_legacy_if_needed()

    if not os.path.exists(STATE_FILE):
        st = default_state()
        atomic_write_text(STATE_FILE, json.dumps(st, ensure_ascii=False))
        return st

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            st = json.load(f)

        st.setdefault("color", "#ff0000")
        st.setdefault("count", 8)
        st.setdefault("rev", 1)
        st.setdefault("updated_at", now_iso())
        return st
    except Exception:
        st = default_state()
        atomic_write_text(STATE_FILE, json.dumps(st, ensure_ascii=False))
        return st


def validate_state(color: str, count: int) -> tuple[bool, str]:
    if not isinstance(color, str) or not HEX_COLOR_RE.match(color):
        return False, "color inválido. Usa formato #RRGGBB"
    if not isinstance(count, int) or not (LED_MIN <= count <= LED_MAX):
        return False, f"count inválido. Debe estar entre {LED_MIN} y {LED_MAX}"
    return True, ""


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True})


@app.get("/api/state")
def get_state():
    return jsonify(load_state())


@app.post("/api/state")
def set_state():
    payload = request.get_json(silent=True) or {}
    color = payload.get("color")
    count = payload.get("count")

    try:
        count = int(count)
    except Exception:
        count = count

    ok, msg = validate_state(color, count)
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400

    st = load_state()
    st["color"] = color
    st["count"] = count
    st["rev"] = int(st.get("rev", 1)) + 1
    st["updated_at"] = now_iso()

    atomic_write_text(STATE_FILE, json.dumps(st, ensure_ascii=False))
    return jsonify({"ok": True, **st})


if __name__ == "__main__":
    # En Render, PORT suele venir seteado (default 10000). En local, 5000.
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
