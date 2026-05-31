"""Analytics dashboard backed by workflow memory."""

from __future__ import annotations

import json
from collections import Counter
from statistics import mean

import streamlit as st

from database.db import list_workflow_runs, workflow_analytics


def render_analytics_dashboard() -> None:
    analytics = workflow_analytics()
    rows = list_workflow_runs(limit=200)
    if not rows:
        st.info("No analytics available yet.")
        return

    export_counter = Counter()
    fallback_counts = 0
    domain_counter = Counter()
    durations = []
    for row in rows:
        durations.append(float(row.get("duration_seconds") or 0.0))
        try:
            extracted = json.loads(row.get("extracted_results", "{}") or "{}")
        except Exception:
            extracted = {}
        for item in (extracted.get("rows") or []):
            if item.get("fallback_used"):
                fallback_counts += 1
            if item.get("domain"):
                domain_counter[item["domain"]] += 1
        try:
            exports = json.loads(row.get("export_paths", "{}") or "{}")
        except Exception:
            exports = {}
        for name, path in exports.items():
            if path:
                export_counter[name] += 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Workflow Success Rate", f"{analytics.get('success_rate', 0.0) * 100:.0f}%")
    c2.metric("Avg Execution Time", f"{analytics.get('avg_duration', 0.0):.2f}s")
    c3.metric("Fallback Usage", fallback_counts)
    c4.metric("Top Domain", (domain_counter.most_common(1)[0][0] if domain_counter else "-"))
    c1.metric("Total Runs", analytics.get("total_runs", 0))
    c2.metric("Most Used Skill", max(analytics.get("most_used_skills", {}) or {"-": 0}, key=(analytics.get("most_used_skills", {}) or {"-": 0}).get))
    c3.metric("Failure Trends", sum(1 for row in rows if row.get("status") == "failed"))
    c4.metric("Retries Triggered", sum(1 for row in rows if "retry" in (row.get("workflow_summary", "") or "").lower()))
    st.caption(f"Export usage: {dict(export_counter)}")
