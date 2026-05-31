"""Workflow graph rendering helpers."""

from __future__ import annotations

from typing import Any, Dict, List

import graphviz
import streamlit as st


def _node_color(name: str, state: Dict[str, Any]) -> str:
    if name in (state.get("failed_nodes") or []):
        return "#dc2626"
    if name == state.get("current_node"):
        return "#f59e0b"
    if name in (state.get("completed_nodes") or []):
        return "#16a34a"
    return "#475569"


def build_workflow_dot(state: Dict[str, Any]) -> graphviz.Digraph:
    dot = graphviz.Digraph()
    dot.attr(rankdir="LR", bgcolor="transparent")
    dot.attr("node", shape="box", style="rounded,filled", fillcolor="#0f172a", fontcolor="white")

    plan: List[str] = ["query_understanding", "supervisor"]
    plan.extend(state.get("execution_plan") or [])
    plan.extend(
        name
        for name in ["page_reader", "parallel_extractors", "aggregation", "comparison_engine", "compare_mode", "exports"]
        if name in ((state.get("completed_nodes") or []) + (state.get("failed_nodes") or []) + [state.get("current_node", "")])
    )

    deduped: List[str] = []
    for name in plan:
        if name and name not in deduped:
            deduped.append(name)

    for name in deduped:
        label = name.replace("_", "\n")
        if name == "parallel_extractors":
            label = "parallel\nextractors"
        dot.node(name, label=label, fillcolor=_node_color(name, state))

    for left, right in zip(deduped, deduped[1:]):
        dot.edge(left, right, color="#94a3b8")

    return dot


def render_workflow_graph(state: Dict[str, Any]) -> None:
    st.graphviz_chart(build_workflow_dot(state), use_container_width=True)
