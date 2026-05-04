import os
import json
from pathlib import Path

import httpx

CONFIG_DIR = Path.home() / ".investr"
CONFIG_FILE = CONFIG_DIR / "config"


def get_config():
    config = {"api_url": "http://localhost:8000/api/v1", "api_key": None}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip()
    # Env overrides
    if os.environ.get("INVESTR_API_URL"):
        config["api_url"] = os.environ["INVESTR_API_URL"]
    if os.environ.get("INVESTR_API_KEY"):
        config["api_key"] = os.environ["INVESTR_API_KEY"]
    return config


def get_client():
    config = get_config()
    headers = {"Content-Type": "application/json"}
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"
    return httpx.Client(base_url=config["api_url"], headers=headers, timeout=30)


def api_post(path: str, body: dict) -> dict:
    with get_client() as client:
        r = client.post(path, json=body)
        r.raise_for_status()
        return r.json()


def api_get(path: str) -> dict:
    with get_client() as client:
        r = client.get(path)
        r.raise_for_status()
        return r.json()


def api_delete(path: str):
    with get_client() as client:
        r = client.delete(path)
        r.raise_for_status()
