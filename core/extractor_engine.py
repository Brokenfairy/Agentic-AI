"""Heuristic and semantic extraction engine."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from config import settings
from core.failure_simulator import maybe_malformed_output, maybe_raise
from schemas import SemanticExtractionResult


MOCK_VALUES: Dict[str, Any] = {
    "price": "Rs. 74,999",
    "rating": "4.4/5",
    "availability": "In Stock",
    "specs": {"ram": "8 GB", "storage": "128 GB", "processor": "A16 Bionic"},
    "location": "Bangalore, Karnataka, India",
    "best_deal": "Competitive value offer",
    "delivery_estimate": "2-4 business days",
    "seller_trust": "High",
    "warranty": "1 year manufacturer warranty",
    "discount": "8%",
    "availability_confidence": "Medium",
}


_PRICE_PATTERN = re.compile(
    r"(?P<currency>Rs\.?|INR|\$|USD|EUR|GBP)\s?(?P<amount>\d{1,3}(?:[,\s]\d{2,3})*(?:\.\d{1,2})?)",
    flags=re.IGNORECASE,
)
_RATING_PATTERN = re.compile(r"(?P<score>\d(?:\.\d)?)\s*(?:/|out of)\s*(?P<scale>5|10)", flags=re.IGNORECASE)
_STOCK_PATTERNS = [
    (r"\bout of stock\b", "Out of Stock", 0.9),
    (r"\bsold out\b", "Out of Stock", 0.9),
    (r"\bin stock\b", "In Stock", 0.9),
    (r"\bavailable now\b", "In Stock", 0.8),
    (r"\bpre[- ]?order\b", "Preorder", 0.8),
]
_LOCATION_PATTERN = re.compile(r"\b(?:address|located at)[:\s]+([A-Z][^\n]{6,120})", flags=re.IGNORECASE)


def _extract_price(text: str, page_meta: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], float]:
    meta = (page_meta or {}).get("metadata") or {}
    amount = meta.get("product:price:amount")
    currency = meta.get("product:price:currency") or "INR"
    if amount:
        return f"{currency} {amount}", 0.95
    match = _PRICE_PATTERN.search(text or "")
    if not match:
        return None, 0.0
    return f"{match.group('currency')} {match.group('amount')}", 0.8


def _extract_rating(text: str, page_meta: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], float]:
    match = _RATING_PATTERN.search(text or "")
    if not match:
        return None, 0.0
    return f"{match.group('score')}/{match.group('scale')}", 0.82


def _extract_availability(text: str, page_meta: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], float]:
    lowered = (text or "").lower()
    for pattern, value, confidence in _STOCK_PATTERNS:
        if re.search(pattern, lowered):
            return value, confidence
    return None, 0.0


def _extract_specs(text: str, page_meta: Optional[Dict[str, Any]] = None) -> Tuple[Optional[Dict[str, str]], float]:
    if not text:
        return None, 0.0
    found: Dict[str, str] = {}
    ram = re.search(r"(\d{1,3})\s*gb\s*(?:ram|memory)", text, flags=re.IGNORECASE)
    storage = re.search(r"(\d{2,4})\s*(gb|tb)\s*(?:storage|ssd|hdd)?", text, flags=re.IGNORECASE)
    processor = re.search(
        r"(intel\s+core\s+i[3579][\w-]*|amd\s+ryzen\s+\w+|apple\s+[am]\d[\w ]*)",
        text,
        flags=re.IGNORECASE,
    )
    battery = re.search(r"(\d{3,5})\s*mah", text, flags=re.IGNORECASE)
    if ram:
        found["ram"] = f"{ram.group(1)} GB"
    if storage:
        found["storage"] = f"{storage.group(1)} {storage.group(2).upper()}"
    if processor:
        found["processor"] = processor.group(1).strip().title()
    if battery:
        found["battery"] = f"{battery.group(1)} mAh"
    return (found, 0.72) if found else (None, 0.0)


def _extract_location(text: str, page_meta: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], float]:
    match = _LOCATION_PATTERN.search(text or "")
    if not match:
        return None, 0.0
    return match.group(1).strip(" ,.;:-"), 0.7


def _extract_discount(text: str, page_meta: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], float]:
    match = re.search(r"(\d{1,2})\s*%\s*(?:off|discount)", text or "", flags=re.IGNORECASE)
    if not match:
        return None, 0.0
    return f"{match.group(1)}%", 0.7


def _extract_warranty(text: str, page_meta: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], float]:
    match = re.search(r"(\d+\s*(?:year|month)[^\n,.]{0,30}warranty)", text or "", flags=re.IGNORECASE)
    if not match:
        return None, 0.0
    return match.group(1).strip(), 0.68


def _extract_delivery_estimate(text: str, page_meta: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], float]:
    match = re.search(r"(delivery[^.:\n]{0,60}(?:day|days|week|weeks))", text or "", flags=re.IGNORECASE)
    if not match:
        return None, 0.0
    return match.group(1).strip(), 0.65


def _extract_seller_trust(text: str, page_meta: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], float]:
    lowered = (text or "").lower()
    if "verified seller" in lowered or "assured" in lowered:
        return "High", 0.7
    if "seller" in lowered:
        return "Medium", 0.45
    return None, 0.0


def _extract_best_deal(text: str, page_meta: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], float]:
    if "best deal" in (text or "").lower():
        return "Explicitly marked as best deal", 0.6
    return None, 0.0


def _extract_availability_confidence(text: str, page_meta: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], float]:
    availability, availability_score = _extract_availability(text, page_meta=page_meta)
    if not availability:
        return None, 0.0
    if availability_score >= 0.85:
        return "High", 0.7
    return "Medium", 0.5


FIELD_EXTRACTORS = {
    "price": _extract_price,
    "rating": _extract_rating,
    "availability": _extract_availability,
    "specs": _extract_specs,
    "location": _extract_location,
    "discount": _extract_discount,
    "warranty": _extract_warranty,
    "delivery_estimate": _extract_delivery_estimate,
    "seller_trust": _extract_seller_trust,
    "best_deal": _extract_best_deal,
    "availability_confidence": _extract_availability_confidence,
}


def _extract_heuristic(
    text: str,
    requested_fields: List[str],
    *,
    page_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    confidences: List[float] = []
    for field in requested_fields:
        extractor = FIELD_EXTRACTORS.get(field)
        if extractor is None:
            fields[field] = None
            confidences.append(0.0)
            continue
        try:
            value, confidence = extractor(text, page_meta=page_meta)
        except Exception:
            value, confidence = None, 0.0
        fields[field] = value
        confidences.append(confidence)
    score = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    return {
        "fields": fields,
        "confidence_score": score,
        "method": "heuristic",
        "fallback_used": False,
    }


def _parse_semantic_output(parsed: Dict[str, Any], requested_fields: List[str]) -> Dict[str, Any]:
    model = SemanticExtractionResult(**parsed)
    payload = model.model_dump() if hasattr(model, "model_dump") else model.dict()
    return {
        field: payload.get(field)
        for field in requested_fields
        if payload.get(field) not in (None, "", [], {})
    }


def _gemini_fill(
    text: str,
    requested_fields: List[str],
    *,
    page_meta: Optional[Dict[str, Any]] = None,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    if not requested_fields or not settings.has_google():
        return {}
    try:
        maybe_raise("gemini")
        import google.generativeai as genai
    except Exception:
        return {}

    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(model_name or settings.DEFAULT_MODEL)
        prompt = (
            "You are a semantic extraction engine.\n"
            "Extract the requested fields from the webpage content and return JSON only.\n"
            "Supported fields include price, rating, availability, specs, location, best_deal, "
            "delivery_estimate, seller_trust, warranty, discount, availability_confidence.\n"
            "Use null for missing values and do not invent unsupported facts.\n"
            f"Requested fields: {requested_fields}\n"
            f"Title: {(page_meta or {}).get('title', '')}\n"
            f"Metadata: {json.dumps((page_meta or {}).get('metadata') or {}, ensure_ascii=True)}\n"
            f"Content:\n{(text or '')[:9000]}"
        )
        response = model.generate_content(prompt)
        content = getattr(response, "text", "") or ""
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z]*\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return {}
        return _parse_semantic_output(maybe_malformed_output(parsed), requested_fields)
    except Exception:
        return {}


def extract_fields(
    text: str,
    requested_fields: List[str],
    *,
    page_meta: Optional[Dict[str, Any]] = None,
    allow_fallback: bool = True,
    use_llm: bool = True,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        maybe_raise("extraction")
    except Exception:
        if allow_fallback:
            fields = {field: MOCK_VALUES.get(field) for field in requested_fields}
            return {
                "fields": fields,
                "fallback_used": True,
                "confidence_score": 0.25,
                "method": "simulated_failure_fallback",
                "semantic_enabled": False,
                "timing_ms": round((time.perf_counter() - start) * 1000, 2),
            }
        raise
    requested_fields = list(requested_fields or [])
    heuristic = _extract_heuristic(text, requested_fields, page_meta=page_meta)
    missing = [
        field
        for field, value in (heuristic.get("fields") or {}).items()
        if value in (None, "", [], {})
    ]

    gemini_values = _gemini_fill(
        text,
        missing,
        page_meta=page_meta,
        model_name=model_name,
    ) if use_llm and missing else {}

    fields = dict(heuristic["fields"])
    fallback_used = False
    confidence_score = heuristic["confidence_score"]
    method = "heuristic"

    if gemini_values:
        method = "semantic_gemini"
        for key, value in gemini_values.items():
            fields[key] = value
        filled_count = len(gemini_values)
        confidence_score = round(min(0.96, confidence_score + (0.1 * filled_count)), 2)

    if allow_fallback:
        for field in requested_fields:
            if fields.get(field) in (None, "", [], {}) and field in MOCK_VALUES:
                fields[field] = MOCK_VALUES[field]
                fallback_used = True
        if fallback_used:
            method = "fallback" if method == "heuristic" else method
            confidence_score = round(min(confidence_score, 0.58), 2)

    return {
        "fields": fields,
        "fallback_used": fallback_used,
        "confidence_score": confidence_score,
        "method": method,
        "semantic_enabled": bool(use_llm and settings.has_google()),
        "timing_ms": round((time.perf_counter() - start) * 1000, 2),
    }
