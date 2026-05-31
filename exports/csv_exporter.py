"""CSV exporter."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config import settings


def export_csv(rows: List[Dict[str, Any]], *, query: str) -> Dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = settings.OUTPUTS_DIR / f"skillflow_results_{timestamp}.csv"
    if not rows:
        return {"csv_path": "", "rows_written": 0, "error": "No rows to write."}

    headers = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    return {"csv_path": str(path), "rows_written": len(rows), "error": ""}
