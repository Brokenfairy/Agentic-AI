"""Best-effort Langfuse wrapper for SkillFlow AI.

Enhanced with best practices from github.com/langfuse/skills:
- user_id / session_id / tags support
- @observe decorator for automatic function tracing
- Generation tracking for LLM calls
- Sensitive data masking
- Proper flush on exit
"""

from __future__ import annotations

import atexit
import functools
import inspect
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from config import settings

from core.langfuse_integration import (  # noqa: F401
    get_langchain_callback,
    is_enabled,
    mask_sensitive,
    observe,
    observe_generation,
)


# ---------------------------------------------------------------------------
# Re-export integration helpers for backward compatibility
# ---------------------------------------------------------------------------
def _maybe_get_client():
    from core.langfuse_integration import get_client
    return get_client()


_CLIENT = _maybe_get_client()


class LangfuseTracker:
    """Enhanced Langfuse trace tracker with best-practice metadata support."""

    def __init__(
        self,
        state: Optional[object] = None,
        *,
        name: str = "skillflow.workflow",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        self.client = _maybe_get_client()
        self.state = state
        self.trace_id = getattr(state, "trace_id", None) or str(uuid.uuid4())
        self.trace = None
        self._spans: Dict[str, Any] = {}
        self._span_started_at: Dict[str, float] = {}

        if self.client is None:
            return

        metadata = {
            "app": "SkillFlow AI",
            "provider": getattr(state, "provider_name", "heuristic"),
            "model": getattr(state, "provider_model", ""),
        }
        try:
            self.trace = self.client.trace(
                id=self.trace_id,
                name=name,
                user_id=user_id or getattr(state, "user_id", None),
                session_id=session_id or getattr(state, "session_id", None),
                tags=tags or getattr(state, "tags", None) or [],
                input=mask_sensitive({"query": getattr(state, "original_query", "")}),
                metadata=metadata,
            )
        except Exception:
            self.trace = None

    def start_span(
        self,
        name: str,
        *,
        input: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> str:
        span_id = str(uuid.uuid4())
        self._span_started_at[span_id] = time.perf_counter()
        if self.trace is not None:
            try:
                span_input = mask_sensitive(input) if input is not None else {}
                span_kwargs: Dict[str, Any] = {"name": name, "input": span_input}
                if model:
                    span_kwargs["metadata"] = {"model": model}
                self._spans[span_id] = self.trace.span(**span_kwargs)
            except Exception:
                pass
        return span_id

    def end_span(
        self,
        span_id: str,
        *,
        output: Optional[Dict[str, Any]] = None,
        level: str = "DEFAULT",
        status_message: Optional[str] = None,
    ) -> float:
        started = self._span_started_at.pop(span_id, None)
        duration = (time.perf_counter() - started) if started is not None else 0.0
        span = self._spans.pop(span_id, None)
        if span is not None:
            try:
                span.end(
                    output=output or {},
                    level=level,
                    status_message=status_message,
                )
            except Exception:
                try:
                    span.end()
                except Exception:
                    pass
        return duration

    def event(self, name: str, **payload: Any) -> None:
        if self.trace is None:
            return
        try:
            self.trace.event(name=name, input=payload)
        except Exception:
            pass

    def end(self, *, output: Optional[Dict[str, Any]] = None, level: str = "DEFAULT") -> None:
        if self.trace is not None:
            try:
                self.trace.update(output=mask_sensitive(output) if output else {}, level=level)
            except Exception:
                pass
        if self.client is not None:
            try:
                self.client.flush()
            except Exception:
                pass

    @property
    def trace_url(self) -> Optional[str]:
        if self.trace is None:
            return None
        try:
            return self.trace.get_trace_url()
        except Exception:
            host = (settings.LANGFUSE_HOST or "").rstrip("/")
            return f"{host}/trace/{self.trace_id}" if host else None


# ---------------------------------------------------------------------------
# Decorator re-export with tracker-aware context
# ---------------------------------------------------------------------------
def track_workflow_step(step_name: str):
    """Decorator to track a workflow step as a Langfuse span.

    Automatically attaches the span to an active LangfuseTracker.trace
    if one exists in the first argument (state).
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracker: Optional[LangfuseTracker] = None
            # Try to find a tracker from state-like first arg
            if args:
                first = args[0]
                if hasattr(first, "_langfuse_tracker"):
                    tracker = first._langfuse_tracker

            if tracker is None or tracker.trace is None:
                return func(*args, **kwargs)

            span_id = tracker.start_span(step_name)
            try:
                result = func(*args, **kwargs)
                tracker.end_span(span_id, output={"status": "ok"})
                return result
            except Exception as exc:
                tracker.end_span(
                    span_id,
                    output={"error": str(exc)},
                    level="ERROR",
                    status_message=str(exc),
                )
                raise
        return wrapper
    return decorator
