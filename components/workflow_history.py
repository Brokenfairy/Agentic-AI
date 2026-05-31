"""Workflow history panel."""

from __future__ import annotations

import json
from typing import Callable, Optional

import streamlit as st

from database.db import list_workflow_runs


def render_workflow_history(on_replay: Optional[Callable[[int], None]] = None) -> None:
    rows = list_workflow_runs(limit=20)
    if not rows:
        st.info("No workflow history yet.")
        return

    for idx, row in enumerate(rows):
        with st.container(border=True):
            st.markdown(f"**{row.get('query', '')}**")
            st.caption(
                f"{row.get('created_at', '')} | status={row.get('status', '')} | "
                f"duration={row.get('duration_seconds', 0)}s | run_id={row.get('id')} | "
                f"health={float(row.get('health_score') or 0.0):.2f}"
            )
            cols = st.columns([1, 1, 1, 4])
            if cols[0].button("Replay", key=f"replay-db-{idx}-{row.get('id')}"):
                if on_replay is not None:
                    on_replay(int(row["id"]))
            if cols[1].button("Summary", key=f"summary-db-{idx}-{row.get('id')}"):
                st.code(row.get("workflow_summary", ""), language="markdown")
            if cols[2].button("Traceability", key=f"traceability-db-{idx}-{row.get('id')}"):
                st.json(row.get("state_obj", {}).get("traceability_chain", []), expanded=False)
