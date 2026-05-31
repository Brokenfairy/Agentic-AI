"""Compare heuristic extraction against Gemini-assisted extraction."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Dict, List, Optional

from config import settings
from core.extractor_engine import extract_fields


def _completeness(fields: Dict[str, Any]) -> float:
    if not fields:
        return 0.0
    filled = sum(1 for value in fields.values() if value not in (None, "", [], {}))
    return round(filled / max(1, len(fields)), 2)


def compare_extraction(
    text: str,
    requested_fields: List[str],
    *,
    page_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    start = perf_counter()
    heuristic = extract_fields(
        text,
        requested_fields,
        page_meta=page_meta,
        allow_fallback=True,
        use_llm=False,
    )
    heuristic_ms = round((perf_counter() - start) * 1000, 2)

    gemini_available = bool(settings.has_google())
    gemini = {
        "fields": {},
        "confidence_score": 0.0,
        "fallback_used": False,
        "method": "unavailable",
        "timing_ms": 0.0,
    }
    gemini_ms = 0.0
    if gemini_available:
        start = perf_counter()
        gemini = extract_fields(
            text,
            requested_fields,
            page_meta=page_meta,
            allow_fallback=True,
            use_llm=True,
            model_name=settings.FALLBACK_GEMINI_MODEL or settings.DEFAULT_MODEL,
        )
        gemini_ms = round((perf_counter() - start) * 1000, 2)

    return {
        "heuristic": {
            "result": heuristic,
            "quality": _completeness(heuristic.get("fields") or {}),
            "timing_ms": heuristic_ms,
        },
        "gemini": {
            "available": gemini_available,
            "result": gemini,
            "quality": _completeness(gemini.get("fields") or {}),
            "timing_ms": gemini_ms,
        },
    }
