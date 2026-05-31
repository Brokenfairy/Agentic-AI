"""Workflow health monitor."""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from core.recovery_engine import count_retries


def render_workflow_health(state: Dict[str, Any]) -> None:
    health = state.get("workflow_health") or {}
    quality = state.get("extraction_quality") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Workflow Health", f"{float(state.get('health_score') or 0.0):.2f}")
    c2.metric("Active Failures", len(state.get("failed_nodes") or []))
    c3.metric("Retry Count", count_retries(state.get("retry_attempts") or []))
    c1.metric("Fallback Count", 1 if state.get("fallback_used") else 0)
    c2.metric("Avg Response Time", f"{float(state.get('total_duration_seconds') or 0.0):.2f}s")
    c3.metric("Extraction Quality", f"{float(quality.get('extraction_success_rate') or 0.0):.2f}")
    st.caption(
        f"Node failure rate: {health.get('node_failure_rate', 0.0)} | "
        f"Recovery success: {health.get('recovery_success', 0.0)} | "
        f"Fallback dependency: {health.get('fallback_dependency', 0.0)}"
    )
