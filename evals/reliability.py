"""Workflow reliability scoring."""

from __future__ import annotations

from typing import Any, Dict

from core.recovery_engine import count_retries


def reliability_metrics(state: Any) -> Dict[str, Any]:
    rows = (state.aggregated_results or {}).get("rows") or []
    retry_count = count_retries(state.retry_attempts or [])
    failure_count = len(state.failed_nodes or [])
    fallback_count = sum(1 for row in rows if row.get("fallback_used"))
    completion = 1.0 if state.workflow_status == "completed" else 0.0
    recovery_success = 1.0 if retry_count and state.workflow_status == "completed" else 0.0
    fallback_dependency = fallback_count / max(1, len(rows))
    node_failure_rate = failure_count / max(1, len((state.completed_nodes or []) + (state.failed_nodes or [])))

    score = (
        (completion * 0.35)
        + ((1 - min(retry_count / 5, 1)) * 0.15)
        + (recovery_success * 0.15)
        + ((1 - fallback_dependency) * 0.15)
        + ((1 - node_failure_rate) * 0.20)
    )
    return {
        "workflow_completion_pct": round(completion, 2),
        "retry_frequency": retry_count,
        "recovery_success": round(recovery_success, 2),
        "fallback_dependency": round(fallback_dependency, 2),
        "node_failure_rate": round(node_failure_rate, 2),
        "reliability_score": round(score, 2),
    }
