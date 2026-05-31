"""Markdown report exporter."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from config import settings


def export_markdown(rows: List[Dict[str, Any]], *, query: str, summary: str) -> Dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = settings.OUTPUTS_DIR / f"skillflow_report_{timestamp}.md"
    lines = ["# SkillFlow Report", "", f"## Query", query, "", "## Summary", summary, "", "## Rows", ""]
    for row in rows:
        lines.append(f"- {row.get('title') or row.get('url')}: price={row.get('price')} rating={row.get('rating')}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"markdown_path": str(path), "rows_written": len(rows), "error": ""}
