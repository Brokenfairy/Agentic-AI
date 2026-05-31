"""Shared workflow state for SkillFlow AI Phase 5."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowState:
    original_query: str = ""

    parsed_query: Dict[str, Any] = field(default_factory=dict)
    provider_name: str = "heuristic"
    provider_model: str = ""
    supervisor_backend: str = "heuristic"
    heuristic_mode: bool = True
    demo_presentation_mode: bool = False

    available_agents: Dict[str, Any] = field(default_factory=dict)
    available_tools: Dict[str, Any] = field(default_factory=dict)
    workflow_templates: List[Dict[str, Any]] = field(default_factory=list)
    marketplace_packs: List[Dict[str, Any]] = field(default_factory=list)

    execution_plan: List[str] = field(default_factory=list)
    plan: Dict[str, Any] = field(default_factory=dict)
    plan_goal: str = ""
    plan_steps: List[str] = field(default_factory=list)
    planning_latency_ms: float = 0.0
    query_category: str = ""
    selected_skills: List[str] = field(default_factory=list)
    skipped_skills: List[Dict[str, str]] = field(default_factory=list)
    supervisor_reasoning: List[str] = field(default_factory=list)
    supervisor_thoughts: List[str] = field(default_factory=list)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)

    collaboration_memory: Dict[str, Any] = field(default_factory=dict)
    collaboration_messages: List[Dict[str, Any]] = field(default_factory=list)
    validation_requests: List[Dict[str, Any]] = field(default_factory=list)

    scraped_urls: List[Dict[str, Any]] = field(default_factory=list)
    page_cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    page_reads: List[Dict[str, Any]] = field(default_factory=list)
    extracted_data: List[Dict[str, Any]] = field(default_factory=list)
    failed_urls: List[Dict[str, Any]] = field(default_factory=list)
    aggregated_results: Dict[str, Any] = field(default_factory=dict)
    comparison_results: Dict[str, Any] = field(default_factory=dict)
    semantic_extraction_enabled: bool = False
    extraction_quality: Dict[str, Any] = field(default_factory=dict)

    export_paths: Dict[str, str] = field(default_factory=dict)
    report_paths: Dict[str, str] = field(default_factory=dict)
    excel_path: Optional[str] = None
    rows_written: int = 0
    replay_trace_path: Optional[str] = None
    cached_data_used: bool = False
    fallback_used: bool = False

    retry_attempts: List[Dict[str, Any]] = field(default_factory=list)
    recovery_actions: List[Dict[str, Any]] = field(default_factory=list)
    checkpoint_paths: List[str] = field(default_factory=list)
    latest_checkpoint_path: Optional[str] = None
    health_score: float = 0.0
    workflow_health: Dict[str, Any] = field(default_factory=dict)
    evaluation_scores: Dict[str, Any] = field(default_factory=dict)

    workflow_status: str = "idle"
    current_node: str = ""
    current_skill: str = ""
    progress_message: str = ""
    progress_percent: float = 0.0
    completed_nodes: List[str] = field(default_factory=list)
    failed_nodes: List[str] = field(default_factory=list)
    execution_times: Dict[str, float] = field(default_factory=dict)
    skill_outputs: Dict[str, Any] = field(default_factory=dict)
    workflow_start_time: Optional[str] = None
    workflow_end_time: Optional[str] = None
    total_duration_seconds: float = 0.0
    artifacts_generated: List[str] = field(default_factory=list)

    trace_url: Optional[str] = None
    trace_path: Optional[str] = None
    summary_markdown: str = ""
    ai_summary: str = ""
    replay_frames: List[Dict[str, Any]] = field(default_factory=list)
    token_usage: Dict[str, Any] = field(default_factory=dict)
    failed_spans: List[str] = field(default_factory=list)
    traceability_chain: List[Dict[str, Any]] = field(default_factory=list)
    prompts_used: List[Dict[str, Any]] = field(default_factory=list)
    skill_docs_used: List[Dict[str, Any]] = field(default_factory=list)
    langfuse_metrics: Dict[str, Any] = field(default_factory=dict)
    simulation_flags: Dict[str, Any] = field(default_factory=dict)

    db_run_id: Optional[int] = None
    persisted: bool = False

    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    workflow_events: List[Dict[str, Any]] = field(default_factory=list)
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def add_error(self, message: str) -> None:
        self.errors.append(message)


def new_state(
    query: str,
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> WorkflowState:
    return WorkflowState(
        original_query=(query or "").strip(),
        user_id=user_id,
        session_id=session_id,
        tags=tags or [],
    )
