"""JSON exporter."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from config import settings


def export_json(rows: List[Dict[str, Any]], *, query: str, summary: Dict[str, Any] | None = None) -> Dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = settings.OUTPUTS_DIR / f"skillflow_results_{timestamp}.json"
    path.write_text(
        json.dumps({"query": query, "rows": rows, "summary": summary or {}}, indent=2, default=str),
        encoding="utf-8",
    )
    return {"json_path": str(path), "rows_written": len(rows), "error": ""}
