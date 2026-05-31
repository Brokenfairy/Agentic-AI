"""Checkpoint helpers for workflow replay and recovery."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from config import settings


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()[:40] or "workflow"


def save_checkpoint(state: Any, stage: str) -> str:
    payload = state.to_dict() if hasattr(state, "to_dict") else dict(state)
    payload["checkpoint_stage"] = stage
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = settings.CHECKPOINTS_DIR / f"{ts}_{_slugify(payload.get('original_query', 'workflow'))}_{stage}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(path)


def load_checkpoint(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
