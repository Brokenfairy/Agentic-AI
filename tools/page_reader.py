"""
Page reader — fetch HTML and return cleaned visible text.

Strategy:
    1. ``requests`` + BeautifulSoup (fast path).
    2. Playwright (sync API) as a JS-rendered fallback.

Both paths are wrapped in defensive try/except blocks. The function
always returns a dict so callers can branch on ``status``:

    {
        "url": "...",
        "title": "...",
        "content": "...",
        "metadata": {...},
        "status": "success" | "failed",
        "method": "requests" | "playwright" | "",
        "error": "",
    }
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from config import settings
from core.failure_simulator import maybe_raise
from tools import register_tool


# Reasonable default UA so most sites don't 403 us immediately.
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# If the requests-based body is shorter than this many chars after
# cleaning, we assume the page needs JS and try Playwright.
_MIN_USEFUL_LENGTH = 400


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
def _clean_visible_text(html: str) -> Dict[str, Any]:
    """Strip scripts/styles and return title + visible text + a bit of meta."""
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        # Fall back to a brutally simple cleanup if bs4 is missing.
        return {
            "title": "",
            "content": _strip_tags_naive(html),
            "metadata": {},
        }

    # lxml is faster but optional; fall back to the stdlib parser if absent.
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # Drop noisy nodes.
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""

    # Capture a few useful meta tags for the extractor.
    metadata: Dict[str, str] = {}
    for meta in soup.find_all("meta"):
        name = (meta.get("name") or meta.get("property") or "").lower()
        content = meta.get("content") or ""
        if name and content and name in {
            "description", "og:title", "og:description",
            "og:site_name", "twitter:title", "twitter:description",
            "product:price:amount", "product:price:currency",
        }:
            metadata[name] = content.strip()

    # Visible text — collapse whitespace.
    text = soup.get_text(separator=" ", strip=True)
    # Cap to keep downstream prompts/regex cheap.
    if len(text) > 60_000:
        text = text[:60_000]

    return {"title": title, "content": text, "metadata": metadata}


def _strip_tags_naive(html: str) -> str:
    """Last-resort tag stripper for when bs4 is unavailable."""
    import re

    no_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", no_scripts)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Fetch paths
# ---------------------------------------------------------------------------
def _fetch_with_requests(url: str, timeout: int) -> Dict[str, Any]:
    """Fast path. Returns a result dict; raises nothing."""
    try:
        import requests  # type: ignore
    except ImportError:
        return {"ok": False, "error": "requests not installed", "html": ""}

    try:
        resp = requests.get(url, headers=_DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
    except Exception as exc:
        return {"ok": False, "error": f"requests error: {exc}", "html": ""}

    if resp.status_code >= 400:
        return {"ok": False, "error": f"HTTP {resp.status_code}", "html": resp.text or ""}

    return {"ok": True, "error": "", "html": resp.text or ""}


def _fetch_with_playwright(url: str, timeout: int) -> Dict[str, Any]:
    """Slow path. Imports lazily and tolerates missing browsers."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        return {"ok": False, "error": "playwright not installed", "html": ""}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                ctx = browser.new_context(user_agent=_DEFAULT_HEADERS["User-Agent"])
                page = ctx.new_page()
                page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
                # Best-effort settle wait without blocking forever.
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                html = page.content()
                return {"ok": True, "error": "", "html": html or ""}
            finally:
                browser.close()
    except Exception as exc:
        # Most common: "Executable doesn't exist" -> user hasn't run
        # `playwright install`. We treat that as a soft failure.
        return {"ok": False, "error": f"playwright error: {exc}", "html": ""}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
@register_tool(
    "page_reader",
    description="Fetch webpage HTML, clean visible text, and expose metadata for extraction agents.",
    supported_tasks=["read_page", "extract_content", "scrape_page"],
    input_schema={"url": "str", "timeout": "int"},
    output_schema={"status": "str", "title": "str", "content": "str", "metadata": "dict", "error": "str"},
)
def read_page(url: str, timeout: Optional[int] = None) -> Dict[str, Any]:
    """Fetch a URL and return cleaned visible text + metadata.

    Always returns a dict; never raises. Inspect ``status`` for branching.
    """
    timeout = int(timeout or settings.PAGE_READ_TIMEOUT)
    if not url:
        return {
            "url": url, "title": "", "content": "", "metadata": {},
            "status": "failed", "method": "", "error": "empty url",
        }

    try:
        maybe_raise("page_read")
    except Exception as exc:
        return {
            "url": url,
            "title": "",
            "content": "",
            "metadata": {},
            "status": "failed",
            "method": "",
            "error": str(exc),
        }

    # 1) requests
    fast = _fetch_with_requests(url, timeout=timeout)
    if fast["ok"]:
        cleaned = _clean_visible_text(fast["html"])
        if len(cleaned["content"]) >= _MIN_USEFUL_LENGTH:
            return {
                "url": url,
                "title": cleaned["title"],
                "content": cleaned["content"],
                "metadata": cleaned["metadata"],
                "status": "success",
                "method": "requests",
                "error": "",
            }
        # Got a page but it's tiny / JS-shell. Try Playwright.
        fast_error = "page too short, retrying with playwright"
    else:
        fast_error = fast["error"]

    # 2) Playwright fallback
    slow = _fetch_with_playwright(url, timeout=timeout)
    if slow["ok"]:
        cleaned = _clean_visible_text(slow["html"])
        if cleaned["content"]:
            return {
                "url": url,
                "title": cleaned["title"],
                "content": cleaned["content"],
                "metadata": cleaned["metadata"],
                "status": "success",
                "method": "playwright",
                "error": "",
            }
        slow_error = "playwright produced empty content"
    else:
        slow_error = slow["error"]

    return {
        "url": url,
        "title": "",
        "content": "",
        "metadata": {},
        "status": "failed",
        "method": "",
        "error": f"requests: {fast_error}; playwright: {slow_error}",
    }
