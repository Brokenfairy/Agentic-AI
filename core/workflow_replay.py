"""Replay and persistence helpers for workflow traces and database runs."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings
from database.db import get_workflow_run, list_workflow_runs


def _slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", (text or "").strip()).strip("_").lower()
    return slug[:40] or "workflow"


def save_trace(state: Any) -> str:
    payload = state.to_dict() if hasattr(state, "to_dict") else dict(state)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = settings.TRACES_DIR / f"{ts}_{_slugify(payload.get('original_query', 'workflow'))}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(path)


def load_trace(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def list_traces(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    paths = sorted(settings.TRACES_DIR.glob("*.json"), reverse=True)
    limit = limit or settings.TRACE_HISTORY_LIMIT
    traces: List[Dict[str, Any]] = []
    for path in paths[:limit]:
        try:
            payload = load_trace(path)
        except Exception:
            continue
        traces.append(
            {
                "path": str(path),
                "query": payload.get("original_query", ""),
                "status": payload.get("workflow_status", "unknown"),
                "selected_skills": payload.get("selected_skills", []),
                "duration": payload.get("total_duration_seconds", 0),
                "created_at": path.stem.split("_")[0],
                "source": "trace",
            }
        )
    return traces


def list_replayables(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    limit = limit or settings.TRACE_HISTORY_LIMIT
    items = list_traces(limit=limit)
    for row in list_workflow_runs(limit=limit):
        items.append(
            {
                "path": str(row.get("id")),
                "query": row.get("query", ""),
                "status": row.get("status", "unknown"),
                "selected_skills": json.loads(row.get("selected_skills", "[]") or "[]"),
                "duration": row.get("duration_seconds", 0),
                "created_at": row.get("created_at", ""),
                "source": "database",
            }
        )
    items.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return items[:limit]


def replay_trace(path: str | Path, source: str = "trace") -> Dict[str, Any]:
    if source == "database":
        row = get_workflow_run(int(path))
        if not row:
            return {}
        state_obj = row.get("state_obj") or {}
        if state_obj:
            return state_obj
        return {
            "db_run_id": row.get("id"),
            "original_query": row.get("query", ""),
            "workflow_status": row.get("status", ""),
            "total_duration_seconds": row.get("duration_seconds", 0.0),
            "selected_skills": json.loads(row.get("selected_skills", "[]") or "[]"),
            "aggregated_results": json.loads(row.get("extracted_results", "{}") or "{}"),
            "workflow_events": json.loads(row.get("execution_trace", "[]") or "[]"),
            "summary_markdown": row.get("workflow_summary", ""),
            "export_paths": json.loads(row.get("export_paths", "{}") or "{}"),
        }
    return load_trace(path)
