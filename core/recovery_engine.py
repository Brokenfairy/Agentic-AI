"""Retry and recovery helpers."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Tuple

from config import settings


def retry_operation(
    operation: Callable[[], Dict[str, Any]],
    *,
    label: str,
    max_retries: int | None = None,
) -> Tuple[Dict[str, Any], list[Dict[str, Any]]]:
    max_retries = settings.MAX_RETRIES if max_retries is None else max_retries
    attempts: list[Dict[str, Any]] = []
    last_result: Dict[str, Any] = {}

    for attempt in range(max_retries + 1):
        started = time.perf_counter()
        try:
            result = operation()
            last_result = result
            success = result.get("status") == "success" or result.get("ok") is True
            attempts.append(
                {
                    "label": label,
                    "attempt": attempt + 1,
                    "success": success,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    "error": result.get("error", ""),
                }
            )
            if success:
                return result, attempts
        except Exception as exc:
            attempts.append(
                {
                    "label": label,
                    "attempt": attempt + 1,
                    "success": False,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

        if attempt < max_retries:
            time.sleep(settings.RETRY_BASE_DELAY * (2 ** attempt))

    return last_result, attempts


def count_retries(attempts: list[Dict[str, Any]]) -> int:
    return sum(1 for item in attempts if int(item.get("attempt", 1) or 1) > 1)
