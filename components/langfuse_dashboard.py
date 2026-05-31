"""Langfuse-oriented dashboard backed by persisted traces."""

from __future__ import annotations

import streamlit as st

from database.db import langfuse_dashboard_data


def render_langfuse_dashboard() -> None:
    data = langfuse_dashboard_data()
    rows = data.get("trace_rows", [])
    c1, c2, c3 = st.columns(3)
    c1.metric("Trace IDs", data.get("trace_count", 0))
    c2.metric("Avg Execution Latency", f"{float(data.get('avg_execution_latency') or 0.0):.2f}s")
    c3.metric("Failed Spans", sum((data.get("failed_spans") or {}).values()))

    st.caption(f"Top failing skills: {data.get('failed_spans', {})}")
    st.caption(f"Retry-heavy workflows: {data.get('retry_heavy_workflows', [])}")
    st.caption(f"Most expensive workflows: {data.get('most_expensive_workflows', [])}")

    for row in rows[:10]:
        with st.container(border=True):
            st.markdown(f"**{row.get('query', '')}**")
            st.caption(
                f"trace_id={row.get('trace_id', '')} | status={row.get('status', '')} | "
                f"duration={row.get('duration_seconds', 0)}s"
            )
            if row.get("trace_url"):
                st.markdown(f"[Open Trace]({row['trace_url']})")
