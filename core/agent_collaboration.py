"""Shared multi-agent collaboration memory."""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any, Dict, List


class CollaborationBus:
    """Thread-safe memory bus for agent collaboration."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.memory: Dict[str, Any] = {"shared_outputs": {}, "validations": [], "messages": []}

    @staticmethod
    def _timestamp() -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"

    def publish_output(self, agent_name: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            self.memory.setdefault("shared_outputs", {})[agent_name] = payload
            self.memory.setdefault("messages", []).append(
                {
                    "kind": "output",
                    "agent": agent_name,
                    "payload": payload,
                    "ts": self._timestamp(),
                }
            )

    def request_validation(self, from_agent: str, to_agent: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = {
            "kind": "validation_request",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "payload": payload,
            "ts": self._timestamp(),
        }
        with self._lock:
            self.memory.setdefault("validations", []).append(request)
            self.memory.setdefault("messages", []).append(request)
        return request

    def publish_message(self, from_agent: str, to_agent: str, message: str, payload: Dict[str, Any] | None = None) -> None:
        item = {
            "kind": "message",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message": message,
            "payload": payload or {},
            "ts": self._timestamp(),
        }
        with self._lock:
            self.memory.setdefault("messages", []).append(item)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "shared_outputs": dict(self.memory.get("shared_outputs", {})),
                "validations": list(self.memory.get("validations", [])),
                "messages": list(self.memory.get("messages", [])),
            }


def suggest_collaboration(agent_name: str, extracted_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
    requests: List[Dict[str, Any]] = []
    if agent_name == "price_extractor" and extracted_fields.get("price"):
        requests.append(
            {
                "target_agent": "specs_extractor",
                "reason": "Validate that the extracted price belongs to the correct product variant.",
            }
        )
    if agent_name == "rating_extractor" and extracted_fields.get("rating"):
        requests.append(
            {
                "target_agent": "specs_extractor",
                "reason": "Verify the rating maps to the same product entity.",
            }
        )
    return requests
