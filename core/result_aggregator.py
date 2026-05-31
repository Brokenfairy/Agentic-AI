"""Flatten workflow results into table-ready rows and summary metrics."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from core.recovery_engine import count_retries
from core.workflow_state import WorkflowState


def _flatten_record(record: Dict[str, Any]) -> Dict[str, Any]:
    row = {
        "url": record.get("url", ""),
        "title": record.get("title", ""),
        "domain": record.get("domain", ""),
        "status": record.get("status", ""),
        "method": record.get("page_method", ""),
        "fallback_used": bool(record.get("fallback_used", False)),
        "confidence_score": record.get("confidence_score", 0.0),
        "source_agents": ", ".join(record.get("source_agents") or []),
    }
    for key, value in (record.get("fields") or {}).items():
        if isinstance(value, dict):
            row[key] = ", ".join(f"{part}: {val}" for part, val in value.items())
            row[f"{key}_raw"] = value
        else:
            row[key] = value
    return row


def aggregate_results(state: WorkflowState) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = [_flatten_record(record) for record in state.extracted_data]
    seen = {row.get("url", "") for row in rows}
    for failed in state.failed_urls:
        if failed.get("url") in seen:
            continue
        rows.append(
            {
                "url": failed.get("url", ""),
                "title": "",
                "domain": failed.get("domain", ""),
                "status": "failed",
                "method": "",
                "fallback_used": False,
                "confidence_score": 0.0,
                "error": failed.get("error", ""),
                "source_agents": "",
            }
        )

    success_count = sum(1 for row in rows if row.get("status") == "success")
    fallback_count = sum(1 for row in rows if row.get("fallback_used"))
    failed_count = sum(1 for row in rows if row.get("status") == "failed")
    domain_counter = Counter(row.get("domain", "") for row in rows if row.get("domain"))
    avg_confidence = round(
        sum(float(row.get("confidence_score") or 0.0) for row in rows) / max(1, len(rows)),
        2,
    )

    summary = {
        "total_urls": len(rows),
        "success_count": success_count,
        "fallback_count": fallback_count,
        "failed_count": failed_count,
        "fields_extracted": list(state.parsed_query.get("requested_fields") or []),
        "search_query": state.parsed_query.get("search_query", ""),
        "trace_id": state.trace_id,
        "average_confidence": avg_confidence,
        "average_urls_processed": round(len(rows) / max(1, len(state.selected_skills)), 2),
        "retries_triggered": count_retries(state.retry_attempts),
        "fallback_usage_percent": round((fallback_count / max(1, len(rows))) * 100, 1),
        "top_domains": [domain for domain, _ in domain_counter.most_common(5)],
    }
    return {"rows": rows, "summary": summary}
