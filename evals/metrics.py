"""Extraction and workflow metrics."""

from __future__ import annotations

from typing import Any, Dict, List


def extraction_metrics(rows: List[Dict[str, Any]], expected_fields: List[str]) -> Dict[str, Any]:
    if not rows:
        return {
            "extraction_success_rate": 0.0,
            "avg_confidence": 0.0,
            "fallback_usage": 0,
            "empty_fields": len(expected_fields),
            "malformed_outputs": 0,
            "extraction_failures": 1,
            "completeness": 0.0,
        }

    filled_slots = 0
    total_slots = len(rows) * max(1, len(expected_fields))
    empty_fields = 0
    malformed = 0
    fallback_usage = 0
    confidence_total = 0.0
    success_rows = 0

    for row in rows:
        confidence_total += float(row.get("confidence_score") or 0.0)
        if row.get("fallback_used"):
            fallback_usage += 1
        if row.get("status") != "failed":
            success_rows += 1
        for field in expected_fields:
            value = row.get(field)
            if value in (None, "", [], {}):
                empty_fields += 1
            else:
                filled_slots += 1
        if row.get("malformed") or ("fields" in row and not isinstance(row.get("fields"), dict)):
            malformed += 1

    return {
        "extraction_success_rate": round(success_rows / max(1, len(rows)), 2),
        "avg_confidence": round(confidence_total / max(1, len(rows)), 2),
        "fallback_usage": fallback_usage,
        "empty_fields": empty_fields,
        "malformed_outputs": malformed,
        "extraction_failures": sum(1 for row in rows if row.get("status") == "failed"),
        "completeness": round(filled_slots / max(1, total_slots), 2),
    }
