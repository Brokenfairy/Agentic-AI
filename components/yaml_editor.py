"""Editable YAML viewer for agent configs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from config import settings


def render_yaml_editor(default_file: Optional[str] = None) -> None:
    yaml_files = sorted(settings.AGENTS_DIR.glob("*.yaml"))
    if not yaml_files:
        st.info("No agent YAML files found.")
        return

    labels = [path.name for path in yaml_files]
    default_index = 0
    if default_file and default_file in labels:
        default_index = labels.index(default_file)

    selected = st.selectbox("Agent YAML", labels, index=default_index)
    path = settings.AGENTS_DIR / selected
    key = f"yaml_editor::{selected}"
    if key not in st.session_state:
        st.session_state[key] = path.read_text(encoding="utf-8")

    updated = st.text_area(
        "Edit YAML",
        value=st.session_state[key],
        height=360,
        key=f"text::{selected}",
    )
    st.session_state[key] = updated

    save_col, reload_col = st.columns(2)
    if save_col.button("Save YAML", use_container_width=True):
        Path(path).write_text(updated, encoding="utf-8")
        st.success(f"Saved {selected}")
    if reload_col.button("Reload File", use_container_width=True):
        st.session_state[key] = path.read_text(encoding="utf-8")
        st.rerun()
