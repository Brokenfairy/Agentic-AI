"""Dependency graph renderer."""

from __future__ import annotations

from typing import Any, Dict

import graphviz
import streamlit as st


def render_dependency_graph(state: Dict[str, Any]) -> None:
    graph = graphviz.Digraph()
    graph.attr(rankdir="LR", bgcolor="transparent")
    graph.attr("node", shape="box", style="rounded,filled", fillcolor="#111827", fontcolor="white")

    dependencies = state.get("dependency_graph") or {}
    if not dependencies:
        st.info("No dependency graph available yet.")
        return

    for node, deps in dependencies.items():
        graph.node(node, node)
        if not deps:
            continue
        for dep in deps:
            graph.node(dep, dep)
            graph.edge(dep, node, color="#94a3b8")

    st.graphviz_chart(graph, use_container_width=True)
