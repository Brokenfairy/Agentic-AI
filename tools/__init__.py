"""Tool registration primitives for SkillFlow AI."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {}
TOOL_METADATA: Dict[str, Dict[str, Any]] = {}


def register_tool(
    name: str,
    *,
    description: str = "",
    supported_tasks: Optional[List[str]] = None,
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None,
):
    """Decorator to register a tool callable plus metadata."""

    def _wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
        TOOL_REGISTRY[name] = fn
        TOOL_METADATA[name] = {
            "name": name,
            "description": description,
            "supported_tasks": list(supported_tasks or []),
            "input_schema": input_schema or {},
            "output_schema": output_schema or {},
            "callable_name": fn.__name__,
            "module": fn.__module__,
        }
        setattr(fn, "_tool_metadata", TOOL_METADATA[name])
        return fn

    return _wrap
