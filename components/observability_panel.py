"""Observability summary renderer."""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from core.recovery_engine import count_retries


def render_observability_panel(state: Dict[str, Any]) -> None:
    c1, c2 = st.columns(2)
    c1.metric("Status", (state.get("workflow_status") or "idle").upper())
    c2.metric("Duration", f"{state.get('total_duration_seconds', 0)}s")
    c1.metric("DB Run ID", state.get("db_run_id") or "-")
    c2.metric("Retries", count_retries(state.get("retry_attempts") or []))
    st.caption(
        f"Provider: {state.get('provider_name') or 'heuristic'} "
        f"/ {state.get('provider_model') or 'none'}"
    )
    st.caption(f"Supervisor backend: {state.get('supervisor_backend') or 'heuristic'}")
    if state.get("trace_url"):
        st.markdown(f"[Open Langfuse Trace]({state['trace_url']})")
    if state.get("trace_path"):
        st.code(state["trace_path"], language="text")
    if state.get("export_paths"):
        st.json(state["export_paths"], expanded=False)
    if state.get("report_paths"):
        st.json(state["report_paths"], expanded=False)
    if state.get("latest_checkpoint_path"):
        st.caption(f"Latest checkpoint: {state['latest_checkpoint_path']}")
    if state.get("traceability_chain"):
        st.caption(f"Traceability links: {len(state['traceability_chain'])}")
    if state.get("cached_data_used"):
        st.info("Cached demo data was used.")
    if state.get("fallback_used"):
        st.warning("Fallback extraction was used in this run.")
