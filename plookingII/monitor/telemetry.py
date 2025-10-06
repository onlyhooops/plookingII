"""
Lightweight optional anonymous telemetry (local-only by default).

Design goals:
- Opt-in via env var PLOOKINGII_TELEMETRY=1 (default off)
- No network I/O; append JSONL to local telemetry file
- Allow overriding directory with PLOOKINGII_TELEMETRY_DIR

Recorded fields: timestamp, event, properties (dict)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any


def _enabled() -> bool:
    return os.environ.get("PLOOKINGII_TELEMETRY", "0") in ("1", "true", "TRUE")


def _default_dir() -> str:
    env_dir = os.environ.get("PLOOKINGII_TELEMETRY_DIR")
    if env_dir:
        try:
            os.makedirs(env_dir, exist_ok=True)
            return env_dir
        except Exception:
            pass
    try:
        base = os.path.expanduser(os.path.join("~", "Library", "Logs", "PlookingII"))
        os.makedirs(base, exist_ok=True)
        return base
    except Exception:
        import tempfile

        base = os.path.join(tempfile.gettempdir(), "PlookingII-logs")
        try:
            os.makedirs(base, exist_ok=True)
        except Exception:
            pass
        return base


def is_telemetry_enabled() -> bool:
    """Check if telemetry is enabled.

    Returns True if PLOOKINGII_TELEMETRY is set to 1/true/TRUE.
    """
    return _enabled()


def record_event(event: str, properties: dict[str, Any] | None = None) -> bool:
    """Record telemetry event to local JSONL when enabled.

    Returns True when event is recorded; False when disabled or failure.
    """
    if not _enabled():
        return False
    try:
        log_dir = _default_dir()
        path = os.path.join(log_dir, "telemetry.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            payload = {
                "ts": int(time.time()),
                "event": event,
                "properties": properties or {},
            }
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False
