"""Heuristic query parser used by planning and fallback orchestration."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from config import settings


FIELD_SYNONYMS: Dict[str, List[str]] = {
    "price": ["price", "cost", "amount", "pricing", "mrp", "rs", "rupees", "usd", "$"],
    "rating": ["rating", "ratings", "review", "reviews", "stars", "score"],
    "availability": ["availability", "available", "stock", "in stock", "sold out"],
    "specs": ["specs", "specifications", "ram", "memory", "processor", "cpu", "storage", "battery"],
    "location": ["location", "address", "nearby", "store", "branch", "city"],
    "discount": ["discount", "offer", "off"],
    "warranty": ["warranty", "guarantee"],
    "delivery_estimate": ["delivery", "shipping", "arrival", "eta"],
    "seller_trust": ["seller", "trusted", "verified"],
    "best_deal": ["best deal", "best", "lowest", "cheapest"],
    "availability_confidence": ["confidence", "certainty"],
}

INSTRUCTION_PATTERNS = [
    r"\b(?:and\s+)?(?:extract|get|return|fetch|pull|grab|compare|rank)\b.*",
    r"\bfind\s+(?:me\s+)?(?:the\s+)?(?:top\s+\d+\s+)?(?:urls?|results?|links?)?\s*(?:for|of|on)?\s*",
    r"\bshow\s+(?:me\s+)?(?:the\s+)?(?:top\s+\d+\s+)?(?:urls?|results?|links?)?\s*(?:for|of|on)?\s*",
    r"\blist\s+(?:me\s+)?(?:the\s+)?(?:top\s+\d+\s+)?(?:urls?|results?|links?)?\s*(?:for|of|on)?\s*",
]


def _detect_limit(query: str) -> int:
    match = re.search(r"\b(?:top|first|best)\s+(\d{1,2})\b", query, flags=re.IGNORECASE)
    if match:
        return max(1, min(int(match.group(1)), 20))
    match = re.search(r"\b(\d{1,2})\s+(?:urls?|results?|links?)\b", query, flags=re.IGNORECASE)
    if match:
        return max(1, min(int(match.group(1)), 20))
    return settings.DEFAULT_URL_LIMIT


def _detect_fields(query: str) -> List[str]:
    lowered = query.lower()
    found: List[str] = []
    for field, terms in FIELD_SYNONYMS.items():
        for term in terms:
            if " " in term:
                hit = term.lower() in lowered
            elif len(term) <= 2 or not term.isalpha():
                hit = term.lower() in lowered
            else:
                hit = re.search(rf"\b{re.escape(term.lower())}\b", lowered) is not None
            if hit:
                found.append(field)
                break
    return found


def _clean_search_query(query: str) -> str:
    cleaned = query.strip()
    for pattern in INSTRUCTION_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;:-")
    return cleaned or query.strip()


def parse_query(query: str) -> Dict[str, Any]:
    raw = (query or "").strip()
    if not raw:
        return {
            "search_query": "",
            "requested_fields": [],
            "limit": settings.DEFAULT_URL_LIMIT,
            "raw": "",
            "parser": "heuristic",
        }
    return {
        "search_query": _clean_search_query(raw),
        "requested_fields": _detect_fields(raw),
        "limit": _detect_limit(raw),
        "raw": raw,
        "parser": "heuristic",
    }
