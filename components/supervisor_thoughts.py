"""Supervisor thought process panel."""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def render_supervisor_thoughts(state: Dict[str, Any]) -> None:
    thoughts = state.get("supervisor_thoughts") or []
    if not thoughts:
        st.info("No supervisor thoughts available yet.")
        return
    st.markdown("**Supervisor Thought Process**")
    for idx, thought in enumerate(thoughts, start=1):
        st.markdown(f"{idx}. {thought}")
