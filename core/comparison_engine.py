"""Structured comparison logic."""

from __future__ import annotations

from typing import Any, Dict, List


def compare_results(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid_rows = [row for row in rows if row.get("status") != "failed"]
    if not valid_rows:
        return {
            "lowest_price": None,
            "highest_rating": None,
            "best_deal": None,
            "ranked_results": [],
            "price_differences": [],
        }

    def _price_value(row: Dict[str, Any]) -> float:
        raw = str(row.get("price") or "")
        digits = "".join(ch for ch in raw if ch.isdigit() or ch == ".")
        try:
            return float(digits)
        except Exception:
            return float("inf")

    def _rating_value(row: Dict[str, Any]) -> float:
        raw = str(row.get("rating") or "")
        token = raw.split("/")[0].strip()
        try:
            return float(token)
        except Exception:
            return 0.0

    sorted_by_price = sorted(valid_rows, key=_price_value)
    sorted_by_rating = sorted(valid_rows, key=_rating_value, reverse=True)
    baseline = _price_value(sorted_by_price[0])
    price_differences = []
    for row in sorted_by_price:
        price = _price_value(row)
        if price == float("inf"):
            continue
        price_differences.append(
            {
                "url": row.get("url", ""),
                "domain": row.get("domain", ""),
                "difference_from_lowest": round(price - baseline, 2),
            }
        )

    ranked = sorted(
        valid_rows,
        key=lambda row: (_price_value(row), -_rating_value(row)),
    )
    return {
        "lowest_price": sorted_by_price[0] if sorted_by_price else None,
        "highest_rating": sorted_by_rating[0] if sorted_by_rating else None,
        "best_deal": ranked[0] if ranked else None,
        "ranked_results": ranked,
        "price_differences": price_differences,
    }
