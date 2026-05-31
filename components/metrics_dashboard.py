"""Trace-derived metrics dashboard."""

from __future__ import annotations

from statistics import mean
from typing import List

import streamlit as st

from core.workflow_replay import list_traces, load_trace


def render_metrics_dashboard() -> None:
    traces = list_traces()
    if not traces:
        st.info("No workflow traces yet.")
        return

    payloads = [load_trace(item["path"]) for item in traces]
    durations: List[float] = [float(item.get("total_duration_seconds") or 0.0) for item in payloads]
    fallback_runs = sum(1 for item in payloads if item.get("fallback_used"))
    failed_runs = sum(1 for item in payloads if item.get("workflow_status") == "failed")
    avg_urls = mean(len(item.get("scraped_urls") or []) for item in payloads)
    success_rate = mean(
        1.0 if item.get("workflow_status") == "completed" else 0.0
        for item in payloads
    )

    selected_counts = {}
    for item in payloads:
        for skill in item.get("selected_skills") or []:
            selected_counts[skill] = selected_counts.get(skill, 0) + 1
    most_selected = max(selected_counts, key=selected_counts.get) if selected_counts else "-"

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Runs", len(payloads))
    c2.metric("Avg Time", f"{mean(durations):.2f}s")
    c3.metric("Success Rate", f"{success_rate * 100:.0f}%")
    c1.metric("Fallback Usage", f"{(fallback_runs / len(payloads)) * 100:.0f}%")
    c2.metric("Failed Workflows", failed_runs)
    c3.metric("Avg URLs", f"{avg_urls:.1f}")
    st.caption(f"Most selected skill: {most_selected}")
