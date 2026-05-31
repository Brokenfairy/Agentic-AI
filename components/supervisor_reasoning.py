"""Supervisor reasoning panel."""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def render_supervisor_reasoning(state: Dict[str, Any]) -> None:
    reasoning = state.get("supervisor_reasoning") or []
    if not reasoning:
        st.info("No supervisor reasoning available yet.")
        return
    st.markdown("**Supervisor Reasoning**")
    for line in reasoning:
        st.markdown(f"- {line}")
