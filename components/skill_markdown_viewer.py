"""Render SKILL.md docs for selected skills."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import streamlit as st

from config import settings


def render_skill_markdown_viewer(state: Dict[str, Any]) -> None:
    selected = state.get("selected_skills") or []
    if not selected:
        st.info("Run a workflow to see skill docs.")
        return

    tabs = st.tabs(selected)
    for tab, skill_name in zip(tabs, selected):
        with tab:
            doc_path = settings.SKILLS_DIR / skill_name / "SKILL.md"
            if not doc_path.exists():
                st.info("No SKILL.md found for this skill.")
                continue
            st.markdown(Path(doc_path).read_text(encoding="utf-8"))
