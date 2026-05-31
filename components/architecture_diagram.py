"""Architecture overview diagram."""

from __future__ import annotations

import graphviz
import streamlit as st


def render_architecture_diagram() -> None:
    dot = graphviz.Digraph()
    dot.attr(rankdir="LR", bgcolor="transparent")
    dot.attr("node", shape="box", style="rounded,filled", fillcolor="#111827", fontcolor="white")

    nodes = [
        "Streamlit UI",
        "Deep Supervisor",
        "YAML Agents",
        "LangGraph Execution",
        "Tools",
        "Langfuse Tracing",
        "Excel Export",
        "Workflow Replay",
    ]
    for node in nodes:
        dot.node(node, node)

    dot.edge("Streamlit UI", "Deep Supervisor")
    dot.edge("YAML Agents", "Deep Supervisor")
    dot.edge("Deep Supervisor", "LangGraph Execution")
    dot.edge("LangGraph Execution", "Tools")
    dot.edge("LangGraph Execution", "Langfuse Tracing")
    dot.edge("LangGraph Execution", "Excel Export")
    dot.edge("LangGraph Execution", "Workflow Replay")

    st.graphviz_chart(dot, use_container_width=True)
