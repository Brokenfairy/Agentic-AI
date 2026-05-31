"""Database row models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class WorkflowRunRecord:
    id: Optional[int]
    trace_id: str
    query: str
    status: str
    duration_seconds: float
    summary_markdown: str
    created_at: str
