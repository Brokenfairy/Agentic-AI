"""Shared Pydantic schemas for SkillFlow AI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, ConfigDict, Field
except Exception:  # pragma: no cover
    BaseModel = object  # type: ignore
    ConfigDict = dict  # type: ignore
    Field = lambda default=None, **_: default  # type: ignore


class SemanticExtractionResult(BaseModel):  # type: ignore[misc]
    model_config = ConfigDict(extra="allow")

    price: Optional[str] = None
    rating: Optional[str] = None
    availability: Optional[str] = None
    location: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    best_deal: Optional[str] = None
    delivery_estimate: Optional[str] = None
    seller_trust: Optional[str] = None
    warranty: Optional[str] = None
    discount: Optional[str] = None
    availability_confidence: Optional[str] = None


class ExecutionPlanSchema(BaseModel):  # type: ignore[misc]
    model_config = ConfigDict(extra="allow")

    goal: str = ""
    steps: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)
    template: Optional[str] = None


class WorkflowSummary(BaseModel):  # type: ignore[misc]
    model_config = ConfigDict(extra="allow")

    query: str = ""
    search_query: str = ""
    requested_fields: List[str] = Field(default_factory=list)
    selected_skills: List[str] = Field(default_factory=list)
    skipped_skills: List[str] = Field(default_factory=list)
    total_urls: int = 0
    success_count: int = 0
    fallback_count: int = 0
    failed_count: int = 0
    total_duration_seconds: float = 0.0
    excel_path: Optional[str] = None
    trace_id: str = ""
    trace_url: Optional[str] = None
    workflow_status: str = "idle"
    supervisor_backend: str = "heuristic"
    provider_name: str = "heuristic"
    provider_model: str = ""
    artifacts_generated: List[str] = Field(default_factory=list)
    plan_goal: str = ""
    retry_count: int = 0
    top_domains: List[str] = Field(default_factory=list)
