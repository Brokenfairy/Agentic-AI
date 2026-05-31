"""LangGraph wrapper for the Phase 5 workflow."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from core.workflow_executor import run_workflow
from core.workflow_state import WorkflowState


EventCallback = Callable[[Dict[str, Any]], None]


NODE_ORDER = [
    "query_understanding",
    "supervisor",
    "url_scraper",
    "page_reader",
    "parallel_extractors",
    "aggregation",
    "comparison_engine",
    "compare_mode",
    "exports",
]


def build_graph():
    try:
        from langgraph.graph import END, StateGraph
    except Exception:
        return None

    graph = StateGraph(WorkflowState)

    def _passthrough(name: str):
        def _node(state: WorkflowState) -> WorkflowState:
            return state

        _node.__name__ = name
        return _node

    for node in NODE_ORDER:
        graph.add_node(node, _passthrough(node))

    graph.set_entry_point(NODE_ORDER[0])
    for left, right in zip(NODE_ORDER, NODE_ORDER[1:]):
        graph.add_edge(left, right)
    graph.add_edge(NODE_ORDER[-1], END)

    try:
        return graph.compile()
    except Exception:
        return None


def run_graph(query: str, *, on_event: Optional[EventCallback] = None) -> WorkflowState:
    return run_workflow(query, on_event=on_event)
