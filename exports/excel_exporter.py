"""Excel export wrapper."""

from __future__ import annotations

from typing import Any, Dict, List

from tools.excel_writer_tool import write_excel


def export_excel(rows: List[Any], *, query: str) -> Dict[str, Any]:
    return write_excel(rows, query=query)
