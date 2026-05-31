"""Supervisor decision analytics."""

from __future__ import annotations

import streamlit as st

from database.db import supervisor_analytics


def render_supervisor_analytics() -> None:
    analytics = supervisor_analytics()
    c1, c2 = st.columns(2)
    c1.metric("Planning Latency", f"{float(analytics.get('planning_latency_ms') or 0.0):.0f}ms")
    c2.metric("Tracked Categories", len(analytics.get("query_categories", {})))
    st.caption(f"Most selected skills: {analytics.get('most_selected_skills', {})}")
    st.caption(f"Most skipped skills: {analytics.get('most_skipped_skills', {})}")
    st.caption(f"Query categories: {analytics.get('query_categories', {})}")
