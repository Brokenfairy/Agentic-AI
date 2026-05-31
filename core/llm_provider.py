"""Provider-agnostic LLM builder."""

from __future__ import annotations

from typing import Any, Dict, Optional

from config import settings


def build_llm(model_name: Optional[str] = None) -> Optional[Any]:
    """Build the configured chat model.

    Returns ``None`` when the Gemini key or package is unavailable so the
    rest of the system can continue in heuristic mode.
    """
    if not settings.has_google():
        return None

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except Exception:
        return None

    try:
        return ChatGoogleGenerativeAI(
            model=model_name or settings.DEFAULT_MODEL,
            temperature=0.1,
            google_api_key=settings.GOOGLE_API_KEY,
            convert_system_message_to_human=True,
        )
    except Exception:
        return None


def provider_status() -> Dict[str, Any]:
    llm = build_llm()
    return {
        "provider": "gemini",
        "model": settings.DEFAULT_MODEL,
        "available": llm is not None,
        "has_key": settings.has_google(),
        "heuristic_mode": llm is None,
    }
