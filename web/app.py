"""MindstormLLM Profile Builder - Visual web UI for configuring robot profiles."""
from __future__ import annotations
import asyncio
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, render_template, request, jsonify, redirect, url_for
import yaml

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "robot.yaml"
PROFILES_DIR = PROJECT_ROOT / "config" / "profiles"

app = Flask(__name__)

# Track running robot process
_robot_proc: subprocess.Popen | None = None


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def load_profiles() -> list[dict]:
    """Load all custom profile YAMLs from config/profiles/."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profiles = []
    for p in sorted(PROFILES_DIR.glob("*.yaml")):
        with open(p) as f:
            data = yaml.safe_load(f)
            data["_filename"] = p.stem
            profiles.append(data)
    return profiles


def save_profile(name: str, profile: dict) -> None:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    path = PROFILES_DIR / f"{name}.yaml"
    with open(path, "w") as f:
        yaml.dump(profile, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def delete_profile(name: str) -> bool:
    path = PROFILES_DIR / f"{name}.yaml"
    if path.exists():
        path.unlink()
        return True
    return False


# --- Routes ---

@app.route("/")
def index():
    config = load_config()
    profiles = load_profiles()
    return render_template("index.html", config=config, profiles=profiles)


@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def update_config():
    existing = load_config()
    incoming = request.json
    # Merge: update existing config without deleting keys not in UI
    for key in ("ports", "driving", "safety", "llm"):
        if key in incoming:
            existing[key] = incoming[key]
    save_config(existing)
    return jsonify({"ok": True})


@app.route("/api/profiles", methods=["GET"])
def get_profiles():
    return jsonify(load_profiles())


@app.route("/api/profiles", methods=["POST"])
def create_profile():
    data = request.json
    name = data.get("name", "").strip().lower().replace(" ", "_")
    if not name:
        return jsonify({"error": "Name is required"}), 400
    save_profile(name, data)
    return jsonify({"ok": True, "name": name})


@app.route("/api/profiles/<name>", methods=["DELETE"])
def remove_profile(name):
    if delete_profile(name):
        return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404


@app.route("/api/robot/start", methods=["POST"])
def start_robot():
    global _robot_proc
    if _robot_proc and _robot_proc.poll() is None:
        return jsonify({"error": "Robot is already running"}), 400

    data = request.json or {}
    profile = data.get("profile", "patrol")

    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    _robot_proc = subprocess.Popen(
        [str(venv_python), "-m", "mindstorm", "run", profile],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return jsonify({"ok": True, "pid": _robot_proc.pid})


@app.route("/api/robot/stop", methods=["POST"])
def stop_robot():
    global _robot_proc
    if _robot_proc and _robot_proc.poll() is None:
        _robot_proc.terminate()
        _robot_proc = None
        return jsonify({"ok": True})
    return jsonify({"error": "No robot is running"}), 400


@app.route("/api/robot/status", methods=["GET"])
def robot_status():
    running = _robot_proc is not None and _robot_proc.poll() is None
    return jsonify({"running": running})


if __name__ == "__main__":
    print("\n  MindstormLLM Profile Builder")
    print("  http://localhost:8080\n")
    app.run(debug=True, port=8080)
