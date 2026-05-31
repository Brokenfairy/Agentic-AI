"""Agent performance dashboard."""

from __future__ import annotations

import streamlit as st

from database.db import agent_performance


def render_agent_performance() -> None:
    metrics = agent_performance()
    usage = metrics.get("usage", {})
    avg_time = metrics.get("avg_execution_time", {})
    avg_conf = metrics.get("avg_confidence", {})
    failure_rate = metrics.get("failure_rate", {})
    recovery_rate = metrics.get("recovery_rate", {})

    c1, c2, c3 = st.columns(3)
    c1.metric("Most Used Agent", next(iter(sorted(usage, key=usage.get, reverse=True)), "-"))
    c2.metric("Successful Runs", metrics.get("successful_runs", 0))
    c3.metric("Tracked Agents", len(usage))

    st.caption(f"Usage: {usage}")
    st.caption(f"Avg execution time: {avg_time}")
    st.caption(f"Avg confidence: {avg_conf}")
    st.caption(f"Failure rate: {failure_rate}")
    st.caption(f"Recovery rate: {recovery_rate}")
