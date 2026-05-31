"""Marketplace pack discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from config import settings


def load_marketplace_packs() -> List[Dict[str, Any]]:
    packs: List[Dict[str, Any]] = []
    for path in sorted(settings.MARKETPLACE_DIR.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if isinstance(raw, dict):
            raw["path"] = str(path)
            packs.append(raw)
    return packs
