"""Langfuse integration helpers following best practices from langfuse/skills.

Provides:
- @observe decorator for automatic function tracing
- Generation tracking for Google GenAI / direct LLM calls
- Sensitive data masking utilities
- LangChain callback handler setup
- Proper trace metadata (user_id, session_id, tags, model)

Usage:
    from core.langfuse_integration import observe, observe_generation, mask_sensitive

    @observe(name="my-function")
    def my_function(query: str):
        return observe_generation(lambda: model.generate(query))
"""

from __future__ import annotations

import atexit
import functools
import inspect
import re
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from config import settings


# ---------------------------------------------------------------------------
# Data masking
# ---------------------------------------------------------------------------
_SENSITIVE_KEYS = re.compile(
    r"(api_key|secret|password|token|auth|credential|private_key)",
    flags=re.IGNORECASE,
)


def mask_sensitive(data: Any) -> Any:
    """Recursively mask sensitive values in dicts/lists."""
    if isinstance(data, dict):
        masked: Dict[str, Any] = {}
        for k, v in data.items():
            if _SENSITIVE_KEYS.search(k):
                masked[k] = "***"
            else:
                masked[k] = mask_sensitive(v)
        return masked
    if isinstance(data, list):
        return [mask_sensitive(v) for v in data]
    if isinstance(data, str) and len(data) > 40:
        # Heuristic: long strings that look like keys
        if data.startswith("sk-") or data.startswith("pk-") or data.startswith("AIza"):
            return data[:8] + "***"
    return data


# ---------------------------------------------------------------------------
# Client helpers
# ---------------------------------------------------------------------------
def _get_langfuse_client():
    """Lazy-init Langfuse client (env vars must be loaded first)."""
    if not settings.has_langfuse():
        return None
    try:
        from langfuse import Langfuse
    except Exception:
        return None
    try:
        return Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except Exception:
        return None


# Lazy singleton
_LANGFUSE_CLIENT: Any = None


def get_client():
    global _LANGFUSE_CLIENT
    if _LANGFUSE_CLIENT is None and settings.has_langfuse():
        _LANGFUSE_CLIENT = _get_langfuse_client()
    return _LANGFUSE_CLIENT


def is_enabled() -> bool:
    return get_client() is not None


# ---------------------------------------------------------------------------
# Flush on exit
# ---------------------------------------------------------------------------
def _flush_langfuse():
    client = get_client()
    if client is not None:
        try:
            client.flush()
        except Exception:
            pass


atexit.register(_flush_langfuse)


# ---------------------------------------------------------------------------
# @observe decorator
# ---------------------------------------------------------------------------
def observe(
    *,
    name: Optional[str] = None,
    capture_input: bool = True,
    capture_output: bool = True,
    mask: bool = True,
):
    """Decorator to trace function execution as a Langfuse span.

    Args:
        name: Observation name (defaults to function name).
        capture_input: Whether to log function arguments.
        capture_output: Whether to log return value.
        mask: Whether to mask sensitive data in inputs/outputs.
    """

    def decorator(func: Callable) -> Callable:
        obs_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            client = get_client()
            if client is None:
                return func(*args, **kwargs)

            # Build input representation
            if capture_input:
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                input_data = dict(bound.arguments)
                if mask:
                    input_data = mask_sensitive(input_data)
            else:
                input_data = {}

            span = None
            started = time.perf_counter()
            try:
                # Use langfuse_context if available (newer SDK)
                try:
                    from langfuse.decorators import langfuse_context, observe as lf_observe

                    @lf_observe(name=obs_name)
                    def _inner():
                        return func(*args, **kwargs)

                    result = _inner()
                except Exception:
                    # Fallback to manual span
                    span = client.span(name=obs_name, input=input_data)
                    result = func(*args, **kwargs)
            except Exception as exc:
                if span is not None:
                    try:
                        span.end(
                            level="ERROR",
                            status_message=str(exc),
                            output={"error": str(exc)} if capture_output else {},
                        )
                    except Exception:
                        pass
                raise
            else:
                duration = time.perf_counter() - started
                if span is not None:
                    output_data = mask_sensitive(result) if (capture_output and mask) else (result if capture_output else {})
                    try:
                        span.end(output=output_data)
                    except Exception:
                        pass
                return result

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Generation tracking
# ---------------------------------------------------------------------------
def observe_generation(
    generate_fn: Callable,
    *,
    name: str = "llm-generation",
    model: Optional[str] = None,
    input_messages: Optional[List[Dict[str, str]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """Wrap an LLM generation call with Langfuse generation tracking.

    Args:
        generate_fn: Callable that returns the LLM response.
        name: Name for the generation observation.
        model: Model name (e.g. "gemini-1.5-pro").
        input_messages: List of message dicts with role/content.
        metadata: Additional metadata to attach.

    Returns:
        Tuple of (response, generation_info) where generation_info contains
        usage stats if available.
    """
    client = get_client()
    if client is None:
        return generate_fn(), None

    start_time = time.perf_counter()
    generation = None
    try:
        generation = client.generation(
            name=name,
            model=model or getattr(settings, "DEFAULT_MODEL", "unknown"),
            input=input_messages or {},
            metadata=mask_sensitive(metadata or {}),
        )
    except Exception:
        pass

    try:
        response = generate_fn()
    except Exception as exc:
        if generation is not None:
            try:
                generation.end(
                    level="ERROR",
                    status_message=str(exc),
                )
            except Exception:
                pass
        raise

    duration = time.perf_counter() - start_time
    usage = _extract_usage(response)

    if generation is not None:
        try:
            output = _extract_output(response)
            generation.end(
                output=output,
                usage=usage,
                metadata={**(metadata or {}), "duration_ms": int(duration * 1000)},
            )
        except Exception:
            pass

    return response, usage


def _extract_usage(response: Any) -> Optional[Dict[str, int]]:
    """Try to extract token usage from common response shapes."""
    # Google GenAI
    if hasattr(response, "usage_metadata"):
        meta = response.usage_metadata
        return {
            "input": getattr(meta, "prompt_token_count", 0),
            "output": getattr(meta, "candidates_token_count", 0),
            "total": getattr(meta, "total_token_count", 0),
        }
    # LangChain
    if hasattr(response, "usage_metadata") and isinstance(response.usage_metadata, dict):
        return {
            "input": response.usage_metadata.get("input_tokens", 0),
            "output": response.usage_metadata.get("output_tokens", 0),
            "total": response.usage_metadata.get("total_tokens", 0),
        }
    # OpenAI-like
    if hasattr(response, "usage"):
        u = response.usage
        return {
            "input": getattr(u, "prompt_tokens", 0),
            "output": getattr(u, "completion_tokens", 0),
            "total": getattr(u, "total_tokens", 0),
        }
    return None


def _extract_output(response: Any) -> Any:
    """Extract text output from common response shapes."""
    if isinstance(response, str):
        return response
    if hasattr(response, "text"):
        return response.text
    if hasattr(response, "content"):
        return response.content
    return str(response)


# ---------------------------------------------------------------------------
# LangChain callback handler
# ---------------------------------------------------------------------------
def get_langchain_callback() -> Optional[Any]:
    """Return a Langfuse callback handler for LangChain if available."""
    if not is_enabled():
        return None
    try:
        from langfuse.callback import CallbackHandler
        return CallbackHandler(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Trace builder helper
# ---------------------------------------------------------------------------
def create_trace(
    *,
    name: str = "skillflow.workflow",
    trace_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    input_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Any], str]:
    """Create a Langfuse trace with best-practice metadata.

    Returns:
        Tuple of (trace_obj, trace_id_str).
    """
    client = get_client()
    tid = trace_id or str(uuid.uuid4())
    if client is None:
        return None, tid

    meta = mask_sensitive(metadata or {})
    meta.setdefault("app", "SkillFlow AI")
    meta.setdefault("version", "1.0.0")

    try:
        trace = client.trace(
            id=tid,
            name=name,
            user_id=user_id,
            session_id=session_id,
            tags=tags or [],
            metadata=meta,
            input=mask_sensitive(input_data) if input_data else {},
        )
        return trace, tid
    except Exception:
        return None, tid
