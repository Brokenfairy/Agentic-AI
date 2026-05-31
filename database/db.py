"""SQLite persistence and analytics for workflow runs."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional

from config import settings
from core.recovery_engine import count_retries


_EXTRA_COLUMNS = {
    "health_score": "REAL DEFAULT 0",
    "fallback_used": "INTEGER DEFAULT 0",
    "retry_count": "INTEGER DEFAULT 0",
    "query_category": "TEXT DEFAULT ''",
    "trace_path": "TEXT DEFAULT ''",
    "trace_url": "TEXT DEFAULT ''",
    "report_paths": "TEXT DEFAULT '{}'",
    "state_json": "TEXT DEFAULT '{}'",
    "evaluation_scores": "TEXT DEFAULT '{}'",
    "langfuse_metrics": "TEXT DEFAULT '{}'",
}


def _connect() -> sqlite3.Connection:
    Path(settings.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _json_loads(raw: Any, default: Any) -> Any:
    if raw in (None, ""):
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _ensure_columns(conn: sqlite3.Connection) -> None:
    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(workflow_runs)").fetchall()
    }
    for column, ddl in _EXTRA_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE workflow_runs ADD COLUMN {column} {ddl}")


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    row["selected_skills_list"] = _json_loads(row.get("selected_skills"), [])
    row["extracted_results_obj"] = _json_loads(row.get("extracted_results"), {})
    row["execution_trace_obj"] = _json_loads(row.get("execution_trace"), [])
    row["export_paths_obj"] = _json_loads(row.get("export_paths"), {})
    row["report_paths_obj"] = _json_loads(row.get("report_paths"), {})
    row["state_obj"] = _json_loads(row.get("state_json"), {})
    row["evaluation_scores_obj"] = _json_loads(row.get("evaluation_scores"), {})
    row["langfuse_metrics_obj"] = _json_loads(row.get("langfuse_metrics"), {})
    return row


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT,
                query TEXT,
                status TEXT,
                duration_seconds REAL,
                selected_skills TEXT,
                extracted_results TEXT,
                execution_trace TEXT,
                workflow_summary TEXT,
                export_paths TEXT,
                created_at TEXT,
                health_score REAL DEFAULT 0,
                fallback_used INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                query_category TEXT DEFAULT '',
                trace_path TEXT DEFAULT '',
                trace_url TEXT DEFAULT '',
                report_paths TEXT DEFAULT '{}',
                state_json TEXT DEFAULT '{}',
                evaluation_scores TEXT DEFAULT '{}',
                langfuse_metrics TEXT DEFAULT '{}'
            )
            """
        )
        _ensure_columns(conn)


def save_workflow_run(state: Any) -> int:
    init_db()
    payload = state.to_dict() if hasattr(state, "to_dict") else dict(state)
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO workflow_runs (
                trace_id, query, status, duration_seconds, selected_skills,
                extracted_results, execution_trace, workflow_summary, export_paths, created_at,
                health_score, fallback_used, retry_count, query_category, trace_path,
                trace_url, report_paths, state_json, evaluation_scores, langfuse_metrics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("trace_id", ""),
                payload.get("original_query", ""),
                payload.get("workflow_status", ""),
                payload.get("total_duration_seconds", 0.0),
                json.dumps(payload.get("selected_skills", [])),
                json.dumps(payload.get("aggregated_results", {})),
                json.dumps(payload.get("workflow_events", [])),
                payload.get("summary_markdown", ""),
                json.dumps(payload.get("export_paths", {})),
                payload.get("workflow_end_time") or payload.get("workflow_start_time") or "",
                float(payload.get("health_score") or 0.0),
                1 if payload.get("fallback_used") else 0,
                count_retries(payload.get("retry_attempts") or []),
                payload.get("query_category", ""),
                payload.get("trace_path", ""),
                payload.get("trace_url", ""),
                json.dumps(payload.get("report_paths", {})),
                json.dumps(payload),
                json.dumps(payload.get("evaluation_scores", {})),
                json.dumps(payload.get("langfuse_metrics", {})),
            ),
        )
        return int(cur.lastrowid)


def list_workflow_runs(limit: int = 50) -> List[Dict[str, Any]]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM workflow_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_normalize_row(dict(row)) for row in rows]


def get_workflow_run(run_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM workflow_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    return _normalize_row(dict(row)) if row else None


def workflow_analytics() -> Dict[str, Any]:
    rows = list_workflow_runs(limit=500)
    if not rows:
        return {
                "total_runs": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0,
                "most_used_skills": {},
                "avg_confidence": 0.0,
                "fallback_usage_rate": 0.0,
                "avg_health_score": 0.0,
                "top_domains": {},
                "retry_count": 0,
            }

    total_runs = len(rows)
    success_runs = sum(1 for row in rows if row.get("status") == "completed")
    avg_duration = round(mean(float(row.get("duration_seconds") or 0.0) for row in rows), 2)
    skill_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    confidence_values: List[float] = []
    retry_total = 0
    fallback_runs = 0
    health_scores: List[float] = []
    category_counts: Counter[str] = Counter()

    for row in rows:
        for skill in row.get("selected_skills_list", []):
            skill_counts[str(skill)] += 1

        extracted = row.get("extracted_results_obj", {})
        for item in extracted.get("rows") or []:
            if item.get("domain"):
                domain_counts[str(item["domain"])] += 1
            if item.get("confidence_score") not in (None, ""):
                try:
                    confidence_values.append(float(item.get("confidence_score") or 0.0))
                except Exception:
                    pass

        retry_total += int(row.get("retry_count") or 0)
        fallback_runs += 1 if row.get("fallback_used") else 0
        health_scores.append(float(row.get("health_score") or 0.0))
        if row.get("query_category"):
            category_counts[str(row["query_category"])] += 1

    return {
        "total_runs": total_runs,
        "success_rate": round(success_runs / max(1, total_runs), 2),
        "avg_duration": avg_duration,
        "most_used_skills": dict(skill_counts),
        "avg_confidence": round(mean(confidence_values), 2) if confidence_values else 0.0,
        "fallback_usage_rate": round(fallback_runs / max(1, total_runs), 2),
        "avg_health_score": round(mean(health_scores), 2) if health_scores else 0.0,
        "top_domains": dict(domain_counts.most_common(10)),
        "retry_count": retry_total,
        "query_categories": dict(category_counts),
    }


def agent_performance() -> Dict[str, Any]:
    rows = list_workflow_runs(limit=500)
    usage: Counter[str] = Counter()
    durations: Dict[str, List[float]] = {}
    confidence: Dict[str, List[float]] = {}
    failures: Counter[str] = Counter()
    recoveries: Counter[str] = Counter()

    for row in rows:
        state = row.get("state_obj", {})
        for skill in row.get("selected_skills_list", []):
            usage[str(skill)] += 1
            if skill in (state.get("execution_times") or {}):
                durations.setdefault(str(skill), []).append(
                    float((state.get("execution_times") or {}).get(skill) or 0.0)
                )
        for item in state.get("extracted_data") or []:
            for agent in item.get("source_agents") or []:
                confidence.setdefault(str(agent), []).append(float(item.get("confidence_score") or 0.0))
        for node in state.get("failed_nodes") or []:
            failures[str(node)] += 1
        for action in state.get("recovery_actions") or []:
            kind = str(action.get("kind") or "")
            if "retry" in kind:
                recoveries[kind] += 1

    return {
        "usage": dict(usage),
        "avg_execution_time": {
            name: round(mean(values), 2) for name, values in durations.items() if values
        },
        "avg_confidence": {
            name: round(mean(values), 2) for name, values in confidence.items() if values
        },
        "failure_rate": dict(failures),
        "recovery_rate": dict(recoveries),
        "successful_runs": sum(1 for row in rows if row.get("status") == "completed"),
    }


def supervisor_analytics() -> Dict[str, Any]:
    rows = list_workflow_runs(limit=500)
    selected_counts: Counter[str] = Counter()
    skipped_counts: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    planning_latency_values: List[float] = []

    for row in rows:
        state = row.get("state_obj", {})
        for skill in row.get("selected_skills_list", []):
            selected_counts[str(skill)] += 1
        for item in state.get("skipped_skills") or []:
            name = str(item.get("name") or "")
            if name:
                skipped_counts[name] += 1
        if row.get("query_category"):
            categories[str(row["query_category"])] += 1
        latency = state.get("planning_latency_ms")
        if latency not in (None, ""):
            planning_latency_values.append(float(latency))

    return {
        "most_selected_skills": dict(selected_counts.most_common(10)),
        "most_skipped_skills": dict(skipped_counts.most_common(10)),
        "query_categories": dict(categories),
        "planning_latency_ms": round(mean(planning_latency_values), 2) if planning_latency_values else 0.0,
    }


def langfuse_dashboard_data() -> Dict[str, Any]:
    rows = list_workflow_runs(limit=200)
    trace_rows = [row for row in rows if row.get("trace_id")]
    failed_spans = Counter()
    workflow_cost = []
    latency = []
    retry_heavy = []

    for row in trace_rows:
        state = row.get("state_obj", {})
        for span_name in state.get("failed_spans") or []:
            failed_spans[str(span_name)] += 1
        latency.append(float(row.get("duration_seconds") or 0.0))
        token_usage = state.get("token_usage") or {}
        total_tokens = float(token_usage.get("total_tokens") or 0.0)
        workflow_cost.append({"query": row.get("query", ""), "tokens": total_tokens})
        if int(row.get("retry_count") or 0) >= 2:
            retry_heavy.append(
                {
                    "query": row.get("query", ""),
                    "retry_count": int(row.get("retry_count") or 0),
                    "trace_id": row.get("trace_id", ""),
                }
            )

    workflow_cost.sort(key=lambda item: item.get("tokens", 0), reverse=True)
    return {
        "trace_count": len(trace_rows),
        "trace_rows": trace_rows[:25],
        "failed_spans": dict(failed_spans),
        "avg_execution_latency": round(mean(latency), 2) if latency else 0.0,
        "most_expensive_workflows": workflow_cost[:10],
        "retry_heavy_workflows": retry_heavy[:10],
    }


def preload_demo_history() -> None:
    """No-op: demo history preloading is disabled."""
    pass
