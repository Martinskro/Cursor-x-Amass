from __future__ import annotations

import json
from pathlib import Path

from cursor_x_amass.investigation.schemas import Investigation

BACKEND_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_DIR = BACKEND_ROOT / ".runtime"
STORE_PATH = RUNTIME_DIR / "investigation.json"
LEGACY_PATH = RUNTIME_DIR / "investigations.json"
PENDING_PATH = RUNTIME_DIR / "pending.json"


def current() -> Investigation | None:
    if STORE_PATH.exists():
        return Investigation.model_validate_json(STORE_PATH.read_text())
    if LEGACY_PATH.exists():
        raw = json.loads(LEGACY_PATH.read_text())
        if isinstance(raw, list) and raw:
            job = Investigation.model_validate(raw[-1])
            save(job)
            LEGACY_PATH.unlink()
            return job
    return None


def save(job: Investigation) -> Investigation:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(job.model_dump_json(indent=2))
    if PENDING_PATH.exists():
        PENDING_PATH.unlink()
    return job


def clear() -> None:
    if STORE_PATH.exists():
        STORE_PATH.unlink()
    if PENDING_PATH.exists():
        PENDING_PATH.unlink()
