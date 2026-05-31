"""Enterprise-style logger for SkillFlow AI."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from config import settings

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init()
except Exception:  # pragma: no cover
    Fore = Style = None  # type: ignore


_LOGGER_NAME = "skillflow"


def _build_base_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


_base_logger = _build_base_logger()


def _get_langfuse_client():
    if not settings.has_langfuse():
        return None
    try:
        from langfuse import Langfuse  # type: ignore

        return Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    except Exception as exc:  # pragma: no cover
        _base_logger.warning("Langfuse client could not be initialised: %s", exc)
        return None


_langfuse = _get_langfuse_client()


class SkillFlowLogger:
    """Logger that mirrors workflow events, supports structured logs, and tags correlation ids."""

    _STDLIB_LEVEL = {
        "INFO": "info",
        "WARNING": "warning",
        "ERROR": "error",
        "DEBUG": "debug",
        "SUCCESS": "info",
    }
    _COLOR = {
        "INFO": getattr(Fore, "CYAN", "") if Fore else "",
        "WARNING": getattr(Fore, "YELLOW", "") if Fore else "",
        "ERROR": getattr(Fore, "RED", "") if Fore else "",
        "DEBUG": getattr(Fore, "MAGENTA", "") if Fore else "",
        "SUCCESS": getattr(Fore, "GREEN", "") if Fore else "",
    }
    _RESET = getattr(Style, "RESET_ALL", "") if Style else ""

    def __init__(
        self,
        state: Optional[object] = None,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.state = state
        self.on_event = on_event

    @staticmethod
    def _now_iso_utc() -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"

    @staticmethod
    def _now_hhmmss() -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _context(self) -> Dict[str, Any]:
        trace_id = getattr(self.state, "trace_id", "") if self.state else ""
        correlation_id = getattr(self.state, "trace_id", "") if self.state else ""
        workflow_status = getattr(self.state, "workflow_status", "") if self.state else ""
        return {
            "trace_id": trace_id,
            "correlation_id": correlation_id,
            "workflow_status": workflow_status,
        }

    def _format_pretty(self, level: str, message: str, ctx: Dict[str, Any]) -> str:
        color = self._COLOR.get(level, "")
        prefix = f"[trace={ctx.get('trace_id') or '-'}]"
        line = f"{prefix} {message}"
        return f"{color}{line}{self._RESET}" if color else line

    def _emit(self, level: str, message: str) -> None:
        timestamp = self._now_iso_utc()
        ctx = self._context()
        if settings.LOG_FORMAT.lower() == "json":
            text = json.dumps(
                {
                    "timestamp": timestamp,
                    "level": level,
                    "message": message,
                    **ctx,
                },
                default=str,
            )
        else:
            text = self._format_pretty(level, message, ctx)

        record = f"[{self._now_hhmmss()}] [{level}] {message}"
        py_method = self._STDLIB_LEVEL.get(level, "info")
        getattr(_base_logger, py_method, _base_logger.info)(text)

        if self.state is not None and hasattr(self.state, "logs"):
            try:
                self.state.logs.append(record)
            except Exception:
                pass

        if self.on_event is not None:
            try:
                self.on_event(
                    {
                        "kind": "log",
                        "level": level,
                        "message": message,
                        "ts": timestamp,
                        "ts_short": self._now_hhmmss(),
                        **ctx,
                    }
                )
            except Exception:
                pass

        if _langfuse is not None:
            try:
                _langfuse.event(
                    name="skillflow.log",
                    level=level,
                    input={"message": message, "ts": timestamp, **ctx},
                    trace_id=ctx.get("trace_id"),
                )
            except Exception:
                pass

    def info(self, message: str) -> None:
        self._emit("INFO", message)

    def success(self, message: str) -> None:
        self._emit("SUCCESS", message)

    def warning(self, message: str) -> None:
        self._emit("WARNING", message)

    def error(self, message: str) -> None:
        self._emit("ERROR", message)

    def debug(self, message: str) -> None:
        self._emit("DEBUG", message)

    def event(self, kind: str, **payload: Any) -> Dict[str, Any]:
        evt = {
            "kind": kind,
            "ts": self._now_iso_utc(),
            "ts_short": self._now_hhmmss(),
            **self._context(),
            **payload,
        }
        if self.state is not None and hasattr(self.state, "workflow_events"):
            try:
                self.state.workflow_events.append(evt)
            except Exception:
                pass
        if self.on_event is not None:
            try:
                self.on_event(evt)
            except Exception:
                pass
        return evt


def get_logger(
    state: Optional[object] = None,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> SkillFlowLogger:
    return SkillFlowLogger(state=state, on_event=on_event)
