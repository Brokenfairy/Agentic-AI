"""Single-screen presentation dashboard."""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from components.agent_performance import render_agent_performance
from components.langfuse_dashboard import render_langfuse_dashboard
from components.workflow_health import render_workflow_health
from database.db import workflow_analytics


def render_presentation_dashboard(state: Dict[str, Any] | None = None) -> None:
    analytics = workflow_analytics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Workflow Success", f"{float(analytics.get('success_rate') or 0.0) * 100:.0f}%")
    c2.metric("Avg Time", f"{float(analytics.get('avg_duration') or 0.0):.2f}s")
    c3.metric("Avg Confidence", f"{float(analytics.get('avg_confidence') or 0.0):.2f}")
    c4.metric("Avg Health", f"{float(analytics.get('avg_health_score') or 0.0):.2f}")
    st.caption(f"Top domains: {analytics.get('top_domains', {})}")

    if state:
        st.divider()
        st.subheader("Current Workflow Health")
        render_workflow_health(state)

    st.divider()
    left, right = st.columns(2)
    with left:
        st.subheader("Langfuse")
        render_langfuse_dashboard()
    with right:
        st.subheader("Agent Performance")
        render_agent_performance()
