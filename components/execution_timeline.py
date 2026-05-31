"""Execution timeline renderer."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import streamlit as st


def render_execution_timeline(state: Dict[str, Any]) -> None:
    rows: List[Dict[str, Any]] = []
    execution_times = state.get("execution_times") or {}
    completed = set(state.get("completed_nodes") or [])
    failed = set(state.get("failed_nodes") or [])

    ordered_names = list(execution_times.keys())
    if not ordered_names:
        st.info("No execution data yet.")
        return

    for name in ordered_names:
        rows.append(
            {
                "Stage": name,
                "Status": "failed" if name in failed else "completed" if name in completed else "running",
                "Duration (s)": execution_times.get(name, 0.0),
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
