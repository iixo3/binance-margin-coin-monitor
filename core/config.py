from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env(path: Path) -> None:
    """Minimal .env loader (no dependency). KEY=VALUE per line."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_env(ROOT / ".env")


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def load_config() -> dict:
    return json.loads((ROOT / "config.json").read_text())
