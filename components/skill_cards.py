"""Selected and skipped skill cards."""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def render_skill_cards(state: Dict[str, Any], *, skills_catalog: Dict[str, Dict[str, Any]]) -> None:
    selected = state.get("selected_skills") or []
    skipped = state.get("skipped_skills") or []

    if selected:
        st.markdown("**Selected**")
        for name in selected:
            meta = skills_catalog.get(name) or {}
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption(meta.get("description", ""))
                tools = ", ".join(meta.get("tools") or []) or "No tools declared"
                st.caption(f"Tools: {tools}")
    else:
        st.info("No selected skills yet.")

    if skipped:
        st.markdown("**Skipped**")
        for item in skipped:
            with st.expander(item.get("name", "unknown"), expanded=False):
                st.write(item.get("reason", "No reason recorded."))
