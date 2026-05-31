"""Backend workflow service helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from core.workflow_executor import run_workflow
from core.workflow_replay import replay_trace
from database.db import get_workflow_run, list_workflow_runs


def run_workflow_service(query: str, *, enable_compare: bool = True) -> Dict[str, Any]:
    state = run_workflow(query, enable_compare=enable_compare)
    return state.to_dict()


def get_history_service(limit: int = 20) -> List[Dict[str, Any]]:
    return list_workflow_runs(limit=limit)


def replay_workflow_service(run_id: int) -> Dict[str, Any]:
    row = get_workflow_run(run_id)
    if not row:
        return {}
    return replay_trace(str(run_id), source="database")
