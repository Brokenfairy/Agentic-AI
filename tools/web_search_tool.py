"""
Web search tool — Tavily primary, DuckDuckGo fallback.

Returns a list of dicts shaped like:

    [
        {"title": "...", "url": "...", "domain": "..."},
        ...
    ]

Design rules
------------
- Tavily is used when an API key is configured.
- If Tavily is unavailable, DuckDuckGo HTML search is used as a real
  fallback (no API key required).
- If both fail, mock results are returned only when ``allow_mock=True``.
- Never raises. The workflow keeps moving even if search is broken.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urlparse

import requests

from config import settings
from core.failure_simulator import maybe_raise
from tools import register_tool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _domain_of(url: str) -> str:
    """Return ``netloc`` for a URL, or empty string on failure."""
    try:
        return urlparse(url).netloc or ""
    except Exception:
        return ""


def _normalize_results(raw_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Pick only the fields we expose downstream and dedupe by URL."""
    seen = set()
    cleaned: List[Dict[str, str]] = []
    for item in raw_results or []:
        url = (item.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        cleaned.append(
            {
                "title": (item.get("title") or "").strip() or url,
                "url": url,
                "domain": _domain_of(url),
            }
        )
    return cleaned


def _duckduckgo_search(search_query: str, limit: int) -> List[Dict[str, str]]:
    """Search DuckDuckGo HTML and extract result links."""
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
        }
        resp = requests.post(url, data={"q": search_query, "kl": "us-en"}, headers=headers, timeout=15)
        resp.raise_for_status()
        html = resp.text

        # DuckDuckGo HTML result links
        links = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        results: List[Dict[str, str]] = []
        seen = set()
        for href, title_raw in links[:limit]:
            # DuckDuckGo wraps external URLs in a redirect
            redirect_match = re.search(r"uddg=([^&]+)", href)
            if redirect_match:
                actual_url = unquote(redirect_match.group(1))
            else:
                actual_url = href

            title = re.sub(r"<[^>]+>", "", title_raw).strip()
            if not actual_url or actual_url in seen:
                continue
            seen.add(actual_url)
            results.append({
                "title": title or actual_url,
                "url": actual_url,
                "domain": _domain_of(actual_url),
            })
        return results
    except Exception:
        return []


def _mock_results(search_query: str, limit: int) -> List[Dict[str, str]]:
    """Deterministic demo results so the UI never feels empty."""
    slug = (search_query or "demo").strip().replace(" ", "-").lower() or "demo"
    samples = [
        ("amazon.in",   f"https://www.amazon.in/s?k={slug}",         f"{search_query} - Amazon.in"),
        ("flipkart.com", f"https://www.flipkart.com/search?q={slug}", f"{search_query} - Flipkart"),
        ("croma.com",    f"https://www.croma.com/search/?q={slug}",   f"{search_query} - Croma"),
        ("reliancedigital.in", f"https://www.reliancedigital.in/search?q={slug}", f"{search_query} - Reliance Digital"),
        ("vijaysales.com", f"https://www.vijaysales.com/search/{slug}", f"{search_query} - Vijay Sales"),
    ]
    out: List[Dict[str, str]] = []
    for domain, url, title in samples[: max(1, limit)]:
        out.append({"title": title, "url": url, "domain": domain})
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
@register_tool(
    "web_search",
    description="Discover candidate URLs for a search query using Tavily or deterministic fallback data.",
    supported_tasks=["discover_urls", "search", "market_research"],
    input_schema={"search_query": "str", "limit": "int", "allow_mock": "bool"},
    output_schema={"results": "list", "source": "str", "error": "str"},
)
def search_web(
    search_query: str,
    limit: int = 5,
    *,
    allow_mock: Optional[bool] = None,
) -> Dict[str, Any]:
    """Run a web search and return ``{"results": [...], "source": "...", "error": "..."}``.

    ``source`` is one of ``"tavily"``, ``"duckduckgo"``, ``"mock"``, or ``"none"`` so the
    caller (and the UI) can show the user where results came from.

    """
    if allow_mock is None:
        allow_mock = False

    search_query = (search_query or "").strip()
    limit = max(1, min(int(limit or 5), 20))

    if not search_query:
        return {"results": [], "source": "none", "error": "empty search_query"}

    # 1) Try Tavily if a key is present
    if settings.has_tavily():
        try:
            maybe_raise("tavily")
            from tavily import TavilyClient  # type: ignore

            client = TavilyClient(api_key=settings.TAVILY_API_KEY)
            raw = client.search(
                query=search_query,
                max_results=limit,
                search_depth="basic",
            )
            results = _normalize_results(raw.get("results") if isinstance(raw, dict) else [])
            if results:
                return {"results": results[:limit], "source": "tavily", "error": ""}
            # Tavily returned 0 hits — fall through to mock if allowed.
        except ImportError:
            error = "tavily-python not installed; run `pip install tavily-python`"
        except Exception as exc:  # network / auth / rate limit
            error = f"Tavily error: {exc}"
        else:
            error = "Tavily returned no results"
    else:
        error = "TAVILY_API_KEY not configured"

    # 2) Try DuckDuckGo real search
    ddg_results = _duckduckgo_search(search_query, limit)
    if ddg_results:
        return {"results": ddg_results[:limit], "source": "duckduckgo", "error": ""}

    # 3) Final mock fallback
    if allow_mock:
        return {
            "results": _mock_results(search_query, limit),
            "source": "mock",
            "error": error,
        }

    return {"results": [], "source": "none", "error": error}


def search_urls(search_query: str, limit: int = 5) -> List[Dict[str, str]]:
    """Convenience wrapper that returns just the list of result dicts."""
    return search_web(search_query, limit=limit).get("results", [])
