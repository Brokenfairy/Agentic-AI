"""Failure simulation hooks for reliability demos."""

from __future__ import annotations

import os
from typing import Any, Dict


_TRUTHY = {"1", "true", "yes", "on", "y"}


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUTHY


def simulation_flags() -> Dict[str, bool]:
    return {
        "tavily_failure": _flag("SIMULATE_TAVILY_FAILURE"),
        "gemini_timeout": _flag("SIMULATE_GEMINI_TIMEOUT"),
        "extraction_failure": _flag("SIMULATE_EXTRACTION_FAILURE"),
        "page_read_failure": _flag("SIMULATE_PAGE_READ_FAILURE"),
        "malformed_output": _flag("SIMULATE_MALFORMED_OUTPUT"),
    }


def maybe_raise(kind: str) -> None:
    flags = simulation_flags()
    if kind == "tavily" and flags["tavily_failure"]:
        raise RuntimeError("Simulated Tavily failure.")
    if kind == "gemini" and flags["gemini_timeout"]:
        raise TimeoutError("Simulated Gemini timeout.")
    if kind == "extraction" and flags["extraction_failure"]:
        raise ValueError("Simulated extraction failure.")
    if kind == "page_read" and flags["page_read_failure"]:
        raise ConnectionError("Simulated page read failure.")


def maybe_malformed_output(payload: Dict[str, Any]) -> Dict[str, Any]:
    if simulation_flags()["malformed_output"]:
        return {"malformed": True, "raw_payload": payload}
    return payload
